import json
from sqlalchemy import delete
import redis.asyncio as redis
from sqlalchemy import inspect
from sqlalchemy.future import select
from typing import Type, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession


from property_street_backend.app.schemas.asset_schemas import (
    AssetSchema
)
from property_street_backend.app.models import (
    Tag, 
    Asset, 
    Agent,
    CloudImageDetail,
    AssetFeature, 
    AssetCloudImage,
    asset_tag_association,
)
from property_street_backend.config.settings import (
    DEBUG
)
from property_street_backend.log_config.logger_config import (
    log_message
)
from property_street_backend.app.controllers.activity.asset_routine_methods import (
    create_or_update_newly_created_asset_cache
)


async def get_existing_instance_from_unique_fields(
    db: AsyncSession, 
    model: Type[Any], 
    obj_data: Dict[str, Any]
) -> Any:
    """
    Automatically find and fetch the instance that violates the uniqueness constraint asynchronously
    by reflecting on the model's unique fields.
    
    Args:
        db (AsyncSession): SQLAlchemy asynchronous database session.
        model (Type[Any]): SQLAlchemy model class.
        obj_data (Dict[str, Any]): Dictionary containing the fields and values for the model instance.

    Returns:
        Any: The existing model instance that violated the uniqueness constraint, or None if not found.
    """
    # Get the unique constraints of the model
    mapper = inspect(model)
    unique_columns = []
    
    # Get columns marked as unique or part of a unique constraint
    for column in mapper.columns:
        if column.unique or column.primary_key:
            unique_columns.append(column.name)

    # Build a query dynamically based on the unique fields found in obj_data
    stmt = select(model)
    for field in unique_columns:
        if field in obj_data:
            stmt = stmt.where(getattr(model, field) == obj_data[field])

    # Execute the query asynchronously
    result = await db.execute(stmt)
    return result.scalar_one_or_none()  # Return the instance if found, else None


async def handle_instance_delete(db: AsyncSession, model: Type[Any], id: int):
    """
    Asynchronously deletes an instance of a given model by id.
    """
    # Perform the deletion asynchronously
    await db.execute(
        model.__table__.delete().where(model.id == id)
    )


async def create_or_update_object(
    db: AsyncSession, 
    model: Type[Any], 
    obj_data: Dict[str, Any], 
    proxyObject: Dict[int, Any], 
    table_id: int = None
) -> Any:
    """
    Asynchronously creates or updates a model instance based on the passed object data.

    Args:
        db (AsyncSession): SQLAlchemy async database session.
        model (Type[Any]): SQLAlchemy model class.
        obj_data (Dict[str, Any]): Dictionary containing the fields and values for the model instance.
        proxyObject (Dict[int, Any]): Dictionary storing already created instances to resolve relationships.
        table_id (int): The ID of the object to update, or None to create a new one.

    Returns:
        Any: The created or updated model instance.
    """
    # Log the arguments for debugging
    # print(f'obj_data: {obj_data} proxyObject: {proxyObject} table_id: {table_id}\r')

    # Initialize an instance
    instance = None

    # Pop out the relationship object if it exists
    relationships = obj_data.pop('relationship', {})
    
    # Fetch the instance if table_id is provided
    if table_id is not None:
        model_instance = await db.execute(
            select(model).filter(
                model.id == table_id
            )
        )
        instance = model_instance.scalars().first()

    if instance is None:  # Create a new instance if it doesn't exist
        
        # Pre-check to avoid duplicate insertions
        existing_instance = await get_existing_instance_from_unique_fields(db, model, obj_data)
        
        if existing_instance:
            instance = existing_instance
        else:
            instance = model(**obj_data)
    else:  # Update the existing instance
        for key, value in obj_data.items():
            setattr(instance, key, value)

    # Handle relationships
    if len(relationships):
        for field, related_indices in relationships.items():
            related_value = None
            if isinstance(related_indices, list):
                related_value = [proxyObject[index] for index in related_indices]
            else:
                related_value = proxyObject.get(related_indices)

            setattr(instance, field, related_value)


    # Add the instance back to the session
    db.add(instance)

    # synchronize the current in-memory state without committing
    await db.flush()
    
    # Return the instance
    return instance


def return_model_from_string(str_value: str):
    """
    Returns the appropriate model class based on the string value.
    """
    if str_value == 'Tag':
        return Tag
    elif str_value == 'Agent':
        return Agent
    elif str_value == 'Asset':
        return Asset
    elif str_value == 'AssetFeature':
        return AssetFeature
    elif str_value == 'AssetCloudImage':
        return AssetCloudImage
    elif str_value == 'CloudImageDetail':
        return CloudImageDetail


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
    newly_created: bool,
    ttl_in_seconds: int,
):
    """
    Processes a batch of assets. Deletes or creates/updates instances as necessary.
    
    Args:
        data_to_be_processed (Dict): The data containing the objects to process.
        db (Session): The database session (injected by FastAPI).
    
    Returns:
        Dict: The result of the processing.
    """
    # variable to hold asset instance
    asset_instance_id_after_flush_before_commit = None
    # Initialize proxy object
    proxy = {}
    # Convert keys to integers for predictable ordering
    data = {int(k): v for k, v in data_to_be_processed.items()}

    try:
        # Attempt to retrieve the agent instance
        agent_obj = data.get(0)
        if agent_obj:
            try:
                if DEBUG:
                    # Log received agent object
                    print(f"Processing agent with ID: {agent_obj['db_table_id']}, and id type {type(agent_obj['db_table_id'])}")
                
                # Ensure db_table_id is integer
                agent_id = int(agent_obj.get("db_table_id", -1))
                
                # Retrieve the agent instance
                agent_instance = await db.execute(
                    select(Agent).filter(Agent.id == agent_id)
                )
                agent_instance = agent_instance.scalars().first()

                # Check if agent instance was found
                if not agent_instance:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Agent not found"
                    )

                # Assign this to the proxy object 
                proxy[0] = agent_instance

                # Remove the agent entry from data as it's now in the proxy
                data.pop(0)

            except SQLAlchemyError as e:
                await db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Database error occurred while retrieving agent instance"
                ) from e
            except Exception as e:
                await db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="An unexpected error occurred while retrieving agent instance"
                ) from e

        # Process the rest of the items
        for key, value in data.items():
            if value.get('db_delete') and value.get('db_table_id') > 0:
                await handle_instance_delete(
                    db=db,
                    model=return_model_from_string(value['db_table_name']),
                    id=value['db_table_id']
                )
            elif value.get('db_delete') == False:
                instance = await create_or_update_object(
                    db=db,
                    model=return_model_from_string(value['db_table_name']),
                    obj_data=value['fields'],
                    proxyObject=proxy,
                    table_id=None if value['db_table_id'] == -1 else value['db_table_id']
                )
                proxy[key] = instance
                # check if the instance is an Asset model instance
                if isinstance(instance, Asset):
                    asset_instance_id_after_flush_before_commit =  instance.id

        # Commit all changes after all operations are completed
        await db.commit()


        # handle caching
        # fetch the asset after all transactions have been done
        result = await db.execute(
            select(Asset).filter(
                Asset.id == asset_instance_id_after_flush_before_commit
            )
        )
        asset_instance = result.scalars().first()
        asset_schema = AssetSchema.model_validate(asset_instance)
        asset_cache_object = json.dumps(
            asset_schema.model_dump()
        )
        await create_or_update_newly_created_asset_cache(
            asset_id = asset_instance.id,
            asset_data = asset_cache_object,
            redis_client = redis_client,
            newly_created = newly_created,
            expiry_seconds = ttl_in_seconds,
        )
        
        return {
            "detail": "Asset processed successfully",
            
            # For debugging
            "status": "success", 
            "processed": len(data),
        }

    except Exception as e:
        await db.rollback()  # Rollback if there's an error to ensure atomicity
        log_message(
            log_type='error',
            message=f'An error occured on processing of asset. Reason: {e}'
        )
        raise HTTPException(    
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the asset."
        )
