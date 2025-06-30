from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, HTTPException, status, Depends

from property_street_backend.app.database import get_db
from property_street_backend.app.initiator import get_redis
from property_street_backend.app.schemas.auth_schemas import (
    UserRegistrationSchema, 
    UserSigninSchema, 
    SigninResponse, 
    TokenData, 
    ProbeUserExistenceSchema,
    SendEmailCodeSchema,
    SignupCodeVerificationSchema,
)
from property_street_backend.log_config.logger_config import log_message
from property_street_backend.app.utils.store import email_verification_code_ttl
from property_street_backend.app.controllers.auth import (
    create_user, 
    authenticate_user, 
    fetched_access_token, 
    decode_user_from_token, 
    decode_user_from_token_optional, 
    check_username_email_availability,
    send_email_verification_code as controller_send_email_verification_code,
    confirm_email_verification_code_and_sign_user_up as controller_confirm_email_verification_code_and_sign_user_up
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
    redis_client: Redis = Depends(get_redis),
    expiry_time_in_secs: int = Depends(email_verification_code_ttl)
):
    try:
        return await controller_send_email_verification_code(
            requester_data = requester_data,
            redis_client = redis_client,
            expiry_time_in_secs = expiry_time_in_secs
        )
    except Exception as e:
        # log the error
        log_message(
            log_type='error',
            message=f'An error occured on retrieval of agent data. Reason: {e}'
        )
        raise e


# confirm email verification endpoint
@router.post("/confirm-email-verification-code", status_code=status.HTTP_200_OK)
async def confirm_email_verification_code(
    requester_data: SignupCodeVerificationSchema, 
    redis_client: Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db),
):
    return await controller_confirm_email_verification_code_and_sign_user_up(
        requester_data = requester_data,
        redis_client = redis_client,
        db = db
    )


# signin endpoint
@router.post("/signin", response_model=SigninResponse, status_code=status.HTTP_200_OK)
async def signin_for_access_token(
    user_data: UserSigninSchema, 
    db: AsyncSession = Depends(get_db)
):
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
    return {
        **fetched_access_token(user),
        "user_id":user.id, 
    }


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
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are restricted to carry out this action!"
        )