from fastapi import APIRouter

from .properties import router as properties_router

router = APIRouter()

router.include_router(properties_router)

__all__ = ["router"]