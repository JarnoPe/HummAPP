"""
Aikavyöhykeapurit.

Tietokantaan tallennetaan naiivit UTC-ajat (SQLite). Käyttäjälle näkyvät
vuorokausirajat ("tänään", päiväkohtaiset summat) lasketaan kuitenkin Suomen
ajassa, jotta yön juomiskerrat eivät siirry väärälle päivälle.
"""
import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from app.config import settings

UTC = datetime.timezone.utc
LOCAL_TZ = ZoneInfo(settings.APP_TIMEZONE)


def utc_now() -> datetime.datetime:
    """Nykyhetki aware-UTC-muodossa."""
    return datetime.datetime.now(UTC)


def to_naive_utc(value: datetime.datetime) -> datetime.datetime:
    """Muuntaa ajan naiiviksi UTC:ksi SQLite-tallennusta varten. Naiivi syöte tulkitaan UTC:ksi."""
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def as_aware_utc(value: datetime.datetime) -> datetime.datetime:
    """Kannasta luettu naiivi UTC -> aware UTC."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def local_day_start_utc(now: Optional[datetime.datetime] = None, days_ago: int = 0) -> datetime.datetime:
    """Paikallisen vuorokauden alku (00:00 Suomen aikaa) naiivina UTC:nä."""
    local_now = as_aware_utc(now or utc_now()).astimezone(LOCAL_TZ)
    # ZoneInfo laskee UTC-siirtymän päivämäärän mukaan, joten kesäaika menee oikein
    start_local = (local_now - datetime.timedelta(days=days_ago)).replace(hour=0, minute=0, second=0, microsecond=0)
    return to_naive_utc(start_local)


def local_date_key(naive_utc: datetime.datetime) -> str:
    """Päiväavain (YYYY-MM-DD) Suomen ajassa kannan naiiville UTC-ajalle."""
    return as_aware_utc(naive_utc).astimezone(LOCAL_TZ).strftime("%Y-%m-%d")


def local_time_label(naive_utc: datetime.datetime, fmt: str = "%H:%M") -> str:
    return as_aware_utc(naive_utc).astimezone(LOCAL_TZ).strftime(fmt)
