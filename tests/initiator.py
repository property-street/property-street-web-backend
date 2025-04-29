from property_street_backend.config.redis_connection_manager import get_redis_instance
from property_street_backend.config.postgres_connection_manager import get_postgres_instance

async def get_test_db(**kwargs):
    env = 'test'
    async for test_db in get_postgres_instance(env,**kwargs):
        yield test_db

async def get_test_redis():
    env = "test"
    async for redis_client in get_redis_instance(env):
        yield redis_client
