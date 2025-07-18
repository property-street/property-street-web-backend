from pydantic import BaseModel

class SendEmailVerificationResponseSchema(BaseModel):
    message: str
    expiry: str

class ConfirmEmailVerificationCodeSchema(BaseModel):
    code: str
    email: str