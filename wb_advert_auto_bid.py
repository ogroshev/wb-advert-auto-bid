import argparse
import datetime
import time

import db_facade
import wb_requests


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

    return adv_company['last_scan_ts'] in (None, '') or \
        (adv_company['last_scan_ts'] + datetime.timedelta(
            seconds=adv_company['scan_interval_sec'])) < datetime.datetime.now()


def should_we_fuck_enemies(advert_first_place_id, own_company_id):
    print('advert_first_place_id: ', advert_first_place_id)
    print('own_company_id: ', own_company_id)
    return advert_first_place_id != own_company_id


def should_we_reduce_bid(second_place_price, own_price):
    return own_price > second_place_price + 1


def work_iteration(db):
    adv_companies = db_facade.get_adv_companies(db)

    for adv_company in adv_companies:
        # если текущее время больше last_scan_ts + scan_interval_sec,
        #   то работаем с этой компанией
        if is_it_time_to_work(adv_company):
            print('checking company: {}'.format(adv_company['name']))
            if adv_company['query'] in (None, ''):
                print('Company: {}. empty query, skipped'.format(
                    adv_company['name']))
                db_facade.update_last_scan_ts(db, adv_company['company_id'])
                continue
            try:
                ads_search_result = wb_requests.search_catalog_ads(
                    adv_company['query'])
                # print(ads_search_result['adverts'])
                # TODO брать свою ставку из базы
                placement_response = wb_requests.get_placement(
                    adv_company['type'], adv_company['company_id'], adv_company['access_token'])
            except Exception as e:
                print('Http error: {}'.format(e))
                db_facade.update_last_scan_ts(db, adv_company['company_id'])
                print('skip {} - {}'.format(adv_company['company_id'], adv_company['name']))
                continue

            # TODO: Добавить обработку ошибок запросов wb
            adverts_array = ads_search_result['adverts']
            if adverts_array is None:
                print('Empty adverts. Json: ', ads_search_result)
            else:
                first_place_advert_id = adverts_array[0]['advertId']
                my_company_id = adv_company['company_id']
                first_place_price = adverts_array[1]['cpm']
                second_place_price = adverts_array[1]['cpm']
                my_price = placement_response['place'][0]['price']
                if should_we_fuck_enemies(first_place_advert_id, my_company_id):
                    new_price = first_place_price + 1
                    print('current my price: {}, first_place_price: {}, set price to: {}'.format(
                        my_price, first_place_price, new_price))
                elif should_we_reduce_bid(second_place_price, my_price):
                    new_price = second_place_price + 1
                    print('current my price: {}, second_place_price: {}, set price to: {} '.format(
                        my_price, second_place_price, new_price))
                else:
                    print('already best price and place')
                    db_facade.update_last_scan_ts(
                        db, adv_company['company_id'])
                    continue
                placement_response['place'][0]['price'] = new_price
                wb_requests.save_advert_campaign(
                    adv_company['type'], adv_company['company_id'], placement_response, adv_company['access_token'])
                print('campaign "{}" saved!'.format(adv_company['name']))
            db_facade.update_last_scan_ts(db, adv_company['company_id'])


def main():
    args = parse_arguments()
    db = db_facade.connect(args)

    while True:
        work_iteration(db)
        time.sleep(2)


if __name__ == "__main__":
    main()
