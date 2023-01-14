from dataclasses import dataclass
from dataclasses import field


@dataclass
class AdvertPlace:
    position: int
    price: int


@dataclass
class AdvertInfo:
    placies: list[AdvertPlace] = field(default_factory=list)

    def fromAdverts(self, json_adverts, my_subject_id) -> None:
        self.placies.clear()
        pos = 1
        for idx in range(len(json_adverts)):
            if json_adverts[idx]['subject'] == my_subject_id:
                self.placies.append(AdvertPlace(
                    position=pos, price=json_adverts[idx]['cpm']))
                pos += 1
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

    def getPlaciesStr(self, count) -> str:
        placies_str = ""
        for idx in range(count if count < len(self.placies) else len(self.placies)):
            placies_str += "position: {} price: {} | ".format(
                self.placies[idx].position, self.placies[idx].price)
        if placies_str == "":
            return "empty"
        else:
            return placies_str


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
            return Decision(current_price != MIN_BID, MIN_BID)
        if current_price == (next_place_price + 1):
            return Decision(False, current_price)
        else:
            return Decision(current_price != next_place_price + 1, next_place_price + 1)

    target_place_info_found = False
    for place in advert_info.placies:
        if place.position == target_place:
            target_place_info_found = True
            d = Decision(current_price != (place.price + 1), place.price + 1)
    if not target_place_info_found:
        print('warning: target place info not found!')
        d = Decision(current_price != MIN_BID, MIN_BID)
    return d
