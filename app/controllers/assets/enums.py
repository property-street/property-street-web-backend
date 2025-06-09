from enum import Enum

class AvailabilityStatus(Enum):
    available = "available"
    unavailable = "unavailable"
    reserved = "reserved"
    pending = "pending"
    sold = "sold"
    rented = "rented"
    maintenance = "maintenance"