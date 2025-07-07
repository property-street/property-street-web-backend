from fastapi import APIRouter, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession


from property_street_backend.app.database import get_db
from property_street_backend.app.controllers.ratings.core import rate_asset
from property_street_backend.app.controllers.ratings.schemas import RatingReviewSchema

router = APIRouter(prefix='/rating-review', tags=['rating-review'])

@router.post('', status_code=status.HTTP_201_CREATED, response_description = "Succesful rating-review of the referenced asset.")
async def review(
    data: RatingReviewSchema,
    db: AsyncSession = Depends(get_db)
):
    return await rate_asset(
        data = data.model_dump(),
        db = db
    )