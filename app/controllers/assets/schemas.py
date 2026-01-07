from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator, condecimal

from property_street_backend.app.controllers.actors.schemas import AgentResponseSchema
from property_street_backend.app.schemas.area_schema import AreaSchema, AreaResponseSchema, AreaPatchSchema
from property_street_backend.app.schemas import ConfigDictSetter, make_optional, UtilitySchemaMixin
    

class AssetFeatureCreateSchema(ConfigDictSetter):
    title: str = Field(..., description="The title of the feature")
    asset_id: Optional[int] = Field(None, description="The ID of the asset to which this feature belongs")


class CloudImageSchema(BaseModel):
    id: Optional[int] = None
    cloud_asset_id: str = Field(..., description="asset_id from the cloud")
    format: str = Field(..., description="The format of the image (e.g. jpg, png)")
    bytes: int = Field(..., description="The size of the image in bytes")
    height: int = Field(..., description="The height of the image in pixels")
    width: int = Field(..., description="The width of the image in pixels")
    public_id: str = Field(..., description="The public ID of the image in the cloud storage")
    secure_url: str = Field(..., description="The secure URL of the image in the cloud storage")

CloudImagePatch = make_optional(CloudImageSchema)
class CloudImagePatchSchema(CloudImagePatch,UtilitySchemaMixin):
    pass


# Asset return schema
class CloudImageResponseSchema(ConfigDictSetter,UtilitySchemaMixin):
    id: int
    public_id: str
    format: str
    secure_url: str = Field(..., description="The secure URL of the image in the cloud storage")


class AssetFeatureSchema(ConfigDictSetter,UtilitySchemaMixin):
    id: Optional[int] = None
    title: str = Field(..., description="The title of the feature")
    cloud_images: Optional[List[CloudImageSchema]] = None

class AssetFeaturePatchSchema(BaseModel,UtilitySchemaMixin):
    id: Optional[int] = None
    title: str = None
    cloud_images: List[CloudImagePatchSchema] = []


class AssetFeatureResponseSchema(AssetFeatureSchema):
    id: int
    cloud_images: List[CloudImageResponseSchema] = Field(..., description="The cloud images of each asset feature")

class NoFeatureSchema(ConfigDictSetter):
    cloud_images: List[CloudImageSchema] = Field(..., description="The cloud images of each asset feature")

class NoFeaturePatchSchema(BaseModel):
    cloud_images: Optional[List[CloudImagePatchSchema]] = None


class TagSchema(BaseModel):
    id: Optional[int] = None
    name: str = Field(..., description="Tag associated with the asset")

TagPatch = make_optional(TagSchema)
class TagPatchSchema(TagPatch,UtilitySchemaMixin):
    pass

class TagSchemaResponse(TagSchema):
    id: int
    model_config = ConfigDict(from_attributes=True)

class FlatPropertyFields(BaseModel):
    id: Optional[int] = None
    title: str = Field(..., description="The title of the asset")
    currency: str = Field(..., description="The currency used for the asset's price (e.g., USD, EUR)")
    price: condecimal(max_digits=15, decimal_places=2) = Field(..., description="The monetary value of the asset")
    lease_duration: Optional[str] = Field(None, description="The lease duration of the asset, if it's a lease.")
    description: str = Field(..., description="A detailed description of the asset, possibly in HTML")
    category: str = Field(..., description="The category of the asset (e.g., House, Hotel)")
    status: str = Field(..., description="The status of the asset (e.g., Available, Sold)")
    availability: str = Field('available', description="availability status")
    agent_id: int

FlatPropertyFieldsPatch = make_optional(FlatPropertyFields)
class FlatFieldsPatchSchema(FlatPropertyFieldsPatch):
    pass

class AssetSchema(FlatPropertyFields):
    area: AreaSchema
    tags: List[TagSchema] = Field(..., description="Tags associated with the asset")
    cover_image: CloudImageSchema = Field(..., description="The main image of the asset")
    features: Optional[List[AssetFeatureSchema]] = Field(None, description="A list of features of the asset")
    unfeatured_images: Optional[List[CloudImageSchema]] = Field(None, description="Fallback images for assets without features")

    @model_validator(mode="after")
    def validate_features_or_no_feature(cls, values):
        if values.features and values.unfeatured_images:
            raise ValueError("Only one of 'features' or 'cloud_images' can be included in the response at a time.")
        return values

class PropertySchema(AssetSchema):
    pass


class AssetResponseSchema(ConfigDictSetter, AssetSchema):
    id: int = Field(..., description="The id of the asset")
    price: float = Field(..., description="The monetary value of the asset")
    has_features: Optional[bool] = Field(None, description="Boolean indicating if the asset has features or not")
    verified: bool
    created_at: datetime
    area: AreaResponseSchema
    tags: List[TagSchemaResponse]
    cover_image: CloudImageResponseSchema
    datetime_declined: Optional[datetime] = None
    features: Optional[List[AssetFeatureResponseSchema]] = None
    unfeatured_images: Optional[Optional[List[CloudImageResponseSchema]]] = None
    agent: AgentResponseSchema

class PropertyResponseSchema(AssetResponseSchema):
    pass

class PatchPropertySchema(FlatFieldsPatchSchema,UtilitySchemaMixin):
    area: Optional[AreaPatchSchema] = None
    tags: Optional[List[TagPatchSchema]] = None
    cover_image: Optional[CloudImagePatchSchema] = None
    features: Optional[List[AssetFeaturePatchSchema]] = None
    unfeatured_images: Optional[List[CloudImagePatchSchema]] = None


class LatestAssetsFetchResponseSchema(ConfigDictSetter):
    assets: List[PropertyResponseSchema]

class PropertySearchResponse(BaseModel):
    type: str = 'property'
    data: AssetResponseSchema

SearchList = List[PropertySearchResponse]