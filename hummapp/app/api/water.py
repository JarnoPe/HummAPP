from typing import List, Optional
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import WaterMeasurement, Horse, User
from app.schemas import WaterMeasurementResponse, WaterDailySummary
from app.auth import get_current_user, require_role
from app.services.water import water_service
from app.config import settings

router = APIRouter(prefix="/api/water", tags=["Juomismittaukset (Antero)"])


@router.get("", response_model=List[WaterMeasurementResponse])
def get_water_measurements(
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Listaa viimeisimmät juomismittaukset.
    Hankkeessa vain Anterolla on juoma-automaatti.
    """
    measurements = (
        db.query(WaterMeasurement)
        .order_by(WaterMeasurement.measured_at.desc())
        .limit(limit)
        .all()
    )

    results = []
    for m in measurements:
        results.append(
            WaterMeasurementResponse(
                id=m.id,
                horse_id=m.horse_id,
                horse_name=m.horse.name if m.horse else "Tunnistamaton / Ei yhdistetty",
                external_measurement_id=m.external_measurement_id,
                external_water_id=m.external_water_id,
                measured_at=m.measured_at,
                liters=m.liters,
                raw_data_json=m.raw_data_json,
                created_at=m.created_at,
            )
        )
    return results


@router.get("/daily", response_model=List[WaterDailySummary])
def get_daily_water_summary(
    days: int = 14,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Palauttaa Anteron päivittäisen juomamäärän litroina Chart.js -kuvaajaa varten.
    """
    antero = db.query(Horse).filter(Horse.name == settings.DRINKING_HORSE_NAME).first()
    if not antero:
        return []

    # Haetaan Anteron mittaukset
    measurements = (
        db.query(WaterMeasurement)
        .filter(WaterMeasurement.horse_id == antero.id)
        .order_by(WaterMeasurement.measured_at.asc())
        .all()
    )

    daily_totals = defaultdict(lambda: {"total": 0.0, "count": 0})
    for m in measurements:
        day_str = m.measured_at.strftime("%Y-%m-%d")
        daily_totals[day_str]["total"] += m.liters
        daily_totals[day_str]["count"] += 1

    summaries = []
    for date_key in sorted(daily_totals.keys())[-days:]:
        summaries.append(
            WaterDailySummary(
                date=date_key,
                total_liters=round(daily_totals[date_key]["total"], 1),
                measurement_count=daily_totals[date_key]["count"],
            )
        )
    return summaries


@router.post("/sync", status_code=status.HTTP_200_OK)
async def sync_water_now(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "user"])),
):
    """Käynnistää välittömän mittausdatan haun juomapalvelusta."""
    synced_count = await water_service.sync_measurements(db)
    return {"message": "Juomadata synkronoitu", "new_records": synced_count}
