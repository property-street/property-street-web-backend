import pytest
import asyncio

from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import create_test_user
from property_street_backend.app.models import User
from property_street_backend.config.settings import BETA_LAUNCHING
from property_street_backend.app.schemas.auth_schemas import UserRegistrationSchema
from property_street_backend.app.controllers.auth.services import generate_beta_signup_link


@pytest.mark.asyncio
async def test_probe_user_existence(client__fixture):
    # fetch the client generator
    httpx_client: AsyncClient = client__fixture['http_client']
    test_db: AsyncSession = client__fixture['db']
    redis_client: Redis = client__fixture['redis_client']

    created_user: User = await create_test_user(test_db)

    beta_token_dict = {"beta_token": (await generate_beta_signup_link(redis_client))['token'] if BETA_LAUNCHING else None}
    payload = {
        "email": "testuser@example.com",
        "username": created_user.username,
        **beta_token_dict,
    }
    # Test 1
    #==============================================
    # making a request with a username that exists
    #==============================================
    response = await httpx_client.post(
        "/auth/probe-user-existence",
        json=payload 
    )
    assert response.status_code == 403


    # Test 2
    #==============================================
    # making a request with email that exists
    #==============================================
    payload = {
        "email": created_user.email,
        "username": "testuser2",
        **beta_token_dict,
    }
    response = await httpx_client.post(
        "/auth/probe-user-existence",
        json=payload  
    )
    assert response.status_code == 403

    # Test 3
    #================================================
    # making a request with non-existent data
    #================================================
    payload = {
        "email": 'johndoe@gmail.com',
        "username": "johndoe",
        **beta_token_dict
    }
    response = await httpx_client.post(
        "/auth/probe-user-existence",
        json=payload  
    )
    assert response.status_code == 200
