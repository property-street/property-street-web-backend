import pytest
from sqlalchemy.ext.asyncio import AsyncSession


from property_street_backend.app.models import CloudImageDetail
from property_street_backend.tests.auth.test_user_creation import create_test_user
from property_street_backend.tests.activity.test_controller.test_objects import cloud_image_template
from property_street_backend.app.controllers.roommate_finder.schemas import RoommateFinderResponseSchema
from property_street_backend.app.controllers.roommate_finder.search import search_roommates, Area, RoommateFinder


@pytest.mark.asyncio
async def test_search_roommates(client__fixture):
    # fetch test DB session
    test_db: AsyncSession = client__fixture['db']
    
    cloud_image_detail = {
        **cloud_image_template,
        "public_id":f"test_image",
    }

    # create test_user and make user agent
    test_user = await create_test_user(test_db)
    # give the user a profile avatar
    test_user.profile_avatar = CloudImageDetail(**cloud_image_detail)
    test_db.add(test_user)

    # Step 1: Create an area (no `name`, but has city/state)
    test_area = Area(
        country="Nigeria",
        state_or_province="Lagos",
        city_or_town="Ikeja",
        street="Allen Avenue",
        zip_or_postal_code="100001"
    )
    test_db.add(test_area)
    await test_db.commit()
    await test_db.refresh(test_area)

    # Step 2: Create sample roommates
    roommates = [
        RoommateFinder(
            extra_conditions="Looking for a clean and quiet roommate near Ikeja City Mall.",
            area_id=test_area.id,
            category = "House",
            requester_id = test_user.id,
            room_images = [
                CloudImageDetail(
                    **{
                        **cloud_image_template,
                        "public_id" : f"id1{i}"
                    },
                ) for i in range(2)
            ]
        ),
        RoommateFinder(
            extra_conditions="Prefer someone working in the area, with neat habits.",
            area_id=test_area.id,
            category = "House",
            requester_id = test_user.id,
            room_images = [
                CloudImageDetail(
                    **{
                        **cloud_image_template,
                        "public_id" : f"id2{i}"
                    },
                ) for i in range(2)
            ]
        )
    ]
    test_db.add_all(roommates)
    await test_db.commit()

    # Step 3: Perform search by keyword
    query_data = {
        "keywords": ["Ikeja", "quiet"],
        "numbers": [150000]
    }
    results = await search_roommates(query_data, test_db)

    # Step 4: Assertions
    assert isinstance(results, list)
    assert len(results) >= 1
    assert any("quiet" in r["data"]['extra_conditions'] for r in results)
    assert all(r["type"] == "roommates-finder" for r in results)

    # print(f"✅ Found {len(results)} roommate(s) matching keywords: {[r['data'].title for r in results]}")