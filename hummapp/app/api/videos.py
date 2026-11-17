from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth import (
    create_video_link_token,
    get_current_user,
    get_token_from_request,
    require_role,
    user_from_token,
    verify_video_link_token,
)
from app.config import settings
from app.constants import ADMIN_ROLES, EDITOR_ROLES, ClipStatus
from app.database import get_db
from app.models import User
from app.schemas import VideoClipResponse, VideoLinkResponse
from app.services import video_review
from app.services.video import validate_and_resolve_video_path

router = APIRouter(prefix="/api/video-clips", tags=["Videoleikkeet"])


def _clip_or_404(db: Session, clip_id: int):
    try:
        return video_review.get_active_clip(db, clip_id)
    except video_review.ClipNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Videoleikettä ei löydy.")


@router.get("/{clip_id}", response_model=VideoClipResponse)
def get_video_clip(clip_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Hakee videoleikkeen metatiedot ja tilan."""
    return _clip_or_404(db, clip_id)


@router.post("/{clip_id}/download-link", response_model=VideoLinkResponse)
def create_download_link(clip_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Luo lyhytikäisen (VIDEO_LINK_EXPIRE_MINUTES) latauslinkin ulkoista videosoitinta varten.
    Linkin token kelpaa vain tämän leikkeen lataamiseen, ei kirjautumiseen.
    """
    _clip_or_404(db, clip_id)
    token = create_video_link_token(clip_id)
    return VideoLinkResponse(
        url=f"/api/video-clips/{clip_id}/download?sig={token}",
        expires_in_seconds=settings.VIDEO_LINK_EXPIRE_MINUTES * 60,
    )


@router.get("/{clip_id}/download")
def download_video_clip(
    clip_id: int,
    request: Request,
    sig: Optional[str] = None,
    token: Optional[str] = Depends(get_token_from_request),
    db: Session = Depends(get_db),
):
    """
    Lataa tai suoratoistaa videoleikkeen (Range-tuki FileResponsessa).
    Tunnistautuminen: Bearer-token, web-UI:n eväste tai /download-link -allekirjoitus.
    """
    if not (user_from_token(token, db) or (sig and verify_video_link_token(sig, clip_id))):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Kirjautumistieto puuttuu tai se on vanhentunut")

    clip = _clip_or_404(db, clip_id)
    try:
        file_path = validate_and_resolve_video_path(clip.relative_file_path)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Videotiedostoa ei löydy levyltä.")
    return FileResponse(path=str(file_path), media_type="video/mp4", filename=file_path.name)


def _review(db: Session, clip_id: int, new_status: ClipStatus):
    try:
        return video_review.set_review_status(db, clip_id, new_status)
    except video_review.ClipNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Videoleikettä ei löydy.")


@router.post("/{clip_id}/approve", response_model=VideoClipResponse)
def approve_video_clip(clip_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_role(EDITOR_ROLES))):
    """Hyväksyy videointikerran onnistuneeksi (APPROVED)."""
    return _review(db, clip_id, ClipStatus.APPROVED)


@router.post("/{clip_id}/reject", response_model=VideoClipResponse)
def reject_video_clip(clip_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_role(EDITOR_ROLES))):
    """
    Hylkää videointikerran (REJECTED). Tiedosto säilyy VIDEO_REJECTED_RETENTION_DAYS päivää,
    minkä jälkeen ajastettu siivous poistaa sen.
    """
    return _review(db, clip_id, ClipStatus.REJECTED)


@router.delete("/{clip_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_video_clip(clip_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_role(ADMIN_ROLES))):
    """Ylläpitäjän poisto: tiedosto poistetaan levyltä vain sallitusta videohakemistosta."""
    try:
        video_review.delete_clip(db, clip_id)
    except video_review.ClipNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Videoleikettä ei löydy.")
    return None
