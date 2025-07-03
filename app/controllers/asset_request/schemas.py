from pydantic import BaseModel, ConfigDict

from property_street_backend.app.schemas.area_schema import AreaSchema

class AssetRequestSchema(BaseModel):
    description: str
    area: AreaSchema

    model_config = ConfigDict(from_attributes=True)