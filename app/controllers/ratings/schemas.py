from typing import Optional, Literal
from pydantic import (
    BaseModel, 
    ConfigDict, 
    model_validator, 
    model_validator,
    Field,
)

from .models import Rating

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
    
class RatingResponseSchema(BaseModel):
    comment: str
    score: int = 0
    commenter: Optional[dict] = Field(None, description='details of the commenter')

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_with_relations(cls, rating: Rating):
        """Transform ORM object to response schema with all relationships resolved"""
        return cls(
            comment=rating.comment,
            score=rating.score,
            commenter=(
                {
                    "profile_avatar_url": commenter.profile_avatar.secure_url if commenter.profile_avatar else "",
                    "name": f"{commenter.first_name} {commenter.last_name}"
                }
                if (commenter := rating.commenter)
                else None
            )
        )