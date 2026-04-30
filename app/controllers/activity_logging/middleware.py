import time

from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware

from property_street_backend.app.controllers.actors.models import User
from property_street_backend.app.controllers.activity_logging.enums import ActivityStatusChoice
from property_street_backend.app.controllers.activity_logging.models import ActivityLog
from property_street_backend.log_config.logger_config import log_error


class ActivityLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        action = f"{request.method} {request.url.path}"
        status_code = None

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except HTTPException as exc:
            log_error(f"{action} {exc}")
            status_code = exc.status_code
            raise
        except Exception as exc:
            log_error(f"{action} {exc}")
            status_code = 500
            raise
        finally:
            user: User = getattr(request.state, "user", None)
            db: AsyncSession = getattr(request.state, "db", None)
            if user and db and status_code is not None:
                try:
                    db.add(
                        ActivityLog(
                            user_id=user.id,
                            action=action,
                            status=(
                                ActivityStatusChoice.success
                                if status_code < 400
                                else ActivityStatusChoice.failed
                            ),
                            method=request.method,
                            endpoint=request.url.path,
                            ip_address=request.client.host if request.client else None,
                            user_agent=request.headers.get("user-agent"),
                            response_status_code=status_code,
                            response_time_ms=int((time.time() - start_time) * 1000),
                        )
                    )
                    await db.commit()
                except Exception:
                    await db.rollback()
