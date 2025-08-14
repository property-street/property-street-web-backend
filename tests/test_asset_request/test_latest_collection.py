import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


from property_street_backend.app.initiator import logger
from property_street_backend.tests.auth.test_user_creation import create_test_user
from property_street_backend.app.models import User, CloudImageDetail, AssetRequest, Area
from property_street_backend.tests.activity.test_controller.test_objects import area_template, cloud_image_template

@pytest.mark.asyncio
async def test_latest_collection(client__fixture):
    async for fixture_obj in client__fixture:
        test_db: AsyncSession = fixture_obj['db'] 
        httpx_client: AsyncClient = fixture_obj['http_client']
        break; 


    # create test_user and make user agent to enable 
    # receipt of notification on asset creation
    test_user: User = await create_test_user(test_db)

    # give the user a profile avata, first name and last name
    test_user.profile_avatar = CloudImageDetail(**cloud_image_template)
    test_db.add(test_user)
    await test_db.flush() # flush to reflect change

    # construct payload
    asset_requests = [
        AssetRequest(
            description = f'I need a 1 bedroom flat in the maldives! {i}',
            area = Area(**{
                **area_template,
                'zip_or_postal_code': "11bced",
                'building_name_or_suite': 'Quando-rondo'
            }),
            requester_id = test_user.id,
        ) for i in range(10)
    ] 
    test_db.add_all(asset_requests)
    await test_db.flush()


    size = 7
    response = await httpx_client.get(f"/asset-requests/latests?size={size}")
    assert response.status_code == 200
    logger.info(response.json())
    assert len(response.json()) == size