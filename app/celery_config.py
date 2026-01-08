import os
import sys
from celery import Celery


# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from property_street_backend.config.settings import (
    REDIS_URL,
    TEST_CART_OFFLOAD_SCHEDULE,
    PROD_CART_OFFLOAD_SCHEDULE,
    AGENT_NOTIFICATION_ENTRY_OFFLOAD_SCHEDULE,
    TEST_AGENT_NOTIFICATION_ENTRY_OFFLOAD_SCHEDULE,
)
from property_street_backend.config.cloudinary import routine_interval as cloudinary_routine_interval

TEST_ENV = os.getenv("TEST_ENV")

# cart routine time
cart_offload_schedule_secs = TEST_CART_OFFLOAD_SCHEDULE if TEST_ENV else PROD_CART_OFFLOAD_SCHEDULE
# agent stall notification deletion schedule
agent_stall_notification_deletion_schedule_secs = TEST_AGENT_NOTIFICATION_ENTRY_OFFLOAD_SCHEDULE if TEST_ENV else AGENT_NOTIFICATION_ENTRY_OFFLOAD_SCHEDULE

celery_app = Celery(
    'celery_config',
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.conf.update(
    broker_connection_retry_on_startup=True,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    beat_schedule={
        # 'offload-cart-items-to-db': {
        #     'task': 'property_street_backend.app.controllers.cart.routines.offload_task.routine',
        #     'schedule': cart_offload_schedule_secs,  # Runs every expiry seconds
        #     'args': (env,),  # Arguments for the task
        # },
        # 'delete_stall_agent_notification_entry': {
        #     'task': 'property_street_backend.app.controllers.asset_request.routines.delete_stall_agent_notification_entries.routine',
        #     'schedule': agent_stall_notification_deletion_schedule_secs,  # Runs every expiry seconds
        #     'args': (env,),  # Arguments for the task
        # },
        'delete_stale_images_from_cloudinary': {
            'task': 'property_street_backend.app.controllers.cloudinary.routines.delete_image_from_cloud.routine',
            'schedule': cloudinary_routine_interval(),  # Runs every expiry seconds
        },
        #...
    },
)

# Ensure tasks are discovered
celery_app.autodiscover_tasks([
    # 'property_street_backend.app.controllers.cart.routines.offload_task',
    # 'property_street_backend.app.controllers.asset_request.routines.delete_stall_agent_notification_entries',
    'property_street_backend.app.controllers.cloudinary.routines.delete_image_from_cloud',
    #...
])
