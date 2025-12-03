from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, HTTPException, status, Depends, Body


from .schemas import (
    Email,
    PasswordResetSchema,
    SendPasswordResetMail,
    GenerateBetaLinkResponse,
    ConfirmEmailVerificationCodeSchema,
    SendEmailVerificationResponseSchema,
)
from property_street_backend.app.database import get_db
from property_street_backend.app.initiator import get_redis
from property_street_backend.app.schemas.auth_schemas import (
    TokenData, 
    SigninResponse, 
    UserSigninSchema, 
    SendEmailCodeSchema,
    UserRegistrationSchema, 
    ProbeUserExistenceSchema,
    SignupCodeVerificationSchema,
)
from property_street_backend.app.models import User
from property_street_backend.app.utils.store import email_verification_code_ttl
from property_street_backend.config.settings import BETA_LAUNCHING
from .services import (
    create_user, 
    create_agent,
    change_password,
    authenticate_user, 
    fetched_access_token, 
    decode_user_from_token, 
    require_roles,
    send_password_reset_mail,
    process_token_validate_user,
    confirm_email_verification_code,
    check_username_email_availability,
    check_password_reset_email_validity,
    generate_beta_signup_link,
    validate_beta_signup_token,
    send_email_verification_code as controller_send_email_verification_code,
    confirm_email_verification_code_and_sign_user_up as controller_confirm_email_verification_code_and_sign_user_up,
)

router = APIRouter(prefix="/auth", tags=["auth"])


# user registeration endpoint
@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(data: UserRegistrationSchema, db: AsyncSession = Depends(get_db)):
    try:
        is_agent = data.user_role and data.user_role == 'agent'
        if is_agent:
           await create_agent(db, data)
        else:
            await create_user(db, data)
    except HTTPException as e:
        raise e

# probe user existence endpoint
@router.post("/probe-user-existence", status_code=status.HTTP_200_OK)
async def probe_user_existence(
    data: ProbeUserExistenceSchema,  
    redis_client: Redis = Depends(get_redis),  
    db: AsyncSession = Depends(get_db)
):
    return await check_username_email_availability(db, redis_client, data.model_dump())


# send email verification for signup endpoint
@router.post("/send-email-verification-code", response_model = SendEmailVerificationResponseSchema )
async def send_email_verification_code(
    data: SendEmailCodeSchema, 
    redis_client: Redis = Depends(get_redis),
    expiry_time_in_secs: int = Depends(email_verification_code_ttl)
):
    return await controller_send_email_verification_code(
        requester_data = data.model_dump(),
        redis_client = redis_client,
        ttl_in_secs = expiry_time_in_secs
    )


# confirm email verification endpoint
@router.post("/confirm-email-verification-code-and-register-user", status_code=status.HTTP_200_OK)
async def handle_email_verification_code_and_register(
    requester_data: SignupCodeVerificationSchema, 
    redis_client: Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db),
):
    return await controller_confirm_email_verification_code_and_sign_user_up(
        requester_data = requester_data,
        redis_client = redis_client,
        db = db
    )


# confirm email verification endpoint
@router.post("/confirm-email-verification-code", status_code=status.HTTP_200_OK)
async def handle_email_verification_code(
    data: ConfirmEmailVerificationCodeSchema, 
    redis_client: Redis = Depends(get_redis),
):
    return await confirm_email_verification_code(
        requester_data = data.model_dump(),
        redis_client = redis_client,
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
            detail="Incorrect signin credentials!",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {
        **fetched_access_token(user),
        "id":user.id, 
        'username': user.username,
        'client_is_agent': True if (user.user_role.value == 'agent') else False,
        'profile_avatar_url': user.profile_avatar.secure_url if user.profile_avatar else None,
        'user_role': user.user_role 
    }


@router.get("/retrieve-client-details")
async def fetch_user(
    current_user: TokenData = Depends(decode_user_from_token)
):
    return {
        "username": current_user.username,
        "user_id": current_user.id
    }


@router.post("/send-password-reset-mail", response_model=SendPasswordResetMail)
async def send_password_reset_mail_endpoint(
    data: Email = Body(...),
    session: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis)
):
    return await send_password_reset_mail(data.email, session, redis_client)


@router.get("/check-email-reset-validity")
async def check_email_reset_validity(
    token: str,
    redis_client: Redis = Depends(get_redis),
    session: AsyncSession = Depends(get_db),
):
    user, secret = await process_token_validate_user(token, session)
    return await check_password_reset_email_validity(user.email, secret, redis_client)


@router.post("/change-password")
async def change_password_endpoint(
    data: PasswordResetSchema = Body(...),
    session: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis)
):
    return await change_password(
        redis_client=redis_client,
        session=session,
        **data.model_dump()
    )


# Beta signup link generation endpoint
@router.get("/generate-beta-signup-link", status_code=status.HTTP_201_CREATED, response_model=GenerateBetaLinkResponse)
async def generate_beta_signup_link_endpoint(
    _: User = Depends(require_roles("admin", "staff")),
    redis_client: Redis = Depends(get_redis),
):
    """
    Generate a time-based beta signup link token.
    Only admin and staff users can generate these links.
    
    Args:
        ttl_in_secs: Time-to-live for the token in seconds (default: 24 hours)
    
    Returns:
        Dictionary containing the generated token and expiry time
    """
    if not BETA_LAUNCHING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Beta launching is not currently enabled"
        )
    
    return await generate_beta_signup_link(redis_client)