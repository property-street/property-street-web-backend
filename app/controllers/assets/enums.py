from enum import Enum

class AvailabilityStatus(str, Enum):
    available = "available"
    unavailable = "unavailable"
    reserved = "reserved"
    pending = "pending"
    sold = "sold"
    rented = "rented"
    maintenance = "maintenance"

class IntentFactor(str, Enum):
    like = "like"
    save = "save"
    share = "share"
    cart = "cart"
    click = "click"
    contact = "contact"

class ImpressionFactor(str, Enum):
    view = "view"
    search_result_appearance = "search_result_appearance"
