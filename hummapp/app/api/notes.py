from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import HorseNote, Horse, User
from app.schemas import HorseNoteCreate, HorseNoteResponse
from app.auth import get_current_user, require_role

router = APIRouter(prefix="/api/horses", tags=["Muistiinpanot"])


@router.get("/{id}/notes", response_model=List[HorseNoteResponse])
def get_horse_notes(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Hakee hevosen aikaisemmat muistiinpanot aikajärjestyksessä."""
    horse = db.query(Horse).filter(Horse.id == id).first()
    if not horse:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hevosta ei löydy.")

    notes = (
        db.query(HorseNote)
        .filter(HorseNote.horse_id == id)
        .order_by(HorseNote.created_at.desc())
        .all()
    )

    results = []
    for n in notes:
        results.append(
            HorseNoteResponse(
                id=n.id,
                horse_id=n.horse_id,
                content=n.content,
                user_id=n.user_id,
                author_username=n.author.username if n.author else None,
                created_at=n.created_at,
            )
        )
    return results


@router.post("/{id}/notes", response_model=HorseNoteResponse, status_code=status.HTTP_201_CREATED)
def add_horse_note(
    id: int,
    note_in: HorseNoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "user"])),
):
    """Lisää hevoskohtaisen muistiinpanon."""
    horse = db.query(Horse).filter(Horse.id == id).first()
    if not horse:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hevosta ei löydy.")

    note = HorseNote(
        horse_id=id,
        content=note_in.content.strip(),
        user_id=current_user.id,
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    return HorseNoteResponse(
        id=note.id,
        horse_id=note.horse_id,
        content=note.content,
        user_id=note.user_id,
        author_username=current_user.username,
        created_at=note.created_at,
    )
