from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Horse, NfcTag, User
from app.schemas import HorseCreate, HorseUpdate, HorseResponse, NfcTagCreate, NfcTagResponse
from app.auth import get_current_user, require_role

router = APIRouter(prefix="/api/horses", tags=["Hevoset"])


@router.get("", response_model=List[HorseResponse])
def list_horses(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Listaa kaikki järjestelmän hevoset."""
    query = db.query(Horse)
    if not include_inactive:
        query = query.filter(Horse.active == True)
    return query.order_by(Horse.name.asc()).all()


@router.post("", response_model=HorseResponse, status_code=status.HTTP_201_CREATED)
def create_horse(
    horse_in: HorseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "user"])),
):
    """Luo uuden hevosen järjestelmään."""
    existing = db.query(Horse).filter(Horse.name == horse_in.name.strip()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Hevonen nimellä '{horse_in.name}' on jo olemassa.",
        )
    horse = Horse(
        name=horse_in.name.strip(),
        breed=horse_in.breed.strip() if horse_in.breed else None,
        birth_year=horse_in.birth_year,
        owner_name=horse_in.owner_name.strip() if horse_in.owner_name else None,
        stall_box=horse_in.stall_box.strip() if horse_in.stall_box else None,
        description=horse_in.description.strip() if horse_in.description else None,
        active=True,
    )
    db.add(horse)
    db.commit()
    db.refresh(horse)
    return horse


@router.get("/{id}", response_model=HorseResponse)
def get_horse(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Hakee yksittäisen hevosen perustiedot."""
    horse = db.query(Horse).filter(Horse.id == id).first()
    if not horse:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hevosta ei löydy.")
    return horse


@router.put("/{id}", response_model=HorseResponse)
@router.patch("/{id}", response_model=HorseResponse)
def update_horse(
    id: int,
    horse_in: HorseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "user"])),
):
    """Päivittää hevosen perustiedot."""
    horse = db.query(Horse).filter(Horse.id == id).first()
    if not horse:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hevosta ei löydy.")

    if horse_in.name is not None:
        cleaned_name = horse_in.name.strip()
        if not cleaned_name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Hevosen nimi ei voi olla tyhjä.")
        dup = db.query(Horse).filter(Horse.name == cleaned_name, Horse.id != id).first()
        if dup:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Hevonen nimellä '{cleaned_name}' on jo olemassa.")
        horse.name = cleaned_name

    if "breed" in horse_in.model_fields_set:
        horse.breed = horse_in.breed.strip() if horse_in.breed else None
    if "birth_year" in horse_in.model_fields_set:
        horse.birth_year = horse_in.birth_year
    if "owner_name" in horse_in.model_fields_set:
        horse.owner_name = horse_in.owner_name.strip() if horse_in.owner_name else None
    if "stall_box" in horse_in.model_fields_set:
        horse.stall_box = horse_in.stall_box.strip() if horse_in.stall_box else None
    if "description" in horse_in.model_fields_set:
        horse.description = horse_in.description.strip() if horse_in.description else None
    if horse_in.active is not None:
        horse.active = horse_in.active

    db.commit()
    db.refresh(horse)
    return horse


@router.post("/{id}/nfc-tag", response_model=NfcTagResponse, status_code=status.HTTP_201_CREATED)
def assign_nfc_tag(
    id: int,
    tag_in: NfcTagCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "user"])),
):
    """
    Yhdistää passiivisen NFC-tagin UID-tunnisteen hevoseen.
    Jos tagi on aiemmin ollut yhdistetty toiseen hevoseen, korjaa liitoksen turvallisesti.
    """
    horse = db.query(Horse).filter(Horse.id == id).first()
    if not horse:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hevosta ei löydy.")

    uid = tag_in.nfc_uid.strip().upper()

    # Tarkista onko tagi jo toisella hevosella
    existing_tag = db.query(NfcTag).filter(NfcTag.nfc_uid == uid).first()
    if existing_tag:
        if existing_tag.horse_id == id:
            # Jo samalla hevosella, aktivoidaan
            existing_tag.active = True
            db.commit()
            db.refresh(existing_tag)
            return existing_tag
        else:
            # Siirretään tagi tälle hevoselle (virheellisen yhdistämisen korjaaminen)
            existing_tag.horse_id = id
            existing_tag.active = True
            db.commit()
            db.refresh(existing_tag)
            return existing_tag

    new_tag = NfcTag(horse_id=id, nfc_uid=uid, active=True)
    db.add(new_tag)
    db.commit()
    db.refresh(new_tag)
    return new_tag


@router.get("/{id}/nfc-tag", response_model=List[NfcTagResponse])
def get_horse_nfc_tags(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Listaa hevoseen yhdistetyt NFC-tagit."""
    tags = db.query(NfcTag).filter(NfcTag.horse_id == id, NfcTag.active == True).all()
    return tags
