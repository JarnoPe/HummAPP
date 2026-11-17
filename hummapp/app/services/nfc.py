import datetime
import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.config import settings
from app.constants import EventStatus, NfcResult
from app.models import NfcEvent, NfcTag, User, utc_now
from app.schemas import NfcEventCreate
from app.timeutils import to_naive_utc

logger = logging.getLogger(__name__)

DEBOUNCE_SECONDS = 10


@dataclass
class NfcRegistration:
    event: NfcEvent
    result: NfcResult


class NfcService:
    @staticmethod
    def register_nfc_event(event_in: NfcEventCreate, current_user: User, db: Session) -> NfcRegistration:
        """
        Rekisteröi Android-sovelluksen lukeman NFC-tapahtuman.

        1. UID on jo normalisoitu skeemassa (normalize_nfc_uid).
        2. Saman tagin kaksoisluku 10 sekunnin ikkunassa ohitetaan (debounce).
        3. Tuntematon tagi: hevosta ei luoda, tapahtuma kirjataan FAILED-tilaan -> UNKNOWN_TAG.
        4. Tunnettu tagi: tapahtuma liitetään hevoseen ja on valmis videoleikkaukselle.
        Puhelimen ja palvelimen kelloero tallennetaan, koska 10 s leike edellyttää tarkkaa aikaa.
        """
        uid = event_in.nfc_uid
        phone_time = to_naive_utc(event_in.phone_timestamp)
        now = utc_now()

        recent_duplicate = (
            db.query(NfcEvent)
            .filter(
                NfcEvent.nfc_uid == uid,
                NfcEvent.server_timestamp >= now - datetime.timedelta(seconds=DEBOUNCE_SECONDS),
            )
            .first()
        )
        if recent_duplicate:
            logger.warning("Estetty kaksoisluku tagille %s (tapahtuma #%s).", uid, recent_duplicate.id)
            return NfcRegistration(recent_duplicate, NfcResult.DUPLICATE_SCAN_IGNORED)

        skew = round((phone_time - now).total_seconds(), 1)
        if abs(skew) > settings.NFC_CLOCK_SKEW_WARNING_SECONDS:
            logger.warning(
                "Puhelimen kello poikkeaa palvelimesta %.1f s (tagi %s). Tarkista puhelimen automaattinen aika "
                "– leike voi osua väärään kohtaan.", skew, uid,
            )

        tag = db.query(NfcTag).filter(NfcTag.nfc_uid == uid, NfcTag.active == True).first()  # noqa: E712
        event = NfcEvent(
            horse_id=tag.horse_id if tag else None,
            nfc_uid=uid,
            phone_timestamp=phone_time,
            server_timestamp=now,
            user_id=current_user.id if current_user else None,
            location=event_in.location,
            status=EventStatus.RECEIVED.value if tag else EventStatus.FAILED.value,
            error_message=None if tag else "UNKNOWN_TAG: Tagia ei ole yhdistetty yhteenkään hevoseen",
            clock_skew_seconds=skew,
        )
        db.add(event)
        db.commit()
        db.refresh(event)

        if not tag:
            logger.warning("Tuntematon NFC-tagi luettu: %s (tapahtuma #%s).", uid, event.id)
            return NfcRegistration(event, NfcResult.UNKNOWN_TAG)

        logger.info("NFC-tapahtuma #%s rekisteröity hevoselle #%s.", event.id, tag.horse_id)
        return NfcRegistration(event, NfcResult.OK)


nfc_service = NfcService()
