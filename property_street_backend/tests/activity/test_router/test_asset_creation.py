import pytest

from property_street_backend.tests.activity.test_controller.test_objects import (
    feature_obj,
)
from property_street_backend.tests.activity.test_controller.test_asset_management_phase1 import (
    add_created_clientId_to_payload,
)


@pytest.mark.asyncio
async def test_asset_upload(client__fixture_with_onlyDB_fixture: tuple):
    # fetch the client generator
    client_gen =  client__fixture_with_onlyDB_fixture
    # get the yield client object
    client, test_db = await client_gen.__anext__()

    # Define a post data
    await add_created_clientId_to_payload(
        db = test_db,
        payload = feature_obj
    )

    # print(feature_obj)

    payload = {
        'tags_to_remove_object': {},
        'asset_data_to_process': feature_obj
    }

    # Make the request using the client provided by the fixture
    response = await client.post(
        "/activity/process_asset",
        json=payload  # Use json instead of data for a JSON body
    )
    
    # Assertions
    assert response.status_code == 200
    json_response = response.json()
    len_processed = json_response.get("processed")
    assert isinstance(len_processed, int)