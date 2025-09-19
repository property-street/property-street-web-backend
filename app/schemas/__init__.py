from pydantic import BaseModel, ConfigDict

class ConfigDictSetter(BaseModel):
    model_config = ConfigDict(from_attributes=True)
