import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.config import settings

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def configure_logging() -> None:
    """Konsoli + kiertävä lokitiedosto (LOG_FILE), jos hakemistoon voi kirjoittaa."""
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if settings.LOG_FILE:
        try:
            Path(settings.LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
            handlers.append(RotatingFileHandler(settings.LOG_FILE, maxBytes=5_000_000, backupCount=5, encoding="utf-8"))
        except OSError as e:
            print(f"Lokitiedostoa {settings.LOG_FILE} ei voi avata: {e}")
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format=LOG_FORMAT,
        handlers=handlers,
        force=True,
    )
