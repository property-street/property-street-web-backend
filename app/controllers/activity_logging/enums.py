from enum import Enum


class ActivityStatusChoice(str, Enum):
    success = "success"
    failed = "failed"
    pending = "pending"
    error = "error"
