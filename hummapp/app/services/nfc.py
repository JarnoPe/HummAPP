import datetime
import logging
from typing import Tuple, Optional
from sqlalchemy.orm import Session
from app.models import NfcTag, NfcEvent, Horse, User, utc_now
from app.schemas import NfcEventCreate

logger = logging.getLogger(__name__)

DEBOUNCE_SECONDS = 10


class NfcService:
    @staticmethod
    def register_nfc_event(
        event_in: NfcEventCreate,
        current_user: User,
        db: Session,
    ) -> Tuple[NfcEvent, bool, str]:
        """
        Rekisteröi Android-sovelluksen lukeman NFC-tapahtuman.
        
        Palauttaa: (NfcEvent, is_success, status_code_or_message)
        
        Toimintasäännöt:
        1. Normalisoi NFC UID (heksamerkit isolla, ei välimerkkejä).
        2. Estä saman tagin kaksoisluku 10 sekunnin ikkunassa (debouncing).
        3. Etsi tagi nfc_tags -taulusta.
        4. Jos tagia EI tunneta: älä luo hevosta, kirjaa tapahtuma ja palauta UNKNOWN_TAG.
        5. Jos tagi tunnetaan: yhdistä hevoseen ja merkitse valmiiksi videoleikkaukselle.
        """
        uid = event_in.nfc_uid.strip().upper()
        phone_time = event_in.phone_timestamp
        if phone_time.tzinfo is not None:
            # Muunna SQLite-sopivaksi UTC ilman tzinfo
            phone_time = phone_time.astimezone(datetime.timezone.utc).replace(tzinfo=None)

        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

        # 1. Kaksoislukemisen esto (Debounce)
        recent_threshold = now - datetime.timedelta(seconds=DEBOUNCE_SECONDS)
        recent_duplicate = (
            db.query(NfcEvent)
            .filter(
                NfcEvent.nfc_uid == uid,
                NfcEvent.server_timestamp >= recent_threshold,
            )
            .first()
        )
        if recent_duplicate:
            logger.warning(f"Estetty kaksoisluku tagille {uid} (tapahtuma #{recent_duplicate.id} äskettäin luotu).")
            return recent_duplicate, False, "DUPLICATE_SCAN_IGNORED"

        # 2. Hevosen etsiminen tagin perusteella
        tag_record = (
            db.query(NfcTag)
            .filter(NfcTag.nfc_uid == uid, NfcTag.active == True)
            .first()
        )

        if not tag_record:
            # Tuntematon tagi: tallenna tapahtuma tunnistamattomana
            event = NfcEvent(
                horse_id=None,
                nfc_uid=uid,
                phone_timestamp=phone_time,
                server_timestamp=now,
                user_id=current_user.id if current_user else None,
                location=event_in.location,
                status="FAILED",
                error_message="UNKNOWN_TAG: Tagia ei ole yhdistetty yhteenkään hevoseen",
            )
            db.add(event)
            db.commit()
            db.refresh(event)
            logger.warning(f"Tuntematon NFC-tagi luettu: {uid}. Tapahtuma #{event.id} merkitty epäonnistuneeksi.")
            return event, False, "UNKNOWN_TAG"

        # 3. Tunnettu tagi: luodaan tapahtuma
        event = NfcEvent(
            horse_id=tag_record.horse_id,
            nfc_uid=uid,
            phone_timestamp=phone_time,
            server_timestamp=now,
            user_id=current_user.id if current_user else None,
            location=event_in.location,
            status="RECEIVED",
        )
        db.add(event)
        db.commit()
        db.refresh(event)

        logger.info(
            f"NFC-tapahtuma #{event.id} rekisteröity onnistuneesti hevoselle #{tag_record.horse_id} "
            f"({tag_record.horse.name if tag_record.horse else 'N/A'})."
        )
        return event, True, "OK"


nfc_service = NfcService()
