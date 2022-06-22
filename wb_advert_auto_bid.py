import requests
from http import HTTPStatus

def __wb_headers_authenticated():
    headers = {
        "Cookie": "x-supplier-id=8e3894a9-dcd7-46a5-96b8-50f76b86b2d1; locale=en; _ga=GA1.2.614722841.1653855369; _gid=GA1.2.1290201017.1654456885; _gcl_au=1.1.1338639992.1654460554; BasketUID=d69f3908-0547-4f73-951c-9c41fcaee7ac; _wbauid=3896566351654460553; WBToken=At_2nAm-0p6pDL6OiKoMQrgjvtwo7M06LkdjQoNJ8f5_DKBNtFUZx5cdJIAxiEM_PQ2de-4HL4SbI0Gi__nNPLAxBjjXjfTn1DNo_iQu_UZnpg; WILDAUTHNEW_V3=83A533A7F3244E8DF7CAD209EA4CFB533AC80210C1E0E99DACB85D6FD1CFAC28FA9CC63117C785A4F2CC1FC912773E7CC909BB8BD8F743E0E1846D2097B5FF72D8D0F4C894D756A8D2B56D493898AC7136ED9086CD5C1179C482B587371E464EA8ACB7CF9382A508663D596321CCCEC3E1C7645831510F47E4F9234286521628F637E72311AC9EEA58AB3060B5F1AB1EC610337043374A6711811F44B9A98E200C54E75769FB5BE3BA257C1C497C53B8B44A1E42AF414BCE1F2D8F54F5C7B649363EF77439D8D641FDBAC7048E8B309FE245B99E392E13111D82F89F0EA326A6D0E9C02774D0C0C752A73CC4F7A34FD5B1236897E5915ACEF5243C60F858354C446E98B7DDDA8F83C1B6A77A5B4AE2646FEA0D9E339518462080E9415B1D8647DCD5F3B6545DDEDDFDE7F644CF58492CB075652660BED25C8C2B1512806F155FBC297D6A0EE73FECB9194F758F91760A62BEFED4; ___wbu=f49253ce-cdd1-47e5-b5c9-423f9226c2d1.1618997329",
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate, br",
        "Host": "seller.wildberries.ru",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15",
        "Accept-Language": "en-us",
        "Referer": "https://seller.wildberries.ru/cmp/campaigns/list/pause/edit/search/{campaign_id}",
        "Connection": "keep-alive"
    }
    return headers


def make_url(advert_type, company_id, request_name):
    return f'https://seller.wildberries.ru/ns/campaigns-api/ads/api/v2/{advert_type}/{company_id}/{request_name}'
    

def get_placement(advert_type, company_id):
    url = make_url(advert_type, company_id, 'placement')
    r = requests.get(url, headers=__wb_headers_authenticated())
    r.raise_for_status()
    return r.json()


def save_advert_campaign(advert_type, company_id, json_request_body):
    url = make_url(advert_type, company_id, 'save')
    r = requests.put(url, headers=__wb_headers_authenticated(), json=json_request_body)
    r.raise_for_status()


placement_json_response = get_placement('search', 1920749)
placement_json_response['place'][0]['price'] = 703
print(placement_json_response)
print(save_advert_campaign('search', 1920749, placement_json_response))
