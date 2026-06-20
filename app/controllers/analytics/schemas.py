from pydantic import BaseModel

class UsersAExtra(BaseModel):
    total_agents: int = 0
    verified_agents: int = 0
    active_agents: int = 0
    inactive_agents: int = 0

class PropertiesAExtra(BaseModel):
    sold: int = 0
    rented: int = 0
    featured: int = 0

class PropertyRequestsAExtra(BaseModel):
    pending_requests: int = 0
    matched_requests: int = 0
    closed_requests: int = 0
    cancelled_requests: int = 0