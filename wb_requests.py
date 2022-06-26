import requests
from http import HTTPStatus
import requests
import urllib
import time


def __wb_headers_authenticated():
    headers = {
        "Cookie": "",
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate, br",
        "Host": "seller.wildberries.ru",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15",
        "Accept-Language": "en-us",
        "Referer": "https://seller.wildberries.ru/cmp/campaigns/list/pause/edit/search/{campaign_id}",
        "Connection": "keep-alive"
    }
    return headers


def __build_headers_with_auth(campaign_id, cookie):
    headers = __wb_headers_authenticated()
    headers['Referer'] = headers['Referer'].replace('{campaign_id}', str(campaign_id))
    headers['Cookie'] = cookie
    # print('cookie: ',headers['Cookie'])
    return headers

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
    headers["Referer"] = headers["Referer"].replace('{url_encoded_query_text}', url_encoded_query_text)
    print('send request: {}'.format(url))
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()


def make_url(advert_type, campaign_id, request_name):
    return f'https://seller.wildberries.ru/ns/campaigns-api/ads/api/v2/{advert_type}/{campaign_id}/{request_name}'
    

def get_placement(advert_type, campaign_id, access_token):
    url = make_url(advert_type, campaign_id, 'placement')
    r = requests.get(url, headers=__build_headers_with_auth(campaign_id, access_token))
    r.raise_for_status()
    return r.json()


def save_advert_campaign(advert_type, campaign_id, json_request_body, access_token):
    url = make_url(advert_type, campaign_id, 'save')
    print('send request: {}'.format(url))

    RETRY_COUNT = 5 
    RETRY_INTERVAL_SEC = 2
    for attemption in range(1, RETRY_COUNT + 1):
        try:
            r = requests.put(url, headers=__build_headers_with_auth(campaign_id, access_token), json=json_request_body)
            r.raise_for_status()
            return
        except Exception as e:
            print('Save campaign. Http error: {}'.format(e))
            print('{} attemption to retry... after {} sec'.format(attemption, RETRY_INTERVAL_SEC))
            time.sleep(RETRY_INTERVAL_SEC)
    print('Could not save advert campaign {} after {} attemtps'.format(campaign_id, RETRY_COUNT))


# placement_json_response = get_placement('search', 1920749, cookie)
# placement_json_response['place'][0]['price'] = 800
# print(placement_json_response)
# print(save_advert_campaign('search', 1920749, placement_json_response, cookie))
