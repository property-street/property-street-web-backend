from typing import List

from property_street_backend.app.enums import AssetCategoryChoice
from .area_schema import  AreaSchema
from .cloud_image_schema import CloudImageSchema
from . import ConfigDictSetter
from property_street_backend.app.controllers.assets.schemas import (
    AssetFetchResponseSchema,
    AssetFeatureCreateSchema,
    RemoveTagFromAssetSchema,
    CloudImageResponseSchema,
    AssetFeatureSchema,
    NoFeatureSchema,
    TagSchema,
    AssetSchema,
    AssetFetchResponseSchema,
    LatestAssetsFetchResponseSchema,
    AssetFetchByIdResponseSchema,
)