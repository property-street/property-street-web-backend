from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import User, Rating
from property_street_backend.tests.auth.test_create_agent import create_test_agent
from property_street_backend.app.controllers.auth.services import fetch_access_token


async def test_area_rating(client__fixture):
    fixture_obj: dict = await anext(client__fixture)
    test_db: AsyncSession = fixture_obj.get('db') 
    http_client: AsyncClient = fixture_obj.get('http_client')
    
    # create test_user and make user agent
    test_agent: User = await create_test_agent(test_db)
    test_agent_id = test_agent.id

    # retrieve access token for requests
    token = fetch_access_token(test_agent)['access_token']
    auth_header = {
        'Authorization': f'Bearer {token}',
        "Content-Type": "application/json"
    }

    payload = {
        'asset_to_rate': 'Agent',
        'comment': 'Good at what he does',
        'score': 3,
        'agent_id': test_agent_id
    }

    response = await http_client.post(
        '/rating-review',
        json = payload,
        headers = auth_header,
    )
    assert response.status_code == 201

    # assert the rating persisted
    stmt = await test_db.execute(
        select(Rating).filter(Rating.agent_id == test_agent_id)
    )
    rating = stmt.scalars().first()

    score = payload.get('score')

    # assert the rating instance exists
    assert rating is not None
    assert rating.comment == payload.get('comment')
    assert rating.score == score

    # assert the area's rating attribute
    await test_db.refresh(test_agent)
    assert test_agent.total_stars == score
    assert test_agent.total_ratings == 1