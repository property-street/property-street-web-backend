import cloudinary.api
from sqlalchemy import text
from sqlalchemy.future import select

from ..models import CloudDeletionOutbox
from property_street_backend.config.cloudinary import (
    delete_image,
    cloudinary_deletion_lock_expiry
)
from property_street_backend.app.initiator import logger
from property_street_backend.config.settings import DEBUG
from property_street_backend.app.celery_config import celery_app
from property_street_backend.config.redis_connection_manager import get_sync_redis
from property_street_backend.config.postgres_connection_manager import runtime_sync_session_maker
#from property_street_backend.config.context_sessions import acquire_redis_lock, release_redis_lock

LOCK_KEY = "cloudinary_deletion_lock"

@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=10)
def routine(self):
    redis = get_sync_redis()

    if not redis.set(LOCK_KEY, "1", nx=True, ex=cloudinary_deletion_lock_expiry()):
        return

    try:
        SessionLocal = runtime_sync_session_maker()
        with SessionLocal() as db:
            jobs = db.execute(select(CloudDeletionOutbox)).scalars().all()
            if DEBUG:
                logger.info(f"**CELERY DB: {db.execute(text("select current_database()")).scalar()}")
                logger.info(f"**Jobs: {jobs}")

            for job in jobs:
                try:
                    delete_image(job.public_id)
                except cloudinary.api.NotFound:
                    pass

                db.delete(job)

            db.commit()
    finally:
        redis.delete(LOCK_KEY)
