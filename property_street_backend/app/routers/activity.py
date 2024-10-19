from typing import Dict
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends

from property_street_backend.app.database import get_db
from property_street_backend.app.controllers.activity.agent_crud_processing import (
    process_asset as controller_process_asset
)


router = APIRouter(prefix="/activity", tags=["activity"])

@router.post("/process_asset")
async def process_asset(data: Dict, db: Session = Depends(get_db)):
    controller_process_asset(
        data = data,
        db = db
    )
    pass