import random 
import redis.asyncio as redis
from jose import jwt, JWTError
from sqlalchemy.future import select
from passlib.context import CryptContext
from sqlalchemy.exc import IntegrityError
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, APIRouter, HTTPException, status, Depends

from property_street_backend.app.models import (
    User,
)
from property_street_backend.app.schemas.auth_schemas import (
    UserRegistrationSchema, 
    TokenData, 
    ProbeUserExistenceSchema,
    SendEmailCodeSchema,
    SignupCodeVerificationSchema
)
from property_street_backend.app.utils.store import (
    read_email_from_html_template_name,
    substituted_string,
    send_email,
)
from property_street_backend.config.settings import JWT_SECRET_KEY, JWT_EXPIRATION_DELTA, JWT_ALGORITHM
from property_street_backend.app.database import get_db


import logging

logger = logging.getLogger(__name__)

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

# signin
async def authenticate_user(db: AsyncSession, login: str, password: str):
    # Check if the login is either a username or an email
    user_query = select(User).filter((User.username == login) | (User.email == login))
    
    # Execute the query
    result = await db.execute(user_query)
    user = result.scalars().first()

    if not user:
        return False

    # Verify the provided password against the stored password hash
    if not verify_password(password, user.password_hash):
        return False

    return user


# user existence
async def check_username_email_availability(db: AsyncSession, user_data: ProbeUserExistenceSchema) -> dict:
    username = user_data.username
    email = user_data.email

    result = {
        "username": "available",
        "email": "available"
    }
    
    # Check if the username exists
    user_by_username = await db.execute(select(User).filter(User.username == username))
    user_by_username = user_by_username.scalars().first()
    
    if user_by_username:
        result["username"] = "unavailable"
    
    # Check if the email exists
    user_by_email = await db.execute(select(User).filter(User.email == email))
    user_by_email = user_by_email.scalars().first()
    
    if user_by_email:
        result["email"] = "unavailable"
    
    return result


# Signup
async def create_user(
    db: AsyncSession, 
    user_data: UserRegistrationSchema
):
    username = user_data.username or user_data.email.strip().split('@')[0]
    existing_user = await db.execute(
        select(User).filter((User.email == user_data.email) | (User.username == username))
    )
    existing_user = existing_user.scalars().first()
    
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email or Username already exists")

    hashed_password = get_password_hash(user_data.password)
    # clone the model so deleting the password entry wont affect the original schema
    cloned_data = user_data.model_copy()
    # convert the user_data to a dictionary
    user_map = vars(cloned_data)
    # remove the password field
    user_map.pop('password')

    # instantiate a user object
    user = User(
        password_hash=hashed_password,
        **user_map,
    )
    
    try:
        db.add(user)
        # Writes changes to the database but does not commit them.
        # Ensure the user is added and has an ID
        await db.flush()  
        # Commit the transaction to make changes permanent
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
    return created_user.agent_profile  


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
    requester_data: SendEmailCodeSchema, 
    redis_client: redis.Redis,
    expiry_time_in_secs: int,
):
    # print(f"**expiry_time_in_secs: {expiry_time_in_secs}")

    email_address = requester_data.email
    user_name = requester_data.username if requester_data.username else "User"
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
        ttl = await redis_client.hget(user_key, "ttl")
        return {
            "email_status": "Dispatched",
            "message": "Please wait before requesting a new code.",
            "ttl": ttl
        }
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
            await redis_client.hset(user_key, reason, new_code)

            # get the current time and add the ttl
            current_time = datetime.now(timezone.utc)
            ttl_time = (current_time + timedelta(seconds=expiry_time_in_secs)).isoformat()

            # save the ttl_time in the ttl field of the user's key
            await redis_client.hset(user_key, "ttl", ttl_time)

            # set an expiry for the user key
            # explicitly convert the expiry_time_in_secs to int
            # to avoid `value is not an integer or out of range` error
            await redis_client.expire(user_key, int(expiry_time_in_secs)) 

            return {
                "email_status":"DispatchedNow",
                "message":"A new verification code has been sent to your email.",
                "ttl": ttl_time
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal Server Error: Something went wrong. Please try again later.",
                headers={"X-Error": "Server error"},
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
    if input_code != user_email_code.decode('utf-8'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code."
        )

    # Hash the user's password before saving it to the database
    # hashed_password = get_password_hash(requester_data.password)

    # get the client type User or Agent
    client_type = requester_data.client_type.lower()
    
    user_data = UserRegistrationSchema(
        email=email_address,
        username=requester_data.username,
        password=requester_data.password,
    )

    created_client = None  # Initialize variable to avoid UnboundLocalError

    if client_type == 'client':
        # Create the new user instance
        created_client = await create_user(
            db = db,
            user_data = user_data   
        )
    elif client_type == 'agent':
        agent = await create_agent(
            db = db,
            user_data = user_data
        )
        created_client = agent.user

    # extracting names from the fullname
    name_list = requester_data.fullname.split()
    
    # adding the first_name
    created_client.first_name = name_list[0]
    
    # adding last_name
    if len(name_list) > 1:
        created_client.last_name = name_list[-1]
    
    # Adding other_names (middle names or any names between the first and last)
    if len(name_list) > 2:
        created_client.other_names = " ".join(name_list[1:-1])

    try:
        # Add the new user to the session and commit the transaction
        db.add(created_client)
        await db.commit()
        await db.refresh(created_client)

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