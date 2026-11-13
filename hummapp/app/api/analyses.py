from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import MovementAnalysis, Horse, VideoClip, User
from app.schemas import MovementAnalysisCreate, MovementAnalysisResponse
from app.auth import get_current_user, require_role

router = APIRouter(tags=["Liikeanalyysi"])


@router.get("/api/horses/{id}/analyses", response_model=List[MovementAnalysisResponse])
def get_horse_analyses(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Hakee hevosen liikeanalyysitulokset."""
    horse = db.query(Horse).filter(Horse.id == id).first()
    if not horse:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hevosta ei löydy.")

    analyses = (
        db.query(MovementAnalysis)
        .filter(MovementAnalysis.horse_id == id)
        .order_by(MovementAnalysis.analysis_timestamp.desc())
        .all()
    )
    return analyses


@router.post("/api/analyses", response_model=MovementAnalysisResponse, status_code=status.HTTP_201_CREATED)
def create_movement_analysis(
    analysis_in: MovementAnalysisCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "user"])),
):
    """
    Lisää manuaalisesti tai ulkoisesta palvelusta saadun liikeanalyysin tuloksen.
    Valmisteltu joustavalla JSON-rakenteella tulevia automaattisia API-integraatioita varten.
    """
    horse = db.query(Horse).filter(Horse.id == analysis_in.horse_id).first()
    if not horse:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hevosta ei löydy.")

    if analysis_in.video_clip_id:
        clip = db.query(VideoClip).filter(VideoClip.id == analysis_in.video_clip_id).first()
        if not clip:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Viitattua videoleikettä ei löydy.")

    analysis = MovementAnalysis(
        horse_id=analysis_in.horse_id,
        video_clip_id=analysis_in.video_clip_id,
        analysis_method=analysis_in.analysis_method,
        summary=analysis_in.summary,
        result_json=analysis_in.result_json,
        status=analysis_in.status,
        created_by=current_user.id,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis
