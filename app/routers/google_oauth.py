from fastapi import (
    Depends,
    Request,
    APIRouter,
    HTTPException,
    Response,
)
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.database import get_db
from property_street_backend.app.initiator import oauth
from property_street_backend.app.models import User, GoogleOAuthDetail
from property_street_backend.config.settings import GOOGLE_REDIRECT_URL
from property_street_backend.app.controllers.auth.services import fetch_access_token


router = APIRouter(prefix="/google_oauth", tags=["google_oauth"])

@router.get("/login/google")
async def login_google(request: Request):
    return await oauth.google.authorize_redirect(request, GOOGLE_REDIRECT_URL)

@router.get("/callback")
async def auth_callback(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
        user_data = await oauth.google.parse_id_token(request, token)
        if not user_data:
            # Redirect to frontend with error
            frontend_url = "http://localhost:3000" if "localhost" in str(request.base_url) else "https://propertystreet.ng"
            return response.redirect(f"{frontend_url}/signin?error=authentication_failed")

        # Check if user exists
        result = await db.execute(select(User).where(User.email == user_data["email"]))
        existing_user = result.scalars().first()

        if not existing_user:
            email = user_data["email"]
            # Register new user
            new_user = User(
                email=email,
                username=email.split('@')[0],
                google_oauth_detail=GoogleOAuthDetail(
                    google_id=user_data["sub"],  # Store Google ID
                    profile_picture=user_data.get("picture")
                )
            )
            db.add(new_user)
            await db.commit()
            await db.refresh(new_user)
            access_token = fetch_access_token(new_user)
        else:
            access_token = fetch_access_token(existing_user)

        # Redirect to frontend with access token
        frontend_url = "http://localhost:3000" if "localhost" in str(request.base_url) else "https://propertystreet.ng"
        return response.redirect(f"{frontend_url}/google_oauth/callback?access_token={access_token}")

    except Exception as e:
        # Redirect to frontend with error
        frontend_url = "http://localhost:3000" if "localhost" in str(request.base_url) else "https://propertystreet.ng"
        return response.redirect(f"{frontend_url}/signin?error=authentication_failed")
