from fastapi import APIRouter, Depends

from .services import (
    StreamState,
    update_state,
    rank_and_select,
    fetch_candidates,
    load_stream_state,
)
from property_street_backend.app.database import get_db
from property_street_backend.app.initiator import get_redis
from property_street_backend.app.controllers.assets.schemas import PropertyResponseSchema
from property_street_backend.app.controllers.auth.services import decode_user_from_token_optional

router = APIRouter(prefix="/stream")

@router.post("/stream")
async def stream_feed(
    db=Depends(get_db),
    redis=Depends(get_redis),
    user=Depends(decode_user_from_token_optional),
):
    state: StreamState = await load_stream_state(redis, user.id)

    quotas = { # category: limit
        "Mini Flat": 6,
        "Self contain": 6,
        "Apartment": 4,
        "Explore": 4,  # fallback pool
    }

    candidates = await fetch_candidates(db, state, quotas)
    results = rank_and_select(candidates, state, limit=20)

    await update_state(redis, user.id, results)

    return [
        PropertyResponseSchema.model_validate(a).model_dump()
        for a in results
    ]
