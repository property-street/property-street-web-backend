from pydantic import BaseModel, ConfigDict

from property_street_backend.app.schemas.area_schema import Area

class AssetRequestSchema(BaseModel):
    description: str
    area: Area

    model_config = ConfigDict(from_attributes=True)