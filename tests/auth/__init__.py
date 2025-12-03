from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import User
from property_street_backend.app.controllers.auth.services import create_user
from property_street_backend.app.schemas.auth_schemas import UserRegistrationSchema

user_data = UserRegistrationSchema(
    email="test@example.com",
    username="testuser",
    password="password123",
    first_name="John",
    last_name="Doe",
)

async def create_test_user(
    db: AsyncSession,
    user_data = user_data
) -> User:
    return await create_user(db, user_data)