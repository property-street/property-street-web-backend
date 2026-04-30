"""
Tests for Google OAuth functionality from frontend perspective.

These tests verify that the OAuth endpoints work correctly for user signup and signin.
"""
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.future import select

from property_street_backend.app.models import User, GoogleOAuthDetail


class TestGoogleOAuthFrontendIntegration:
    """Test Google OAuth functionality as called by frontend."""

    @pytest.mark.asyncio
    async def test_oauth_signup_new_user_creation(
        self,
        client__fixture
    ):
        """Test OAuth callback creates new user (signup flow)."""
        client = client__fixture["http_client"]
        db = client__fixture["db"]

        # Mock Google OAuth token exchange and user data for new user
        mock_token = {"access_token": "google_token"}
        mock_user_data = {
            "email": "newsignup@example.com",
            "sub": "google_user_456",
            "picture": "https://example.com/photo.jpg"
        }

        with patch('property_street_backend.app.controllers.oauth.routes.oauth.google.authorize_access_token', return_value=mock_token), \
            patch('property_street_backend.app.controllers.oauth.routes.oauth.google.parse_id_token', return_value=mock_user_data):

            response = await client.get("/oauth/google/callback")

            # Should redirect to frontend callback URL with access token
            assert response.status_code == 302  # Found (redirect)
            assert "google_oauth/callback?access_token=" in str(response.headers.get("location"))

            # Verify new user was created in database
            result = await db.execute(select(User).where(User.email == "newsignup@example.com"))
            user = result.scalars().first()
            assert user is not None
            assert user.username == "newsignup"
            assert user.google_oauth_detail is not None
            assert user.google_oauth_detail.google_id == "google_user_456"
            assert user.google_oauth_detail.profile_picture == "https://example.com/photo.jpg"

    @pytest.mark.asyncio
    async def test_oauth_signin_existing_user_login(
        self,
        client__fixture
    ):
        """Test OAuth callback for existing user (signin flow)."""
        client = client__fixture["http_client"]
        db = client__fixture["db"]

        # Create existing user with Google OAuth details
        existing_user = User(
            email="existingsignin@example.com",
            username="existingsignin",
            google_oauth_detail=GoogleOAuthDetail(
                google_id="existing_google_id_789",
                profile_picture="https://example.com/old_photo.jpg"
            )
        )
        db.add(existing_user)
        await db.commit()

        # Mock Google OAuth for existing user signin
        mock_token = {"access_token": "google_token"}
        mock_user_data = {
            "email": "existingsignin@example.com",
            "sub": "existing_google_id_789",
            "picture": "https://example.com/new_photo.jpg"
        }

        with patch('property_street_backend.app.controllers.oauth.routes.oauth.google.authorize_access_token', return_value=mock_token), \
             patch('property_street_backend.app.controllers.oauth.routes.oauth.google.parse_id_token', return_value=mock_user_data):

            response = await client.get("/oauth/google/callback")

            # Should redirect to frontend callback URL with access token
            assert response.status_code == 302
            assert "google_oauth/callback?access_token=" in str(response.headers.get("location"))

            # Verify existing user still exists and wasn't duplicated
            result = await db.execute(select(User).where(User.email == "existingsignin@example.com"))
            users = result.scalars().all()
            assert len(users) == 1  # Should only be one user
            user = users[0]
            assert user.username == "existingsignin"
            assert user.google_oauth_detail.google_id == "existing_google_id_789"