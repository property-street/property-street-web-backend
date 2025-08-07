from typing import Optional, Literal
from pydantic import BaseModel, ConfigDict

from property_street_backend.app.controllers.activity.schemas import UserUIMetaDataSchema

class SendEmailVerificationResponseSchema(BaseModel):
    message: str
    expiry: str

class ConfirmEmailVerificationCodeSchema(BaseModel):
    code: str
    email: str

class UserSigninSchema(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
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


class SigninResponse(Token, UserUIMetaDataSchema):
    id: int
    username: str
    client_is_agent: bool
    is_authenticated: bool = True
    user_role: str

class TokenData(BaseModel):
    username: str | None = None

class UserResponseSchema(BaseModel):
    id: int
    email: str
    username: str

    model_config = ConfigDict(from_attributes=True)
