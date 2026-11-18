"""
Kevyet skeemamigraatiot olemassa olevalle SQLite-kannalle.

`Base.metadata.create_all` luo puuttuvat taulut, mutta ei lisää uusia sarakkeita
vanhoihin tauluihin. Lisää uudet sarakkeet tähän listaan; migraatio on idempotentti.
(Jos skeemamuutoksia alkaa tulla paljon, siirry Alembiciin.)
"""
import logging

from sqlalchemy.engine import Engine

from app.database import Base

logger = logging.getLogger(__name__)

# (taulu, sarake, SQL-tyyppi ja oletus)
COLUMN_ADDITIONS = [
    ("horses", "breed", "VARCHAR(128)"),
    ("horses", "birth_year", "INTEGER"),
    ("horses", "owner_name", "VARCHAR(128)"),
    ("horses", "stall_box", "VARCHAR(64)"),
    ("horses", "description", "TEXT"),
    ("nfc_events", "clock_skew_seconds", "FLOAT"),
    ("video_clips", "is_mock", "BOOLEAN NOT NULL DEFAULT 0"),
    ("users", "display_name", "VARCHAR(128)"),
    ("users", "token_version", "INTEGER NOT NULL DEFAULT 0"),
    ("users", "last_login_at", "DATETIME"),
]

INDEXES = [
    "CREATE INDEX IF NOT EXISTS ix_air_sensor_measured ON stable_air_measurements (sensor_id, measured_at)",
]


def run_migrations(engine: Engine) -> None:
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        existing: dict[str, set[str]] = {}
        for table, column, col_type in COLUMN_ADDITIONS:
            if table not in existing:
                rows = conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
                existing[table] = {row[1] for row in rows}
            if column not in existing[table]:
                logger.info("Migraatio: lisätään sarake %s.%s", table, column)
                conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
                existing[table].add(column)
        for statement in INDEXES:
            conn.exec_driver_sql(statement)
