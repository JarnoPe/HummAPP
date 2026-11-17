"""Käynnistyksen alustus: migraatiot, pääkäyttäjä, juomahevonen ja (valinnainen) demodata."""
import logging

from sqlalchemy.orm import Session

from app.auth import seed_admin_user
from app.config import settings
from app.database import SessionLocal, engine
from app.migrations import run_migrations
from app.models import Horse, NfcTag
from app.services.air_quality import air_quality_service
from app.services.horses import get_drinking_horse
from app.services.water import water_service

logger = logging.getLogger(__name__)

# Esimerkkitagit vain SEED_DEMO_DATA=true -tilassa (Android-sovelluksen pikatestipainikkeet)
DEMO_HORSES = {settings.DRINKING_HORSE_NAME: "04A31B92C56F80", "Valo": "04E24589F10123"}


def ensure_drinking_horse(db: Session) -> None:
    if get_drinking_horse(db):
        return
    logger.info("Luodaan juoma-automaattia käyttävä hevonen '%s'.", settings.DRINKING_HORSE_NAME)
    db.add(Horse(name=settings.DRINKING_HORSE_NAME, active=True))
    db.commit()


def seed_demo_data(db: Session) -> None:
    for name, uid in DEMO_HORSES.items():
        horse = db.query(Horse).filter(Horse.name == name).first()
        if not horse:
            horse = Horse(name=name, active=True)
            db.add(horse)
            db.flush()
        if not db.query(NfcTag).filter(NfcTag.nfc_uid == uid).first():
            db.add(NfcTag(horse_id=horse.id, nfc_uid=uid, active=True))
    db.commit()
    logger.info("Demodata (SEED_DEMO_DATA=true) varmistettu.")


async def initialize_application() -> None:
    run_migrations(engine)
    logger.info("Tietokantataulut ja migraatiot varmistettu.")

    db = SessionLocal()
    try:
        seed_admin_user(db)
        ensure_drinking_horse(db)
        if settings.SEED_DEMO_DATA:
            seed_demo_data(db)
        if settings.WATER_USE_MOCK:
            await water_service.sync_measurements(db)
        if settings.AIR_USE_MOCK:
            await air_quality_service.sync_air_readings(db)
    except Exception:
        logger.exception("Virhe käynnistysalustuksessa")
    finally:
        db.close()
