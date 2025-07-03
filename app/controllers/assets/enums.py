from enum import Enum

class AvailabilityStatus(str, Enum):
    available = "available"
    unavailable = "unavailable"
    reserved = "reserved"
    pending = "pending"
    sold = "sold"
    rented = "rented"
    maintenance = "maintenance"