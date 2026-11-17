from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_role
from app.constants import EDITOR_ROLES
from app.database import get_db
from app.models import StableAirMeasurement, User
from app.schemas import StableAirMeasurementResponse
from app.services.air_quality import air_quality_service

router = APIRouter(prefix="/api/stable-air", tags=["Talli-ilman mittaukset"])


@router.get("", response_model=List[StableAirMeasurementResponse])
def get_air_measurements(
    limit: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Listaa tuoreimmat talli-ilman ja olosuhdemittausten lukemat."""
    return (
        db.query(StableAirMeasurement)
        .order_by(StableAirMeasurement.measured_at.desc())
        .limit(limit)
        .all()
    )


@router.post("/sync")
async def sync_air_now(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(EDITOR_ROLES)),
):
    """Käynnistää välittömän talli-ilman mittausten haun anturipalvelusta."""
    synced_count = await air_quality_service.sync_air_readings(db)
    return {"message": "Talli-ilman mittaukset synkronoitu", "new_records": synced_count}
