import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import Area, CloudImageDetail, User
from property_street_backend.tests.auth.test_user_creation import create_test_user
from property_street_backend.app.controllers.roommate_finder.models import RoommateFinder


@pytest.mark.asyncio
async def test_discover_roommate_finder_requests(client__fixture):
    test_db: AsyncSession = client__fixture["db"]
    http_client: AsyncClient = client__fixture["http_client"]

    test_user: User = await create_test_user(test_db)

    amount = 7
    requests = [
        RoommateFinder(
            area=Area(
                country="Nigeria",
                state_or_province="Lagos",
                city_or_town="Ikeja",
                street=f"Roommate Street {index}",
            ),
            max_roomies=2,
            extra_conditions=f"Quiet apartment with workspace {index}",
            category="apartment",
            requester_id=test_user.id,
            room_images=[
                CloudImageDetail(
                    cloud_asset_id=f"roommate_discover_asset_{index}",
                    format="jpg",
                    bytes=102400,
                    height=800,
                    public_id=f"roommate_discover_image_{index}",
                    secure_url=f"https://example.com/roommate_discover_image_{index}.jpg",
                    width=600,
                )
            ],
        )
        for index in range(amount)
    ]
    test_db.add_all(requests)
    await test_db.flush()

    size = 5
    response = await http_client.get(f"/roommate-finder/discover?size={size}")

    assert response.status_code == 200
    data = response.json()
    assert len(data["requests"]) == size
    assert data["has_more"] is True
    assert data["total_count"] == amount
    assert data["cached_roomies_application_ids"] == []
