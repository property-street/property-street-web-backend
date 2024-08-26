from fastapi import FastAPI, APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
import random 
import redis.asyncio as redis

from property_street_backend.app.models import (
    User,
    EmailManagementModel,
)
from property_street_backend.app.schemas.auth_schemas import (
    UserRegistrationSchema, 
    TokenData, 
    ProbeUserExistenceSchema,
    SendEmailCodeSchema
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

# crud level
# Signin
async def authenticate_user(db: AsyncSession, username: str, password: str):
    user = await db.execute(select(User).filter(User.username == username))
    user = user.scalars().first()
    if not user:
        return False
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
async def create_user(db: AsyncSession, user_data: UserRegistrationSchema):
    username = user_data.username or user_data.email.strip().split('@')[0]
    existing_user = await db.execute(
        select(User).filter((User.email == user_data.email) | (User.username == username))
    )
    existing_user = existing_user.scalars().first()
    
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email or Username already exists")

    hashed_password = get_password_hash(user_data.password)
    user = User(
        email=user_data.email,
        username=username,
        password_hash=hashed_password
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

# Session token validity
async def decode_user_from_token(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
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


async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    await db.delete(user)
    await db.commit()
    return user


async def send_email_verification_code(requester_data: SendEmailCodeSchema, redis_client: redis.Redis):
    email_address = requester_data.email
    user_name = requester_data.username if requester_data.username else "User"
    reason = "email_verification"
    one_minute = 60
    expiry_time = 5 * one_minute #5 miutes expiry time 

    """
        `email:reason` is the hset's key 
        the reason is the field
        the code is the value
    """

    # Check if the code exists in the cache
    user_key = f'{email_address}:{reason}'
    user_email_code = await redis_client.hget(user_key, reason)

    if user_email_code: #When a result is found
        return {"message": "Please wait before requesting a new code."}
    else: # When no result is found
        try:
            # create a new cache object for the user
        
            # Generate a new five-digit code
            new_code = '{:05d}'.format(random.randint(0, 99999))

            # call the email function and send the email
            # extract the email content from the template
            email_template_content = read_email_from_html_template_name('email_verification_code_template')
            
            email_string = substituted_string(
                email_template_content,
                {
                    "user_name":user_name,
                    "verification_code":new_code,
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
            # set an expiry
            await redis_client.expire(user_key, expiry_time) 

            return {"message":"A new verification code has been sent to your email"}
        except Exception as e:
            print(e)
            return {"message":"An error occured"}