from typing import List
from typing import Optional
from pydantic import BaseModel
from property_street_backend.app.schemas import ConfigDictSetter
from property_street_backend.app.controllers.assets.schemas import (
    AssetResponseSchema, 
    PartialPropertyResponseSchema
)
from property_street_backend.app.controllers.asset_request.schemas import AssetRequestResponseSchema
from property_street_backend.app.controllers.roommate_finder.schemas import RoommateFinderResponseSchema

class LCollectionProperties(BaseModel):
    latests: List[AssetResponseSchema]
    all: List[PartialPropertyResponseSchema]

class LCollectionRoommateRequests(BaseModel):
    requests: List[RoommateFinderResponseSchema]
    cached_roomies_application_ids: List[int] = []

class LatestCollectionSchema(ConfigDictSetter):
    properties: LCollectionProperties
    roommates_finder: LCollectionRoommateRequests
    # asset_requests: Optional[list[AssetRequestResponseSchema]]


class ProcessAssetSchema(ConfigDictSetter):
    tags_to_remove_object: Optional[dict]
    asset_data_to_process: Optional[dict]

class AgentDetails(BaseModel):
    property_count: Optional[int] = None
    pass

class UserUIMetaDataSchema(BaseModel):
    id: Optional[int] = None
    username: Optional[str] = None
    is_authenticated: Optional[bool] = False
    profile_avatar_url: Optional[str] = None
    user_role: Optional[str] = None
    agent_details: Optional[AgentDetails] = None
    
