from typing import List
from pydantic import (
    BaseModel, 
    Field, 
    ConfigDict,
    model_validator
)
from typing import Optional
from property_street_backend.app.enums import AssetCategoryChoice
from .area_schema import  AreaSchema
from .cloud_image_schema import CloudImageSchema
from . import ConfigDictSetter
from property_street_backend.app.controllers.assets.schemas import (
    AssetResponseSchema,
    AssetFeatureCreateSchema,
    RemoveTagFromAssetSchema,
    CloudImageResponseSchema,
    AssetFeatureSchema,
    NoFeatureSchema,
    TagSchema,
    AssetSchema,
)


class AssetFetchResponseSchema(ConfigDictSetter):
    first_name: Optional[str] = None
    client_is_agent: Optional[bool] = None
    is_authenticated: bool

    model_config = ConfigDict(from_attributes=True)


class LatestAssetsFetchResponseSchema(BaseModel):
    assets: List[AssetSchema]


class AssetFetchByIdResponseSchema(AssetFetchResponseSchema):
    asset: AssetSchema