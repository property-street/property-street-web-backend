#Defines the structure of the data used in API requests and responses.
#Utilizes Pydantic for data validation and serialization.
#Ensures data consistency between the client and the server.

from pydantic import BaseModel, ConfigDict

class UserSigninSchema(BaseModel):
    username: str
    password: str

class ProbeUserExistenceSchema(BaseModel):
    username: str
    email: str

class UserRegistrationSchema(BaseModel):
    email: str
    username: str
    password: str
    #first_name: str
    #last_name: str
    # Add other fields as needed

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str | None = None

class UserResponseSchema(BaseModel):
    id: int
    email: str
    username: str

    model_config = ConfigDict(from_attributes=True)
