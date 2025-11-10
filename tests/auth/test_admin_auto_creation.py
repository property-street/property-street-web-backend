import pytest
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.config.settings import (
    ADMIN_EMAIL,
    ADMIN_USERNAME,
    ADMIN_PASSWORD,
)
from property_street_backend.app.controllers.actors.models import User
from property_street_backend.app.controllers.auth.services import verify_password
from property_street_backend.config.postgres_connection_manager import get_postgres_instance

@pytest.mark.asyncio
async def test_admin_auto_creation(app_subprocess):

    async with get_postgres_instance() as session:
        session: AsyncSession
        user = (await session.execute(
            select(User)
            .where(
                User.email == ADMIN_EMAIL,
            )
        )).scalar_one_or_none()
        assert user
        assert user.is_admin
        assert user.user_role == 'admin'
        assert user.username == ADMIN_USERNAME
        assert verify_password(ADMIN_PASSWORD,user.password_hash)