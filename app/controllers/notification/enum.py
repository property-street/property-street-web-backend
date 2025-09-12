from enum import Enum

class NotificationStateChoice(str, Enum):
    read = 'read'
    delivered = 'delivered'
    undelivered = 'undelivered'

class NotificationTypeChoice(str, Enum):
    chat = 'chat'
    roommate_finder = 'roommate_finder'
    asset_request = 'asset_request'
    property = 'property'
    generic = 'generic'