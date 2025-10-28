from pydantic import BaseModel

from property_street_backend.app.controllers.actors.schemas import AgentResponseSchema

class AgentSearchResponseSchema(BaseModel):
    type: str = "agent"
    data: AgentResponseSchema