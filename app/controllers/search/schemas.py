from pydantic import BaseModel
from typing import List, Literal, Optional

from property_street_backend.app.controllers.actors.schemas import AgentResponseSchema
from property_street_backend.app.controllers.assets.schemas import AssetResponseSchema
from property_street_backend.app.controllers.asset_request.schemas import AssetRequestResponseSchema
from property_street_backend.app.controllers.roommate_finder.schemas import RoommateFinderResponseSchema

class SearchResultSchema(BaseModel):
    type: Literal['agent','asset_request','asset','roommates_finder']
    data: Optional[AssetRequestResponseSchema|AssetResponseSchema|RoommateFinderResponseSchema|AgentResponseSchema] = None
    score: float