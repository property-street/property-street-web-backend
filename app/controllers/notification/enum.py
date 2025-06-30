from enum import Enum

class NotificationStateChoice(str, Enum):
    read = 'read'
    delivered = 'delivered'
    undelivered = 'undelivered'