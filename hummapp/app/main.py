import os
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, Form, Depends, HTTPException, status, Response
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.database import engine, Base, SessionLocal, get_db
from app.models import (
    User,
    Horse,
    NfcTag,
    NfcEvent,
    VideoClip,
    HorseNote,
    MovementAnalysis,
    WaterMeasurement,
    StableAirMeasurement,
    SystemEvent,
    utc_now,
)
from app.auth import (
    seed_admin_user,
    verify_password,
    create_access_token,
    get_token_from_request,
)
import jwt

# Tuodaan API-reitit
from app.api.auth import router as auth_router
from app.api.system import router as system_router
from app.api.horses import router as horses_router
from app.api.nfc import router as nfc_router
from app.api.videos import router as videos_router
from app.api.notes import router as notes_router
from app.api.analyses import router as analyses_router
from app.api.water import router as water_router
from app.api.air import router as air_router
from app.api.public import router as public_router

from app.services.water import water_service
from app.services.air_quality import air_quality_service
from app.services.video import validate_and_resolve_video_path

# Lokituksen alustus
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("hummapp")

# Ajastin taustahakuja varten
scheduler = AsyncIOScheduler()


async def scheduled_water_sync():
    """Ajastettu Anteron juomamittausten haku."""
    db = SessionLocal()
    try:
        await water_service.sync_measurements(db)
    finally:
        db.close()


async def scheduled_air_sync():
    """Ajastettu talli-ilman mittausten haku."""
    db = SessionLocal()
    try:
        await air_quality_service.sync_air_readings(db)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Sovelluksen käynnistys- ja sammutustoimenpiteet."""
    logger.info(f"Käynnistetään {settings.APP_NAME} (Ympäristö: {settings.APP_ENV})...")

    # 1. Alustetaan SQLite-tietokanta ja taulut
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        cols = [row[1] for row in conn.exec_driver_sql("PRAGMA table_info(horses)").fetchall()]
        for col_name, col_type in [
            ("breed", "VARCHAR(128)"),
            ("birth_year", "INTEGER"),
            ("owner_name", "VARCHAR(128)"),
            ("stall_box", "VARCHAR(64)"),
            ("description", "TEXT"),
        ]:
            if col_name not in cols:
                conn.exec_driver_sql(f"ALTER TABLE horses ADD COLUMN {col_name} {col_type};")
    logger.info("Tietokantataulut varmistettu.")

    # 2. Varmistetaan oletuspääkäyttäjä
    db = SessionLocal()
    try:
        seed_admin_user(db)

        # 3. Tarkistetaan Antero-hevonen pilotissa
        antero = db.query(Horse).filter(Horse.name == settings.DRINKING_HORSE_NAME).first()
        if not antero:
            logger.info(f"Luodaan pilottiin juoma-automaattia käyttävä hevonen '{settings.DRINKING_HORSE_NAME}'...")
            antero = Horse(name=settings.DRINKING_HORSE_NAME, active=True)
            db.add(antero)
            db.commit()
            db.refresh(antero)
            # Yhdistetään myös esimerkkikäyttöön NFC-tagi
            default_tag = NfcTag(horse_id=antero.id, nfc_uid="04A31B92C56F80", active=True)
            db.add(default_tag)
            db.commit()
            logger.info(f"Hevonen '{settings.DRINKING_HORSE_NAME}' ja tagi '04A31B92C56F80' alustettu.")

        # Varmistetaan toinenkin tallihevonen pilottitestejä varten (esim. Valo)
        second_horse = db.query(Horse).filter(Horse.name == "Valo").first()
        if not second_horse:
            second_horse = Horse(name="Valo", active=True)
            db.add(second_horse)
            db.commit()
            db.refresh(second_horse)
            db.add(NfcTag(horse_id=second_horse.id, nfc_uid="04E24589F10123", active=True))
            db.commit()

        # Tehdään alkusynkronointi mock-datalla
        if settings.WATER_USE_MOCK:
            await water_service.sync_measurements(db)
        if settings.AIR_USE_MOCK:
            await air_quality_service.sync_air_readings(db)

    except Exception as e:
        logger.exception(f"Virhe käynnistysalustuksessa: {e}")
    finally:
        db.close()

    # 4. Käynnistetään ajastetut mittaushaut (APScheduler)
    if settings.WATER_FETCH_INTERVAL_MINUTES > 0:
        scheduler.add_job(
            scheduled_water_sync,
            "interval",
            minutes=settings.WATER_FETCH_INTERVAL_MINUTES,
            id="water_sync_job",
        )
    if settings.AIR_FETCH_INTERVAL_MINUTES > 0:
        scheduler.add_job(
            scheduled_air_sync,
            "interval",
            minutes=settings.AIR_FETCH_INTERVAL_MINUTES,
            id="air_sync_job",
        )
    scheduler.start()
    logger.info("APScheduler ajastettu mittauspalvelu käynnistetty.")

    yield

    # Sammutus
    logger.info("Sammutetaan HummAPP...")
    if scheduler.running:
        scheduler.shutdown()


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="HummAPP - Hevosten hyvinvointi ja talliseuranta (Synology NAS Pilotti)",
    lifespan=lifespan,
)

# CORS-määritykset
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Staattiset tiedostot ja mallineet
static_dir = Path(__file__).resolve().parent / "static"
templates_dir = Path(__file__).resolve().parent / "templates"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
templates = Jinja2Templates(directory=str(templates_dir))

# Liitetään API-reitit
app.include_router(auth_router)
app.include_router(system_router)
app.include_router(horses_router)
app.include_router(nfc_router)
app.include_router(videos_router)
app.include_router(notes_router)
app.include_router(analyses_router)
app.include_router(water_router)
app.include_router(air_router)
app.include_router(public_router)


# --- Apufunktio Web UI:n autentikointiin ---
def get_web_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    token = get_token_from_request(request)
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username = payload.get("sub")
        if not username:
            return None
        return db.query(User).filter(User.username == username, User.active == True).first()
    except Exception:
        return None


# --- Web UI Reitit ---
@app.get("/", response_class=HTMLResponse)
def index_page(request: Request, db: Session = Depends(get_db)):
    user = get_web_user(request, db)
    if not user:
        return RedirectResponse(url="/web/login", status_code=status.HTTP_302_FOUND)

    horse_count = db.query(Horse).filter(Horse.active == True).count()
    video_count = db.query(VideoClip).filter(VideoClip.status != "DELETED").count()

    # Anteron juomamäärä tänään
    antero = db.query(Horse).filter(Horse.name == settings.DRINKING_HORSE_NAME).first()
    antero_today_liters = 0.0
    antero_today_count = 0
    antero_last_drink = None

    if antero:
        today_start = utc_now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_m = (
            db.query(WaterMeasurement)
            .filter(WaterMeasurement.horse_id == antero.id, WaterMeasurement.measured_at >= today_start)
            .all()
        )
        antero_today_liters = round(sum(m.liters for m in today_m), 1)
        antero_today_count = len(today_m)

        latest_m = (
            db.query(WaterMeasurement)
            .filter(WaterMeasurement.horse_id == antero.id)
            .order_by(WaterMeasurement.measured_at.desc())
            .first()
        )
        if latest_m:
            antero_last_drink = f"{latest_m.liters} L ({latest_m.measured_at.strftime('%H:%M')})"

    latest_air = db.query(StableAirMeasurement).order_by(StableAirMeasurement.measured_at.desc()).first()
    recent_events = db.query(NfcEvent).order_by(NfcEvent.server_timestamp.desc()).limit(8).all()

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "current_user": user,
            "active_page": "dashboard",
            "horse_count": horse_count,
            "video_count": video_count,
            "antero_today_liters": antero_today_liters,
            "antero_today_count": antero_today_count,
            "antero_last_drink": antero_last_drink,
            "latest_air": latest_air,
            "recent_events": recent_events,
        },
    )


@app.get("/web/login", response_class=HTMLResponse)
def login_page(request: Request, error: Optional[str] = None):
    return templates.TemplateResponse("login.html", {"request": request, "error": error, "current_user": None})


@app.post("/web/login")
def login_post(
    response: Response,
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Virheellinen käyttäjätunnus tai salasana", "current_user": None},
            status_code=400,
        )

    token = create_access_token(data={"sub": user.username, "role": user.role, "uid": user.id})
    redirect = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    redirect.set_cookie(
        key="access_token",
        value=f"Bearer {token}",
        httponly=True,
        samesite="lax",
        max_age=30 * 24 * 3600,
    )
    return redirect


@app.get("/web/logout")
def logout_get():
    redirect = RedirectResponse(url="/web/login", status_code=status.HTTP_302_FOUND)
    redirect.delete_cookie(key="access_token")
    return redirect


@app.get("/web/horses", response_class=HTMLResponse)
def horses_page(request: Request, db: Session = Depends(get_db)):
    user = get_web_user(request, db)
    if not user:
        return RedirectResponse(url="/web/login", status_code=status.HTTP_302_FOUND)

    horses = db.query(Horse).filter(Horse.active == True).order_by(Horse.name.asc()).all()
    return templates.TemplateResponse(
        "horses.html",
        {
            "request": request,
            "current_user": user,
            "active_page": "horses",
            "horses": horses,
            "drinking_horse_name": settings.DRINKING_HORSE_NAME,
        },
    )


@app.post("/web/horses/create")
def horse_create_post(
    request: Request,
    name: str = Form(...),
    db: Session = Depends(get_db),
):
    user = get_web_user(request, db)
    if not user:
        return RedirectResponse(url="/web/login", status_code=status.HTTP_302_FOUND)

    cleaned = name.strip()
    if cleaned:
        existing = db.query(Horse).filter(Horse.name == cleaned).first()
        if not existing:
            horse = Horse(name=cleaned, active=True)
            db.add(horse)
            db.commit()

    return RedirectResponse(url="/web/horses", status_code=status.HTTP_302_FOUND)


@app.post("/web/horses/assign-tag")
def assign_tag_post(
    request: Request,
    horse_id: int = Form(...),
    nfc_uid: str = Form(...),
    db: Session = Depends(get_db),
):
    user = get_web_user(request, db)
    if not user:
        return RedirectResponse(url="/web/login", status_code=status.HTTP_302_FOUND)

    uid = nfc_uid.replace(" ", "").replace(":", "").upper()
    existing_tag = db.query(NfcTag).filter(NfcTag.nfc_uid == uid).first()
    if existing_tag:
        existing_tag.horse_id = horse_id
        existing_tag.active = True
    else:
        new_tag = NfcTag(horse_id=horse_id, nfc_uid=uid, active=True)
        db.add(new_tag)
    db.commit()

    return RedirectResponse(url="/web/horses", status_code=status.HTTP_302_FOUND)


@app.get("/web/horses/{id}", response_class=HTMLResponse)
def horse_detail_page(id: int, request: Request, db: Session = Depends(get_db)):
    user = get_web_user(request, db)
    if not user:
        return RedirectResponse(url="/web/login", status_code=status.HTTP_302_FOUND)

    horse = db.query(Horse).filter(Horse.id == id).first()
    if not horse:
        raise HTTPException(status_code=404, detail="Hevosta ei löydy.")

    # Haetaan hevosen videoleikkeet nfc_events kautta
    video_clips = (
        db.query(VideoClip)
        .join(NfcEvent, VideoClip.nfc_event_id == NfcEvent.id)
        .filter(NfcEvent.horse_id == id, VideoClip.status != "DELETED")
        .order_by(VideoClip.created_at.desc())
        .all()
    )

    return templates.TemplateResponse(
        "horse_detail.html",
        {
            "request": request,
            "current_user": user,
            "active_page": "horses",
            "horse": horse,
            "video_clips": video_clips,
            "drinking_horse_name": settings.DRINKING_HORSE_NAME,
        },
    )


@app.post("/web/horses/{id}/notes")
def add_horse_note_post(
    id: int,
    request: Request,
    content: str = Form(...),
    db: Session = Depends(get_db),
):
    user = get_web_user(request, db)
    if not user:
        return RedirectResponse(url="/web/login", status_code=status.HTTP_302_FOUND)

    if content.strip():
        note = HorseNote(horse_id=id, content=content.strip(), user_id=user.id)
        db.add(note)
        db.commit()

    return RedirectResponse(url=f"/web/horses/{id}", status_code=status.HTTP_302_FOUND)


@app.post("/web/horses/{id}/analyses")
def add_horse_analysis_post(
    id: int,
    request: Request,
    analysis_method: str = Form(...),
    summary: str = Form(...),
    db: Session = Depends(get_db),
):
    user = get_web_user(request, db)
    if not user:
        return RedirectResponse(url="/web/login", status_code=status.HTTP_302_FOUND)

    analysis = MovementAnalysis(
        horse_id=id,
        analysis_method=analysis_method.strip(),
        summary=summary.strip(),
        status="APPROVED",
        created_by=user.id,
    )
    db.add(analysis)
    db.commit()

    return RedirectResponse(url=f"/web/horses/{id}", status_code=status.HTTP_302_FOUND)


@app.get("/web/nfc-events", response_class=HTMLResponse)
def nfc_events_page(request: Request, db: Session = Depends(get_db)):
    user = get_web_user(request, db)
    if not user:
        return RedirectResponse(url="/web/login", status_code=status.HTTP_302_FOUND)

    events = db.query(NfcEvent).order_by(NfcEvent.server_timestamp.desc()).limit(100).all()
    return templates.TemplateResponse(
        "nfc_events.html",
        {
            "request": request,
            "current_user": user,
            "active_page": "events",
            "events": events,
        },
    )


@app.post("/web/video-clips/{id}/approve")
def approve_clip_web(id: int, request: Request, next: str = "/web/nfc-events", db: Session = Depends(get_db)):
    user = get_web_user(request, db)
    if not user:
        return RedirectResponse(url="/web/login", status_code=status.HTTP_302_FOUND)

    clip = db.query(VideoClip).filter(VideoClip.id == id).first()
    if clip:
        clip.status = "APPROVED"
        clip.approved_at = utc_now()
        if clip.nfc_event:
            clip.nfc_event.status = "APPROVED"
        db.commit()

    return RedirectResponse(url=next, status_code=status.HTTP_302_FOUND)


@app.post("/web/video-clips/{id}/reject")
def reject_clip_web(id: int, request: Request, next: str = "/web/nfc-events", db: Session = Depends(get_db)):
    user = get_web_user(request, db)
    if not user:
        return RedirectResponse(url="/web/login", status_code=status.HTTP_302_FOUND)

    clip = db.query(VideoClip).filter(VideoClip.id == id).first()
    if clip:
        clip.status = "REJECTED"
        clip.rejected_at = utc_now()
        if clip.nfc_event:
            clip.nfc_event.status = "REJECTED"
        db.commit()

    return RedirectResponse(url=next, status_code=status.HTTP_302_FOUND)


@app.post("/web/video-clips/{id}/delete")
def delete_clip_web(id: int, request: Request, next: str = "/web/nfc-events", db: Session = Depends(get_db)):
    user = get_web_user(request, db)
    if not user or user.role != "admin":
        return RedirectResponse(url="/web/login", status_code=status.HTTP_302_FOUND)

    clip = db.query(VideoClip).filter(VideoClip.id == id).first()
    if clip:
        try:
            file_path = validate_and_resolve_video_path(clip.relative_file_path)
            if file_path.exists():
                file_path.unlink()
        except Exception:
            pass
        clip.status = "DELETED"
        clip.deleted_at = utc_now()
        db.commit()

    return RedirectResponse(url=next, status_code=status.HTTP_302_FOUND)


@app.get("/web/water", response_class=HTMLResponse)
def water_page(request: Request, db: Session = Depends(get_db)):
    user = get_web_user(request, db)
    if not user:
        return RedirectResponse(url="/web/login", status_code=status.HTTP_302_FOUND)

    antero = db.query(Horse).filter(Horse.name == settings.DRINKING_HORSE_NAME).first()
    measurements = db.query(WaterMeasurement).order_by(WaterMeasurement.measured_at.desc()).limit(50).all()

    today_start = utc_now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_records = [m for m in measurements if m.measured_at >= today_start and m.horse_id == (antero.id if antero else -1)]
    today_liters = round(sum(m.liters for m in today_records), 1)
    today_count = len(today_records)
    latest_measurement = measurements[0] if measurements else None

    return templates.TemplateResponse(
        "water.html",
        {
            "request": request,
            "current_user": user,
            "active_page": "water",
            "drinking_horse_name": settings.DRINKING_HORSE_NAME,
            "water_external_id": settings.WATER_EXTERNAL_ID,
            "antero_found": bool(antero),
            "today_liters": today_liters,
            "today_count": today_count,
            "latest_measurement": latest_measurement,
            "measurements": measurements,
        },
    )


@app.post("/web/water/sync")
async def sync_water_web(request: Request, db: Session = Depends(get_db)):
    user = get_web_user(request, db)
    if not user:
        return RedirectResponse(url="/web/login", status_code=status.HTTP_302_FOUND)
    await water_service.sync_measurements(db)
    return RedirectResponse(url="/web/water", status_code=status.HTTP_302_FOUND)


@app.get("/web/air", response_class=HTMLResponse)
def air_page(request: Request, db: Session = Depends(get_db)):
    user = get_web_user(request, db)
    if not user:
        return RedirectResponse(url="/web/login", status_code=status.HTTP_302_FOUND)

    readings = db.query(StableAirMeasurement).order_by(StableAirMeasurement.measured_at.desc()).limit(50).all()
    latest = readings[0] if readings else None

    return templates.TemplateResponse(
        "air.html",
        {
            "request": request,
            "current_user": user,
            "active_page": "air",
            "readings": readings,
            "latest": latest,
        },
    )


@app.post("/web/air/sync")
async def sync_air_web(request: Request, db: Session = Depends(get_db)):
    user = get_web_user(request, db)
    if not user:
        return RedirectResponse(url="/web/login", status_code=status.HTTP_302_FOUND)
    await air_quality_service.sync_air_readings(db)
    return RedirectResponse(url="/web/air", status_code=status.HTTP_302_FOUND)


@app.get("/web/system", response_class=HTMLResponse)
def system_page(request: Request, db: Session = Depends(get_db)):
    user = get_web_user(request, db)
    if not user:
        return RedirectResponse(url="/web/login", status_code=status.HTTP_302_FOUND)

    antero = db.query(Horse).filter(Horse.name == settings.DRINKING_HORSE_NAME).first()
    system_events = db.query(SystemEvent).order_by(SystemEvent.created_at.desc()).limit(30).all()
    cam_dir_ok = Path(settings.CAMERA_SOURCE_PATH).exists()

    return templates.TemplateResponse(
        "system.html",
        {
            "request": request,
            "current_user": user,
            "active_page": "system",
            "settings": settings,
            "antero_found": bool(antero),
            "camera_dir_exists": cam_dir_ok,
            "system_events": system_events,
        },
    )
