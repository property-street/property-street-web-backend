"""
OAuth routes for Google OAuth authentication.
"""
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.database import get_db
from property_street_backend.app.initiator import oauth
from property_street_backend.config.settings import GOOGLE_REDIRECT_URL
from .services import (
    get_or_create_user_from_google,
    generate_oauth_access_token,
    get_frontend_url
)


router = APIRouter(prefix="/oauth", tags=["oauth"])


@router.get("/login/google")
async def initiate_google_oauth(request: Request):
    """
    Initiate Google OAuth flow.
    
    Returns:
        Redirect to Google OAuth consent screen
    """
    return await oauth.google.authorize_redirect(request, GOOGLE_REDIRECT_URL)


@router.get("/google/callback")
async def google_oauth_callback(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """
    Google OAuth callback endpoint.
    
    Handles:
    1. Token exchange with Google
    2. User data parsing
    3. User creation or retrieval
    4. Access token generation
    5. Redirect to frontend with token
    
    Args:
        request: FastAPI Request
        response: FastAPI Response
        db: Database session
    
    Returns:
        Redirect response to frontend with access_token or error
    """
    try:
        # Exchange authorization code for token
        token = await oauth.google.authorize_access_token(request)
        
        # Parse and validate Google ID token
        user_data = await oauth.google.parse_id_token(request, token)
        
        # Get or create user in database
        user, is_new = await get_or_create_user_from_google(user_data, db)
        
        # Generate access token for our application
        access_token = await generate_oauth_access_token(user)
        
        # Determine frontend URL and redirect with token
        frontend_url = get_frontend_url(request)
        return response.redirect(
            f"{frontend_url}/google_oauth/callback?access_token={access_token}"
        )

    except Exception as e:
        # Log the error in production
        frontend_url = get_frontend_url(request)
        error_message = "authentication_failed"
        return response.redirect(
            f"{frontend_url}/signin?error={error_message}"
        )
