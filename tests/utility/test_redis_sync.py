import pytest
from redis.asyncio import Redis

from property_street_backend.app.initiator import get_redis

@pytest.mark.asyncio
async def test_redis_sync(test_env_var):
    redis_inst_1 = None
    redis_inst_2= None
    try:
        redis_inst_1 = await get_redis().__anext__()
        await redis_inst_1.set('test',1)
        assert await redis_inst_1.exists('test')

        redis_inst_2 = await get_redis().__anext__()
        assert await redis_inst_2.exists('test')
    finally:
        if redis_inst_1:
            await redis_inst_1.aclose()
        if redis_inst_2:
            await redis_inst_2.aclose()