from fastapi import FastAPI, APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError

from property_street_backend.app.models import User
from property_street_backend.app.database import get_db
from property_street_backend.app.schemas.auth_schemas import UserRegistrationSchema, TokenData
from property_street_backend.config.settings import JWT_SECRET_KEY, JWT_EXPIRATION_DELTA, JWT_ALGORITHM


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
async def check_username_email_availability(db: AsyncSession, username: str, email: str) -> dict:
    result = {"username": "available", "email": "available"}
    
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