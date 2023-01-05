from dataclasses import dataclass
from dataclasses import field


@dataclass
class AdvertPlace:
    position: int
    price: int


@dataclass
class AdvertInfo:
    placies: list[AdvertPlace] = field(default_factory=list)

    def fromAdverts(self, json_adverts) -> None:
        self.placies.clear()
        for idx in range(len(json_adverts)):
            self.placies.append(AdvertPlace(position=idx+1, price=json_adverts[idx]['cpm']))
        return self

    def getPrice(self, position: int):
        price = 0
        for place in self.placies:
            if place.position == position:
                price = place.price
        return price

    def getPosition(sefl, price: int):
        position = 0
        for place in sefl.placies:
            if place.price == price:
                position = place.position
        return position
                

@dataclass
class Decision:
    changePriceNeeded: bool
    targetPrice: int


def calcBestPrice(advert_info: AdvertInfo, 
                    current_place:  int, 
                    current_price: int, 
                    target_place: int) -> Decision:
    MIN_BID = 50
    d = Decision(False, 0)

    if current_place == target_place:
        next_place_price = advert_info.getPrice(current_place + 1)
        if next_place_price == 0:
            print('warning: next place price not found!')
            return Decision(True, MIN_BID)
        if current_price == (next_place_price + 1):
            return Decision(False, current_price)
        else:
            return Decision(True, next_place_price + 1)

    target_place_info_found = False
    for place in advert_info.placies:
        if place.position == target_place:
            target_place_info_found = True
            d = Decision(True, place.price + 1)
    if not target_place_info_found:
        print('warning: target place info not found!')                
        d = Decision(True, MIN_BID)
    return d
