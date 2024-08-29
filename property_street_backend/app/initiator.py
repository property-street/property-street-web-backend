from fastapi import FastAPI
import logging
import redis.asyncio as redis

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)\
#logging.basicConfig(level=logging.DEBUG)  # Set the logging level to DEBUG or lower as needed


app = FastAPI()

async def redis_client():
    client = await redis.Redis(
        host='localhost', 
        port=6379, 
        db=2, #db2 for property street main cache; 3 should be for production
    )
    try:
        yield client
    finally:
        await client.aclose()