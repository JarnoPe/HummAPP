import os
import datetime
from pathlib import Path
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.config import settings
from app.models import Horse, SystemEvent
from app.schemas import SystemStatusResponse

router = APIRouter(tags=["Järjestelmä"])


@router.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    """
    Kevyt kunnonvalvontapäätepiste (Healthcheck).
    Käytetään Dockerin HEALTHCHECK-komennossa ja Synology Container Managerissa.
    """
    try:
        db.execute(text("SELECT 1")).scalar()
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {e}"

    return {
        "status": "ok" if db_status == "healthy" else "degraded",
        "app": settings.APP_NAME,
        "database": db_status,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


@router.get("/api/system/status", response_model=SystemStatusResponse)
def system_status(db: Session = Depends(get_db)):
    """
    Yksityiskohtainen järjestelmätilaraportti ylläpitäjälle.
    Tarkistaa:
    - Tietokannan toiminnan
    - Kameran ja videoiden hakemistot
    - Onko Antero luotu tietokantaan juomamittausten vastaanottoa varten
    - Ulkoisten palveluiden mock-tilat
    """
    db_ok = True
    try:
        db.execute(text("SELECT 1")).scalar()
    except Exception:
        db_ok = False

    cam_dir_ok = Path(settings.CAMERA_SOURCE_PATH).exists()
    vid_dir_ok = Path(settings.VIDEO_OUTPUT_PATH).exists()

    antero = db.query(Horse).filter(Horse.name == settings.DRINKING_HORSE_NAME).first()

    return SystemStatusResponse(
        status="operational" if (db_ok and antero) else "attention_required",
        app_name=settings.APP_NAME,
        version="1.0.0",
        database_ok=db_ok,
        camera_dir_exists=cam_dir_ok,
        video_dir_exists=vid_dir_ok,
        antero_configured=bool(settings.DRINKING_HORSE_NAME),
        antero_horse_found=bool(antero),
        antero_horse_id=antero.id if antero else None,
        water_external_id=settings.WATER_EXTERNAL_ID,
        mock_water_enabled=settings.WATER_USE_MOCK,
        mock_air_enabled=settings.AIR_USE_MOCK,
        uptime_utc=datetime.datetime.now(datetime.timezone.utc),
    )
