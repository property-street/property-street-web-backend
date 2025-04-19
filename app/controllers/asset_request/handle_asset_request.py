import json
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import AssetRequest, Area

async def handle_asset_request(
    requester_id: int,
    db: AsyncSession,
    request_data: dict,
    redis_client: Redis,
):
    """Saves the user's request to the database and publishes to the notification agent-wide

    Args:
        request_data (dict): object holding asset's description
        redis_client (Redis): Redis session object
        db (AsyncSession): postgres session object
    """
    # conver the pydantic model to a dictionary 
    # pop off and get the description entry so only area details would be left
    # create and save an instance of the AssetRequest 
    request_data_to_dict = vars(request_data)
    cloned_request_data_to_dict = {**request_data_to_dict}
    description = request_data_to_dict.pop('description')
    request_instance = AssetRequest(
        area = Area(**request_data_to_dict),
        description = description,
        requester_id = requester_id
    )
    db.add(request_instance)
    await db.commit()

    # publish the request to the asset_request channel
    await redis_client.publish('asset-request-channel', json.dumps(cloned_request_data_to_dict))