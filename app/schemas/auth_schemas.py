#Defines the structure of the data used in API requests and responses.
#Utilizes Pydantic for data validation and serialization.
#Ensures data consistency between the client and the server.

from pydantic import BaseModel, ConfigDict, EmailStr
from typing import Optional, Literal


class UserSigninSchema(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: str

class ProbeUserExistenceSchema(BaseModel):
    username: str
    email: str

class SendEmailCodeSchema(BaseModel):
    email: str
    username: str

class UserRegistrationSchema(BaseModel):
    email: str
    username: str
    password: str
    first_name: str
    last_name: Optional[str] = None
    other_names: Optional[str] = None
    user_role: Optional[Literal['user','agent']] = None
    # Add other fields as needed

class AgentRegistrationSchema(UserRegistrationSchema):
    pass

class VerifyEmailCodeSchema(BaseModel):
    verification_code: str
    email: str

class SignupCodeVerificationSchema(UserRegistrationSchema):
    verification_code: str
    fullname: str

class Token(BaseModel):
    access_token: str
    token_type: str

class SigninResponse(Token):
    user_id: int

class TokenData(BaseModel):
    username: str | None = None

class UserResponseSchema(BaseModel):
    id: int
    email: str
    username: str

    model_config = ConfigDict(from_attributes=True)
