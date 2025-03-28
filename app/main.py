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
    auth, 
    activity,
    search,
    settings,
    google_oauth
)
from property_street_backend.app.initiator import (
    app, 
    redis_client
)
from property_street_backend.config.settings import (
    environment,
    CORS_ORIGINS,
)
from property_street_backend.app.controllers.activity.asset_routine_methods import (
    asset_auto_category_expiry
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    redis = await redis_client().__anext__()
    await asset_auto_category_expiry(
        redis_client=redis
    )
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
    redis_client: redis.Redis = Depends(redis_client),
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
app.include_router(home_router)