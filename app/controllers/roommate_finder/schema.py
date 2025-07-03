from typing import Optional, List, Literal
from pydantic import BaseModel, Field, ConfigDict

from property_street_backend.app.schemas.area_schema import AreaSchema
from property_street_backend.app.schemas.cloud_image_schema import CloudImageSchema

class RoommateFinderRequestSchema(BaseModel):
    extra_conditions:Optional[str] = Field(None, description="extra conditions the requester requires")
    area: AreaSchema
    room_images: List[CloudImageSchema]
    max_roomies: int = 1
    gender: Literal['male', 'female']
    category: str

    model_config = ConfigDict(from_attributes=True)