from sqlalchemy import func
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
from property_street_backend.app.controllers.assets.models import Asset

async def ensure_admin_user(session: AsyncSession):
    if not (ADMIN_EMAIL and ADMIN_USERNAME and ADMIN_PASSWORD):
        raise RuntimeError(
            "❌ ADMIN_EMAIL, ADMIN_USERNAME, ADMIN_PASSWORD must be set in .env.backend"
        )
    
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
    if admin.user_role != 'admin':
        admin.user_role='admin'
        updated = True
    if admin.email != ADMIN_EMAIL:
        admin.email = ADMIN_EMAIL
        updated = True
    if admin.username != ADMIN_USERNAME:
        admin.username = ADMIN_USERNAME
        updated = True
    if not verify_password(ADMIN_PASSWORD, admin.password_hash):
        admin.password_hash = get_password_hash(ADMIN_PASSWORD)
        updated = True

    if updated:
        await session.commit()
        # if DEBUG:
        logger.info("⚙️ Admin credentials updated to match environment.")
    else:
        # if DEBUG:
        logger.info("✅ Admin already up-to-date.")
    
    return admin

async def user_ui_metadata(db: AsyncSession, user: User, is_authenticated: bool) -> dict:
    property_count = (await db.execute(
        select(func.count(Asset.id)).where(Asset.agent_id == user.id)
    )).scalar() or 0
    return {
        "id":user.id, 
        'username': user.username,
        'profile_avatar_url': user.profile_avatar.secure_url if user.profile_avatar else None,
        'user_role': user.user_role,
        'is_authenticated': is_authenticated,
        'agent_details': {
            'property_count': property_count,
        }
    } if user else {}
