from enum import Enum

class UserRoleChoice(str, Enum):
    admin = "admin"
    staff = "staff"
    agent = "agent"
    user = "user"


class ClientGenderChoice(str, Enum):
    male = 'male'
    female = 'female'
    custom = 'custom'