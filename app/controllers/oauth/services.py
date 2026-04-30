"""
OAuth service layer for handling Google OAuth authentication.
"""
from typing import Tuple
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from property_street_backend.app.models import User, GoogleOAuthDetail
from property_street_backend.app.controllers.auth.services import fetch_access_token


async def get_or_create_user_from_google(
    user_data: dict,
    db: AsyncSession
) -> Tuple[User, bool]:
    """
    Get existing user or create new one from Google OAuth data.
    
    Args:
        user_data: Google user data dict containing 'email', 'sub', 'picture'
        db: AsyncSession database connection
    
    Returns:
        Tuple of (User object, is_new_user: bool)
    
    Raises:
        HTTPException: If user data is invalid
    """
    if not user_data or not user_data.get("email"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Google user data"
        )

    email = user_data["email"]
    
    # Check if user exists
    result = await db.execute(select(User).where(User.email == email))
    existing_user = result.scalars().first()

    if existing_user:
        return existing_user, False

    # Create new user from Google data
    username = email.split('@')[0]
    new_user = User(
        email=email,
        username=username,
        google_oauth_detail=GoogleOAuthDetail(
            google_id=user_data.get("sub"),
            profile_picture=user_data.get("picture")
        )
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    return new_user, True


async def generate_oauth_access_token(user: User) -> str:
    """
    Generate access token for OAuth authenticated user.
    
    Args:
        user: User object
    
    Returns:
        Access token string
    """
    return fetch_access_token(user)


def get_frontend_url(request) -> str:
    """
    Determine frontend URL based on request context.
    
    Args:
        request: FastAPI Request object
    
    Returns:
        Frontend URL string
    """
    # Check if running in local development
    if "localhost" in str(request.base_url):
        return "http://localhost:3000"
    return "https://propertystreet.ng"
