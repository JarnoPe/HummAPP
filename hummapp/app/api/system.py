import datetime
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth import require_role
from app.config import settings
from app.constants import ADMIN_ROLES
from app.database import get_db
from app.models import User
from app.schemas import SystemStatusResponse
from app.services.horses import get_drinking_horse

router = APIRouter(tags=["Järjestelmä"])

APP_VERSION = "1.1.0"


def database_ok(db: Session) -> bool:
    try:
        db.execute(text("SELECT 1")).scalar()
        return True
    except Exception:
        return False


@router.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    """Kevyt healthcheck Dockerille / Container Managerille. Ei paljasta sisäisiä tietoja."""
    ok = database_ok(db)
    return {
        "status": "ok" if ok else "degraded",
        "app": settings.APP_NAME,
        "database": "healthy" if ok else "unhealthy",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


@router.get("/api/system/status", response_model=SystemStatusResponse)
def system_status(db: Session = Depends(get_db), current_user: User = Depends(require_role(ADMIN_ROLES))):
    """Yksityiskohtainen järjestelmätila ylläpitäjälle (vaatii admin-roolin)."""
    db_ok = database_ok(db)
    horse = get_drinking_horse(db)
    return SystemStatusResponse(
        status="operational" if (db_ok and horse) else "attention_required",
        app_name=settings.APP_NAME,
        version=APP_VERSION,
        database_ok=db_ok,
        camera_dir_exists=Path(settings.CAMERA_SOURCE_PATH).exists(),
        video_dir_exists=Path(settings.VIDEO_OUTPUT_PATH).exists(),
        antero_configured=bool(settings.DRINKING_HORSE_NAME),
        antero_horse_found=bool(horse),
        antero_horse_id=horse.id if horse else None,
        water_external_id=settings.WATER_EXTERNAL_ID,
        mock_water_enabled=settings.WATER_USE_MOCK,
        mock_air_enabled=settings.AIR_USE_MOCK,
        mock_camera_fallback_enabled=settings.ENABLE_MOCK_CAMERA_FALLBACK,
        video_seconds_before=settings.VIDEO_SECONDS_BEFORE,
        video_seconds_after=settings.VIDEO_SECONDS_AFTER,
        uptime_utc=datetime.datetime.now(datetime.timezone.utc),
    )
