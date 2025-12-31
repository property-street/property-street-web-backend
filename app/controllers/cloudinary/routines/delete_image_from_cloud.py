import asyncio
import cloudinary.api
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import CloudDeletionOutbox
from property_street_backend.config.settings import (
    DEBUG,
)
from property_street_backend.config.cloudinary import (
    delete_image,
    cloudinary_deletion_lock_expiry
)
from property_street_backend.app.initiator import logger
from property_street_backend.app.celery_config import celery_app
from property_street_backend.config.redis_connection_manager import get_redis
from property_street_backend.config.postgres_connection_manager import AsyncSessionLocal
from property_street_backend.config.context_sessions import acquire_redis_lock, release_redis_lock

LOCK_KEY = "cloudinary_deletion_lock"

@celery_app.task
def routine():
    new_loop = False  # Flag to track if we create a new loop

    try:
        try:
            loop = asyncio.get_running_loop()  # Get the current event loop
        except RuntimeError:
            loop = asyncio.new_event_loop()  # Create a new loop if none exists
            asyncio.set_event_loop(loop)
            new_loop = True  # Mark that we created a new loop
        
        # Run the task in the loop
        loop.run_until_complete(run_task())
    
    finally:
        if new_loop:  # Only close if we created a new loop
            loop.close()


async def run_task():
    """Executes the offload task for deleted cloud_images"""
    async with get_redis() as redis_client:
        if not await acquire_redis_lock(redis_client, LOCK_KEY, cloudinary_deletion_lock_expiry()):
            if DEBUG:
                logger.info("**Another instance is already running. Skipping execution.")
            return
        try:
            async with AsyncSessionLocal() as db:
                db: AsyncSession
                pending_jobs = (await db.execute(select(CloudDeletionOutbox))).scalars().all()
                for job in pending_jobs:
                    try:
                        delete_image(job.public_id)
                    except cloudinary.api.NotFound:
                        pass
                    await db.delete(job)
                await db.commit()
        finally:
            await release_redis_lock(redis_client, LOCK_KEY)