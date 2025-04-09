import logging
from fastapi import FastAPI
from redis.asyncio import Redis

from property_street_backend.config.settings import (
    REDIS_CACHE_DB,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    REDIS_HOST,
    PROD_REDIS_CACHE_DB,
)
from authlib.integrations.starlette_client import OAuth
from property_street_backend.config.settings import DEBUG
from property_street_backend.config.redis_connection_manager import (
    get_redis_instance,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)\


app = FastAPI()

oauth = OAuth()
# Google OAuth
oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    authorize_url="https://accounts.google.com/o/oauth2/auth",
    token_url="https://oauth2.googleapis.com/token",
    client_kwargs={"scope": "openid email profile"},
)

async def get_redis_client():
    client = await Redis(
        host=REDIS_HOST, 
        port=6379, 
        db=REDIS_CACHE_DB, #db1 for property street dev cache; 0 should be for production
    )
    try:
        await client.config_set('notify-keyspace-events', 'Ex')
        yield client
    finally:
        await client.aclose()

async def get_redis():
    async for redis_client in get_redis_instance():
        yield redis_client