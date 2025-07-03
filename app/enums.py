import enum

class EmailManagementReasonChoice(enum.Enum):
    email_verification = 'email-verification'
    password_change = 'password-change'
    verified = 'verified'


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