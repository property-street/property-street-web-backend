import asyncio
from IPython import get_ipython  # Import IPython for interactive use
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from sqlalchemy import delete, insert, text

from property_street_backend.app.models import (
    Asset, 
    AssetFeature, 
    User,
    Tag,
    UserSetting,
)
from property_street_backend.app.schemas.auth_schemas import (
    UserRegistrationSchema,
)
from property_street_backend.app.schemas.asset_schemas import (
    TagSchema,
)
from property_street_backend.config.postgres_connection_manager import AsyncSessionLocal

async def setup():
    # Create a new database session
    async with AsyncSessionLocal() as db:
        # Add the session and models to the IPython user namespace
        ipython = get_ipython()
        # Bind database session and models to IPython namespace
        ipython.user_ns['db'] = db
        ipython.user_ns['select'] = select
        ipython.user_ns['insert'] = insert
        ipython.user_ns['text'] = text
        ipython.user_ns['delete'] = delete
        ipython.user_ns['joinedload'] = joinedload
        ipython.user_ns['Tag'] = Tag
        ipython.user_ns['User'] = User
        ipython.user_ns['Asset'] = Asset
        ipython.user_ns['TagSchema'] = TagSchema
        ipython.user_ns['UserSetting'] = UserSetting
        ipython.user_ns['AssetFeature'] = AssetFeature
        ipython.user_ns['UserRegistrationSchema'] = UserRegistrationSchema


        print("Database session 'db' and models are available.")
        
# Start the event loop and run the setup function
asyncio.run(setup())

# To begin a new transaction with this Session,
# first issue db.rollback()
