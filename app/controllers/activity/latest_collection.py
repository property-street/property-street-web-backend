from redis.asyncio import Redis
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession


from property_street_backend.app.initiator import logger
from property_street_backend.app.controllers.assets.services import fetch_latest_assets
from property_street_backend.app.controllers.asset_request.services import fetch_recent_asset_request
from property_street_backend.app.controllers.roommate_finder.fetch_latest_requests import fetch_recent_roommate_finder_request

async def fetch_latest_collection(
    page: int,
    size: int,
    session: AsyncSession,
    redis_client: Redis
):
    try:
        properties = await fetch_latest_assets(
            page = page,
            size = size,
            session = session,
            redis_client = redis_client
        )

        roommates_finder_requests = await fetch_recent_roommate_finder_request(
            page = page,
            size = size,
            session = session
        )

        # asset_requests = await fetch_recent_asset_request(
        #     page = page,
        #     size = size,
        #     session = session
        # )

        return {
            'properties': properties,
            'roommates_requests': roommates_finder_requests,
            # 'asset_requests': asset_requests
        }
    except Exception as e:
        f_message = "An error occurred while retrieving latest collection."
        d_message = f"{f_message} Reason: {e}"
        logger.error(d_message)
        raise HTTPException(status_code=500, detail=f_message) from e