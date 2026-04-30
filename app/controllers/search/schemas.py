from pydantic import BaseModel
from typing import List, Literal, Optional, Any

from property_street_backend.app.controllers.actors.schemas import AgentResponseSchema
from property_street_backend.app.controllers.assets.schemas import AssetResponseSchema
from property_street_backend.app.controllers.asset_request.schemas import AssetRequestResponseSchema
from property_street_backend.app.controllers.roommate_finder.schemas import RoommateFinderResponseSchema

class SearchResultSchema(BaseModel):
    type: Literal['agent','property-request','property','roommates-finder']
    id: int
    data: Optional[Any] = None
    # data: Optional[AssetRequestResponseSchema|AssetResponseSchema|RoommateFinderResponseSchema|AgentResponseSchema] = None
    score: float

class PaginatedSearchResultSchema(BaseModel):
    results: List[SearchResultSchema]
    total: int
    limit: int
    offset: int
    has_more: bool