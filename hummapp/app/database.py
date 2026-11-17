import logging
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)

db_path = Path(settings.DATABASE_PATH)
try:
    db_path.parent.mkdir(parents=True, exist_ok=True)
except OSError as e:
    logger.warning("Tietokantahakemistoa %s ei voitu luoda: %s", db_path.parent, e)

SQLALCHEMY_DATABASE_URL = f"sqlite:///{settings.DATABASE_PATH}"

# check_same_thread=False: FastAPI ajaa synkroniset reitit säiepoolissa
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 15},
    echo=False,
)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """WAL-tila, lukitusodotus ja viite-eheys jokaiselle SQLite-yhteydelle."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA busy_timeout=5000;")
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.execute("PRAGMA synchronous=NORMAL;")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Tietokantasession riippuvuusinjektio FastAPI-reiteille."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
