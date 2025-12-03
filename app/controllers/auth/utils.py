from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.config.settings import (
    DEBUG,
    ADMIN_EMAIL,
    ADMIN_USERNAME,
    ADMIN_PASSWORD,
)
from property_street_backend.app.initiator import logger
from property_street_backend.app.controllers.auth.services import (
    verify_password,
    get_password_hash,
)
from property_street_backend.app.controllers.actors.models import User

async def ensure_admin_user(session: AsyncSession):
    result = await session.execute(
        select(User)
        .where(User.is_admin == True)
    )
    admin: User = result.scalar_one_or_none()

    if not admin:
        # Create the admin for the first time
        admin = User(
            email=ADMIN_EMAIL,
            username=ADMIN_USERNAME,
            password_hash=get_password_hash(ADMIN_PASSWORD),
            is_admin=True,
            user_role='admin'
        )
        session.add(admin)
        await session.commit()
        if DEBUG:
            logger.info("✅ Admin user created.")
        return admin

    # Update existing admin if credentials differ
    updated = False
    if admin.email != ADMIN_EMAIL:
        admin.email = ADMIN_EMAIL
        updated = True
    if admin.username != ADMIN_USERNAME:
        admin.email = ADMIN_USERNAME
        updated = True
    if not verify_password(ADMIN_PASSWORD, admin.password_hash):
        admin.password_hash = get_password_hash(ADMIN_PASSWORD)
        updated = True

    if updated:
        await session.commit()
        if DEBUG:
            logger.info("⚙️ Admin credentials updated to match environment.")
    else:
        if DEBUG:
            logger.info("✅ Admin already up-to-date.")
    
    return admin