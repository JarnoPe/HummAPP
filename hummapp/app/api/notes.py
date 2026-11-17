from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.auth import get_current_user, require_role
from app.constants import EDITOR_ROLES
from app.database import get_db
from app.models import Horse, HorseNote, User
from app.schemas import HorseNoteCreate, HorseNoteResponse

router = APIRouter(prefix="/api/horses", tags=["Muistiinpanot"])


def serialize_note(note: HorseNote) -> HorseNoteResponse:
    return HorseNoteResponse(
        id=note.id,
        horse_id=note.horse_id,
        content=note.content,
        user_id=note.user_id,
        author_username=note.author.username if note.author else None,
        created_at=note.created_at,
    )


@router.get("/{horse_id}/notes", response_model=List[HorseNoteResponse])
def get_horse_notes(
    horse_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Hakee hevosen muistiinpanot uusimmasta vanhimpaan."""
    if not db.get(Horse, horse_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hevosta ei löydy.")
    notes = (
        db.query(HorseNote)
        .options(selectinload(HorseNote.author))
        .filter(HorseNote.horse_id == horse_id)
        .order_by(HorseNote.created_at.desc())
        .all()
    )
    return [serialize_note(n) for n in notes]


@router.post("/{horse_id}/notes", response_model=HorseNoteResponse, status_code=status.HTTP_201_CREATED)
def add_horse_note(
    horse_id: int,
    note_in: HorseNoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(EDITOR_ROLES)),
):
    """Lisää hevoskohtaisen muistiinpanon."""
    if not db.get(Horse, horse_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hevosta ei löydy.")
    note = HorseNote(horse_id=horse_id, content=note_in.content.strip(), user_id=current_user.id)
    db.add(note)
    db.commit()
    db.refresh(note)
    return serialize_note(note)
