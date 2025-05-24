from typing import Optional, Literal
from pydantic import (
    BaseModel, 
    ConfigDict, 
    model_validator, 
    model_validator,
    Field,
)

class RatingReviewSchema(BaseModel):
    asset_to_rate: Literal['Agent', 'Area']
    comment: str
    score: int = 0
    agent_id: Optional[int] = Field(None, description='database id of the agent to rate.')
    area_id: Optional[int] = Field(None, description='database id of the area to rate.')

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def asset_id_or_area_id(cls, values):
        if not values.agent_id and not values.area_id:
            raise ValueError("Either one of agent_id or area_id must be populated!")
        elif values.agent_id and values.area_id:
            raise ValueError("Only one of area_id or agent_id can be included in the request at a time!")
        return values