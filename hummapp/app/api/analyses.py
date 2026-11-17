from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_role
from app.constants import EDITOR_ROLES
from app.database import get_db
from app.models import Horse, MovementAnalysis, User, VideoClip
from app.schemas import MovementAnalysisCreate, MovementAnalysisResponse

router = APIRouter(tags=["Liikeanalyysi"])


@router.get("/api/horses/{horse_id}/analyses", response_model=List[MovementAnalysisResponse])
def get_horse_analyses(
    horse_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Hakee hevosen liikeanalyysitulokset."""
    if not db.get(Horse, horse_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hevosta ei löydy.")
    return (
        db.query(MovementAnalysis)
        .filter(MovementAnalysis.horse_id == horse_id)
        .order_by(MovementAnalysis.analysis_timestamp.desc())
        .all()
    )


@router.post("/api/analyses", response_model=MovementAnalysisResponse, status_code=status.HTTP_201_CREATED)
def create_movement_analysis(
    analysis_in: MovementAnalysisCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(EDITOR_ROLES)),
):
    """
    Lisää manuaalisesti tai ulkoisesta palvelusta saadun liikeanalyysin tuloksen.
    Joustava JSON-rakenne tulevia automaattisia API-integraatioita varten.
    """
    if not db.get(Horse, analysis_in.horse_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hevosta ei löydy.")
    if analysis_in.video_clip_id and not db.get(VideoClip, analysis_in.video_clip_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Viitattua videoleikettä ei löydy.")

    analysis = MovementAnalysis(**analysis_in.model_dump(), created_by=current_user.id)
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis
