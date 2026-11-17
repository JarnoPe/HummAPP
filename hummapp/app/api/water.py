from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, selectinload

from app.auth import get_current_user, require_role
from app.constants import EDITOR_ROLES
from app.database import get_db
from app.models import User, WaterMeasurement
from app.schemas import WaterDailySummary, WaterMeasurementResponse
from app.services.water import water_service

router = APIRouter(prefix="/api/water", tags=["Juomismittaukset (Antero)"])

UNASSIGNED_LABEL = "Tunnistamaton / Ei yhdistetty"


@router.get("", response_model=List[WaterMeasurementResponse])
def get_water_measurements(
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Listaa viimeisimmät juomismittaukset (pilotissa vain Anterolla on juoma-automaatti)."""
    measurements = (
        db.query(WaterMeasurement)
        .options(selectinload(WaterMeasurement.horse))
        .order_by(WaterMeasurement.measured_at.desc())
        .limit(limit)
        .all()
    )
    return [
        WaterMeasurementResponse(
            id=m.id,
            horse_id=m.horse_id,
            horse_name=m.horse.name if m.horse else UNASSIGNED_LABEL,
            external_measurement_id=m.external_measurement_id,
            external_water_id=m.external_water_id,
            measured_at=m.measured_at,
            liters=m.liters,
            raw_data_json=m.raw_data_json,
            created_at=m.created_at,
        )
        for m in measurements
    ]


@router.get("/daily", response_model=List[WaterDailySummary])
def get_daily_water_summary(
    days: int = Query(14, ge=1, le=366),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Anteron päivittäinen juomamäärä litroina (vuorokausi Suomen ajan mukaan)."""
    return [WaterDailySummary(**vars(d)) for d in water_service.daily_summary(db, days)]


@router.post("/sync")
async def sync_water_now(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(EDITOR_ROLES)),
):
    """Käynnistää välittömän mittausdatan haun juomapalvelusta."""
    synced_count = await water_service.sync_measurements(db)
    return {"message": "Juomadata synkronoitu", "new_records": synced_count}
