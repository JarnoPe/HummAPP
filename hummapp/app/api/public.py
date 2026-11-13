from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from collections import defaultdict
from app.config import settings
from app.database import get_db
from app.models import (
    Horse,
    NfcTag,
    NfcEvent,
    VideoClip,
    HorseNote,
    MovementAnalysis,
    WaterMeasurement,
    StableAirMeasurement,
    utc_now,
)

router = APIRouter(prefix="/api/public", tags=["Julkinen vain luku"])


@router.get("/overview")
def public_overview(db: Session = Depends(get_db)):
    """Julkinen vain luku -näkymä hummapp.fi-verkkosivustolle (ei sisällä muokkausoikeuksia)."""
    horses_db = db.query(Horse).filter(Horse.active == True).order_by(Horse.name.asc()).all()
    horses_out = []
    for h in horses_db:
        tags = db.query(NfcTag).filter(NfcTag.horse_id == h.id, NfcTag.active == True).all()
        notes = (
            db.query(HorseNote)
            .filter(HorseNote.horse_id == h.id)
            .order_by(HorseNote.created_at.desc())
            .limit(20)
            .all()
        )
        analyses = (
            db.query(MovementAnalysis)
            .filter(MovementAnalysis.horse_id == h.id)
            .order_by(MovementAnalysis.analysis_timestamp.desc())
            .limit(20)
            .all()
        )
        horses_out.append(
            {
                "id": h.id,
                "name": h.name,
                "breed": h.breed,
                "birth_year": h.birth_year,
                "owner_name": h.owner_name,
                "stall_box": h.stall_box,
                "description": h.description,
                "active": h.active,
                "created_at": h.created_at.isoformat() if h.created_at else None,
                "nfc_tags": [{"id": t.id, "nfc_uid": t.nfc_uid} for t in tags],
                "notes": [
                    {
                        "id": n.id,
                        "horse_id": n.horse_id,
                        "content": n.content,
                        "author_username": n.author.username if n.author else "Tallitiimi",
                        "created_at": n.created_at.isoformat() if n.created_at else None,
                    }
                    for n in notes
                ],
                "analyses": [
                    {
                        "id": a.id,
                        "horse_id": a.horse_id,
                        "analysis_method": a.analysis_method,
                        "analysis_timestamp": a.analysis_timestamp.isoformat() if a.analysis_timestamp else None,
                        "summary": a.summary,
                        "status": a.status,
                    }
                    for a in analyses
                ],
            }
        )

    antero = db.query(Horse).filter(Horse.name == settings.DRINKING_HORSE_NAME).first()
    water_daily = []
    if antero:
        w_rows = (
            db.query(WaterMeasurement)
            .filter(WaterMeasurement.horse_id == antero.id)
            .order_by(WaterMeasurement.measured_at.asc())
            .all()
        )
        grouped = defaultdict(lambda: {"total": 0.0, "count": 0})
        for r in w_rows:
            day_key = r.measured_at.strftime("%Y-%m-%d")
            grouped[day_key]["total"] += r.liters
            grouped[day_key]["count"] += 1
        for k in sorted(grouped.keys())[-14:]:
            water_daily.append(
                {
                    "date": k,
                    "total_liters": round(grouped[k]["total"], 1),
                    "measurement_count": grouped[k]["count"],
                }
            )

    water_recent = (
        db.query(WaterMeasurement).order_by(WaterMeasurement.measured_at.desc()).limit(30).all()
    )
    air_readings = (
        db.query(StableAirMeasurement).order_by(StableAirMeasurement.measured_at.desc()).limit(30).all()
    )
    events = db.query(NfcEvent).order_by(NfcEvent.server_timestamp.desc()).limit(25).all()

    events_out = []
    for ev in events:
        clip = (
            db.query(VideoClip)
            .filter(VideoClip.nfc_event_id == ev.id, VideoClip.status != "DELETED")
            .order_by(VideoClip.id.desc())
            .first()
        )
        events_out.append(
            {
                "id": ev.id,
                "horse_id": ev.horse_id,
                "horse_name": ev.horse.name if ev.horse else None,
                "nfc_uid": ev.nfc_uid,
                "phone_timestamp": ev.phone_timestamp.isoformat() if ev.phone_timestamp else None,
                "location": ev.location,
                "status": ev.status,
                "video_clip_id": clip.id if clip else None,
                "video_clip_status": clip.status if clip else None,
            }
        )

    return {
        "read_only": True,
        "generated_at": utc_now().isoformat(),
        "water_external_id": settings.WATER_EXTERNAL_ID,
        "drinking_horse_name": settings.DRINKING_HORSE_NAME,
        "horses": horses_out,
        "water_daily": water_daily,
        "water_measurements": [
            {
                "id": w.id,
                "horse_id": w.horse_id,
                "horse_name": w.horse.name if w.horse else settings.DRINKING_HORSE_NAME,
                "external_measurement_id": w.external_measurement_id,
                "external_water_id": w.external_water_id,
                "measured_at": w.measured_at.isoformat() if w.measured_at else None,
                "liters": w.liters,
                "raw_data_json": w.raw_data_json,
            }
            for w in water_recent
        ],
        "air_readings": [
            {
                "id": a.id,
                "sensor_id": a.sensor_id,
                "location": a.location,
                "measured_at": a.measured_at.isoformat() if a.measured_at else None,
                "temperature": a.temperature,
                "humidity": a.humidity,
                "ammonia": a.ammonia,
                "co2": a.co2,
                "particulate_matter": a.particulate_matter,
            }
            for a in air_readings
        ],
        "nfc_events": events_out,
    }
