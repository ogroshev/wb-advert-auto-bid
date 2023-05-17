import requests
from http import HTTPStatus
import requests
import urllib
import time
import json


def __wb_headers_whitout_cookies():
    headers = {
        "Accept": "*/*",
        "Origin": "https://www.wildberries.ru",
        "Accept-Encoding": "gzip, deflate, br",
        "Host": "catalog-ads.wildberries.ru",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15",
        "Accept-Language": "en-us",
        "Referer": "https://www.wildberries.ru/catalog/0/search.aspx?search={url_encoded_query_text}",
        "Connection": "keep-alive"
    }
    return headers


def search_catalog_ads(query_text):
    url_encoded_query_text = urllib.parse.quote_plus(query_text)
    url = f'https://catalog-ads.wildberries.ru/api/v5/search?keyword={url_encoded_query_text}'
    headers = __wb_headers_whitout_cookies()
    headers["Referer"] = headers["Referer"].replace(
        '{url_encoded_query_text}', url_encoded_query_text)
    print('send request: {}'.format(url))

    RETRY_COUNT = 5
    RETRY_INTERVAL_SEC = 2
    for attemption in range(1, RETRY_COUNT + 1):
        try:
            r = requests.get(url, headers=headers, timeout=15)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.HTTPError as e:
            print('catalog-ads. Http error: {}'.format(e))
            print('{} attemption to retry... after {} sec'.format(
                attemption, RETRY_INTERVAL_SEC))
            time.sleep(RETRY_INTERVAL_SEC)
        except Exception as e:
            print('Unknown exception: {}'.format(e))
    return None


def save_advert_campaign_by_api(campaign_id, token, price, subject_id):
    url = 'https://advert-api.wb.ru/adv/v0/cpm'
    headers = {
        "Accept": "*/*",
        "Content-Type": "application/json",
    }
    headers["Authorization"] = token
    json_request_body = f'''
    {{
        "advertId": {campaign_id},
        "type": 6, 
        "cpm": {price},
        "param": {subject_id}
    }}'''
    body = json.loads(json_request_body)

    print('send request: {} | advertId: {} | cpm: {} | param: {} | token: {}'.format(
        url, campaign_id, price, subject_id, token))

    RETRY_COUNT = 5
    RETRY_INTERVAL_SEC = 2
    result_code = None
    error_str = None
    for attemption in range(1, RETRY_COUNT + 1):
        try:
            r = requests.post(url, headers=headers, json=body)
            r.raise_for_status()
            return (True, r.status_code, None)
        except requests.exceptions.HTTPError as e:
            print('[API] save campaign. Http error: {}'.format(e))
            result_code = e.response.status_code
            error_str = '{}'.format(e)
            if result_code == 422:
                break
            print('{} attemption to retry... after {} sec'.format(
                attemption, RETRY_INTERVAL_SEC))
            time.sleep(RETRY_INTERVAL_SEC)

        except Exception as e:
            print('Unknown exception: {}'.format(e))

    print('Could not save advert campaign {} after {} attemtps'.format(
        campaign_id, RETRY_COUNT))
    return (False, result_code, error_str)

# token = ''
# print(save_advert_campaign_by_api(4086336, token, 549, 268))

def validate_response_advert_info_by_api(response) -> tuple[bool, str]:
    print('validate_response_advert_info_by_api')
    err_head = 'API adv/v0/advert response invalid: '

    if len(response.content) == 0:
        err = err_head + 'empty response body'
        return False, err
    try:
        json_body = response.json()
    except Exception as e:
        err = err_head + 'could not parse json: ' + str(e)
        return False, err

    if 'params' not in json_body:
        err = err_head + '[params] not found'
        return False, err
    elif len(json_body['params']) == 0:
        valid = False
        err = err_head + '[params] is empty'
    elif 'price' not in json_body ['params'][0]:
        valid = False
        err = err_head + '[price] not found'
    elif 'subjectId' not in json_body ['params'][0]:
        valid = False
        err = err_head + '[subjectId] not found'
    return True, None

# validate_response_advert_info_by_api()

def get_advert_info_by_api(campaign_id, token):
    url = 'https://advert-api.wb.ru/adv/v0/advert'
    headers = {
        "Accept": "*/*",
        "Content-Type": "application/json",
    }
    headers["Authorization"] = token
    print('send request: {} | query params: id={} | token: {}'.format(url, campaign_id, token))

    RETRY_COUNT = 5
    RETRY_INTERVAL_SEC = 2
    result_code = None
    error_str = None
    for attemption in range(1, RETRY_COUNT + 1):
        try:
            r = requests.get(url, headers=headers, params={'id': campaign_id})
            r.raise_for_status()
            print('response. status: {} body: {}'.format(r.status_code, r.text))

            is_valid, error_str = validate_response_advert_info_by_api(r)
            if is_valid:
                return (True, r.status_code, r.json(), None)
            return (False, r.status_code, None, error_str)
        except requests.exceptions.HTTPError as e:
            print('[API] method advert. Http error: {}'.format(e))
            result_code = e.response.status_code
            error_str = '{}'.format(e)
            print('{} attemption to retry... after {} sec'.format(
                attemption, RETRY_INTERVAL_SEC))
            time.sleep(RETRY_INTERVAL_SEC)

        except Exception as e:
            print('Unknown exception: {}'.format(e))

    print('Could not get advert info id={} after {} attemtps'.format(
        campaign_id, RETRY_COUNT))
    return (False, result_code, None, error_str)

# import logging
# import http.client as http_client
# http_client.HTTPConnection.debuglevel = 1
# logging.basicConfig()
# logging.getLogger().setLevel(logging.DEBUG)
# requests_log = logging.getLogger("requests.packages.urllib3")
# requests_log.setLevel(logging.DEBUG)
# requests_log.propagate = True
# token = ''
# print(get_advert_info_by_api(4131487, token))


# for i in range(10):
#     ads_search_result = search_catalog_ads('перчатки нитриловые l')
#     # print(ads_search_result)
#     adverts_array = ads_search_result['adverts']
#     if adverts_array is None:
#         print(ads_search_result)
#         print("search_catalog_ads empty ads_search_result['adverts']")
