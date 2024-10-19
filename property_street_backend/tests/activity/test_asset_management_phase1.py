import pytest
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import (
    Asset, 
    AssetFeature, 
)
from property_street_backend.app.controllers.auth import create_user
from property_street_backend.app.schemas.auth_schemas import UserRegistrationSchema
from property_street_backend.app.controllers.activity.agent_crud_processing import process_asset

# Test data
feature_obj = {
    0: {
        "db_table_id": 1,
        "db_table_name": "Agent",
    },
    1: {
        # tag 1
        "db_table_id": -1,
        "db_delete": False,
        "db_table_name": "Tag",

        # fields
        "fields": {
            "name": "tag_value"
        }
    },
    2: {
        # tag 2
        "db_table_id": -1,
        "db_delete": False,
        "db_table_name": "Tag",

        # fields
        "fields": {
            "name": "tag_value"
        }
    },
    3: {
        # cover image
        "db_delete": False,
        "db_table_id": -1,
        "db_table_name": "CloudImageDetail",

        # fields
        "fields": {
            "asset_id": "value",
            "created_at": "",
            "format": "",
            "bytes": "",
            "height": "",
            "public_id": "",
            "secure_url": "",
            "width": "",
        }
    },
    4: {
        # Asset
        "db_delete": False,
        "db_table_id": -1,
        "db_table_name": "Asset",

        # fields
        "fields": {
            "title": "value",
            "country": "Caicos",
            "address": "Barbados street",
            "currency": "usd",
            "status": "Auction",
            "amount": "amount",
            "description": "<span>bla bla bla</span>",
            "has_features": True,
        },

        "relationship": {
            "tags": [1, 2],
            "cover_image": 2,
            "agent": 0,
        }
    },
    5: {
        # image for asset feature
        "db_delete": False,
        "db_table_id": -1,
        "db_table_name": "CloudImageDetail",

        # fields
        "fields": {
            "asset_id": "value",
            "created_at": "",
            "format": "",
            "bytes": "",
            "height": "",
            "public_id": "",
            "secure_url": "",
            "width": "",
        }
    },
    6: {
        # asset features
        "db_delete": False,
        "db_table_id": -1,
        "db_table_name": "AssetFeature",

        # fields
        "fields": {
            "title": "value",
        },

        "relationship": {
            "cloud_image_details": 5,
            "asset": 3,
        }
    },
}

no_feature_obj = {
    0: {
        "db_table_id": 1,
        "db_table_name": "Agent",
    },
    1: {
        # tag 1
        "db_table_id": -1,
        "db_delete": False,
        "db_table_name": "Tag",

        # fields
        "fields": {
            "name": "tag_value"
        }
    },
    2: {
        # cover image
        "db_delete": False,
        "db_table_id": -1,
        "db_table_name": "CloudImageDetail",

        # fields
        "fields": {
            "asset_id": "value",
            "created_at": "",
            "format": "",
            "bytes": "",
            "height": "",
            "public_id": "",
            "secure_url": "",
            "width": "",
        }
    },
    3: {
        # Asset
        "db_delete": False,
        "db_table_id": -1,
        "db_table_name": "Asset",

        # fields
        "fields": {
            "title": "value",
            "country": "Caicos",
            "address": "Barbados street",
            "currency": "usd",
            "status": "Auction",
            "amount": "amount",
            "description": "<span>bla bla bla</span>",
            "has_features": True,
        },

        "relationship": {
            "tags": 1,
            "cover_image": 2
        }
    },
    4: {
        # asset feature image
        "db_delete": False,
        "db_table_id": -1,
        "db_table_name": "CloudImageDetail",

        # fields
        "fields": {
            "asset_id": "value",
            "created_at": "",
            "format": "",
            "bytes": "",
            "height": "",
            "public_id": "",
            "secure_url": "",
            "width": "",
        },

        "relationship": {
            "asset": 3
        }
    },
    5: {
        # asset feature image
        "db_delete": False,
        "db_table_id": -1,
        "db_table_name": "CloudImageDetail",

        # fields
        "fields": {
            "asset_id": "value",
            "created_at": "",
            "format": "",
            "bytes": "",
            "height": "",
            "public_id": "",
            "secure_url": "",
            "width": "",
        },

        "relationship": {
            "asset": 3
        }
    },
    6: {
        # asset feature image
        "db_delete": False,
        "db_table_id": -1,
        "db_table_name": "CloudImageDetail",

        # fields
        "fields": {
            "asset_id": "value",
            "created_at": "",
            "format": "",
            "bytes": "",
            "height": "",
            "public_id": "",
            "secure_url": "",
            "width": "",
        },

        "relationship": {
            "asset": 3
        }
    },
}


@pytest.mark.asyncio
async def test_create_asset_with_feature(get_test_db__fixture: AsyncSession):
    test_db = await get_test_db__fixture

    # Define a test client
    user_data = UserRegistrationSchema(
        email="test@example.com",
        username="testuser",
        password="password123"
    )

    # Call the create_user function
    created_user = await create_user(test_db, user_data)

    created_agent = created_user.become_agent()

    # modify feature object to include an agent's id
    feature_obj[0]['db_table_id'] = created_agent.id
    
    # Process asset with features
    await process_asset(feature_obj, test_db)

    # Fetch the created asset from the database
    result = await test_db.execute(select(Asset).filter(Asset.title == feature_obj[4]['fields']['title']))
    created_asset = result.scalars().first()

    # Assertions
    assert created_asset is not None
    assert created_asset.title == feature_obj[4]['fields']['title']
    assert created_asset.has_features is True

    # Check the features
    result = await test_db.execute(select(AssetFeature).filter(AssetFeature.asset_id == created_asset.id))
    asset_feature = result.scalars().first()
    assert asset_feature is not None


