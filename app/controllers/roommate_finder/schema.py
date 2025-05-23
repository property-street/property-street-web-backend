from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

from property_street_backend.app.schemas.area_schema import Area
from property_street_backend.app.schemas.cloud_image_schema import CloudImageCreateSchema

class RoommateFinderRequestSchema(BaseModel):
    extra_conditions:Optional[str] = Field(None, description="extra conditions the requester requires")
    area: Area
    room_images: List[CloudImageCreateSchema]
    max_roomies: int = 1

    model_config = ConfigDict(from_attributes=True)