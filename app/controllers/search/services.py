import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from .tools import normalize_query, rank_results
from property_street_backend.app.models import Area
from property_street_backend.app.controllers.assets.search import search_assets
from property_street_backend.app.controllers.agents.search import search_agents
from property_street_backend.app.controllers.roommate_finder.search import search_roommates
from property_street_backend.app.controllers.asset_request.search import search_asset_requests
from property_street_backend.config.postgres_connection_manager import get_postgres_instance as async_session_maker

def area_like_pattern(like_pattern):
    return (
        Area.country.ilike(like_pattern),
        Area.state_or_province.ilike(like_pattern),
        Area.city_or_town.ilike(like_pattern),
        Area.street.ilike(like_pattern),
    )


async def global_search(query: str):
    """
    Searches across Asset, AssetRequest, RoommateFinder, and Agent tables.
    Returns ranked, structured results.
    """
    normalized_query = normalize_query(query)

    async with async_session_maker() as db1, \
            async_session_maker() as db2, \
            async_session_maker() as db3, \
            async_session_maker() as db4:

        # Run individual searches concurrently
        results = await asyncio.gather(
            search_assets(normalized_query, db1),
            search_asset_requests(normalized_query, db2),
            search_roommates(normalized_query, db3),
            search_agents(normalized_query, db4),
        )
    
    # Flatten and rank results by relevance
    combined_results = rank_results(sum(results, []), query)
    
    return combined_results
