import os
import sys
from celery import Celery


# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from property_street_backend.config.settings import (
    REDIS_HOST,
    CART_OFFLOAD_SCHEDULE,
)

celery_app = Celery(
    'celery_config',
    broker=f'redis://{REDIS_HOST}:6379/0',
    backend=f'redis://{REDIS_HOST}:6379/0'
)

celery_app.conf.update(
    broker_connection_retry_on_startup=True,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    beat_schedule={
        'offload-cart-items-to-db': {
            'task': 'bot.tasks.routine',
            'schedule': CART_OFFLOAD_SCHEDULE,  # Runs every expiry seconds
            'args': (),  # Arguments for the task
        },
        #...
    },
)

# Ensure tasks are discovered
celery_app.autodiscover_tasks(['property_street_backend.app.controllers.cart.tasks'])
