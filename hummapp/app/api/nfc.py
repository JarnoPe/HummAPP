from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import NfcEvent, User, Horse
from app.schemas import NfcEventCreate, NfcEventResponse
from app.auth import get_current_user
from app.services.nfc import nfc_service
from app.services.video import video_service

router = APIRouter(prefix="/api/nfc-events", tags=["NFC-videointi"])


def serialize_nfc_event(event: NfcEvent) -> NfcEventResponse:
    horse_name = event.horse.name if event.horse else None
    active_clips = [c for c in (event.video_clips or []) if c.status != "DELETED"]
    latest_clip = sorted(active_clips, key=lambda c: c.id, reverse=True)[0] if active_clips else None
    return NfcEventResponse(
        id=event.id,
        horse_id=event.horse_id,
        horse_name=horse_name,
        nfc_uid=event.nfc_uid,
        phone_timestamp=event.phone_timestamp,
        server_timestamp=event.server_timestamp,
        user_id=event.user_id,
        location=event.location,
        status=event.status,
        error_message=event.error_message,
        video_clip_id=latest_clip.id if latest_clip else None,
        video_clip_status=latest_clip.status if latest_clip else None,
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
    
    1. Normalisoi NFC UID:n.
    2. Estää peräkkäiset kaksoislukemiset (debouncing).
    3. Hakee hevosen. Jos tagi on tuntematon, palauttaa HTTP 404 UNKNOWN_TAG -virheen.
    4. Käynnistää videoleikkauksen taustatehtävänä.
    """
    event, is_success, result_code = nfc_service.register_nfc_event(
        event_in=event_in,
        current_user=current_user,
        db=db,
    )

    if result_code == "UNKNOWN_TAG":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="UNKNOWN_TAG: Luettua NFC-tagia ei ole yhdistetty yhteenkään hevoseen.",
        )

    if result_code == "DUPLICATE_SCAN_IGNORED":
        # Palautetaan aiemmin luotu tapahtuma eikä käynnistetä uutta leikkausta
        return serialize_nfc_event(event)

    # Tunnettu hevonen ja uusi tapahtuma: käynnistetään taustaleikkaus
    background_tasks.add_task(video_service.cut_video_for_event, event.id)

    return serialize_nfc_event(event)


@router.get("", response_model=List[NfcEventResponse])
def list_nfc_events(
    limit: int = 50,
    horse_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Listaa viimeisimmät NFC-tapahtumat."""
    query = db.query(NfcEvent)
    if horse_id:
        query = query.filter(NfcEvent.horse_id == horse_id)
    events = query.order_by(NfcEvent.server_timestamp.desc()).limit(limit).all()
    return [serialize_nfc_event(e) for e in events]


@router.get("/{id}", response_model=NfcEventResponse)
def get_nfc_event(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Hakee yksittäisen NFC-tapahtuman tilan."""
    event = db.query(NfcEvent).filter(NfcEvent.id == id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tapahtumaa ei löydy.")
    return serialize_nfc_event(event)
