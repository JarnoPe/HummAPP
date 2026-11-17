from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, selectinload

from app.auth import get_current_user
from app.constants import ClipStatus, NfcResult
from app.database import get_db
from app.models import NfcEvent, User
from app.schemas import NfcEventCreate, NfcEventResponse
from app.services.nfc import nfc_service
from app.services.video import video_service

router = APIRouter(prefix="/api/nfc-events", tags=["NFC-videointi"])


def latest_active_clip(event: NfcEvent):
    active = [c for c in (event.video_clips or []) if c.status != ClipStatus.DELETED.value]
    return max(active, key=lambda c: c.id) if active else None


def serialize_nfc_event(event: NfcEvent) -> NfcEventResponse:
    clip = latest_active_clip(event)
    return NfcEventResponse(
        id=event.id,
        horse_id=event.horse_id,
        horse_name=event.horse.name if event.horse else None,
        nfc_uid=event.nfc_uid,
        phone_timestamp=event.phone_timestamp,
        server_timestamp=event.server_timestamp,
        user_id=event.user_id,
        location=event.location,
        status=event.status,
        error_message=event.error_message,
        clock_skew_seconds=event.clock_skew_seconds,
        video_clip_id=clip.id if clip else None,
        video_clip_status=clip.status if clip else None,
    )


@router.post("", response_model=NfcEventResponse, status_code=status.HTTP_201_CREATED)
def register_nfc_event(
    event_in: NfcEventCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Vastaanottaa Android-sovelluksen NFC-lukutapahtuman.
    Tuntematon tagi -> HTTP 404 UNKNOWN_TAG. Kaksoisluku -> palautetaan aiempi tapahtuma.
    Tunnettu tagi -> videoleikkaus (5 s ennen + 13 s jälkeen) käynnistyy taustalla.
    """
    registration = nfc_service.register_nfc_event(event_in=event_in, current_user=current_user, db=db)

    if registration.result == NfcResult.UNKNOWN_TAG:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="UNKNOWN_TAG: Luettua NFC-tagia ei ole yhdistetty yhteenkään hevoseen.",
        )
    if registration.result == NfcResult.OK:
        background_tasks.add_task(video_service.cut_video_for_event, registration.event.id)

    return serialize_nfc_event(registration.event)


@router.get("", response_model=List[NfcEventResponse])
def list_nfc_events(
    limit: int = Query(50, ge=1, le=500),
    horse_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Listaa viimeisimmät NFC-tapahtumat."""
    query = db.query(NfcEvent).options(selectinload(NfcEvent.horse), selectinload(NfcEvent.video_clips))
    if horse_id:
        query = query.filter(NfcEvent.horse_id == horse_id)
    events = query.order_by(NfcEvent.server_timestamp.desc()).limit(limit).all()
    return [serialize_nfc_event(e) for e in events]


@router.get("/{event_id}", response_model=NfcEventResponse)
def get_nfc_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Hakee yksittäisen NFC-tapahtuman tilan."""
    event = db.get(NfcEvent, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tapahtumaa ei löydy.")
    return serialize_nfc_event(event)
