from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_role
from app.constants import EDITOR_ROLES
from app.database import get_db
from app.models import Horse, NfcTag, User
from app.schemas import HorseCreate, HorseResponse, HorseUpdate, NfcTagCreate, NfcTagResponse
from app.services.horses import assign_nfc_tag as assign_tag_service
from app.services.horses import clean_optional, find_horse_by_name

router = APIRouter(prefix="/api/horses", tags=["Hevoset"])

OPTIONAL_TEXT_FIELDS = ("breed", "owner_name", "stall_box", "description")


def _get_horse_or_404(db: Session, horse_id: int) -> Horse:
    horse = db.get(Horse, horse_id)
    if not horse:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hevosta ei löydy.")
    return horse


@router.get("", response_model=List[HorseResponse])
def list_horses(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Listaa järjestelmän hevoset."""
    query = db.query(Horse)
    if not include_inactive:
        query = query.filter(Horse.active == True)  # noqa: E712
    return query.order_by(Horse.name.asc()).all()


@router.post("", response_model=HorseResponse, status_code=status.HTTP_201_CREATED)
def create_horse(
    horse_in: HorseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(EDITOR_ROLES)),
):
    """Luo uuden hevosen järjestelmään."""
    name = horse_in.name.strip()
    if find_horse_by_name(db, name):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Hevonen nimellä '{name}' on jo olemassa.")
    horse = Horse(
        name=name,
        birth_year=horse_in.birth_year,
        active=True,
        **{field: clean_optional(getattr(horse_in, field)) for field in OPTIONAL_TEXT_FIELDS},
    )
    db.add(horse)
    db.commit()
    db.refresh(horse)
    return horse


@router.get("/{horse_id}", response_model=HorseResponse)
def get_horse(
    horse_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Hakee yksittäisen hevosen perustiedot."""
    return _get_horse_or_404(db, horse_id)


@router.put("/{horse_id}", response_model=HorseResponse)
@router.patch("/{horse_id}", response_model=HorseResponse)
def update_horse(
    horse_id: int,
    horse_in: HorseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(EDITOR_ROLES)),
):
    """Päivittää hevosen perustiedot. Vain pyynnössä annetut kentät muuttuvat."""
    horse = _get_horse_or_404(db, horse_id)

    if horse_in.name is not None:
        name = horse_in.name.strip()
        if not name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Hevosen nimi ei voi olla tyhjä.")
        if find_horse_by_name(db, name, exclude_id=horse_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Hevonen nimellä '{name}' on jo olemassa.")
        horse.name = name

    for field in OPTIONAL_TEXT_FIELDS:
        if field in horse_in.model_fields_set:
            setattr(horse, field, clean_optional(getattr(horse_in, field)))
    if "birth_year" in horse_in.model_fields_set:
        horse.birth_year = horse_in.birth_year
    if horse_in.active is not None:
        horse.active = horse_in.active

    db.commit()
    db.refresh(horse)
    return horse


@router.post("/{horse_id}/nfc-tag", response_model=NfcTagResponse, status_code=status.HTTP_201_CREATED)
def assign_nfc_tag(
    horse_id: int,
    tag_in: NfcTagCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(EDITOR_ROLES)),
):
    """Yhdistää NFC-tagin hevoseen. Toisella hevosella ollut tagi siirretään tälle (korjaus)."""
    _get_horse_or_404(db, horse_id)
    return assign_tag_service(db, horse_id, tag_in.nfc_uid)


@router.get("/{horse_id}/nfc-tag", response_model=List[NfcTagResponse])
def get_horse_nfc_tags(
    horse_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Listaa hevoseen yhdistetyt aktiiviset NFC-tagit."""
    return db.query(NfcTag).filter(NfcTag.horse_id == horse_id, NfcTag.active == True).all()  # noqa: E712
