from property_street_backend.config import env_is_test
from property_street_backend.config.settings import (
    NEWLY_CREATED_ASSET_TTL,
    TEST_NEWLY_CREATED_ASSET_TTL,
)

def property_create_persistence_ttl() -> int:
    """returns the cache persistence property depending on context

    Returns:
        int: time in seconds
    """
    return (TEST_NEWLY_CREATED_ASSET_TTL 
        if env_is_test() else 
    NEWLY_CREATED_ASSET_TTL)