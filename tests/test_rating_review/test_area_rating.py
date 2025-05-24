from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import Area, User, Rating
from property_street_backend.app.initiator import logger
from property_street_backend.app.controllers.auth import fetched_access_token
from property_street_backend.tests.auth.test_user_creation import create_test_user


async def test_area_rating(client__fixture):
    fixture_obj: dict = await anext(client__fixture)
    test_db: AsyncSession = fixture_obj.get('db') 
    http_client: AsyncClient = fixture_obj.get('http_client')
    
    # create test_user and make user agent
    test_user: User = await create_test_user(test_db)

    # retrieve access token for requests
    token = fetched_access_token(test_user)['access_token']
    auth_header = {
        'Authorization': f'Bearer {token}',
        "Content-Type": "application/json"
    }

    area: Area = Area(
        country ='Sri-lanka',
        state_or_province = 'Mogadishu',
        city_or_town = 'Pisque Central', 
        street = 'No 11 Jokey street',
        building_name_or_suite = 'Jackals base',
        zip_or_postal_code = '50001'
    )
    test_db.add(area)
    await test_db.commit()
    await test_db.refresh(area)

    payload = {
        'asset_to_rate': 'Area',
        'comment': 'Hmmm! Nawa oh for this kind mumu area',
        'score': 1,
        'area_id': area.id
    }

    response = await http_client.post(
        '/rating-review',
        json = payload,
        headers = auth_header,
    )
    assert response.status_code == 201

    # assert the rating persisted
    stmt = await test_db.execute(
        select(Rating).filter(Rating.area_id == area.id)
    )
    rating = stmt.scalars().first()

    score = payload.get('score')

    # assert the rating instance exists
    assert rating is not None
    assert rating.comment == payload.get('comment')
    assert rating.score == score

    # assert the area's rating attribute
    await test_db.refresh(area)
    assert area.total_stars == score
    assert area.total_ratings == 1