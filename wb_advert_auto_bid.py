import argparse
import datetime
import time

import db_facade
import wb_requests
import choosing_bid as cb

import logging
import sys
import pytz

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
            try:
                ads_search_result = wb_requests.search_catalog_ads(
                    adv_company['query'])
                adverts_array = ads_search_result['adverts']
                logger.info('adverts_array[:3]: {}'.format(adverts_array[:3]))
                placement_response = wb_requests.get_placement(
                    adv_company['type'], adv_company['company_id'],
                    adv_company['cpm_cookies'], adv_company['x_user_id'])
            except Exception as e:
                global error_counter
                error_counter += 1
                logger.info('{} Http error: {}'.format(error_counter, e))
                db_facade.update_last_scan_ts(db, adv_company['company_id'])

                logger.info(
                    'skip {} - {}'.format(adv_company['company_id'], adv_company['name']))
                continue

            if adverts_array is None:
                logger.info('Empty adverts. Json: ', ads_search_result)
            else:
                target_place = adv_company['target_place']
                my_price = placement_response['place'][0]['price']
                my_company_id = adv_company['company_id']
                my_place = search_my_place(adverts_array, my_company_id)

                logger.debug('my_price: {} my_place: {} target_place: {}'.format(
                    my_price, my_place, target_place))

                advert_info = cb.AdvertInfo()
                advert_info.fromAdverts(adverts_array)
                decision = cb.calcBestPrice(
                    advert_info, my_place, my_price, target_place)

                if decision.changePriceNeeded:
                    if decision.targetPrice > adv_company['max_bet']:
                        logger.info('targetPrice: {} max_bet: {}. Skip...'.format(
                            decision.targetPrice, adv_company['max_bet']))
                    else:
                        placement_response['place'][0]['price'] = decision.targetPrice
                        wb_requests.save_advert_campaign(
                            adv_company['type'], adv_company['company_id'], placement_response,
                            adv_company['cpm_cookies'], adv_company['x_user_id'])
                        logger.info('campaign "{}" saved! New price: {}'.format(
                            adv_company['name'], decision.targetPrice))
                else:
                    logger.info('already best price and place')
            db_facade.update_last_scan_ts(db, adv_company['company_id'])


def main():
    logger.info('Service starting...')
    args = parse_arguments()
    db = db_facade.connect(args)

    while True:
        work_iteration(db)
        time.sleep(2)


if __name__ == "__main__":
    main()
