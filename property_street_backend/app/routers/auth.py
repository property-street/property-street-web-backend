from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.database import get_db
from property_street_backend.app.schemas.auth_schemas import UserRegistrationSchema, UserSigninSchema, Token, TokenData
from property_street_backend.app.controllers.auth import create_user, authenticate_user, decode_user_from_token, fetched_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserRegistrationSchema, db: AsyncSession = Depends(get_db)):
    try:
        user = await create_user(db, user_data)
    except HTTPException as e:
        raise e
    return fetched_access_token(user)


@router.post("/signin", response_model=Token, status_code=status.HTTP_200_OK)
async def signin_for_access_token(user_data: UserSigninSchema, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, user_data.username, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return fetched_access_token(user)


@router.get("/fetch-user")
async def fetch_user(current_user: TokenData = Depends(decode_user_from_token)):
    return {"username": current_user.username}