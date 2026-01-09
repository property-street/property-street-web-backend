import pytest
import asyncio
from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from property_street_backend.app.models import User
from property_street_backend.config.settings import BETA_LAUNCHING
from property_street_backend.config.settings import REAL_TEST_EMAIL
from property_street_backend.app.controllers.auth.services import generate_beta_signup_link

@pytest.mark.asyncio
async def test_send_and_confirm_email_verification_code(client__fixture):    
    # Fetch the client generator
    httpx_client: AsyncClient = client__fixture['http_client']
    redis_client: Redis = client__fixture['redis_client']

    # Define the post data for sending the email verification code
    beta_token = (await generate_beta_signup_link(redis_client))['token']
    send_code_data = {
        "email": REAL_TEST_EMAIL,
        "username": "crank",
        "beta_token": beta_token if BETA_LAUNCHING else None,
    }

    #++++++++++++++++++++++++++++++
    # Request a verification code
    #++++++++++++++++++++++++++++++
    response = await httpx_client.post(
        "/auth/send-email-verification-code",
        json=send_code_data  
    )
    # Assertions for sending the verification code
    assert response.status_code == 200
    json_response = response.json()
    assert json_response.get("message") == "A new verification code has been sent to your email."
    assert not await redis_client.exists(beta_token)


    #-------------------------------------
    # Request verification code again
    #-------------------------------------
    # generate a new token
    beta_token = (await generate_beta_signup_link(redis_client))['token']
    response = await httpx_client.post(
        "/auth/send-email-verification-code",
        json={
            **send_code_data,
            "beta_token": beta_token if BETA_LAUNCHING else None
        } 
    ) 
    # Assertions for sending the verification code
    assert response.status_code == 302
    json_response = response.json()
    assert json_response['detail']['message'] == "Please wait before requesting a new code."
    assert json_response['detail']['expiry']

    # Retrieve the code directly from Redis (this simulates the user entering the code they received)
    user_key = f'{send_code_data["email"]}:email_verification'
    verification_code: bytes = await redis_client.hget(user_key, "email_verification")
    assert verification_code is not None


    # ***************************************************** 
    # testing the confirm_email_verification_code function
    # ***************************************************** 

    #=======================
    # Case 1: Correct code
    #=======================
    confirm_code_data = {
        "email": send_code_data["email"],
        "code": verification_code,
    }
    # Confirm the verification code with correct data
    response = await httpx_client.post(
        "/auth/confirm-email-verification-code",
        json=confirm_code_data  # Use json instead of data for a JSON body
    )
    # Assertions for confirming the verification code
    assert response.status_code == 200
    json_response = response.json()
    assert json_response['message'] == "The email address has been successfully verified." 


    #===================================
    # Case 2: Expired verification code
    #===================================
    # Try confirming again
    response = await httpx_client.post(
        "/auth/confirm-email-verification-code",
        json=confirm_code_data  # Re-use the correct code data
    )
    # Assertions for the expired code
    assert response.status_code == 404
    json_response = response.json()
    assert json_response["detail"] == "Verification code not found or expired."
