"""
Web-käyttöliittymän reitit. Logiikka on palvelukerroksessa (app/services),
jota myös REST-API käyttää – reitit vain lukevat lomakkeet ja renderöivät sivut.
"""
import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, selectinload

from app.auth import COOKIE_NAME, authenticate, create_user_token, get_token_from_request, set_auth_cookie, user_from_token
from app.config import settings
from app.constants import EDITOR_ROLES, ClipStatus, Role
from app.database import get_db
from app.models import utc_now
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
from app.services import users as users_service
from app.services import video_review
from app.services.air_quality import air_quality_service
from app.services.horses import assign_nfc_tag, find_horse_by_name, get_drinking_horse
from app.services.water import water_service
from app.timeutils import local_date_key, local_time_label, utc_now as aware_utc_now
from app.web import ui

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.filters["local_time"] = local_time_label
templates.env.filters["num"] = ui.format_number
templates.env.globals.update(
    role_label=ui.role_label,
    clip_seconds=settings.clip_duration_seconds,
    clip_before=settings.VIDEO_SECONDS_BEFORE,
    clip_after=settings.VIDEO_SECONDS_AFTER,
    status_label=ui.status_label,
    status_tone=ui.status_tone,
    event_error_text=ui.event_error_text,
    drinking_horse_name=settings.DRINKING_HORSE_NAME,
)

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


def require_web_editor(user: User = Depends(require_web_user)) -> User:
    """Muutokset vaativat ylläpitäjän tai tallin käyttäjän roolin (katselija näkee vain)."""
    if user.role not in EDITOR_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Katselija-rooli ei voi muuttaa tietoja.")
    return user


def require_web_admin(user: User = Depends(require_web_user)) -> User:
    if user.role != Role.ADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Toiminto vaatii admin-roolin.")
    return user


def redirect(url: str, flash: Optional[str] = None) -> RedirectResponse:
    if flash:
        url = f"{url}{'&' if '?' in url else '?'}ilmoitus={flash}"
    return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)


def pending_review_count(db: Session) -> int:
    """Leikkeet, jotka odottavat käyttäjän tarkastusta (valmiit, ei vielä hyväksytty tai hylätty)."""
    return db.query(VideoClip).filter(VideoClip.status == ClipStatus.READY.value).count()


def wants_json(request: Request) -> bool:
    return "application/json" in request.headers.get("accept", "")


def safe_next(next_url: Optional[str], default: str = DEFAULT_NEXT) -> str:
    """Sallii vain saman palvelun suhteelliset polut (estää avoimen uudelleenohjauksen)."""
    if next_url and next_url.startswith("/") and not next_url.startswith(("//", "/\\")):
        return next_url
    return default


def render(request: Request, template: str, user: Optional[User], active_page: str = "",
           db: Optional[Session] = None, **context):
    base = {
        "current_user": user,
        "active_page": active_page,
        "flash": ui.flash_for(request.query_params.get("ilmoitus")),
        "pending_reviews": pending_review_count(db) if (db is not None and user) else 0,
        "can_edit": bool(user and user.role in EDITOR_ROLES),
    }
    return templates.TemplateResponse(request, template, {**base, **context})


# --- Kirjautuminen ---------------------------------------------------------
@router.get("/web/login", response_class=HTMLResponse)
def login_page(request: Request, error: Optional[str] = None):  # noqa: ARG001
    return render(request, "login.html", None, error=error)


@router.post("/web/login")
def login_post(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = authenticate(db, username, password)
    if not user or not user.active:
        message = "Käyttäjätili on passivoitu" if user else "Virheellinen käyttäjätunnus tai salasana"
        response = render(request, "login.html", None, error=message)
        response.status_code = status.HTTP_400_BAD_REQUEST
        return response
    users_service.record_login(db, user)
    response = redirect("/")
    set_auth_cookie(response, create_user_token(user))
    return response


@router.get("/web/logout")
def logout_get():
    response = redirect(LOGIN_URL)
    response.delete_cookie(key=COOKIE_NAME)
    return response


# --- Katsaus ---------------------------------------------------------------
def attention_items(db: Session, pending: int, today, latest_air) -> list:
    """Etusivun "Vaatii huomiota" -lista: vain asiat, joille käyttäjä voi tehdä jotain."""
    items = []
    if pending:
        items.append({"tone": "pending", "text": f"{pending} videoleike{'ttä' if pending > 1 else ''} odottaa tarkastusta",
                      "href": "/web/nfc-events?nayta=odottaa", "action": "Tarkasta"})
    since = utc_now() - datetime.timedelta(days=1)
    failed = (
        db.query(NfcEvent)
        .filter(NfcEvent.status == "FAILED", NfcEvent.server_timestamp >= since)
        .count()
    )
    if failed:
        items.append({"tone": "error", "text": f"{failed} leimaus{'ta' if failed > 1 else ''} epäonnistui viimeisen vuorokauden aikana",
                      "href": "/web/nfc-events?nayta=virheet", "action": "Näytä"})
    if get_drinking_horse(db) is None:
        items.append({"tone": "error", "text": f"Hevosta {settings.DRINKING_HORSE_NAME} ei löydy, joten juomamittauksia ei voi yhdistää",
                      "href": "/web/horses", "action": "Lisää hevonen"})
    elif today.latest:
        hours = (utc_now() - today.latest.measured_at).total_seconds() / 3600
        if hours >= ui.ANTERO_NO_DRINK_ALERT_HOURS:
            items.append({"tone": "pending", "text": f"{settings.DRINKING_HORSE_NAME} ei ole juonut {int(hours)} tuntiin",
                          "href": "/web/water", "action": "Juomahistoria"})
    if latest_air:
        off = [m.label.lower() for m in ui.AIR_METRICS if m.state(getattr(latest_air, m.key)) in ("high", "low")]
        if off:
            items.append({"tone": "pending", "text": "Talli-ilma poikkeaa suosituksesta: " + ", ".join(off),
                          "href": "/web/air", "action": "Talli-ilma"})
    return items


@router.get("/", response_class=HTMLResponse)
def index_page(request: Request, db: Session = Depends(get_db), user: User = Depends(require_web_user)):
    today = water_service.today(db)
    latest_air = db.query(StableAirMeasurement).order_by(StableAirMeasurement.measured_at.desc()).first()
    pending = pending_review_count(db)
    today_key = local_date_key(utc_now())
    chart = ui.build_daily_bar_chart(water_service.daily_summary(db, 14), today_key)
    recent_events = (
        db.query(NfcEvent)
        .options(selectinload(NfcEvent.horse))
        .order_by(NfcEvent.server_timestamp.desc())
        .limit(6)
        .all()
    )
    return render(
        request, "index.html", user, "dashboard", db,
        today_label=ui.local_day_label(aware_utc_now()),
        attention=attention_items(db, pending, today, latest_air),
        today_water=today,
        water_chart=chart,
        latest_air=latest_air,
        air_metrics=ui.AIR_METRICS,
        recent_events=recent_events,
        horse_count=db.query(Horse).filter(Horse.active == True).count(),  # noqa: E712
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
    return render(request, "horses.html", user, "horses", db, horses=horses)


@router.post("/web/horses/create")
def horse_create_post(name: str = Form(...), db: Session = Depends(get_db), user: User = Depends(require_web_editor)):
    cleaned = name.strip()
    if not cleaned:
        return redirect("/web/horses", "nimi-puuttuu")
    if find_horse_by_name(db, cleaned):
        return redirect("/web/horses", "hevonen-on-jo")
    db.add(Horse(name=cleaned, active=True))
    db.commit()
    return redirect("/web/horses", "hevonen-lisatty")


@router.post("/web/horses/assign-tag")
def assign_tag_post(
    horse_id: int = Form(...),
    nfc_uid: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_web_editor),
):
    if not db.get(Horse, horse_id):
        raise HTTPException(status_code=404, detail="Hevosta ei löydy.")
    try:
        assign_nfc_tag(db, horse_id, nfc_uid)
    except ValueError:
        return redirect("/web/horses", "tagi-virheellinen")
    return redirect("/web/horses", "tagi-yhdistetty")


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
    return render(request, "horse_detail.html", user, "horses", db, horse=horse, video_clips=video_clips)


@router.post("/web/horses/{horse_id}/notes")
def add_horse_note_post(horse_id: int, content: str = Form(...), db: Session = Depends(get_db),
                        user: User = Depends(require_web_editor)):
    if content.strip() and db.get(Horse, horse_id):
        db.add(HorseNote(horse_id=horse_id, content=content.strip(), user_id=user.id))
        db.commit()
        return redirect(f"/web/horses/{horse_id}", "muistiinpano-tallennettu")
    return redirect(f"/web/horses/{horse_id}")


@router.post("/web/horses/{horse_id}/analyses")
def add_horse_analysis_post(
    horse_id: int,
    analysis_method: str = Form(...),
    summary: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_web_editor),
):
    if db.get(Horse, horse_id) and summary.strip():
        db.add(MovementAnalysis(horse_id=horse_id, analysis_method=analysis_method.strip(),
                                summary=summary.strip(), status="APPROVED", created_by=user.id))
        db.commit()
        return redirect(f"/web/horses/{horse_id}", "analyysi-tallennettu")
    return redirect(f"/web/horses/{horse_id}")


# --- NFC-tapahtumat ja videoiden tarkastus -------------------------------------
REVIEW_FILTERS = ("odottaa", "kaikki", "virheet")


def active_clip(event: NfcEvent):
    clips = [c for c in event.video_clips if c.status != ClipStatus.DELETED.value]
    return max(clips, key=lambda c: c.id) if clips else None


@router.get("/web/nfc-events", response_class=HTMLResponse)
def nfc_events_page(request: Request, nayta: Optional[str] = None, db: Session = Depends(get_db),
                    user: User = Depends(require_web_user)):
    events = (
        db.query(NfcEvent)
        .options(selectinload(NfcEvent.horse), selectinload(NfcEvent.video_clips))
        .order_by(NfcEvent.server_timestamp.desc())
        .limit(150)
        .all()
    )
    rows = [{"event": e, "clip": active_clip(e)} for e in events]
    pending_rows = [r for r in rows if r["clip"] and r["clip"].status == ClipStatus.READY.value]
    failed_rows = [r for r in rows if r["event"].status == "FAILED"]
    working = [r["event"].id for r in rows if r["event"].status in ui.WORKING_STATUSES]

    if nayta not in REVIEW_FILTERS:
        nayta = "odottaa" if pending_rows else "kaikki"
    shown = {"odottaa": pending_rows, "virheet": failed_rows, "kaikki": rows}[nayta]
    return render(
        request, "nfc_events.html", user, "events", db,
        rows=shown, nayta=nayta, counts={"odottaa": len(pending_rows), "virheet": len(failed_rows), "kaikki": len(rows)},
        working_event_ids=working,
    )


def _review_web(request: Request, db: Session, clip_id: int, new_status: ClipStatus, next_url: Optional[str]):
    try:
        clip = video_review.set_review_status(db, clip_id, new_status)
    except video_review.ClipNotFound:
        if wants_json(request):
            return JSONResponse({"detail": "Videoleikettä ei löydy."}, status_code=404)
        raise HTTPException(status_code=404, detail="Videoleikettä ei löydy.")
    if wants_json(request):
        return JSONResponse({
            "clip_id": clip.id,
            "status": clip.status,
            "label": ui.status_label(clip.status),
            "tone": ui.status_tone(clip.status),
            "pending": pending_review_count(db),
        })
    flash = "hyvaksytty" if new_status == ClipStatus.APPROVED else "hylatty"
    return redirect(safe_next(next_url), flash)


@router.post("/web/video-clips/{clip_id}/approve")
def approve_clip_web(clip_id: int, request: Request, next: Optional[str] = None, db: Session = Depends(get_db),
                     user: User = Depends(require_web_editor)):
    return _review_web(request, db, clip_id, ClipStatus.APPROVED, next)


@router.post("/web/video-clips/{clip_id}/reject")
def reject_clip_web(clip_id: int, request: Request, next: Optional[str] = None, db: Session = Depends(get_db),
                    user: User = Depends(require_web_editor)):
    return _review_web(request, db, clip_id, ClipStatus.REJECTED, next)


@router.post("/web/video-clips/{clip_id}/delete")
def delete_clip_web(clip_id: int, next: Optional[str] = None, db: Session = Depends(get_db),
                    user: User = Depends(require_web_admin)):
    try:
        video_review.delete_clip(db, clip_id)
    except video_review.ClipNotFound:
        raise HTTPException(status_code=404, detail="Videoleikettä ei löydy.")
    return redirect(safe_next(next), "poistettu")


@router.get("/web/nfc-events/status")
def nfc_events_status(ids: str = "", db: Session = Depends(get_db), user: User = Depends(require_web_user)):
    """
    Kevyt tilakysely tarkastusjonolle. Palauttaa käsittelyssä olleiden tapahtumien
    lopputilan, jotta valmistunut leike (READY) ja epäonnistunut leikkaus (FAILED)
    voidaan ilmoittaa eri tavoin.
    """
    wanted = [int(i) for i in ids.split(",") if i.isdigit()][:50]
    events = db.query(NfcEvent).filter(NfcEvent.id.in_(wanted)).all() if wanted else []
    return {
        "pending": pending_review_count(db),
        "still_working": [e.id for e in events if e.status in ui.WORKING_STATUSES],
        "finished": [{"id": e.id, "status": e.status} for e in events if e.status not in ui.WORKING_STATUSES],
    }


# --- Juominen ja talli-ilma ---------------------------------------------------
@router.get("/web/water", response_class=HTMLResponse)
def water_page(request: Request, db: Session = Depends(get_db), user: User = Depends(require_web_user)):
    today = water_service.today(db)
    measurements = (
        db.query(WaterMeasurement)
        .options(selectinload(WaterMeasurement.horse))
        .order_by(WaterMeasurement.measured_at.desc())
        .limit(50)
        .all()
    )
    today_key = local_date_key(utc_now())
    return render(
        request, "water.html", user, "water", db,
        water_external_id=settings.WATER_EXTERNAL_ID,
        antero_found=get_drinking_horse(db) is not None,
        today_water=today,
        water_chart=ui.build_daily_bar_chart(water_service.daily_summary(db, 21), today_key, width=760, height=200, span_days=21),
        measurements=measurements,
    )


@router.post("/web/water/sync")
async def sync_water_web(db: Session = Depends(get_db), user: User = Depends(require_web_editor)):
    await water_service.sync_measurements(db)
    return redirect("/web/water", "juominen-paivitetty")


@router.get("/web/air", response_class=HTMLResponse)
def air_page(request: Request, db: Session = Depends(get_db), user: User = Depends(require_web_user)):
    readings = db.query(StableAirMeasurement).order_by(StableAirMeasurement.measured_at.desc()).limit(48).all()
    latest = readings[0] if readings else None
    chronological = list(reversed(readings))
    metrics = [
        {
            "metric": m,
            "value": getattr(latest, m.key) if latest else None,
            "state": m.state(getattr(latest, m.key) if latest else None),
            "spark": ui.build_sparkline((getattr(r, m.key) for r in chronological), m),
        }
        for m in ui.AIR_METRICS
    ]
    return render(request, "air.html", user, "air", db, readings=readings[:24], latest=latest, metrics=metrics)


@router.post("/web/air/sync")
async def sync_air_web(db: Session = Depends(get_db), user: User = Depends(require_web_editor)):
    await air_quality_service.sync_air_readings(db)
    return redirect("/web/air", "ilma-paivitetty")


# --- Käyttäjät (vain ylläpitäjä) ---------------------------------------------
def _user_or_404(db: Session, user_id: int) -> User:
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="Käyttäjää ei löydy.")
    return target


@router.get("/web/users", response_class=HTMLResponse)
def users_page(request: Request, db: Session = Depends(get_db), user: User = Depends(require_web_admin)):
    return render(request, "users.html", user, "users", db, users=users_service.list_users(db),
                  role_choices=users_service.ROLE_CHOICES, role_labels=ui.ROLE_LABELS,
                  min_password=users_service.MIN_PASSWORD_LENGTH)


@router.post("/web/users/create")
def users_create(
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    display_name: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_web_admin),
):
    try:
        users_service.create_user(db, username, password, role, display_name)
    except users_service.UserError as e:
        return redirect("/web/users", e.code)
    return redirect("/web/users", "kayttaja-luotu")


@router.post("/web/users/{user_id}/password")
def users_reset_password(user_id: int, password: str = Form(...), db: Session = Depends(get_db),
                         user: User = Depends(require_web_admin)):
    try:
        users_service.set_password(db, _user_or_404(db, user_id), password)
    except users_service.UserError as e:
        return redirect("/web/users", e.code)
    return redirect("/web/users", "salasana-asetettu")


@router.post("/web/users/{user_id}/active")
def users_set_active(user_id: int, active: str = Form(...), db: Session = Depends(get_db),
                     user: User = Depends(require_web_admin)):
    make_active = active == "1"
    try:
        users_service.set_active(db, user, _user_or_404(db, user_id), make_active)
    except users_service.UserError as e:
        return redirect("/web/users", e.code)
    return redirect("/web/users", "kayttaja-aktivoitu" if make_active else "kayttaja-passivoitu")


@router.post("/web/users/{user_id}/role")
def users_set_role(user_id: int, role: str = Form(...), db: Session = Depends(get_db),
                   user: User = Depends(require_web_admin)):
    try:
        users_service.set_role(db, user, _user_or_404(db, user_id), role)
    except users_service.UserError as e:
        return redirect("/web/users", e.code)
    return redirect("/web/users", "rooli-vaihdettu")


# --- Oma tili ---------------------------------------------------------------
@router.get("/web/account", response_class=HTMLResponse)
def account_page(request: Request, db: Session = Depends(get_db), user: User = Depends(require_web_user)):
    return render(request, "account.html", user, "account", db, min_password=users_service.MIN_PASSWORD_LENGTH)


@router.post("/web/account/password")
def account_change_password(
    current_password: str = Form(...),
    new_password: str = Form(...),
    new_password_again: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_web_user),
):
    if new_password != new_password_again:
        return redirect("/web/account", "salasanat-eri")
    try:
        users_service.change_own_password(db, user, current_password, new_password)
    except users_service.UserError as e:
        return redirect("/web/account", e.code)
    # Tämä selain pysyy kirjautuneena uudella tokenilla, muut laitteet kirjautuvat ulos
    response = redirect("/web/account", "oma-salasana-vaihdettu")
    set_auth_cookie(response, create_user_token(user))
    return response


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
        request, "system.html", user, "system", db,
        settings=system_info,
        antero_found=get_drinking_horse(db) is not None,
        camera_dir_exists=Path(settings.CAMERA_SOURCE_PATH).exists(),
        system_events=db.query(SystemEvent).order_by(SystemEvent.created_at.desc()).limit(30).all(),
    )
