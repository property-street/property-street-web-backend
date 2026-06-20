from enum import Enum

class ResourceType(str, Enum):
    property='property'
    property_request='property_request'
    roommate_finder='roommate_finder'
    user='user'