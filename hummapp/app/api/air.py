from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import StableAirMeasurement, User
from app.schemas import StableAirMeasurementResponse
from app.auth import get_current_user, require_role
from app.services.air_quality import air_quality_service

router = APIRouter(prefix="/api/stable-air", tags=["Talli-ilman mittaukset"])


@router.get("", response_model=List[StableAirMeasurementResponse])
def get_air_measurements(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Listaa tuoreimmat talli-ilman ja olosuhdemittausten lukemat."""
    readings = (
        db.query(StableAirMeasurement)
        .order_by(StableAirMeasurement.measured_at.desc())
        .limit(limit)
        .all()
    )
    return readings


@router.post("/sync", status_code=status.HTTP_200_OK)
async def sync_air_now(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "user"])),
):
    """Käynnistää välittömän talli-ilman mittausten haun anturipalvelusta."""
    synced_count = await air_quality_service.sync_air_readings(db)
    return {"message": "Talli-ilman mittaukset synkronoitu", "new_records": synced_count}
