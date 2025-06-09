from typing import List
from pydantic import (
    BaseModel, 
    Field, 
    ConfigDict,
    model_validator
)
from typing import Optional
from property_street_backend.app.enums import AssetCategoryChoice
from .area_schema import Area as AreaSchema
from .cloud_image_schema import CloudImageSchema

class ConfigDictSetter(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    

class AssetFeatureCreateSchema(BaseModel):
    title: str = Field(..., description="The title of the feature")
    asset_id: Optional[int] = Field(None, description="The ID of the asset to which this feature belongs")

    model_config = ConfigDict(from_attributes=True)




class RemoveTagFromAssetSchema(BaseModel):
    asset_id: int = Field(..., description="The id of the asset whose tags is to be removed")
    tag_ids: List[int] = Field(..., description="Ids of tags to be removed from the asset")

    model_config = ConfigDict(from_attributes=True)


# Asset return schema
class CloudImageResponseSchema(BaseModel):
    secure_url: str = Field(..., description="The secure URL of the image in the cloud storage")

    model_config = ConfigDict(from_attributes=True)

class AssetFeatureSchema(ConfigDictSetter):
    title: str = Field(..., description="The title of the feature")
    cloud_images: List[CloudImageSchema] = Field(..., description="The cloud images of each asset feature")


class NoFeatureSchema(ConfigDictSetter):
    cloud_images: List[CloudImageSchema] = Field(..., description="The cloud images of each asset feature")


class TagSchema(BaseModel):
    name: str = Field(..., description="Tag associated with the asset")

    model_config = ConfigDict(from_attributes=True)


class AssetSchema(ConfigDictSetter):
    id: int = Field(..., description="The id of the asset")
    title: str = Field(..., description="The title of the asset")
    currency: str = Field(..., description="The currency used for the asset's price (e.g., USD, EUR)")
    price: float = Field(..., description="The monetary value of the asset")
    lease_duration: Optional[str] = Field(None, description="The lease duration of the asset, if it's a lease.")
    description: str = Field(..., description="A detailed description of the asset, possibly in HTML")
    category: str = Field(..., description="The category of the asset (e.g., House, Hotel)")
    status: str = Field(..., description="The status of the asset (e.g., Available, Sold)")
    availability: str = Field(..., description="availability status")
    has_features: bool = Field(..., description="Boolean indicating if the asset has features or not")

    # Updated fields to allow for multiple entries
    tags: List[TagSchema] = Field(..., description="Tags associated with the asset")
    cover_image: CloudImageSchema = Field(..., description="The main image of the asset")
    features: Optional[List[AssetFeatureSchema]] = Field(None, description="A list of features of the asset")
    cloud_images: Optional[List[CloudImageSchema]] = Field(None, description="Fallback images for assets without features")

    @model_validator(mode="after")
    def validate_features_or_no_feature(cls, values):
        if values.features and values.cloud_images:
            raise ValueError("Only one of 'features' or 'cloud_images' can be included in the response at a time.")
        return values


class AssetResponseSchema(AssetSchema):
    cover_image: CloudImageResponseSchema


class AssetFetchResponseSchema(BaseModel):
    first_name: Optional[str] = None
    client_is_agent: Optional[bool] = None
    is_authenticated: bool

    model_config = ConfigDict(from_attributes=True)


class LatestAssetsFetchResponseSchema(BaseModel):
    assets: List[AssetSchema]


class AssetFetchByIdResponseSchema(AssetFetchResponseSchema):
    asset: AssetSchema