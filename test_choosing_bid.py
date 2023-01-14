import choosing_bid as cb

import json


def test_calcBestPrice():
    a = cb.AdvertInfo()
    a.placies.append(cb.AdvertPlace(position=1, price=300))
    a.placies.append(cb.AdvertPlace(position=2, price=200))
    a.placies.append(cb.AdvertPlace(position=3, price=100))

    assert cb.calcBestPrice(advert_info=a, current_place=2, current_price=200, target_place=2) == cb.Decision(True, 101)
    assert cb.calcBestPrice(advert_info=a, current_place=0, current_price=0, target_place=2) == cb.Decision(True, 201)
    assert cb.calcBestPrice(advert_info=a, current_place=2, current_price=200, target_place=3) == cb.Decision(True, 101)
    assert cb.calcBestPrice(advert_info=a, current_place=2, current_price=200, target_place=4) == cb.Decision(True, 50)
    assert cb.calcBestPrice(advert_info=a, current_place=3, current_price=100, target_place=3) == cb.Decision(True, 50)

    # assert cb.calcBestPrice(advert_info=a, current_price=200, target_place=2) == cb.Decision(True, 101)
    # assert cb.calcBestPrice(advert_info=a, current_price=0, target_place=2) == cb.Decision(True, 201)
    # assert cb.calcBestPrice(advert_info=a, current_price=200, target_place=3) == cb.Decision(True, 101)
    # assert cb.calcBestPrice(advert_info=a, current_price=200, target_place=4) == cb.Decision(True, 5)
    # assert cb.calcBestPrice(advert_info=a, current_price=100, target_place=3) == cb.Decision(True, 5)

    
    a = cb.AdvertInfo()    
    a.placies.append(cb.AdvertPlace(position=1, price=300))
    a.placies.append(cb.AdvertPlace(position=2, price=299))
    a.placies.append(cb.AdvertPlace(position=3, price=100))
    assert cb.calcBestPrice(advert_info=a, current_place=2, current_price=200, target_place=2) == cb.Decision(True, 101)
    # assert cb.calcBestPrice(advert_info=a, current_price=299, target_place=2) == cb.Decision(True, 101)
    
    a = cb.AdvertInfo()
    a.placies.append(cb.AdvertPlace(position=1, price=300))
    assert cb.calcBestPrice(advert_info=a, current_place=2, current_price=200, target_place=2) == cb.Decision(True, 50)
    # assert cb.calcBestPrice(advert_info=a, current_price=200, target_place=2) == cb.Decision(True, 5)

    a = cb.AdvertInfo()
    assert cb.calcBestPrice(advert_info=a, current_place=2, current_price=200, target_place=1) == cb.Decision(True, 50)
    assert cb.calcBestPrice(advert_info=a, current_place=2, current_price=200, target_place=2) == cb.Decision(True, 50)
    assert cb.calcBestPrice(advert_info=a, current_place=2, current_price=200, target_place=3) == cb.Decision(True, 50)

    
def test_AdvertInfo():
    json_data = [{'code': '', 'advertId': 2487286, 'id': 93089486, 'cpm': 865, 'subject': 4444}, 
        {'code': '', 'advertId': 3964213, 'id': 97662406, 'cpm': 864, 'subject': 4683}, 
        {'code': '', 'advertId': 3794903, 'id': 17762592, 'cpm': 858, 'subject': 4683}]
    ai = cb.AdvertInfo()
    ai.fromAdverts(json_data, 4683)
    assert len(ai.placies) == 2

    assert ai.placies[0].position == 1
    assert ai.placies[0].price == 864
    assert ai.placies[1].position == 2
    assert ai.placies[1].price == 858