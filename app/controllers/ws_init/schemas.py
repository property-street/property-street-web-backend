from typing import Optional
from pydantic import BaseModel


class SocketInitializerKwargsSchema(BaseModel):
    last_n_timestamp: Optional[int]