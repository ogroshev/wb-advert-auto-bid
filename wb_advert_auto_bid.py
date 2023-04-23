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
import asyncio

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


def get_catalog_ads_adverts_info(adv_company):
    result_code = 200
    error_str = None

    ads_search_result = wb_requests.search_catalog_ads(
        adv_company['query'])
    if ads_search_result is None:
        logger.info('search_catalog_ads error')
        return (False, None, None, 1000, 'search_catalog_ads http error')

    priority_subjects = ads_search_result['prioritySubjects']
    adverts_array = ads_search_result['adverts']
    logger.info('priority_subjects[]: {}'.format(
        priority_subjects))

    if adverts_array is None:
        logger.info('Empty adverts. Json: ', ads_search_result)
        result_code = 1000
        error_str = "search_catalog_ads empty ads_search_result['adverts']"
        return (False, None, None, result_code, error_str)

    logger.info('adverts_array[:3]: {}'.format(
        ads_search_result['adverts'][:3]))

    return (True, adverts_array, priority_subjects, result_code, error_str)


async def work_iteration(db):
    adv_companies = db_facade.get_adv_companies(db)
    if len(adv_companies) == 0:
        logger.debug('nothing to do')

    logger.info(
        f"get {len(adv_companies)} companies. start at {time.strftime('%X')}")
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(handle_company(db, ac))
                 for ac in adv_companies]
    logger.info(
        f"finish handling {len(adv_companies)} companies at {time.strftime('%X')}")


def is_valid(adv_company) -> tuple[bool, str]:
    valid = True
    reason = ''
    if adv_company['query'] in (None, ''):
        reason = 'field advert_company.query IS NULL'
        valid = False
    if adv_company['cpm_token'] in (None, ''):
        reason = 'field sellers.cpm_token IS NULL'
        valid = False

    if not valid:
        logger.warning('Company: {} - {} skipped. Reson: {}'.format(adv_company['company_id'],
                       adv_company['name'], reason))
        return False, reason
    return True, None


async def handle_company(db, adv_company):
    # если текущее время больше last_scan_ts + scan_interval_sec,
    #   то работаем с этой кампанией
    if is_it_time_to_work(adv_company):
        logger.info('checking company: {}'.format(adv_company['name']))
        valid, error_str = is_valid(adv_company)
        if not valid:
            db_facade.update_last_scan_ts(db, adv_company['company_id'])
            db_facade.log_advert_bid(db, adv_company['company_id'], None, None,
                                     None, None, None, 1001,
                                     error_str, '{}', '{}', None)
            return

        if adv_company['current_bet'] in (None, ''):
            ok, result_code, advert_info_response, error_str = wb_requests.get_advert_info_by_api(
                adv_company['company_id'], adv_company['cpm_token'])
            if not ok:
                logger.info('Company: {} skipped. Could not get current bet. Http code: {}. Error: {}'.format(
                    adv_company['company_id'], result_code, error_str))
                db_facade.update_last_scan_ts(
                    db, adv_company['company_id'])
                db_facade.log_advert_bid(db, adv_company['company_id'], None, None,
                                         None, None, None, result_code,
                                         error_str, '{}', '{}', 'advert')
            logger.info('Company: {} Got current_bet: {}'.format(
                        adv_company['company_id'], advert_info_response['params'][0]['price']))
            adv_company['current_bet'] = advert_info_response['params'][0]['price']
            db_facade.update_company(
                db, adv_company['company_id'], adv_company['current_bet'], advert_info_response['params'][0]['subjectId'])

        ok, adverts_array, priority_subjects, result_code, error_str = get_catalog_ads_adverts_info(
            adv_company)
        request_name = "catalog-ads"

        my_price = None
        my_place = None
        target_price = None
        target_place = None
        decision_str = None
        if ok:
            target_place = adv_company['target_place']
            my_price = adv_company['current_bet']
            my_company_id = adv_company['company_id']
            my_subject_id = adv_company['subject_id']

            my_place = search_my_place(adverts_array, my_company_id)

            logger.debug('my_price: {} my_place: {} target_place: {} '.format(
                my_price, my_place, target_place))

            advert_info = cb.AdvertInfo()
            advert_info.fromAdverts(adverts_array, my_subject_id)
            logger.info('Adverts with my subject_id: {}'.format(
                advert_info.getPlaciesStr(target_place + 1)))

            decision = cb.calcBestPrice(
                advert_info, my_place, my_price, target_place)

            if decision.changePriceNeeded:
                target_price = decision.targetPrice
                if decision.targetPrice > adv_company['max_bet']:
                    logger.info('campaign: {}. targetPrice: {} max_bet: {}. Skip...'.format(adv_company['company_id'],
                                                                                            target_price, adv_company['max_bet']))
                    decision_str = 'max bet'
                else:
                    decision_str = 'change bet'

                    # перед изменением ставки проверяем еще что РК заведена в самой приоритетной категории
                    ok, result_code, advert_info_response, error_str = wb_requests.get_advert_info_by_api(
                        adv_company['company_id'], adv_company['cpm_token'])
                    request_name = 'advert'
                    logger.info("campaign: {}. 'advert' before save. result_code: {} error_str: {}".format(
                                adv_company['company_id'], result_code, error_str))
                    if ok:
                        my_subject_id = advert_info_response['params'][0]['subjectId']
                        if priority_subjects is not None and my_subject_id != priority_subjects[0]:
                            error_str = "priority_subjects[0]: {} not equal adverts's subject_id: {}".format(
                                priority_subjects[0], my_subject_id)
                            db_facade.log_advert_bid(db, adv_company['company_id'], None, None,
                                                     None, None, None, 1002,
                                                     error_str, '{}', '{}', 'advert')
                            db_facade.alarm(
                                db, adv_company['company_id'], error_str)
                            logger.warning("Company: {} skipped. Alarm: {}".format(
                                adv_company['company_id'], error_str))
                            db_facade.update_last_scan_ts(
                                db, adv_company['company_id'])
                            return

                    ok, result_code, error_str = wb_requests.save_advert_campaign_by_api(
                        adv_company['company_id'], adv_company['cpm_token'], decision.targetPrice, adv_company['subject_id'])
                    request_name = "save"
                    if ok:
                        logger.info('campaign "{}" saved! New price: {}'.format(
                            adv_company['name'], target_price))
                        db_facade.update_company(
                            db, adv_company['company_id'], decision.targetPrice, my_subject_id)
                    else:
                        logger.warn('could not save campaign: {} - {}'.format(
                                    adv_company['company_id'], adv_company['name']))
            else:
                logger.info('already best price and place')
                decision_str = 'no changes'

        json_adverts_array_first_five = '{}' if adverts_array is None else json.dumps(
            adverts_array[:4])
        json_priority_subjects = '{}' if priority_subjects is None else json.dumps(
            priority_subjects)
        db_facade.log_advert_bid(db, adv_company['company_id'], my_price, my_place,
                                 target_price, target_place, decision_str, result_code,
                                 error_str, json_adverts_array_first_five, json_priority_subjects, request_name)
        db_facade.update_last_scan_ts(db, adv_company['company_id'])


def main():
    logger.info('Service starting...')
    args = parse_arguments()
    db = db_facade.connect(args)

    while True:
        asyncio.run(work_iteration(db))
        time.sleep(2)


if __name__ == "__main__":
    main()
