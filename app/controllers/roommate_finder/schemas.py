from typing import Optional, List, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator

from .models import RoommateFinder
from property_street_backend.app.schemas.cloud_image_schema import CloudImageSchema
from property_street_backend.app.schemas.area_schema import AreaSchema, AreaResponseSchema

class RoommateFinderRequestSchema(BaseModel):
    gender: Literal['male', 'female']
    extra_conditions:Optional[str] = Field(None, description="extra conditions the requester requires")
    area: AreaSchema
    room_images: List[CloudImageSchema]
    max_roomies: int = 1
    category: str

    model_config = ConfigDict(from_attributes=True)



class RoommateFinderResponseSchema(RoommateFinderRequestSchema):
    id: int
    area: AreaResponseSchema
    room_images: List[str] = []# Flattened
    requester: dict
    gender: Optional[str] = None

    @classmethod
    def from_orm_with_relations(cls, roommate_finder: RoommateFinder):
        """Transform ORM object to response schema with all relationships resolved"""
        return cls(
            id=roommate_finder.id,
            extra_conditions=roommate_finder.extra_conditions,
            area=roommate_finder.area,
            room_images=[img.secure_url for img in roommate_finder.room_images],
            max_roomies=roommate_finder.max_roomies,
            category=roommate_finder.category,
            requester={
                "id": roommate_finder.requester.id,
                "username": roommate_finder.requester.username,
                "first_name": roommate_finder.requester.first_name,
                "last_name": roommate_finder.requester.last_name,
                "avatar_url": (
                    roommate_finder.requester.profile_avatar.secure_url
                    if (roommate_finder.requester and roommate_finder.requester.profile_avatar)
                    else ""
                ),
                "gender": roommate_finder.requester.gender if roommate_finder.requester else None,
            } if roommate_finder.requester
                else None,
        )

class RFRSListWithCachedIds(BaseModel):
    requests: list[RoommateFinderResponseSchema] = []
    cached_roomies_application_ids: Optional[list[int]] = []

class RoommateRequestSearchResponse(BaseModel):
    type: str = 'roommates-finder'
    data: RoommateFinderResponseSchema

#--* Previously used validators *--#
#@field_validator('room_images', mode='before')
#def transform_room_images(cls, value):
#    if value and isinstance(value, list) and hasattr(value[0], 'secure_url'):
#        return [img.secure_url for img in value]
#    return value
#
#@field_validator('requester', mode='before')
#def serialize_requester(cls, value):
#    if value and isinstance(value, dict):
#        return f"{value.first_name} {value.last_name}"
#    return ""
#
#
#@field_validator('gender', mode='before')
#def get_gender_from_requester(cls, value, info):
#    # 'value' here is the RoommateFinder instance
#    if isinstance(value, RoommateFinder):
#        return value.requester.gender if value.requester else ""
#    return ""

# @field_validator('requester_avatar_url', mode='before')
# def transform_requester_avatar_url(cls, value, info):
#     # 'value' here is the RoommateFinder instance
#     if isinstance(value, RoommateFinder):
#         return (
#             value.requester.profile_avatar.secure_url 
#             if (value.requester and value.requester.profile_avatar) 
#             else ""
#         )
#     return ""

#Assuming you have a RoommateFinder ORM instance called 'finder_instance'
# response_data = RoommateFinderResponseSchema.from_orm_with_relations(finder_instance)