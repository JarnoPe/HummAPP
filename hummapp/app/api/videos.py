import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import VideoClip, User, utc_now
from app.schemas import VideoClipResponse
from app.auth import get_current_user, require_role
from app.services.video import validate_and_resolve_video_path

router = APIRouter(prefix="/api/video-clips", tags=["Videoleikkeet"])


@router.get("/{id}", response_model=VideoClipResponse)
def get_video_clip(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Hakee videoleikkeen metatiedot ja tilan."""
    clip = db.query(VideoClip).filter(VideoClip.id == id).first()
    if not clip or clip.status == "DELETED":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Videoleikettä ei löydy.")
    return clip


@router.get("/{id}/download")
def download_video_clip(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lataa tai suoratoistaa videoleikkeen.
    Suojattu Path Traversal -hyökkäyksiä vastaan.
    """
    clip = db.query(VideoClip).filter(VideoClip.id == id).first()
    if not clip or clip.status == "DELETED":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Videoleikettä ei löydy.")

    try:
        file_path = validate_and_resolve_video_path(clip.relative_file_path)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Videotiedostoa ei löydy levyltä.")

    return FileResponse(
        path=str(file_path),
        media_type="video/mp4",
        filename=file_path.name,
    )


@router.post("/{id}/approve", response_model=VideoClipResponse)
def approve_video_clip(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "user"])),
):
    """
    Käyttäjä hyväksyy videointikerran onnistuneeksi (APPROVED).
    """
    clip = db.query(VideoClip).filter(VideoClip.id == id).first()
    if not clip or clip.status == "DELETED":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Videoleikettä ei löydy.")

    clip.status = "APPROVED"
    clip.approved_at = utc_now()
    clip.rejected_at = None

    if clip.nfc_event:
        clip.nfc_event.status = "APPROVED"

    db.commit()
    db.refresh(clip)
    return clip


@router.post("/{id}/reject", response_model=VideoClipResponse)
def reject_video_clip(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "user"])),
):
    """
    Käyttäjä hylkää videointikerran (REJECTED).
    Videon tiedostoa ei poisteta heti, vaan se siirretään pois aktiiviseurannasta
    ja säilytetään turva-ajan mukaisesti.
    """
    clip = db.query(VideoClip).filter(VideoClip.id == id).first()
    if not clip or clip.status == "DELETED":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Videoleikettä ei löydy.")

    clip.status = "REJECTED"
    clip.rejected_at = utc_now()

    if clip.nfc_event:
        clip.nfc_event.status = "REJECTED"

    db.commit()
    db.refresh(clip)
    return clip


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_video_clip(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"])),
):
    """
    Ylläpitäjän hallittu poistotoiminto.
    Poistaa tiedoston levyltä turvallisesti vain sallitusta videohakemistosta.
    """
    clip = db.query(VideoClip).filter(VideoClip.id == id).first()
    if not clip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Videoleikettä ei löydy.")

    try:
        file_path = validate_and_resolve_video_path(clip.relative_file_path)
        if file_path.exists():
            file_path.unlink()
    except Exception as e:
        # Lokita poistovirhe mutta merkitse kantaan
        pass

    clip.status = "DELETED"
    clip.deleted_at = utc_now()
    db.commit()
    return None
