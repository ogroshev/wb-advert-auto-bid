import argparse
import datetime
import time

import db_facade
import wb_requests
import choosing_bid as cb
import json

import logging
import sys
import pytz
import requests

logger = logging.getLogger('logger')
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)
error_counter = 0


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='WB advert parser', add_help=False)
    parser.add_argument('-u', '--db-user', dest='db_user', help='db user name')
    parser.add_argument('-p', '--db-password',
                        dest='db_password', help='db password')
    parser.add_argument('-d', '--db-name', dest='db_name',
                        help='database name')
    parser.add_argument('-P', '--db-port', dest='db_port',
                        help='database port')
    parser.add_argument('-h', '--db-host', dest='db_host',
                        help='database host')
    return parser.parse_args()


def is_it_time_to_work(adv_company):
    if adv_company['last_scan_ts'] in (None, ''):
        return True

    tz = pytz.timezone('Europe/Moscow')
    msk_now = datetime.datetime.now(tz=tz)
    last_scan_ts = tz.localize(adv_company['last_scan_ts'], is_dst=None)

    sec_to_start = last_scan_ts + datetime.timedelta(
        seconds=adv_company['scan_interval_sec']) - msk_now
    return (last_scan_ts + datetime.timedelta(
            seconds=adv_company['scan_interval_sec'])) < msk_now


def is_target_place_ours(target_place_id, own_company_id):
    logger.info('target_place_id: {}'.format(target_place_id))
    logger.info('own_company_id: {}'.format(own_company_id))
    return target_place_id == own_company_id


def should_we_reduce_bid(target_place_price, own_price):
    return own_price > target_place_price + 1


def search_my_place(adverts_array, my_company_id):
    my_place = 0
    for idx in range(len(adverts_array)):
        if adverts_array[idx]['advertId'] == my_company_id:
            my_place = idx + 1
            break
    return my_place


def get_advert_info(adv_company):
    result_code = 200
    error_str = None
    try:
        ads_search_result = wb_requests.search_catalog_ads(
            adv_company['query'])
        priority_subjects = ads_search_result['prioritySubjects']
        adverts_array = ads_search_result['adverts']
        logger.info('priority_subjects[]: {}'.format(
            priority_subjects))
        placement_response = wb_requests.get_placement(
            adv_company['type'], adv_company['company_id'],
            adv_company['cpm_cookies'], adv_company['x_user_id'])
        if adverts_array is not None:
            logger.info('adverts_array[:3]: {}'.format(
                ads_search_result['adverts'][:3]))
            # logger.info('placement_response: {}'.format(placement_response))
            return (True, adverts_array, priority_subjects, placement_response, result_code, error_str)
        else:
            logger.info('Empty adverts. Json: ', ads_search_result)
            result_code = 1000
            error_str = "search_catalog_ads empty ads_search_result['adverts']"
    except requests.exceptions.HTTPError as e:
        global error_counter
        error_counter += 1
        logger.info('{} Http error: {} skip {} - {}'.format(error_counter, e, adv_company['company_id'], adv_company['name']))
        result_code = e.response.status_code
        error_str = '{}'.format(e)
    return (False, None, None, None, result_code, error_str)


def work_iteration(db):
    adv_companies = db_facade.get_adv_companies(db)
    if len(adv_companies) == 0:
        logger.debug('nothing to do')

    for adv_company in adv_companies:
        # если текущее время больше last_scan_ts + scan_interval_sec,
        #   то работаем с этой компанией
        if is_it_time_to_work(adv_company):
            logger.info('checking company: {}'.format(adv_company['name']))
            if adv_company['query'] in (None, ''):
                logger.info('Company: {}. empty query, skipped'.format(
                    adv_company['name']))
                db_facade.update_last_scan_ts(db, adv_company['company_id'])
                continue

            ok, adverts_array, priority_subjects, placement_response, result_code, error_str = get_advert_info(
                adv_company)

            my_price = None
            my_place = None
            target_price = None
            target_place = None
            decision_str = None
            if ok:
                target_place = adv_company['target_place']
                my_price = placement_response['place'][0]['price']
                my_subject_id = placement_response['place'][0]['subjectId']
                my_company_id = adv_company['company_id']

                if priority_subjects is not None and my_subject_id != priority_subjects[0]:
                    error_str = "priority_subjects[0]: {} not equal placement's subject_id: {}".format(
                        priority_subjects[0], my_subject_id)
                    db_facade.alarm(db, adv_company['company_id'], error_str)
                    logger.warning("Company: {} skipped. Alarm: {}".format(adv_company['company_id'], error_str))
                    db_facade.update_last_scan_ts(db, adv_company['company_id'])
                    continue

                my_place = search_my_place(adverts_array, my_company_id)

                logger.debug('my_price: {} my_place: {} target_place: {} my_subject_id: {}'.format(
                    my_price, my_place, target_place, my_subject_id))

                advert_info = cb.AdvertInfo()
                advert_info.fromAdverts(adverts_array, my_subject_id)
                logger.info('Adverts with my subject_id: {}'.format(
                    advert_info.getPlaciesStr(target_place + 1)))
                decision = cb.calcBestPrice(
                    advert_info, my_place, my_price, target_place)

                if decision.changePriceNeeded:
                    target_price = decision.targetPrice
                    if decision.targetPrice > adv_company['max_bet']:
                        logger.info('targetPrice: {} max_bet: {}. Skip...'.format(
                            target_price, adv_company['max_bet']))
                        decision_str = 'max bet'
                    else:
                        decision_str = 'change bet'
                        placement_response['place'][0]['price'] = decision.targetPrice
                        ok, result_code, error_str = wb_requests.save_advert_campaign(
                            adv_company['type'], adv_company['company_id'], placement_response,
                            adv_company['cpm_cookies'], adv_company['x_user_id'])
                        if ok:
                            logger.info('campaign "{}" saved! New price: {}'.format(
                                adv_company['name'], target_price))
                        else:
                            logger.warn('could not save campaign: {} - {}',
                                        adv_company['company_id'], adv_company['name'])

                else:
                    logger.info('already best price and place')
                    decision_str = 'no changes'

            json_adverts_array_first_five = '{}' if adverts_array is None else json.dumps(adverts_array[:4])
            json_priority_subjects = '{}' if priority_subjects is None else json.dumps(priority_subjects)
            db_facade.log_advert_bid(db, adv_company['company_id'], my_price, my_place,
                                     target_price, target_place, decision_str, result_code,
                                     error_str, json_adverts_array_first_five, json_priority_subjects)
            db_facade.update_last_scan_ts(db, adv_company['company_id'])
        time.sleep(1)


def main():
    logger.info('Service starting...')
    args = parse_arguments()
    db = db_facade.connect(args)

    while True:
        work_iteration(db)
        time.sleep(2)


if __name__ == "__main__":
    main()
