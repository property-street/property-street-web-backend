from enum import Enum


class MessageTypes(str, Enum):
    inbound_message = 'inbound_message'
    outbound_message = 'outbound_message'
    delivered_message = 'delivered_message'
    read_message = 'read_message'
    completed = 'completed'


class MessageStatus(str, Enum):
    unsent = "unsent"
    sent = "sent"
    delivered = "delivered"
    read = "read"