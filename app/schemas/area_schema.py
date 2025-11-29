from typing import Optional
from . import ConfigDictSetter
from pydantic import Field, BaseModel

from . import UtilitySchemaMixin, make_optional

class AreaSchema(BaseModel,UtilitySchemaMixin):
    id: Optional[int] = None
    country: str
    state_or_province: str
    city_or_town: str
    county: Optional[str] = Field('', description='Asset county') 
    street: Optional[str] = Field('', description='Street detail')
    zip_or_postal_code: Optional[str] = Field('', description='Postal code')
    building_name_or_suite: Optional[str] = Field('', description='Building name')


class AreaResponseSchema(ConfigDictSetter,AreaSchema):
    id: int

AreaPatch = make_optional(AreaSchema)
class AreaPatchSchema(AreaPatch):
    pass