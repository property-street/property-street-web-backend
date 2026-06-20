from typing import Optional, List
from pydantic import BaseModel, ConfigDict, model_validator

from .models import AssetRequest
from property_street_backend.app.schemas import ConfigDictSetter
from property_street_backend.app.controllers.assets.schemas import PropertySchema
from property_street_backend.app.schemas.area_schema import AreaResponseSchema, AreaSchema

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
    resolutions: Optional[list[dict]] = []
    area: AreaResponseSchema
    
    @classmethod
    def from_orm_with_relations(cls, data: AssetRequest):
            return cls(
                id = data.id,
                requester = ({
                    'first_name': data.requester.first_name,
                    'last_name': data.requester.last_name,
                    'username': data.requester.username,
                    'avatar_url': (
                        data.requester.profile_avatar.secure_url
                        if data.requester and getattr(data.requester, 'profile_avatar', None) and getattr(data.requester.profile_avatar, 'secure_url', None)
                        else ""
                    )
                }),
                description = data.description,
                area = data.area,
                time_requested = data.created_at.isoformat(),
                resolutions = ([
                    {
                        'id': resolution.id,
                        'cover_image_url': (
                            resolution.cover_image.secure_url
                            if getattr(resolution, 'cover_image', None) and getattr(resolution.cover_image, 'secure_url', None)
                            else ""
                        ),
                        'title': resolution.title
                    } for resolution in data.assets
                ] if data.assets else []),
            )
    
class PropertyRequestSchema(AssetRequestResponseSchema):
    pass
    
class PropertyRequestSearchResponse(BaseModel):
    type: str = 'property-request'
    data: PropertyRequestSchema

class DiscoverResponse(BaseModel):
    requests: List[AssetRequestResponseSchema] = []
    has_more: bool
    total_count: int


class RequestResolution(BaseModel):
    property_id: Optional[int] = None
    property: Optional[PropertySchema] = None
    
    @model_validator(mode="after")
    def validate_property_id_or_property(cls, values):
        if not (values.property_id or values.property):
            raise ValueError("Either of 'property_id' or 'property' must be included in the payload. Both can't be non-empty.")
        return values
