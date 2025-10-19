from property_street_backend.config import env_is_test
from property_street_backend.config.settings import (
    PASSWORD_UPDATE_TTL,
    TEST_PASSWORD_UPDATE_TTL,
)

def get_password_update_ttl():
    return TEST_PASSWORD_UPDATE_TTL if env_is_test() else PASSWORD_UPDATE_TTL

def password_update_set_token(email): 
    return f"{email}_verified_for_password_update"
