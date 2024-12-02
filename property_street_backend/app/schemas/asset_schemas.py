from typing import List
from pydantic import (
    BaseModel, 
    Field, 
    ConfigDict,
    model_validator
)
from typing import Optional
from property_street_backend.app.enums import AssetCategoryChoice



class AssetFeatureCreateSchema(BaseModel):
    title: str = Field(..., description="The title of the feature")
    asset_id: Optional[int] = Field(None, description="The ID of the asset to which this feature belongs")

    model_config = ConfigDict(from_attributes=True)


class CloudImageCreateSchema(BaseModel):
    cloud_asset_id: str = Field(..., description="asset_id from the cloud")
    format: str = Field(..., description="The format of the image (e.g. jpg, png)")
    bytes: int = Field(..., description="The size of the image in bytes")
    height: int = Field(..., description="The height of the image in pixels")
    width: int = Field(..., description="The width of the image in pixels")
    public_id: str = Field(..., description="The public ID of the image in the cloud storage")
    secure_url: str = Field(..., description="The secure URL of the image in the cloud storage")
    asset_id: Optional[int] = Field(None, description="The ID of the asset to which this image is linked")

    model_config = ConfigDict(from_attributes=True)


class AssetCreateSchema(BaseModel):
    title: str = Field(..., description="The title of the asset")
    country: str = Field(..., description="The country where the asset is located")
    address: str = Field(..., description="The physical address of the asset")
    currency: str = Field(..., description="The currency used for the asset's price (e.g. USD, EUR)")
    amount: float = Field(..., description="The monetary value of the asset")
    description: str = Field(..., description="A detailed description of the asset, possibly in HTML")
    category: str = Field(..., description="The category of the asset (e.g. House, Hotel)")
    status: str = Field(..., description="The category of the asset (e.g. House, Hotel)")
    availability: bool = Field(..., description="Whether the asset is currently available")
    # Tags can be a string or a list of strings
    tags: Optional[str | List[str]] = Field(None, description="Tags associated with the asset")
    agent_id: Optional[int] = Field(None, description="The ID of the agent managing the asset")
    cover_image: CloudImageCreateSchema

    model_config = ConfigDict(from_attributes=True)


class RemoveTagFromAssetSchema(BaseModel):
    asset_id: int = Field(..., description="The id of the asset whose tags is to be removed")
    tag_ids: List[int] = Field(..., description="Ids of tags to be removed from the asset")

    model_config = ConfigDict(from_attributes=True)


# Asset return schema
class CloudImageSchema(BaseModel):
    secure_url: str = Field(..., description="The secure URL of the image in the cloud storage")

    model_config = ConfigDict(from_attributes=True)

class AssetCloudImageSchema(CloudImageSchema):
    pass

class AssetFeatureSchema(BaseModel):
    title: str = Field(..., description="The title of the feature")
    cloud_images: List[AssetCloudImageSchema] = Field(..., description="The cloud images of each asset feature")

    model_config = ConfigDict(from_attributes=True)

class TagSchema(BaseModel):
    name: str = Field(..., description="Tag associated with the asset")

    model_config = ConfigDict(from_attributes=True)

class AssetSchema(BaseModel):
    id: int = Field(..., description="The id of the asset")
    title: str = Field(..., description="The title of the asset")
    country: str = Field(..., description="The country where the asset is located")
    address: str = Field(..., description="The physical address of the asset")
    currency: str = Field(..., description="The currency used for the asset's price (e.g., USD, EUR)")
    amount: float = Field(..., description="The monetary value of the asset")
    lease_duration: str = Field(..., description="The lease duration of the asset, if it's a lease.")
    description: str = Field(..., description="A detailed description of the asset, possibly in HTML")
    category: str = Field(..., description="The category of the asset (e.g., House, Hotel)")
    status: str = Field(..., description="The status of the asset (e.g., Available, Sold)")
    availability: bool = Field(..., description="Whether the asset is currently available")
    has_features: bool = Field(..., description="Boolean indicating if the asset has features or not")

    # Updated fields to allow for multiple entries
    tags: List[TagSchema] = Field(..., description="Tags associated with the asset")
    cover_image: CloudImageSchema = Field(..., description="The main image of the asset")
    features: Optional[List[AssetFeatureSchema]] = Field(None, description="A list of features of the asset")
    cloud_images: Optional[List[AssetCloudImageSchema]] = Field(None, description="Fallback images for assets without features")

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def validate_features_or_no_feature(cls, values):
        if values.features and values.cloud_images:
            raise ValueError("Only one of 'features' or 'cloud_images' can be included in the response at a time.")
        return values
    
class AssetFetchResponseSchema(BaseModel):
    first_name: Optional[str] = None
    client_is_agent: Optional[bool] = None
    is_authenticated: bool

    model_config = ConfigDict(from_attributes=True)

class LatestAssetsFetchResponseSchema(AssetFetchResponseSchema):
    assets: List[AssetSchema]

class AssetFetchByIdResponseSchema(AssetFetchResponseSchema):
    asset: AssetSchema