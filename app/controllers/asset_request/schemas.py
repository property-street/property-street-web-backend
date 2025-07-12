from typing import Optional, List
from pydantic import BaseModel, ConfigDict, model_validator

from property_street_backend.app.schemas import ConfigDictSetter
from property_street_backend.app.schemas.area_schema import AreaSchema
from .models import AssetRequest

class BaseSchema(ConfigDictSetter):
    description: str
    area: AreaSchema


class AssetRequestSchema(BaseSchema):
    description: str
    area: AreaSchema


class AssetRequestResponseSchema(BaseSchema):
    id: Optional[int] = None
    requester: dict
    time_requested: str
    resolutions: Optional[list[dict]] = None
    
    @classmethod
    def from_orm_with_relations(cls, data: AssetRequest):
        return cls(
            id = data.id,
            requester = ({
                'name': f"{data.requester.first_name} {data.requester.last_name}",
                'avatar_url': (
                    data.requester.profile_avatar.secure_url 
                    if data.requester and data.requester.profile_avatar 
                    else ""
            )}),
            description = data.description,
            area = data.area,
            time_requested = data.created_at.isoformat(), 
            resolutions = ([
                {
                    'id': resolution.id,
                    'cover_image_url': resolution.cover_image.secure_url,
                } for resolution in data.assets if data.assets
            ]),
        )