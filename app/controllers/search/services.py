import asyncio
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from .tools import normalize_query, rank_results
from property_street_backend.app.models import Area
from property_street_backend.app.controllers.assets.search import search_assets
from property_street_backend.app.controllers.agents.search import search_agents
from property_street_backend.app.controllers.roommate_finder.search import search_roommates
from property_street_backend.app.controllers.asset_request.search import search_asset_requests


def area_like_pattern(like_pattern):
    return (
        Area.country.ilike(like_pattern),
        Area.state_or_province.ilike(like_pattern),
        Area.city_or_town.ilike(like_pattern),
        Area.street.ilike(like_pattern),
    )


async def global_search(query: str, limit: int = 20, offset: int = 0, seen_ids: List[int] = None):
    """
    Searches across Asset, AssetRequest, RoommateFinder, and Agent tables.
    Returns ranked, structured results with pagination support.
    
    Args:
        query: Search query string
        limit: Number of results to return per page
        offset: Number of results to skip
        seen_ids: List of IDs to exclude from results (for pagination)
    """
    if seen_ids is None:
        seen_ids = []
    
    normalized_query = normalize_query(query)

    # Run individual searches concurrently
    results = await asyncio.gather(
        search_assets(normalized_query, limit=limit*2, seen_ids=seen_ids),
        search_asset_requests(normalized_query, limit=limit*2, seen_ids=seen_ids),
        search_roommates(normalized_query, limit=limit*2, seen_ids=seen_ids),
        search_agents(normalized_query, limit=limit*2, seen_ids=seen_ids),
    )
    
    # Flatten and rank results by relevance
    combined_results = rank_results(sum(results, []), query)
    
    # Apply pagination
    total = len(combined_results)
    paginated_results = combined_results[offset:offset + limit]
    
    return {
        "results": paginated_results,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": (offset + limit) < total
    }
