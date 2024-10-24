from typing import List
from pydantic import (
    BaseModel, 
    Field, 
    ConfigDict,
)
from typing import Optional
from datetime import datetime
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
