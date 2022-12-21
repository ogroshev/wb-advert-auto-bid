import argparse
import datetime
import time

import db_facade
import wb_requests
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
    logger.debug('is_it_time_to_work. last_scan_ts: {} current_time: {} interval_sec: {} sec_to_start: {}'
                 .format(last_scan_ts, msk_now, adv_company['scan_interval_sec'], sec_to_start))
    return (last_scan_ts + datetime.timedelta(
            seconds=adv_company['scan_interval_sec'])) < msk_now


def is_target_place_ours(target_place_id, own_company_id):
    logger.info('target_place_id: {}'.format(target_place_id))
    logger.info('own_company_id: {}'.format(own_company_id))
    return target_place_id == own_company_id


def should_we_reduce_bid(target_place_price, own_price):
    return own_price > target_place_price + 1


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
                # logger.info(ads_search_result['adverts'])
                # TODO брать свою ставку из базы
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

            # TODO: Добавить обработку ошибок запросов wb
            adverts_array = ads_search_result['adverts']
            logger.info('adverts_array[:3]: {}'.format(adverts_array[:3]))
            if adverts_array is None:
                logger.info('Empty adverts. Json: ', ads_search_result)
            else:
                # logger.debug('adverts_array: {}'.format(adverts_array))
                second_place_advert_id = adverts_array[1]['advertId']
                my_company_id = adv_company['company_id']
                first_place_price = adverts_array[0]['cpm']
                second_place_price = adverts_array[1]['cpm']
                third_place_price = adverts_array[2]['cpm']
                my_price = placement_response['place'][0]['price']

                logger.debug('my_price: {} first_place_price: {} second_place_price: {} third_place_price: {} '.format(
                    my_price, first_place_price, second_place_price, third_place_price))
                new_price = my_price
                if is_target_place_ours(second_place_advert_id, my_company_id):
                    logger.info('already second place')
                    if should_we_reduce_bid(second_place_price, my_price):
                        new_price = second_place_price + 1
                        logger.info('redusing bid. current my price: {}, second_place_price: {}, target price: {} '.format(
                            my_price, second_place_price, new_price))
                else: 
                    new_price = second_place_price + 1
                    logger.info('change bid. current my price: {}, second_place_price: {}, target price: {}'.format(
                        my_price, second_place_price, new_price))

                if my_price != new_price:
                    placement_response['place'][0]['price'] = new_price
                    wb_requests.save_advert_campaign(
                        adv_company['type'], adv_company['company_id'], placement_response, 
                        adv_company['cpm_cookies'], adv_company['x_user_id'])
                    logger.info('campaign "{}" saved!'.format(
                        adv_company['name']))
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
