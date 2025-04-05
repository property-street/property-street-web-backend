from redis.asyncio import Redis, ConnectionPool

from property_street_backend.config.settings import (
    REDIS_HOST,
    TEST_REDIS_CACHE_DB,
    PROD_REDIS_CACHE_DB,
)

# Globals
_redis_instances = {}


# Redis Factory
async def get_redis_instance(env: str = None) -> Redis:
    global _redis_instances

    db = TEST_REDIS_CACHE_DB if env == "test" else PROD_REDIS_CACHE_DB
    key = f"{env}_{db}"
    
    if key not in _redis_instances:
        pool = ConnectionPool.from_url(f"redis://{REDIS_HOST}:6379/{db}")
        redis_client = Redis(connection_pool=pool)
        # await redis_client.config_set('notify-keyspace-events', 'Ex')
        _redis_instances[key] = redis_client
    
    return _redis_instances[key]
