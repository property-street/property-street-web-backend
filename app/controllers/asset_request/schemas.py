from pydantic import BaseModel, ConfigDict, Field
from typing import Optional

class Area(BaseModel):
    country: str
    state_or_province: str
    city_or_town: str
    county: Optional[str] = Field(None, description='Asset county') 
    street: Optional[str] = Field(None, description='Street detail')
    zip_or_postal_code: Optional[int] = Field(None, description='Postal code')
    building_name_or_suite: Optional[str] = Field(None, description='Building name')
    
class AssetRequestSchema(BaseModel):
    description: str
    area: Area

    model_config = ConfigDict(from_attributes=True)