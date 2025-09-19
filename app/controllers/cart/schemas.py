from pydantic import (
    Field, 
    BaseModel, 
    ConfigDict,
    condecimal
)
from typing import Annotated

class AddToCartSchema(BaseModel):
    quantity: int = Field(..., description="cart item quantity")
    asset_cover_url: str = Field(..., description="asset cover-image url")
    asset_title: str = Field(..., description="asset's title")
    price:  Annotated[float, condecimal(gt=0, decimal_places=2)] = Field(..., description="asset price")

    model_config = ConfigDict(from_attributes=True)
