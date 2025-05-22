# main.py
import redis
from fastapi import (
    APIRouter, 
    Depends, 
    FastAPI
)
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession
)
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.middleware.cors import CORSMiddleware



from property_street_backend.app.database import (
    get_db,
)
from property_street_backend.app.routers import (
    ws,
    auth, 
    activity,
    search,
    settings,
    deep_chat,
    google_oauth,
    asset_request,
)
from property_street_backend.app.initiator import (
    app, 
    get_redis,
)
from property_street_backend.config.settings import (
    ENVIRONMENT as environment,
    CORS_ORIGINS,
)
from property_street_backend.app.controllers.cache_expiration import cache_expiry_initializer


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    async for redis_client in get_redis():
        break

    await cache_expiry_initializer(redis_client)
    yield  # Application runs here
    # Shutdown logic (if needed)
    # e.g., await redis_client.close()

app = FastAPI(lifespan=lifespan)



# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include celery app

home_router = APIRouter()

@home_router.get("/")
def read_root():
    return {
        "message": "Hello, World!",
        "environment": environment
    }

@home_router.get("/test-redis")
async def test_redis(
    redis_client: redis.Redis = Depends(get_redis),
):
    await redis_client.set("test_key", "value")
    value = await redis_client.get("test_key")
    return {
        "test_key": value,
        "environment": environment
    }

@home_router.get("/test-database")
async def test_database(
    session: AsyncSession = Depends(get_db),
):
    """
    Test database connectivity by running a simple query.
    """
    try:
        # Test query (replace 'your_table_name' with a real table if needed)
        result = await session.execute(text("SELECT 1"))
        value = result.scalar()  # Fetch the first scalar result

        return {
            "database_connected": True,
            "test_value": value,
            "environment": environment,
        }
    except Exception as e:
        # Log and return error details
        return {
            "database_connected": False,
            "error": str(e),
            "environment": environment,
        }

# Include routers
app.include_router(auth.router)
app.include_router(activity.router)
app.include_router(search.router)
app.include_router(settings.router)
app.include_router(google_oauth.router)
app.include_router(deep_chat.router)
app.include_router(ws.router)
app.include_router(asset_request.router)
app.include_router(home_router)