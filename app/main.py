# main.py
from redis.asyncio import Redis
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
from property_street_backend.app.controllers.auth import routes as auth_routes
from property_street_backend.app.controllers.chat import routes as chat_routes
from property_street_backend.app.controllers.ws_init import routes as ws_routes
from property_street_backend.app.controllers.auth.utils import ensure_admin_user
from property_street_backend.app.controllers.search import routes as search_routes
from property_street_backend.app.controllers.actors import routes as actors_routes
from property_street_backend.app.controllers.assets import routes as assets_routes
from property_street_backend.app.controllers.settings import routes as settings_routes
from property_street_backend.app.controllers.activity import routes as activity_routes
from property_street_backend.app.controllers.ratings import routes as rating_review_routes
from property_street_backend.app.controllers.notification import routes as notification_routes
from property_street_backend.app.controllers.asset_request import routes as asset_request_routes
from property_street_backend.app.controllers.roommate_finder import routes as roommates_finder_routes
from property_street_backend.app.routers import (
    google_oauth,
)
from property_street_backend.config.postgres_connection_manager import get_postgres_instance
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
    async with get_postgres_instance() as session:
        await ensure_admin_user(session)
    async for redis_client in get_redis():
        (
            listener_task, 
            stop_event, 
            _
        ) = await cache_expiry_initializer(redis_client)
    
    yield  
    # Application runs here
    # Shutdown logic (if needed)
    # e.g., await redis_client.close()

    if stop_event:
        stop_event.set()
    if listener_task:
        await listener_task

app = FastAPI(lifespan=lifespan)



# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


home_router = APIRouter()

@home_router.get("/")
def read_root():
    return {
        "message": "Hello, World!",
        "environment": environment
    }

@home_router.get("/test-redis")
async def test_redis(
    redis_client: Redis = Depends(get_redis),
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
app.include_router(home_router)
app.include_router(ws_routes.router)
app.include_router(auth_routes.router)
app.include_router(chat_routes.router)
app.include_router(google_oauth.router)
app.include_router(actors_routes.router)
app.include_router(search_routes.router)
app.include_router(assets_routes.router)
app.include_router(assets_routes.router)
app.include_router(settings_routes.router)
app.include_router(activity_routes.router)
app.include_router(notification_routes.router)
app.include_router(asset_request_routes.router)
app.include_router(rating_review_routes.router)
app.include_router(roommates_finder_routes.router)