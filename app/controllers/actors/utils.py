from property_street_backend.config import env_is_test
from property_street_backend.config.settings import (
    STAFF_LINK_VALIDITY, 
    TEST_STAFF_LINK_VALIDITY
)


def get_staff_validity_link():
    return TEST_STAFF_LINK_VALIDITY if env_is_test() else STAFF_LINK_VALIDITY