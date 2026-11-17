import json
import logging
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models import SystemEvent

logger = logging.getLogger(__name__)


def record_system_event(
    db: Session,
    level: str,
    event_type: str,
    message: str,
    details: Optional[dict[str, Any]] = None,
    commit: bool = True,
) -> None:
    """Kirjaa hälytyslokiin (näkyy /web/system-sivulla). Ei koskaan kaada kutsujaa."""
    try:
        db.add(
            SystemEvent(
                level=level,
                event_type=event_type,
                message=message,
                details_json=json.dumps(details, default=str) if details else None,
            )
        )
        if commit:
            db.commit()
    except Exception:  # pragma: no cover - lokitus ei saa estää varsinaista toimintoa
        logger.exception("SystemEventin kirjaus epäonnistui: %s", message)
        db.rollback()
