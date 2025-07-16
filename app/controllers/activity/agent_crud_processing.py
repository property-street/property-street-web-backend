import traceback
from typing import Dict
from sqlalchemy import delete
import redis.asyncio as redis
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession


from property_street_backend.app.controllers.assets.schemas import (
    AssetResponseSchema
)
from property_street_backend.app.models import (
    User,
    Asset, 
    Agent,
    asset_tag_association,
)
from property_street_backend.config.settings import (
    DEBUG
)
from property_street_backend.app.initiator import logger
from property_street_backend.app.controllers.utils import (
    return_model_from_string,
    handle_instance_delete,
    create_or_update_object,
)
from property_street_backend.log_config.logger_config import (
    log_message
)
from property_street_backend.app.controllers.activity.asset_routine_methods import (
    create_or_update_newly_created_asset_cache
)
from property_street_backend.app.controllers.assets.services import eager_asset_load

async def remove_tags_from_asset(session: AsyncSession, asset_id: int, tag_ids: list[int]) -> bool:
    """
    Asynchronously remove multiple tags from an asset in the many-to-many relationship.
    
    Args:
        session (AsyncSession): SQLAlchemy asynchronous database session.
        asset_id (int): ID of the asset.
        tag_ids (list[int]): List of tag IDs to remove.
    
    Returns:
        bool: True if at least one tag was successfully removed, False otherwise.
    """
    # Return early if no tags are provided
    if not tag_ids:
        return False

    # Create a delete statement to remove the relationships for the given tags from the association table
    stmt = delete(asset_tag_association).where(
        asset_tag_association.c.asset_id == asset_id,
        asset_tag_association.c.tag_id.in_(tag_ids)  # Use IN clause for multiple tag IDs
    )

    # Execute the statement asynchronously
    result = await session.execute(stmt)
    
    # Commit the transaction asynchronously
    await session.commit()
    
    # Return whether any rows were affected (True if at least one tag was removed, False otherwise)
    return result.rowcount > 0


async def process_asset(
    data_to_be_processed: Dict, 
    db: AsyncSession,
    redis_client: redis.Redis,
    ttl_in_seconds: int,
    agent: Agent
):
    """
    Processes a batch of assets. Deletes or creates/updates instances as necessary.
    
    Args:
        data_to_be_processed (Dict): The data containing the objects to process.
        db (Session): The database session (injected by FastAPI).
    
    Returns:
        Dict: The result of the processing.
    """

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized access to carry out this operation!"
        )
    

    try:
        # Initialize proxy object and put the agent instance at -1
        proxy = {}
        # Convert keys to integers for predictable ordering
        data = {int(k): v for k, v in data_to_be_processed.items()}
        newly_created = None
        asset = None
        asset_instance_before_commit = None

        # Process the rest of the items
        for key, value in data.items():
            value: dict
            db_delete: bool = value.get('db_delete',False)
            if db_delete and value.get('db_table_id') > 0: # delete the entry
                await handle_instance_delete(
                    db=db,
                    model=return_model_from_string(value['db_table_name']),
                    id=value['db_table_id']
                )
            # create or update the entry
            elif db_delete == False:
                fields = value['fields']
                table_id = None if value['db_table_id'] == -1 else value['db_table_id']
                
                # Handles newly created asset/properties
                is_asset = value.get('db_table_name') == "Asset"
                if is_asset and not table_id:
                        fields['agent_id'] = agent.id
                        # modify newly_created to True
                        newly_created = True
                
                instance = await create_or_update_object(
                    db = db,
                    model = return_model_from_string(value['db_table_name']),
                    fields = fields,
                    proxyObject = proxy,
                    table_id = table_id
                )
                proxy[key] = instance # bind the created or modified instance to the proxy of the data_to_be_processed

                # check if the instance is an Asset model instance
                if isinstance(instance, Asset): 
                    # hold the asset instance id
                    asset_instance_before_commit = instance

        # Commit all changes after all operations are completed
        await db.commit()

        if asset_instance_before_commit:
            result = await db.execute(
                eager_asset_load()
                .filter(Asset.id == asset_instance_before_commit.id)
            )
            asset = result.unique().scalars().first()
        
        # Handle caching
        if asset:
            try:
                schematized_asset = AssetResponseSchema.model_validate(asset) # schema instance of asset
                schematized_asset_to_dict = schematized_asset.model_dump()
                await create_or_update_newly_created_asset_cache(
                    asset_id = asset.id,
                    asset_data = schematized_asset_to_dict,
                    redis_client = redis_client,
                    newly_created = newly_created,
                    expiry_seconds = ttl_in_seconds,
                )
            except Exception as e:
                logger.warning(f"Cache update failed: {e}")
                raise
        
        return asset if asset else None

    except Exception as e:
        await db.rollback()  # Rollback if there's an error to ensure atomicity
        f_message=f'An error occured on processing of asset. Reason: {e}'
        d_message=f'An error occured on processing of asset. Reason: {traceback.format_exc()}'
        if DEBUG:
            logger.error(d_message)
        log_message(
            log_type = 'error',
            message = f_message
        )
        raise HTTPException(    
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = "An error occurred while creating the asset."
        )
