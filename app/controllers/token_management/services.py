from datetime import datetime, timezone
from typing import Dict, List

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from property_street_backend.app.controllers.actors.models import User
from property_street_backend.app.controllers.auth.models import RefreshSession


def serialize_refresh_session(session: RefreshSession) -> Dict:
    return {
        "id": session.id,
        "ip_address": session.ip_address,
        "user_agent": session.user_agent,
        "is_revoked": session.is_revoked,
        "expires_at": session.expires_at.isoformat() if session.expires_at else None,
        "last_used_at": session.last_used_at.isoformat() if session.last_used_at else None,
    }


async def list_user_sessions(db: AsyncSession, user: User) -> List[Dict]:
    result = await db.execute(
        select(RefreshSession)
        .where(RefreshSession.user_id == user.id)
        .order_by(RefreshSession.id.desc())
    )
    return [serialize_refresh_session(session) for session in result.scalars().all()]


async def revoke_refresh_token(db: AsyncSession, user: User, token_id: int) -> Dict:
    session = (
        await db.execute(
            select(RefreshSession).where(
                RefreshSession.id == token_id,
                RefreshSession.user_id == user.id,
            )
        )
    ).scalars().first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Refresh token not found")

    if session.is_revoked:
        return {"detail": "Refresh token already revoked"}

    session.is_revoked = True
    session.last_used_at = datetime.now(timezone.utc)
    db.add(session)
    await db.commit()
    return {"detail": "Refresh token revoked"}


async def revoke_all_user_tokens(db: AsyncSession, user: User) -> Dict:
    result = await db.execute(select(RefreshSession).where(RefreshSession.user_id == user.id))
    for session in result.scalars().all():
        session.is_revoked = True
        session.last_used_at = datetime.now(timezone.utc)
        db.add(session)
    await db.commit()
    return {"detail": "All refresh sessions revoked"}
