"""
Julkinen vain luku -näkymä hummapp.fi-verkkosivustolle.

Rajattu tarkoituksella: ei omistajien nimiä (henkilötieto), ei NFC-tagien UID:itä
(tagin voisi kloonata), ei käyttäjätunnuksia eikä raakadataa. Muistiinpanot
julkaistaan vain, jos PUBLIC_INCLUDE_NOTES=true (voivat sisältää terveysmerkintöjä).
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.database import get_db
from app.models import Horse, NfcEvent, StableAirMeasurement, WaterMeasurement, utc_now
from app.api.nfc import latest_active_clip
from app.schemas import (
    PublicAirReading,
    PublicAnalysis,
    PublicHorse,
    PublicNfcEvent,
    PublicNote,
    PublicOverview,
    PublicWaterMeasurement,
    WaterDailySummary,
)
from app.services.horses import get_drinking_horse
from app.services.water import water_service

router = APIRouter(prefix="/api/public", tags=["Julkinen vain luku"])

ITEMS_PER_HORSE = 20
RECENT_ITEMS = 30
RECENT_EVENTS = 25


def _public_horse(horse: Horse) -> PublicHorse:
    notes = sorted(horse.notes, key=lambda n: n.created_at, reverse=True)[:ITEMS_PER_HORSE]
    analyses = sorted(horse.analyses, key=lambda a: a.analysis_timestamp, reverse=True)[:ITEMS_PER_HORSE]
    return PublicHorse(
        id=horse.id,
        name=horse.name,
        breed=horse.breed,
        birth_year=horse.birth_year,
        stall_box=horse.stall_box,
        description=horse.description,
        active=horse.active,
        created_at=horse.created_at,
        has_nfc_tag=any(t.active for t in horse.nfc_tags),
        notes=[
            PublicNote(id=n.id, horse_id=n.horse_id, content=n.content, created_at=n.created_at)
            for n in notes
        ] if settings.PUBLIC_INCLUDE_NOTES else [],
        analyses=[
            PublicAnalysis(
                id=a.id, horse_id=a.horse_id, analysis_method=a.analysis_method,
                analysis_timestamp=a.analysis_timestamp, summary=a.summary, status=a.status,
            )
            for a in analyses
        ],
    )


def _public_event(event: NfcEvent) -> PublicNfcEvent:
    clip = latest_active_clip(event)
    return PublicNfcEvent(
        id=event.id,
        horse_id=event.horse_id,
        horse_name=event.horse.name if event.horse else None,
        phone_timestamp=event.phone_timestamp,
        location=event.location,
        status=event.status,
        video_clip_id=clip.id if clip else None,
        video_clip_status=clip.status if clip else None,
    )


@router.get("/overview", response_model=PublicOverview)
def public_overview(db: Session = Depends(get_db)):
    horses = (
        db.query(Horse)
        .options(
            selectinload(Horse.nfc_tags),
            selectinload(Horse.notes),
            selectinload(Horse.analyses),
        )
        .filter(Horse.active == True)  # noqa: E712
        .order_by(Horse.name.asc())
        .all()
    )

    drinking_horse = get_drinking_horse(db)
    water_recent = (
        db.query(WaterMeasurement)
        .filter(WaterMeasurement.horse_id == (drinking_horse.id if drinking_horse else -1))
        .order_by(WaterMeasurement.measured_at.desc())
        .limit(RECENT_ITEMS)
        .all()
    )
    air_readings = (
        db.query(StableAirMeasurement).order_by(StableAirMeasurement.measured_at.desc()).limit(RECENT_ITEMS).all()
    )
    events = (
        db.query(NfcEvent)
        .options(selectinload(NfcEvent.horse), selectinload(NfcEvent.video_clips))
        .filter(NfcEvent.horse_id.isnot(None))
        .order_by(NfcEvent.server_timestamp.desc())
        .limit(RECENT_EVENTS)
        .all()
    )

    return PublicOverview(
        generated_at=utc_now(),
        drinking_horse_name=settings.DRINKING_HORSE_NAME,
        clip_seconds_before=settings.VIDEO_SECONDS_BEFORE,
        clip_seconds_after=settings.VIDEO_SECONDS_AFTER,
        horses=[_public_horse(h) for h in horses],
        water_daily=[WaterDailySummary(**vars(d)) for d in water_service.daily_summary(db, 14)],
        water_measurements=[
            PublicWaterMeasurement(id=w.id, measured_at=w.measured_at, liters=w.liters) for w in water_recent
        ],
        air_readings=[
            PublicAirReading(
                id=a.id, location=a.location, measured_at=a.measured_at, temperature=a.temperature,
                humidity=a.humidity, ammonia=a.ammonia, co2=a.co2, particulate_matter=a.particulate_matter,
            )
            for a in air_readings
        ],
        nfc_events=[_public_event(e) for e in events],
    )
