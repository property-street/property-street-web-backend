from sqlalchemy import inspect
from typing import Type, Dict, Any
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from property_street_backend.app.models import (
    Tag, 
    Area,
    User,
    Asset, 
    Agent,
    UserSetting,
    CloudImageDetail,
    AssetFeature, 
    AssetCloudImage,
)


def return_model_from_string(str_value: str):
    """
    Returns the appropriate model class based on the string value.
    """
    if str_value == 'Tag':
        return Tag
    if str_value == 'Area':
        return Area
    elif str_value == 'User':
        return User
    elif str_value == 'Agent':
        return Agent
    elif str_value == 'Asset':
        return Asset
    if str_value == 'UserSetting':
        return UserSetting
    elif str_value == 'AssetFeature':
        return AssetFeature
    elif str_value == 'AssetCloudImage':
        return AssetCloudImage
    elif str_value == 'CloudImageDetail':
        return CloudImageDetail
    else: 
        raise Exception('Model equivalent of str_value not found')


async def get_existing_instance_from_unique_fields(
    db: AsyncSession, 
    model: Type[Any], 
    model_fields: Dict[str, Any]
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
        if field in model_fields:
            stmt = stmt.where(getattr(model, field) == model_fields[field])

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
    fields: Dict[str, Any], 
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
    relationships: dict = fields.pop('relationship', {})
    
    # Fetch the instance if table_id is provided
    if table_id is not None:
        model_instance = await db.execute(
            select(model).filter(
                model.id == table_id
            )
        )
        instance = model_instance.scalars().first()

    if instance is None:  # Create a new instance if it doesn't exist
        
        # redundant-check to avoid duplicate insertions
        existing_instance = await get_existing_instance_from_unique_fields(db, model, fields)
        
        if existing_instance:
            instance = existing_instance
        else:
            instance = model(**fields) # create a new instance
    else:  # Update the existing instance
        for key, value in fields.items():
            setattr(instance, key, value)

    # Handle relationships
    if relationships:
        for field, related_indices in relationships.items():
            if isinstance(related_indices, list):
                related_objects = [proxyObject[index] for index in related_indices]
                existing_value = getattr(instance, field, None)
                
                # If it's not new, extend the relationship, else create it
                if isinstance(existing_value, list):
                    existing_value.extend(related_objects)
                else:
                    setattr(instance, field, related_objects)
            else:
                related_object = proxyObject.get(related_indices)
                setattr(instance, field, related_object)

    # Add the instance back to the session
    db.add(instance)

    # synchronize the current in-memory state without committing
    await db.flush()
    
    # Return the instance
    return instance
