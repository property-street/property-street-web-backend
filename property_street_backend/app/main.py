# main.py
import redis
from fastapi import APIRouter, Depends
from fastapi.middleware.cors import CORSMiddleware


from property_street_backend.config.settings import CORS_ORIGINS
from property_street_backend.app.initiator import app, redis_client
from property_street_backend.app.routers import auth, activity
from property_street_backend.app.controllers.activity.asset_routine_methods import (
    asset_auto_category_expiry,
)


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# Assuming your media files are in the "media" directory
# app.mount("/media", StaticFiles(directory="media"), name="media")



# Include celery app


home_router = APIRouter()

@home_router.get("/")
def read_root():
    return {"message": "Hello, World!"}

@home_router.get("/test-redis")
async def test_redis(
    redis_client: redis.Redis = Depends(redis_client),
):
    await redis_client.set("test_key", "value")
    value = await redis_client.get("test_key")
    return {"test_key": value.decode()}


# Include routers
app.include_router(auth.router)
app.include_router(activity.router)
app.include_router(home_router)



# Initiate rountine startup
# run routine
# async def on_startup():
#     # Get the Redis client asynchronously
#     try:
#         redis = await redis_client().__anext__()
#         await asset_auto_category_expiry(
#             redis_client = redis
#         )
#     finally:
#         pass
# 
# @app.on_event("startup")
# async def startup_event():
#     # Call the on_startup function asynchronously during the app startup
#     await on_startup()
