"""
Web-käyttöliittymän reitit. Logiikka on palvelukerroksessa (app/services),
jota myös REST-API käyttää – reitit vain lukevat lomakkeet ja renderöivät sivut.
"""
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, selectinload

from app.auth import COOKIE_NAME, authenticate, create_user_token, get_token_from_request, set_auth_cookie, user_from_token
from app.config import settings
from app.constants import ClipStatus, Role
from app.database import get_db
from app.models import (
    Horse,
    HorseNote,
    MovementAnalysis,
    NfcEvent,
    StableAirMeasurement,
    SystemEvent,
    User,
    VideoClip,
    WaterMeasurement,
)
from app.services import video_review
from app.services.air_quality import air_quality_service
from app.services.horses import assign_nfc_tag, find_horse_by_name, get_drinking_horse
from app.services.water import water_service
from app.timeutils import local_time_label

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.filters["local_time"] = local_time_label
templates.env.globals["clip_seconds"] = settings.clip_duration_seconds

router = APIRouter(include_in_schema=False)

LOGIN_URL = "/web/login"
DEFAULT_NEXT = "/web/nfc-events"


class WebLoginRequired(Exception):
    """Nostetaan, kun web-sivu vaatii kirjautumisen. Käsitellään main.py:ssä uudelleenohjauksella."""


def get_web_user(token: Optional[str] = Depends(get_token_from_request), db: Session = Depends(get_db)) -> Optional[User]:
    # HUOM: get_token_from_request on riippuvuus – sitä ei saa kutsua suoraan, koska silloin
    # bearer_token-parametrin oletusarvo on Depends-olio (alkuperäisen version virhe).
    return user_from_token(token, db)


def require_web_user(user: Optional[User] = Depends(get_web_user)) -> User:
    if not user:
        raise WebLoginRequired()
    return user


def require_web_admin(user: User = Depends(require_web_user)) -> User:
    if user.role != Role.ADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Toiminto vaatii admin-roolin.")
    return user


def redirect(url: str) -> RedirectResponse:
    return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)


def safe_next(next_url: Optional[str], default: str = DEFAULT_NEXT) -> str:
    """Sallii vain saman palvelun suhteelliset polut (estää avoimen uudelleenohjauksen)."""
    if next_url and next_url.startswith("/") and not next_url.startswith(("//", "/\\")):
        return next_url
    return default


def render(request: Request, template: str, user: Optional[User], active_page: str = "", **context):
    return templates.TemplateResponse(
        request, template, {"current_user": user, "active_page": active_page, **context}
    )


# --- Kirjautuminen ---------------------------------------------------------
@router.get("/web/login", response_class=HTMLResponse)
def login_page(request: Request, error: Optional[str] = None):
    return render(request, "login.html", None, error=error)


@router.post("/web/login")
def login_post(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = authenticate(db, username, password)
    if not user or not user.active:
        message = "Käyttäjätili on passivoitu" if user else "Virheellinen käyttäjätunnus tai salasana"
        response = render(request, "login.html", None, error=message)
        response.status_code = status.HTTP_400_BAD_REQUEST
        return response
    response = redirect("/")
    set_auth_cookie(response, create_user_token(user))
    return response


@router.get("/web/logout")
def logout_get():
    response = redirect(LOGIN_URL)
    response.delete_cookie(key=COOKIE_NAME)
    return response


# --- Katsaus ---------------------------------------------------------------
@router.get("/", response_class=HTMLResponse)
def index_page(request: Request, db: Session = Depends(get_db), user: User = Depends(require_web_user)):
    today = water_service.today(db)
    latest = today.latest
    recent_events = (
        db.query(NfcEvent)
        .options(selectinload(NfcEvent.horse))
        .order_by(NfcEvent.server_timestamp.desc())
        .limit(8)
        .all()
    )
    return render(
        request, "index.html", user, "dashboard",
        horse_count=db.query(Horse).filter(Horse.active == True).count(),  # noqa: E712
        video_count=db.query(VideoClip).filter(VideoClip.status != ClipStatus.DELETED.value).count(),
        antero_today_liters=today.liters,
        antero_today_count=today.count,
        antero_last_drink=f"{latest.liters} L ({local_time_label(latest.measured_at)})" if latest else None,
        latest_air=db.query(StableAirMeasurement).order_by(StableAirMeasurement.measured_at.desc()).first(),
        recent_events=recent_events,
    )


# --- Hevoset ---------------------------------------------------------------
@router.get("/web/horses", response_class=HTMLResponse)
def horses_page(request: Request, db: Session = Depends(get_db), user: User = Depends(require_web_user)):
    horses = (
        db.query(Horse)
        .options(selectinload(Horse.nfc_tags))
        .filter(Horse.active == True)  # noqa: E712
        .order_by(Horse.name.asc())
        .all()
    )
    return render(request, "horses.html", user, "horses", horses=horses,
                  drinking_horse_name=settings.DRINKING_HORSE_NAME)


@router.post("/web/horses/create")
def horse_create_post(name: str = Form(...), db: Session = Depends(get_db), user: User = Depends(require_web_user)):
    cleaned = name.strip()
    if cleaned and not find_horse_by_name(db, cleaned):
        db.add(Horse(name=cleaned, active=True))
        db.commit()
    return redirect("/web/horses")


@router.post("/web/horses/assign-tag")
def assign_tag_post(
    horse_id: int = Form(...),
    nfc_uid: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_web_user),
):
    if not db.get(Horse, horse_id):
        raise HTTPException(status_code=404, detail="Hevosta ei löydy.")
    try:
        assign_nfc_tag(db, horse_id, nfc_uid)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return redirect("/web/horses")


@router.get("/web/horses/{horse_id}", response_class=HTMLResponse)
def horse_detail_page(horse_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_web_user)):
    horse = db.get(Horse, horse_id)
    if not horse:
        raise HTTPException(status_code=404, detail="Hevosta ei löydy.")
    video_clips = (
        db.query(VideoClip)
        .join(NfcEvent, VideoClip.nfc_event_id == NfcEvent.id)
        .filter(NfcEvent.horse_id == horse_id, VideoClip.status != ClipStatus.DELETED.value)
        .order_by(VideoClip.created_at.desc())
        .all()
    )
    return render(request, "horse_detail.html", user, "horses", horse=horse, video_clips=video_clips,
                  drinking_horse_name=settings.DRINKING_HORSE_NAME)


@router.post("/web/horses/{horse_id}/notes")
def add_horse_note_post(horse_id: int, content: str = Form(...), db: Session = Depends(get_db),
                        user: User = Depends(require_web_user)):
    if content.strip() and db.get(Horse, horse_id):
        db.add(HorseNote(horse_id=horse_id, content=content.strip(), user_id=user.id))
        db.commit()
    return redirect(f"/web/horses/{horse_id}")


@router.post("/web/horses/{horse_id}/analyses")
def add_horse_analysis_post(
    horse_id: int,
    analysis_method: str = Form(...),
    summary: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_web_user),
):
    if db.get(Horse, horse_id) and summary.strip():
        db.add(MovementAnalysis(horse_id=horse_id, analysis_method=analysis_method.strip(),
                                summary=summary.strip(), status="APPROVED", created_by=user.id))
        db.commit()
    return redirect(f"/web/horses/{horse_id}")


# --- NFC-tapahtumat ja videot ------------------------------------------------
@router.get("/web/nfc-events", response_class=HTMLResponse)
def nfc_events_page(request: Request, db: Session = Depends(get_db), user: User = Depends(require_web_user)):
    events = (
        db.query(NfcEvent)
        .options(selectinload(NfcEvent.horse), selectinload(NfcEvent.video_clips))
        .order_by(NfcEvent.server_timestamp.desc())
        .limit(100)
        .all()
    )
    return render(request, "nfc_events.html", user, "events", events=events)


def _review_web(db: Session, clip_id: int, new_status: ClipStatus, next_url: Optional[str]):
    try:
        video_review.set_review_status(db, clip_id, new_status)
    except video_review.ClipNotFound:
        raise HTTPException(status_code=404, detail="Videoleikettä ei löydy.")
    return redirect(safe_next(next_url))


@router.post("/web/video-clips/{clip_id}/approve")
def approve_clip_web(clip_id: int, next: Optional[str] = None, db: Session = Depends(get_db),
                     user: User = Depends(require_web_user)):
    return _review_web(db, clip_id, ClipStatus.APPROVED, next)


@router.post("/web/video-clips/{clip_id}/reject")
def reject_clip_web(clip_id: int, next: Optional[str] = None, db: Session = Depends(get_db),
                    user: User = Depends(require_web_user)):
    return _review_web(db, clip_id, ClipStatus.REJECTED, next)


@router.post("/web/video-clips/{clip_id}/delete")
def delete_clip_web(clip_id: int, next: Optional[str] = None, db: Session = Depends(get_db),
                    user: User = Depends(require_web_admin)):
    try:
        video_review.delete_clip(db, clip_id)
    except video_review.ClipNotFound:
        raise HTTPException(status_code=404, detail="Videoleikettä ei löydy.")
    return redirect(safe_next(next))


# --- Juominen ja talli-ilma ---------------------------------------------------
@router.get("/web/water", response_class=HTMLResponse)
def water_page(request: Request, db: Session = Depends(get_db), user: User = Depends(require_web_user)):
    today = water_service.today(db)
    measurements = db.query(WaterMeasurement).order_by(WaterMeasurement.measured_at.desc()).limit(50).all()
    return render(
        request, "water.html", user, "water",
        drinking_horse_name=settings.DRINKING_HORSE_NAME,
        water_external_id=settings.WATER_EXTERNAL_ID,
        antero_found=get_drinking_horse(db) is not None,
        today_liters=today.liters,
        today_count=today.count,
        latest_measurement=measurements[0] if measurements else None,
        measurements=measurements,
    )


@router.post("/web/water/sync")
async def sync_water_web(db: Session = Depends(get_db), user: User = Depends(require_web_user)):
    await water_service.sync_measurements(db)
    return redirect("/web/water")


@router.get("/web/air", response_class=HTMLResponse)
def air_page(request: Request, db: Session = Depends(get_db), user: User = Depends(require_web_user)):
    readings = db.query(StableAirMeasurement).order_by(StableAirMeasurement.measured_at.desc()).limit(50).all()
    return render(request, "air.html", user, "air", readings=readings, latest=readings[0] if readings else None)


@router.post("/web/air/sync")
async def sync_air_web(db: Session = Depends(get_db), user: User = Depends(require_web_user)):
    await air_quality_service.sync_air_readings(db)
    return redirect("/web/air")


# --- Järjestelmä --------------------------------------------------------------
@router.get("/web/system", response_class=HTMLResponse)
def system_page(request: Request, db: Session = Depends(get_db), user: User = Depends(require_web_admin)):
    # Templatelle annetaan vain näytettävät arvot – EI koko settings-oliota (sisältää SECRET_KEYn)
    system_info = {
        "DATABASE_PATH": settings.DATABASE_PATH,
        "DRINKING_HORSE_NAME": settings.DRINKING_HORSE_NAME,
        "WATER_EXTERNAL_ID": settings.WATER_EXTERNAL_ID,
        "CAMERA_SOURCE_PATH": settings.CAMERA_SOURCE_PATH,
        "VIDEO_OUTPUT_PATH": settings.VIDEO_OUTPUT_PATH,
        "CAMERA_TIMEZONE": settings.CAMERA_TIMEZONE,
        "VIDEO_SECONDS_BEFORE": settings.VIDEO_SECONDS_BEFORE,
        "VIDEO_SECONDS_AFTER": settings.VIDEO_SECONDS_AFTER,
        "ENABLE_MOCK_CAMERA_FALLBACK": settings.ENABLE_MOCK_CAMERA_FALLBACK,
    }
    return render(
        request, "system.html", user, "system",
        settings=system_info,
        antero_found=get_drinking_horse(db) is not None,
        camera_dir_exists=Path(settings.CAMERA_SOURCE_PATH).exists(),
        system_events=db.query(SystemEvent).order_by(SystemEvent.created_at.desc()).limit(30).all(),
    )
