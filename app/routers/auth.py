from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from property_street_backend.app.initiator import redis_client
from property_street_backend.app.database import get_db
from property_street_backend.app.schemas.auth_schemas import (
    UserRegistrationSchema, 
    UserSigninSchema, 
    Token, 
    TokenData, 
    ProbeUserExistenceSchema,
    SendEmailCodeSchema,
    SignupCodeVerificationSchema,
)
from property_street_backend.app.controllers.auth import (
    create_user, 
    authenticate_user, 
    decode_user_from_token, 
    fetched_access_token, 
    check_username_email_availability,
    send_email_verification_code as controller_send_email_verification_code,
    confirm_email_verification_code_and_sign_user_up as controller_confirm_email_verification_code_and_sign_user_up
)
from property_street_backend.app.utils.store import (
    email_verification_code_ttl,
)

router = APIRouter(prefix="/auth", tags=["auth"])

# user registeration endpoint
@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserRegistrationSchema, db: AsyncSession = Depends(get_db)):
    try:
        user = await create_user(db, user_data)
    except HTTPException as e:
        raise e
    return fetched_access_token(user)

# probe user existence endpoint
@router.post("/probe-user-existence", status_code=status.HTTP_200_OK)
async def probe_user_existence(
    user_data: ProbeUserExistenceSchema,    
    db: AsyncSession = Depends(get_db)
):
    return await check_username_email_availability(db, user_data)

# send email verification for signup endpoint
@router.post("/send-email-verification-code", status_code=status.HTTP_200_OK)
async def send_email_verification_code(
    requester_data: SendEmailCodeSchema, 
    redis_client: redis.Redis = Depends(redis_client),
    expiry_time_in_secs: int = Depends(email_verification_code_ttl)
):
    return await controller_send_email_verification_code(
        requester_data = requester_data,
        redis_client = redis_client,
        expiry_time_in_secs = expiry_time_in_secs
    )

# confirm email verification endpoint
@router.post("/confirm-email-verification-code", status_code=status.HTTP_200_OK)
async def confirm_email_verification_code(
    requester_data: SignupCodeVerificationSchema, 
    redis_client: redis.Redis = Depends(redis_client),
    db: AsyncSession = Depends(get_db),
):
    return await controller_confirm_email_verification_code_and_sign_user_up(
        requester_data = requester_data,
        redis_client = redis_client,
        db = db
    )


# signin endpoint
@router.post("/signin", response_model=Token, status_code=status.HTTP_200_OK)
async def signin_for_access_token(user_data: UserSigninSchema, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(
        db = db, 
        login = user_data.email, 
        password = user_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return fetched_access_token(user)


@router.get("/retrieve-client-details")
async def fetch_user(
    current_user: TokenData = Depends(decode_user_from_token)
):
    return {
        "username": current_user.username,
        "user_id": current_user.id
    }


@router.get("/retrieve-agent-details")
async def fetch_agent(
    current_user: TokenData = Depends(decode_user_from_token)
):
    if current_user.agent_profile:
        return {
            "agent_id": current_user.agent_profile_id
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )