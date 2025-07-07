from property_street_backend.app.schemas import ConfigDictSetter
from property_street_backend.app.controllers.assets.schemas import AssetResponseSchema
from property_street_backend.app.controllers.asset_request.schemas import AssetRequestResponseSchema
from property_street_backend.app.controllers.roommate_finder.schemas import RoommateFinderResponseSchema


class LatestCollection(ConfigDictSetter):
    properties: list[AssetResponseSchema]
    roommates_finder_requests: list[RoommateFinderResponseSchema]
    asset_requests: list[AssetRequestResponseSchema]