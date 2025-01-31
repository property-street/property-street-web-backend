from fastapi import FastAPI
import logging
import redis.asyncio as redis

from property_street_backend.config.settings import (
    environment,
    REDIS_CACHE_DB,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)\


app = FastAPI()

async def redis_client():
    host = 'localhost' if environment == 'development' else 'redis'
    client = await redis.Redis(
        host=host, 
        port=6379, 
        db=REDIS_CACHE_DB, #db2 for property street dev cache; 1 should be for production
    )
    try:
        await client.config_set('notify-keyspace-events', 'Ex')
        yield client
    finally:
        await client.aclose()

