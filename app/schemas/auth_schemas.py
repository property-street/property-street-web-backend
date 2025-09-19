#Defines the structure of the data used in API requests and responses.
#Utilizes Pydantic for data validation and serialization.
#Ensures data consistency between the client and the server.

from typing import Optional, Literal
from pydantic import BaseModel, ConfigDict, EmailStr
from property_street_backend.app.controllers.activity.schemas import UserUIMetaDataSchema
from property_street_backend.app.controllers.auth.schemas import (
    UserSigninSchema,
    ProbeUserExistenceSchema,
    SendEmailCodeSchema,
    UserRegistrationSchema,
    AgentRegistrationSchema,
    VerifyEmailCodeSchema,
    SignupCodeVerificationSchema,
    Token,
    SigninResponse,
    TokenData,
    UserResponseSchema
)