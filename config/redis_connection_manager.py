from redis.asyncio import Redis, ConnectionPool
from property_street_backend.config.settings import (
    REDIS_HOST,
    TEST_REDIS_CACHE_DB,
    PROD_REDIS_CACHE_DB,
)

# Globals
_redis_instances = {"active_connections": {}}

# Redis Factory
async def get_redis_instance(env: str = None):
    global _redis_instances

    db = TEST_REDIS_CACHE_DB if env == "test" else PROD_REDIS_CACHE_DB
    key = f"{env}_{db}"
    redis_client = _redis_instances.get(key)

    try:
        # Increment active connection counter
        _redis_instances["active_connections"][key] = (
            _redis_instances["active_connections"].get(key, 0) + 1
        )

        if redis_client:
            yield redis_client
        else:
            pool = ConnectionPool.from_url(f"redis://{REDIS_HOST}:6379/{db}")
            redis_client = Redis(connection_pool=pool, decode_responses=True)
            _redis_instances[key] = redis_client
            yield redis_client
    finally:
        # Decrement and possibly close connection
        _redis_instances["active_connections"][key] -= 1

        if _redis_instances["active_connections"][key] == 0:
            redis_to_close = _redis_instances.pop(key, None)
            if redis_to_close:
                await redis_to_close.aclose()
            _redis_instances["active_connections"].pop(key, None)
