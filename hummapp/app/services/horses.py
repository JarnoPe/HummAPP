from typing import Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Horse, NfcTag
from app.nfc_uid import normalize_nfc_uid


def get_drinking_horse(db: Session) -> Optional[Horse]:
    """Juoma-automaattia käyttävä hevonen (pilotissa Antero, DRINKING_HORSE_NAME)."""
    return db.query(Horse).filter(Horse.name == settings.DRINKING_HORSE_NAME).first()


def find_horse_by_name(db: Session, name: str, exclude_id: Optional[int] = None) -> Optional[Horse]:
    query = db.query(Horse).filter(Horse.name == name.strip())
    if exclude_id is not None:
        query = query.filter(Horse.id != exclude_id)
    return query.first()


def assign_nfc_tag(db: Session, horse_id: int, raw_uid: str) -> NfcTag:
    """
    Yhdistää tagin hevoseen. Jos tagi oli toisella hevosella, liitos siirretään
    (virheellisen yhdistämisen korjaus). Heittää ValueErrorin virheellisestä UID:stä.
    """
    uid = normalize_nfc_uid(raw_uid)
    tag = db.query(NfcTag).filter(NfcTag.nfc_uid == uid).first()
    if tag:
        tag.horse_id = horse_id
        tag.active = True
    else:
        tag = NfcTag(horse_id=horse_id, nfc_uid=uid, active=True)
        db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


def clean_optional(value: Optional[str]) -> Optional[str]:
    """Trimmaa merkkijonon; tyhjä -> None."""
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
