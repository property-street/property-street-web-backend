from fastapi import FastAPI
import logging
import redis.asyncio as redis
from property_street_backend.config.settings import environment

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)\
#logging.basicConfig(level=logging.DEBUG)  # Set the logging level to DEBUG or lower as needed


app = FastAPI()

async def redis_client():
    host = 'localhost' if environment == 'development' else 'redis'
    cache_db = 2 if environment == 'development' else 1
    client = await redis.Redis(
        host=host, 
        port=6379, 
        db=cache_db, #db2 for property street dev cache; 1 should be for production
    )
    try:
        await client.config_set('notify-keyspace-events', 'Ex')
        yield client
    finally:
        await client.aclose()

