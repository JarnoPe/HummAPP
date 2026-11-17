"""Videoleikkeiden tarkastus ja poisto – yhteinen logiikka API:lle ja web-UI:lle."""
import datetime
import logging

from sqlalchemy.orm import Session

from app.config import settings
from app.constants import ClipStatus
from app.models import VideoClip, utc_now
from app.services.system_events import record_system_event
from app.services.video import validate_and_resolve_video_path

logger = logging.getLogger(__name__)


class ClipNotFound(Exception):
    pass


def get_active_clip(db: Session, clip_id: int) -> VideoClip:
    clip = db.get(VideoClip, clip_id)
    if not clip or clip.status == ClipStatus.DELETED.value:
        raise ClipNotFound(clip_id)
    return clip


def set_review_status(db: Session, clip_id: int, new_status: ClipStatus) -> VideoClip:
    """Hyväksyy (APPROVED) tai hylkää (REJECTED) leikkeen ja päivittää NFC-tapahtuman tilan."""
    if new_status not in (ClipStatus.APPROVED, ClipStatus.REJECTED):
        raise ValueError(f"Tarkastustila ei voi olla {new_status}")
    clip = get_active_clip(db, clip_id)
    now = utc_now()
    clip.status = new_status.value
    clip.approved_at = now if new_status == ClipStatus.APPROVED else None
    clip.rejected_at = now if new_status == ClipStatus.REJECTED else None
    if clip.nfc_event:
        clip.nfc_event.status = new_status.value
    db.commit()
    db.refresh(clip)
    return clip


def delete_clip(db: Session, clip_id: int) -> VideoClip:
    """Poistaa tiedoston levyltä ja merkitsee leikkeen DELETED-tilaan."""
    clip = db.get(VideoClip, clip_id)
    if not clip:
        raise ClipNotFound(clip_id)
    _remove_file(db, clip)
    clip.status = ClipStatus.DELETED.value
    clip.deleted_at = utc_now()
    db.commit()
    return clip


def purge_rejected_clips(db: Session) -> int:
    """Poistaa hylätyt leikkeet, joiden turva-aika (VIDEO_REJECTED_RETENTION_DAYS) on umpeutunut."""
    if settings.VIDEO_REJECTED_RETENTION_DAYS <= 0:
        return 0
    cutoff = utc_now() - datetime.timedelta(days=settings.VIDEO_REJECTED_RETENTION_DAYS)
    expired = (
        db.query(VideoClip)
        .filter(VideoClip.status == ClipStatus.REJECTED.value, VideoClip.rejected_at < cutoff)
        .all()
    )
    for clip in expired:
        _remove_file(db, clip)
        clip.status = ClipStatus.DELETED.value
        clip.deleted_at = utc_now()
    db.commit()
    if expired:
        logger.info("Poistettiin %s vanhentunutta hylättyä videoleikettä.", len(expired))
    return len(expired)


def _remove_file(db: Session, clip: VideoClip) -> None:
    try:
        path = validate_and_resolve_video_path(clip.relative_file_path)
        path.unlink(missing_ok=True)
    except (ValueError, OSError) as e:
        logger.warning("Videotiedoston poisto epäonnistui (leike #%s): %s", clip.id, e)
        record_system_event(
            db, "WARNING", "VIDEO", f"Videotiedoston poisto epäonnistui (leike #{clip.id})",
            {"path": clip.relative_file_path, "error": str(e)}, commit=False,
        )
