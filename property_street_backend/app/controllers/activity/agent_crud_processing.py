from sqlalchemy import delete
from fastapi import HTTPException, status
from sqlalchemy import inspect
from typing import Type, Dict, Any
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import (
    Tag, 
    Asset, 
    Agent,
    CloudImageDetail,
    AssetFeature, 
    AssetCloudImage,
    asset_tag_association,
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


async def process_asset(data_to_be_processed: Dict, db: AsyncSession):
    """
    Processes a batch of assets. Deletes or creates/updates instances as necessary.
    
    Args:
        data (Dict): The data containing the objects to process.
        db (Session): The database session (injected by FastAPI).
    
    Returns:
        Dict: The result of the processing (you can adjust the return type).
    """
    # initialize proxy object
    proxy = {}
    # Convert keys to integers
    data = {int(k): v for k, v in data_to_be_processed.items()}

    try:
        # get the agent instance if it exists
        agent_obj = data.get(0)

        if agent_obj:
            agent_instance = await db.execute(
                select(Agent).filter(
                    Agent.id == agent_obj["db_table_id"]
                )
            )
            agent_instance = agent_instance.scalars().first()
            
            # assign this to the proxy object 
            proxy[0] = agent_instance

            # delete the agent entry from the data object since 
            # it would not be neeeded for the remaining processing
            data.pop(0)

        # process the rest of items
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
                    model=return_model_from_string(
                        value['db_table_name']),
                        obj_data=value['fields'],
                        proxyObject=proxy,
                        table_id=None if value['db_table_id'] == -1 else value['db_table_id']
                    )
                proxy[key] = instance

        # Commit all changes at once after all operations are completed
        await db.commit()
        
        # for debugging
        # print({"status": "success", "processed": len(data)})
        return {"status": "success", "processed": len(data)}
    except Exception as e:
        await db.rollback()  # Rollback if there's an error to ensure atomicity
        print({"status": "error", "message": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the user."
        )

