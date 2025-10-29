from typing import Optional
from pydantic import Field
from . import ConfigDictSetter


class AreaSchema(ConfigDictSetter):
    country: str
    state_or_province: str
    city_or_town: str
    county: Optional[str] = Field('', description='Asset county') 
    street: Optional[str] = Field('', description='Street detail')
    zip_or_postal_code: Optional[str] = Field('', description='Postal code')
    building_name_or_suite: Optional[str] = Field('', description='Building name')


class AreaResponseSchema(AreaSchema):
    id: int