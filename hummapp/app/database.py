import os
import logging
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.config import settings

logger = logging.getLogger(__name__)

# Varmista tietokantakansion olemassaolo
db_path = Path(settings.DATABASE_PATH)
try:
    db_path.parent.mkdir(parents=True, exist_ok=True)
except Exception as e:
    logger.warning(f"Could not create database directory {db_path.parent}: {e}")

SQLALCHEMY_DATABASE_URL = f"sqlite:///{settings.DATABASE_PATH}"

# SQLite-yhteyden alustaminen
# check_same_thread=False tarvitaan FastAPI:n asynkronisille pyynnöille
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 15},
    echo=False,
)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """
    Pakota SQLite käyttämään WAL (Write-Ahead Logging) -tilaa,
    reilua lukitusodotusta (busy_timeout) ja viiteavaimien eheyttä (foreign_keys).
    Tämä takaa erinomaisen suorituskyvyn ja vikasietoisuuden Synology NASilla.
    """
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
