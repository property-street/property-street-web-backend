from pydantic import BaseModel, ConfigDict
from typing import Optional

class AssetRequestSchema(BaseModel):
    description: str
    country: str
    state_or_province: str
    city_or_town: str
    street: Optional[str]
    postal_code: Optional[int]
    building_name_or_suite: Optional[str]
    
    model_config = ConfigDict(from_attributes=True)