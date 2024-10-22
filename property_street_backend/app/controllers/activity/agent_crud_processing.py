from fastapi import APIRouter
from sqlalchemy.orm import Session
from typing import Type, Dict, Any
from sqlalchemy.future import select

from property_street_backend.app.models import (
    Tag, 
    Asset, 
    Agent,
    CloudImageDetail,
    AssetFeature, 
    AssetCloudImage,
)

router = APIRouter()


def handle_instance_delete(db: Session, model: Type[Any], id: int):
    """
    Deletes an instance of a given model by id.
    """
    db.query(model).filter(model.id == id).delete()

def create_or_update_object(db: Session, model: Type[Any], obj_data: Dict[str, Any], proxyObject: Dict[int, Any], table_id: int = None) -> Any:
    """
    Creates or updates a model instance based on the passed object data.
    
    Args:
        db (Session): SQLAlchemy database session.
        model (Type[Any]): SQLAlchemy model class.
        obj_data (Dict[str, Any]): Dictionary containing the fields and values for the model instance.
        proxyObject (Dict[int, Any]): Dictionary storing already created instances to resolve relationships.
        table_id (int): The ID of the object to update, or None to create a new one.

    Returns:
        Any: The created or updated model instance.
    """
    # log the argument of debugging purpose
    print(f'model:{model} obj_data:{obj_data} proxyObject:{proxyObject} table_id: {table_id}')

    # Initialize an instance
    instance = None

    # Pop out the relationship object if there is
    relationships = obj_data.pop('relationship', {})
    
    # Fetches the instance whose id matches table_id if it exists
    if table_id is not None:
        instance = db.query(model).filter(model.id == table_id).first()

    if instance is None: # creates a new instance if instance is none
        instance = model(**obj_data)
    else: # modifies the already existing instance
        for key, value in obj_data.items():
            setattr(instance, key, value)


    # loops throught the relationship object
    for field, related_indices in relationships.items():
        related_value = None
        if isinstance(related_indices, list): # makes the related_value a list of related index if related_indeces is a list
            related_value = [proxyObject[index] for index in related_indices]
        else:
            related_value = proxyObject.get(related_indices)

        # assigns the realation to the model instance
        setattr(instance, field, related_value)

    # adds the instance to the db session and returns it
    db.add(instance)
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


async def process_asset(data: Dict, db: Session):
    """
    Processes a batch of assets. Deletes or creates/updates instances as necessary.
    
    Args:
        data (Dict): The data containing the objects to process.
        db (Session): The database session (injected by FastAPI).
    
    Returns:
        Dict: The result of the processing (you can adjust the return type).
    """
    proxy = {}

    try:
        # get the agent instance
        agent_instance = await db.execute(select(Agent).filter(Agent.id == data[0]["db_table_id"]))
        agent_instance = agent_instance.scalars().first()
        
        # assign this to the proxy object 
        proxy[0] = agent_instance

        # delete the agent entry from the data object since 
        # it would not be neeeded for the remaining processing
        data.pop(0)

        for key, value in data.items():
            if value.get('db_delete') and value.get('db_table_id') > 0:
                handle_instance_delete(
                    db=db,
                    model=return_model_from_string(value['db_table_name']),
                    id=value['db_table_id']
                )

            elif value.get('db_delete') == False:
                instance = create_or_update_object(
                    db=db,
                    model=return_model_from_string(value['db_table_name']),
                    obj_data=value['fields'],
                    proxyObject=proxy,
                    table_id=None if value['db_table_id'] == -1 else value['db_table_id']
                )
                proxy[key] = instance

        # Commit all changes at once after all operations are completed
        await db.commit()
        
        print({"status": "success", "processed": len(data)})
        return {"status": "success", "processed": len(data)}
    except Exception as e:
        await db.rollback()  # Rollback if there's an error to ensure atomicity
        print({"status": "error", "message": str(e)})
        return {"status": "error", "message": str(e)}
