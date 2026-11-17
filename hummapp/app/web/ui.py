"""
Web-käyttöliittymän esityslogiikka: tilojen suomenkieliset nimet, ilmanlaadun
raja-arvot, ilmoitukset ja palvelimella piirrettävien SVG-kuvaajien geometria.

Kuvaajat lasketaan palvelimella, jotta käyttöliittymä toimii myös ilman
internetyhteyttä (NAS lähiverkossa) eikä tarvitse JavaScript-kirjastoja.
"""
import datetime
import math
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Sequence

from app.constants import ClipStatus, EventStatus

# --- Tilat -------------------------------------------------------------------
# tone: pending (odottaa käyttäjää), working (järjestelmä työskentelee), ok, error, muted
STATUS_LABELS = {
    EventStatus.RECEIVED.value: ("Vastaanotettu", "working"),
    EventStatus.WAITING_FOR_RECORDING.value: ("Odottaa tallennetta", "working"),
    EventStatus.PROCESSING.value: ("Leikataan", "working"),
    EventStatus.READY.value: ("Odottaa tarkastusta", "pending"),
    EventStatus.FAILED.value: ("Epäonnistui", "error"),
    EventStatus.APPROVED.value: ("Hyväksytty", "ok"),
    EventStatus.REJECTED.value: ("Hylätty", "muted"),
    ClipStatus.DELETED.value: ("Poistettu", "muted"),
}

WORKING_STATUSES = {EventStatus.RECEIVED.value, EventStatus.WAITING_FOR_RECORDING.value, EventStatus.PROCESSING.value}


def status_label(status: str) -> str:
    return STATUS_LABELS.get(status, (status, "muted"))[0]


def status_tone(status: str) -> str:
    return STATUS_LABELS.get(status, (status, "muted"))[1]


def event_error_text(error_message: Optional[str]) -> Optional[str]:
    """Muuttaa tekniset virhekoodit ohjeeksi käyttäjälle."""
    if not error_message:
        return None
    if error_message.startswith("UNKNOWN_TAG"):
        return "Tagia ei ole yhdistetty hevoseen. Yhdistä se Hevoset-sivulla."
    if "Kameratallennetta ei löytynyt" in error_message:
        return "Kameratallennetta ei löytynyt. Tarkista kameran kello ja tallennuskansio."
    return error_message


# --- Ilmoitukset (flash) -----------------------------------------------------
# Vain ennalta määritellyt viestit: URL-parametri ei voi tuoda sivulle vapaata tekstiä.
FLASH_MESSAGES = {
    "hevonen-lisatty": ("ok", "Hevonen lisätty."),
    "hevonen-on-jo": ("error", "Samanniminen hevonen on jo olemassa."),
    "nimi-puuttuu": ("error", "Anna hevoselle nimi."),
    "tagi-yhdistetty": ("ok", "NFC-tagi yhdistetty."),
    "tagi-virheellinen": ("error", "Tagin tunnisteen pitää olla 8–20 heksamerkkiä, esim. 04A31B92C56F80."),
    "muistiinpano-tallennettu": ("ok", "Muistiinpano tallennettu."),
    "analyysi-tallennettu": ("ok", "Liikeanalyysi tallennettu."),
    "hyvaksytty": ("ok", "Leike hyväksytty."),
    "hylatty": ("ok", "Leike hylätty."),
    "poistettu": ("ok", "Leike poistettu."),
    "jono-valmis": ("ok", "Kaikki leikkeet on tarkastettu."),
    "juominen-paivitetty": ("ok", "Juomamittaukset päivitetty."),
    "ilma-paivitetty": ("ok", "Anturilukemat päivitetty."),
}


def flash_for(key: Optional[str]):
    if not key or key not in FLASH_MESSAGES:
        return None
    tone, text = FLASH_MESSAGES[key]
    return {"tone": tone, "text": text}


# --- Talli-ilman raja-arvot ---------------------------------------------------
@dataclass(frozen=True)
class AirMetric:
    key: str
    label: str
    unit: str
    low: Optional[float] = None    # alle tämän = poikkeama
    high: Optional[float] = None   # yli tämän = poikkeama
    guidance: str = ""
    decimals: int = 1

    def state(self, value: Optional[float]) -> str:
        if value is None:
            return "none"
        if self.high is not None and value > self.high:
            return "high"
        if self.low is not None and value < self.low:
            return "low"
        return "ok"

    def state_text(self, value: Optional[float]) -> str:
        return {"high": "Yli suosituksen", "low": "Alle suosituksen", "ok": "Suosituksen mukainen", "none": "Ei lukemaa"}[
            self.state(value)
        ]


AIR_METRICS: List[AirMetric] = [
    AirMetric("temperature", "Lämpötila", "°C", low=8, high=14, guidance="Suositus 8–14 °C"),
    AirMetric("humidity", "Ilmankosteus", "%", low=60, high=80, guidance="Suositus 60–80 %", decimals=0),
    AirMetric("ammonia", "Ammoniakki", "ppm", high=10, guidance="Suositus alle 10 ppm"),
    AirMetric("co2", "Hiilidioksidi", "ppm", high=1500, guidance="Suositus alle 1 500 ppm", decimals=0),
    AirMetric("particulate_matter", "Pienhiukkaset", "µg/m³", guidance="Pöly- ja kuivikekuorma"),
]

ANTERO_NO_DRINK_ALERT_HOURS = 8


def format_number(value: Optional[float], decimals: int = 1) -> str:
    """Suomalainen numeromuoto: desimaalipilkku ja ohut välilyönti tuhaterottimena."""
    if value is None:
        return "–"
    text = f"{value:,.{decimals}f}".replace(",", " ").replace(".", ",")
    return text


# --- SVG-kuvaajat -------------------------------------------------------------
@dataclass
class Bar:
    x: float
    y: float
    width: float
    height: float
    value: float
    label: str
    is_today: bool = False


@dataclass
class BarChart:
    width: int
    height: int
    bars: List[Bar] = field(default_factory=list)
    average: Optional[float] = None
    average_y: Optional[float] = None
    max_value: float = 0.0
    gridlines: List[dict] = field(default_factory=list)


def _nice_ceiling(value: float) -> float:
    """Pyöristää akselin ylärajan seuraavaan "siistiin" lukuun (esim. 23 -> 25, 61 -> 80)."""
    if value <= 0:
        return 1.0
    magnitude = 10 ** math.floor(math.log10(value))
    for multiplier in (1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
        if value <= multiplier * magnitude:
            return multiplier * magnitude
    return 10 * magnitude


def build_daily_bar_chart(
    days: Sequence, today_key: str, width: int = 640, height: int = 180, span_days: int = 14
) -> BarChart:
    """
    Pylväskaavio vuorokausisummista. `days` = DailyWater-olioita (date, total_liters).
    Puuttuvat päivät näytetään nollana, jotta aikajana pysyy tasavälisenä.
    """
    by_date = {d.date: d.total_liters for d in days}
    end = datetime.date.fromisoformat(today_key)
    keys = [(end - datetime.timedelta(days=i)).isoformat() for i in range(span_days - 1, -1, -1)]
    values = [by_date.get(k, 0.0) for k in keys]

    chart = BarChart(width=width, height=height)
    past = [v for k, v in zip(keys, values) if k != today_key and v > 0]
    chart.average = round(sum(past) / len(past), 1) if past else None
    top = max(values + ([chart.average] if chart.average else []) + [1.0])
    chart.max_value = _nice_ceiling(top)

    plot_top, plot_bottom = 8, height - 22
    plot_h = plot_bottom - plot_top
    slot = width / span_days
    bar_w = slot * 0.62
    for i, (key, value) in enumerate(zip(keys, values)):
        h = plot_h * (value / chart.max_value)
        day = datetime.date.fromisoformat(key)
        chart.bars.append(
            Bar(
                x=round(i * slot + (slot - bar_w) / 2, 1),
                y=round(plot_bottom - h, 1),
                width=round(bar_w, 1),
                height=round(h, 1),
                value=value,
                label=f"{day.day}.{day.month}.",
                is_today=key == today_key,
            )
        )
    for fraction in (0.5, 1.0):
        chart.gridlines.append(
            {"y": round(plot_bottom - plot_h * fraction, 1), "label": format_number(chart.max_value * fraction, 0)}
        )
    if chart.average:
        chart.average_y = round(plot_bottom - plot_h * (chart.average / chart.max_value), 1)
    return chart


@dataclass
class Sparkline:
    points: str
    width: int
    height: int
    band: Optional[dict]
    last_x: float
    last_y: float


def build_sparkline(
    values: Iterable[Optional[float]], metric: AirMetric, width: int = 220, height: int = 48
) -> Optional[Sparkline]:
    """Pieni viivakaavio yhdelle mittarille. Suosituksen alue piirretään taustalle."""
    series = [v for v in values if v is not None]
    if len(series) < 2:
        return None
    bounds = series + [b for b in (metric.low, metric.high) if b is not None]
    lo, hi = min(bounds), max(bounds)
    pad = (hi - lo) * 0.1 or 1.0
    lo, hi = lo - pad, hi + pad

    def y(v: float) -> float:
        return round(height - (v - lo) / (hi - lo) * height, 1)

    step = width / (len(series) - 1)
    pts = [(round(i * step, 1), y(v)) for i, v in enumerate(series)]
    band = None
    if metric.low is not None or metric.high is not None:
        top = y(metric.high) if metric.high is not None else 0
        bottom = y(metric.low) if metric.low is not None else height
        band = {"y": top, "height": round(bottom - top, 1)}
    return Sparkline(" ".join(f"{px},{py}" for px, py in pts), width, height, band, pts[-1][0], pts[-1][1])


WEEKDAYS = ["maanantai", "tiistai", "keskiviikko", "torstai", "perjantai", "lauantai", "sunnuntai"]


def local_day_label(now_utc: datetime.datetime) -> str:
    """Esim. "tiistai 17.11.2026" Suomen ajassa."""
    from app.timeutils import LOCAL_TZ, as_aware_utc
    local = as_aware_utc(now_utc).astimezone(LOCAL_TZ)
    return f"{WEEKDAYS[local.weekday()]} {local.day}.{local.month}.{local.year}"
