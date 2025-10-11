import random
import secrets 
import redis.asyncio as redis
from redis.asyncio import Redis
from jose import jwt, JWTError
from typing import List, Callable
from sqlalchemy.future import select
from passlib.context import CryptContext
from sqlalchemy.exc import IntegrityError
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, APIRouter, HTTPException, status, Depends, Response

from property_street_backend.app.schemas.auth_schemas import (
    TokenData, 
    UserRegistrationSchema, 
    SignupCodeVerificationSchema
)
from property_street_backend.app.initiator import logger
from property_street_backend.app.utils.store import (
    read_email_from_html_template_name,
    substituted_string,
    send_email,
)
from property_street_backend.config.settings import (
    DEBUG,
    JWT_SECRET_KEY,
    JWT_EXPIRATION_DELTA,
    JWT_ALGORITHM,
    PASSWORD_LINK_TTL,
    TEST_PASSWORD_LINK_TTL,
)
from property_street_backend.config import env_is_test
from property_street_backend.app.database import get_db
from property_street_backend.app.controllers.actors.models import User

# Constants for JWT
SECRET_KEY = JWT_SECRET_KEY
ALGORITHM = JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = JWT_EXPIRATION_DELTA

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI()
router = APIRouter()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def fetched_access_token(user: User):
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

def fetch_access_token(user: User):
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# signin
async def authenticate_user(db: AsyncSession, login: str, password: str):
    # Check if the login is either a username or an email
    user_query = select(User).filter((User.username == login) | (User.email == login))
    
    # Execute the query
    result = await db.execute(user_query)
    user = result.scalars().first()

    if not user:
        return None

    # Verify the provided password against the stored password hash
    if not verify_password(password, user.password_hash):
        return None

    return user


# user existence
async def check_username_email_availability(db: AsyncSession, data: dict):
    username = data['username']
    email = data['email']
    
    # Check if the username exists
    username_query = await db.execute(
        select(User)
        .where(User.username == username)
    )
    username_exists = username_query.scalars().first()
    if username_exists:
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail = f"Username {username} already exists"
        )
    

    email_query = await db.execute(
        select(User)
        .where(User.email == email)
    )
    email_exists = email_query.scalars().first()
    if email_exists:
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail = f"Email {email} already exists"
        )


# Signup
async def create_user(
    db: AsyncSession, 
    user_data: UserRegistrationSchema
):
    username = user_data.username or user_data.email.strip().split('@')[0]
    existing_user = await db.execute(
        select(User)
        .filter(
            (User.email == user_data.email) 
            | (User.username == username)
        )
    )
    existing_user = existing_user.scalars().first()
    
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email or Username already exists")

    user_data_to_dict = user_data.model_dump(exclude={"password"})
    user_data_to_dict['password_hash'] = get_password_hash(user_data.password)
    
    # instantiate a user object
    user = User(
        **user_data_to_dict,
    )
    
    try:
        db.add(user)
        await db.commit()  
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error occurred")
    
    # Ensure the user instance reflects the latest state from the database
    await db.refresh(user)
    return user


async def create_agent(
    db:AsyncSession, 
    user_data:UserRegistrationSchema,
):

    """
    Helper function to create and return a test agent.
    """
    
    # Call the create_user function
    created_user = await create_user(
        db = db, 
        user_data = user_data,
    )
    
    # call the `become agent` on the created user
    await created_user.become_agent(
        session = db
    )

    # return the newly created agent
    await db.refresh(created_user)
    return created_user


def require_roles(*allowed_roles: List[str]) -> Callable:
    async def wrapper(current_user: User = Depends(decode_user_from_token)):
        if current_user.user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action"
            )
        return current_user  # Optionally return for access
    return wrapper

# Session token validity
async def decode_user_from_token(
    token: str = Depends(oauth2_scheme), 
    db: AsyncSession = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    result = await db.execute(select(User).filter(User.username == token_data.username))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    return user


async def decode_user_from_token_optional(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """
    Decode user from token without raising exceptions.
    Returns None if the token is invalid or the user is not found.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            return None
    except JWTError:
        return None

    # Query the user in the database
    result = await db.execute(select(User).filter(User.username == username))
    user = result.scalars().first()
    return user


async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    await db.delete(user)
    await db.commit()
    return user


async def send_email_verification_code(
    requester_data: dict, 
    redis_client: redis.Redis,
    ttl_in_secs: int,
):
    email_address = requester_data['email']
    user_name = requester_data['username']
    reason = "email_verification"

    """
        `email:reason` is the hset's key 
        the reason is the field
        the code is the value
    """

    # Check if the code exists in the cache
    user_key = f'{email_address}:{reason}'
    user_email_code = await redis_client.hget(user_key, reason)

    if user_email_code: #When a result is found
        expiry = await redis_client.hget(user_key, "ttl")

        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            detail = {
                "message" : "Please wait before requesting a new code.",
                "expiry" : (expiry.decode() 
                        if isinstance(expiry,bytes) 
                        else expiry)
                }
        )
    else: # When no result is found
        try:
            # Generate a new five-digit code
            new_code = '{:04d}'.format(random.randint(0, 9999))

            # call the email function and send the email
            # extract the email content from the template
            email_template_content = read_email_from_html_template_name('email_verification_code_template')
            property_street_address = "Port Harcourt"
            
            email_string = substituted_string(
                email_template_content,
                {
                    "user_name":user_name,
                    "verification_code":new_code,
                    "property_street_address": property_street_address
                }
            )
            from_address="team@stackfinancialsolutions.com"
            subject="Property street Verification Code"
            from_name="Property street"
            #to_name="Customer"

            send_email(
                from_email=from_address,
                to_email=email_address,
                from_name=from_name,
                subject=subject,
                html_email=email_string
            )

            # create another instance of the user with the new code
            await redis_client.hset(user_key, reason, str(new_code))

            # get the current time and add the ttl
            current_time = datetime.now(timezone.utc)
            expiry_time = (current_time + timedelta(seconds=ttl_in_secs)).isoformat()

            # save the ttl_time in the ttl field of the user's key
            await redis_client.hset(user_key, "ttl", expiry_time)

            # set an expiry for the user key
            # explicitly convert the expiry_time_in_secs to int
            # to avoid `value is not an integer or out of range` error
            await redis_client.expire(user_key, int(ttl_in_secs)) 

            return {
                "message":"A new verification code has been sent to your email.",
                "expiry": expiry_time
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Something went wrong. Please try again later.",
                headers={"X-Error": "Server error"},
            )


async def confirm_email_verification_code(
    requester_data: dict, 
    redis_client: redis.Redis,
):
    email_address = requester_data['email']
    input_code = requester_data['code']
    if DEBUG:
        logger.info(f"**Requesting code: {input_code}")
    reason = "email_verification"

    # `email:reason` is the HSET's key
    user_key = f'{email_address}:{reason}'

    # Check if the key exists in the cache
    cached_code = await redis_client.hget(user_key, reason)
    emailed_code = (
        cached_code.decode() 
        if isinstance(cached_code,bytes) 
        else cached_code
    )
    if DEBUG:
        logger.info(f"**Emailed code: {emailed_code}")
        
    if not emailed_code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification code not found or expired."
        )

    # Confirm the input code matches the one in the cache
    if input_code != emailed_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code."
        )


    try:
        # delete the verification code from Redis after successful registration
        await redis_client.delete(user_key)

        return {
            "message" : "The email address has been successfully verified.",
        }

    except Exception as e:
        f_message = "An error occurred while verifying the email address."
        d_message = f"{f_message} Reason: {e}"
        if DEBUG:
            logger.info(d_message)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f_message
        )


async def confirm_email_verification_code_and_sign_user_up(
    requester_data: SignupCodeVerificationSchema, 
    redis_client: redis.Redis,
    db: AsyncSession,
):
    email_address = requester_data.email
    reason = "email_verification"
    input_code = requester_data.verification_code

    # `email:reason` is the HSET's key
    user_key = f'{email_address}:{reason}'

    # Check if the key exists in the cache
    user_email_code = await redis_client.hget(user_key, reason)

    if not user_email_code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification code not found or expired."
        )

    # Confirm the input code matches the one in the cache
    if input_code != user_email_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code."
        )

    # get the client type User or Agent
    user_role = requester_data.role.lower()

    # extracting names from the fullname
    name_list = requester_data.fullname.split()
    
    # adding the first_name
    first_name = name_list[0]

    user_data = UserRegistrationSchema(
        email = email_address,
        username = requester_data.username,
        password = requester_data.password,
        role = user_role,
        first_name = first_name,
    )
    
    # adding last_name
    if len(name_list) == 2:
        user_data.last_name = name_list[-1]
    
    # Adding other_names (middle names or any names between the first and last)
    if len(name_list) >= 3:
        user_data.other_names = " ".join(name_list[1:-1])

    if user_role == 'client':
        # Create the new user instance
        created_client = await create_user(
            db = db,
            user_data = user_data   
        ) 
    elif user_role == 'agent':
        created_client = await create_agent(
            db = db,
            user_data = user_data
        )


    try:
        # delete the verification code from Redis after successful registration
        await redis_client.delete(user_key)

        return {
            "email_status": "Verified",
            "message": "The email has been successfully verified and the user has been registered.",
            "user_id": created_client.id,
        }

    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or username already exists."
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the user."
        )
    

#-- password reset --#
sec_field_name = 'secret'
exp_field_name = 'expiry'
password_reset_reason = "password_reset"

def get_password_reset_link_ttl():
    return TEST_PASSWORD_LINK_TTL if env_is_test() else PASSWORD_LINK_TTL

async def send_password_reset_mail(
    email: str, 
    session: AsyncSession,
    redis_client: redis.Redis,
    ttl_in_secs: int = get_password_reset_link_ttl(),
):
    """
        `email:reason` is the hset's key 
        the reason is the field
        the code is the value
    """
    query = await session.execute(
        select(User)
        .where(User.email == email)
    )
    user = query.scalars().one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found!"
        )


    # Check if the code exists in the cache
    user_key = hset_password_reset_key(email)
    secret_exists = await redis_client.hget(user_key, sec_field_name)

    if secret_exists: #When a result is found
        expiry = await redis_client.hget(user_key, exp_field_name)

        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            detail = {
                "message" : "Please wait before requesting a new password link.",
                "expiry" : (expiry.decode() 
                        if isinstance(expiry,bytes) 
                        else expiry)
                }
        )
    else: # When no result is found
        try:
            # Generate a new five-digit code
            secret = secrets.token_urlsafe()

            # call the email function and send the email
            # extract the email content from the template
            email_template_content = read_email_from_html_template_name('password_reset_template')
            property_street_address = "Port Harcourt"
            
            email_string = substituted_string(
                email_template_content,
                {
                    "reset_link":f"https://propertystreet.ng/reset-password?token={user.id}_{secret}",
                    "property_street_address": property_street_address
                }
            )
            from_address="team@stackfinancialsolutions.com"
            subject="Password Reset Request"
            from_name="Property street"
            #to_name="Customer"

            send_email(
                from_email=from_address,
                to_email=email,
                from_name=from_name,
                subject=subject,
                html_email=email_string
            )

            # create an instance of the user with the data
            await redis_client.hset(user_key, sec_field_name, secret)

            # get the current time and add the ttl
            current_time = datetime.now(timezone.utc)
            expiry_time = (current_time + timedelta(seconds=ttl_in_secs)).isoformat()

            # save the ttl_time in the ttl field of the user's key
            await redis_client.hset(user_key, exp_field_name, expiry_time)

            # set an expiry for the user key
            # explicitly convert the expiry_time_in_secs to int
            # to avoid `value is not an integer or out of range` error
            await redis_client.expire(user_key, int(ttl_in_secs)) 

            return {
                "detail":"Password reset email sent!",
                "expiry": expiry_time
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Something went wrong sending a password reset mail. Please try again later.",
                headers={"X-Error": "Server error"},
            )


_exc = HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail = "Malformed request or link expired."
)

def hset_password_reset_key(email):
    return f'{email}:{password_reset_reason}'


async def check_password_reset_email_validity(
    email: str,
    secret: str,
    redis_client: Redis,
):

    """
        `email:reason` is the hset's key 
        the reason is the field
        the code is the value
    """
    # Check if the secret exists in the cache
    user_key = hset_password_reset_key(email)
    cached_secret = await redis_client.hget(user_key, sec_field_name)

    decoded_secret = cached_secret.decode() if isinstance(cached_secret, bytes) else cached_secret
    if not cached_secret or (decoded_secret != secret): #When a result is found
        if DEBUG:
            logger.info("Cached_secret malformed.")
        raise _exc
    

async def process_token_validate_user(token:str, session: AsyncSession):
    split_token = token.split('_', maxsplit=1)
    user_id = int(split_token[0])
    secret = split_token[1]

    user = await session.get(User, user_id)
    if not user:
        raise _exc
    
    return user, secret
    

async def change_password(
    password: str,
    token: str,
    session: AsyncSession,
    redis_client: Redis,
):
    split_token = token.split('_', maxsplit=1)
    user_id = int(split_token[0])
    secret = split_token[1]

    
    user = await session.get(User, user_id)
    if not user:
        if DEBUG:
            logger.info(f'**User not found')
        raise _exc
    
    email = user.email

    # check validity of request
    await check_password_reset_email_validity(email, secret, redis_client)

    # check that password ain't same
    result = await authenticate_user(session, email, password)
    if result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password can't be same as old."
        )
    else:
        hash = get_password_hash(password)
        user.password_hash = hash
        session.add(user)
        await session.commit()
        # delete the key
        key = hset_password_reset_key(email)
        await redis_client.delete(key)
    