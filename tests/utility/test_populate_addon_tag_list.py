import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from property_street_backend.utility_scripts.retrieve_and_store_all_tags import (
    populate_addon_tag_list
)


@pytest.mark.asyncio
async def test_create_agent(get_test_db__fixture: AsyncSession):
    try:
        # fetch the testdb
        test_db = await get_test_db__fixture

        await populate_addon_tag_list(session=test_db)
    finally:
        await test_db.close()