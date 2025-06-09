import enum

class EmailManagementReasonChoice(enum.Enum):
    email_verification = 'email-verification'
    password_change = 'password-change'
    verified = 'verified'

class ClientTypeChoice(enum.Enum):
    client = 'client'
    agent = 'agent'

class ClientGenderChoice(enum.Enum):
    male = 'male'
    female = 'female'
    custom = 'custom'

class AssetCategoryChoice(enum.Enum):
    house = "House"
    hotel = "Hotel"
    land = "Land"
    estate = "Estate"
    fabricated_homes = "Fabricated Homes"
    peng_house = "Peng house"
    office_complex = "Office complex"
    oriental_suite = "Oriental suite"
    # Add more relevant options as needed