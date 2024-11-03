from typing import Dict
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, status

from property_street_backend.app.models import (
    User,
)
from property_street_backend.app.controllers.auth import (
    decode_user_from_token,
)
from property_street_backend.app.database import get_db
from property_street_backend.app.controllers.activity.agent_crud_processing import (
    process_asset as controller_process_asset,
    remove_tags_from_asset,
)
from property_street_backend.app.schemas.route_based_asset_schemas import AssetComponentSchema

router = APIRouter(prefix="/activity", tags=["activity"])

@router.post("/process_asset", status_code=status.HTTP_200_OK)
async def process_asset(
    data: Dict, 
    db: AsyncSession = Depends(get_db),
    _: User = Depends(decode_user_from_token)
):
    # check if the tags to remove is present
    tags_to_remove_object = data.get('tags_to_remove_object')
    if (len(tags_to_remove_object)):
        await remove_tags_from_asset(
            session = db,
            asset_id = tags_to_remove_object.asset_id,
            tag_ids=tags_to_remove_object.tag_ids
        )
    
    # check for asset data to process
    asset_data_to_process = data.get('asset_data_to_process')
    if (len(asset_data_to_process)):
        return await controller_process_asset(
            data_to_be_processed = asset_data_to_process,
            db = db
        )