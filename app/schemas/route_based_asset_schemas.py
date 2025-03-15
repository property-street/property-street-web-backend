from pydantic import (
    RootModel,
    BaseModel, 
    field_validator, 
)
from typing import Optional, List, Dict, Union

# Define each structure component

class Relationship(BaseModel):
    tags: Optional[List[int]] = None
    cover_image: Optional[int] = None
    cloud_images: Optional[List[int]] = None
    asset: Optional[int] = None
    agent: Optional[int] = None


class TagFields(BaseModel):
    name: str


class CloudImageDetailFields(BaseModel):
    cloud_asset_id: str
    format: str
    bytes: int
    height: int
    public_id: str
    secure_url: str
    width: int


class AssetFields(BaseModel):
    title: Optional[str] = None
    country: Optional[str] = None
    address: Optional[str] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    amount: Optional[float] = None
    category: Optional[str] = None
    description: Optional[str] = None
    has_features: Optional[bool] = None
    relationship: Optional[Relationship] = None


class AssetFeatureFields(BaseModel):
    title: str
    relationship: Optional[Relationship] = None


class TableObject(BaseModel):
    db_table_id: int
    db_table_name: str
    db_delete: Optional[bool] = False
    fields: Optional[Union[TagFields, CloudImageDetailFields, AssetFields, AssetFeatureFields]] = None

    @field_validator('fields', mode='before')
    def validate_fields(cls, v, values):
        table_name = values.data.get('db_table_name')
        if table_name == 'Tag':
            return TagFields(**v) if v else None
        elif table_name in ['CloudImageDetail', 'AssetCloudImage']:
            return CloudImageDetailFields(**v) if v else None
        elif table_name == 'Asset':
            return AssetFields(**v) if v else None
        elif table_name == 'AssetFeature':
            return AssetFeatureFields(**v) if v else None
        return v


# Main schema for the entire variable data structure
class AssetComponentSchema(RootModel[Dict[int, TableObject]]):
    pass

class UserUIMetaDataSchema(BaseModel):
    user_id: Optional[int] = None
    first_name: Optional[str] = None
    client_is_agent: Optional[bool] = None
    is_authenticated: bool
    profile_avatar_url: Optional[str] = None