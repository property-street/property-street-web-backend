# main.py
from fastapi import APIRouter
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware


from property_street_backend.config.settings import CORS_ORIGINS
from property_street_backend.app.initiator import app
from property_street_backend.app.routers import auth



# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# Assuming your media files are in the "media" directory
app.mount("/media", StaticFiles(directory="media"), name="media")



# Include celery app


home_router = APIRouter()

@home_router.get("/")
def read_root():
    return {"message": "Hello, World!"}

# Include routers
app.include_router(auth.router)
app.include_router(home_router)

