import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.nfc_uid import normalize_nfc_uid


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str
    user_id: int


class LoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    active: bool
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


# --- Hevoset ---
class HorseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    breed: Optional[str] = Field(default=None, max_length=128)
    birth_year: Optional[int] = None
    owner_name: Optional[str] = Field(default=None, max_length=128)
    stall_box: Optional[str] = Field(default=None, max_length=64)
    description: Optional[str] = None


class HorseUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    breed: Optional[str] = Field(default=None, max_length=128)
    birth_year: Optional[int] = None
    owner_name: Optional[str] = Field(default=None, max_length=128)
    stall_box: Optional[str] = Field(default=None, max_length=64)
    description: Optional[str] = None
    active: Optional[bool] = None


class HorseResponse(BaseModel):
    id: int
    name: str
    breed: Optional[str] = None
    birth_year: Optional[int] = None
    owner_name: Optional[str] = None
    stall_box: Optional[str] = None
    description: Optional[str] = None
    active: bool
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


# --- NFC Tagi ---
class NfcTagCreate(BaseModel):
    nfc_uid: str = Field(..., min_length=4, max_length=64)

    @field_validator("nfc_uid")
    @classmethod
    def normalize_uid(cls, v: str) -> str:
        return normalize_nfc_uid(v)


class NfcTagResponse(BaseModel):
    id: int
    horse_id: int
    nfc_uid: str
    active: bool
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


# --- NFC Tapahtuma ---
class NfcEventCreate(BaseModel):
    nfc_uid: str = Field(..., min_length=4, max_length=64)
    phone_timestamp: datetime.datetime
    location: Optional[str] = "kuvausalue-1"

    @field_validator("nfc_uid")
    @classmethod
    def normalize_uid(cls, v: str) -> str:
        return normalize_nfc_uid(v)


class NfcEventResponse(BaseModel):
    id: int
    horse_id: Optional[int] = None
    horse_name: Optional[str] = None
    nfc_uid: str
    phone_timestamp: datetime.datetime
    server_timestamp: datetime.datetime
    user_id: Optional[int] = None
    location: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    clock_skew_seconds: Optional[float] = None
    video_clip_id: Optional[int] = None
    video_clip_status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# --- Videoleikkeet ---
class VideoClipResponse(BaseModel):
    id: int
    nfc_event_id: int
    relative_file_path: str
    status: str
    created_at: datetime.datetime
    approved_at: Optional[datetime.datetime] = None
    rejected_at: Optional[datetime.datetime] = None
    deleted_at: Optional[datetime.datetime] = None
    is_mock: bool = False

    model_config = ConfigDict(from_attributes=True)


# --- Liikeanalyysit ---
class MovementAnalysisCreate(BaseModel):
    horse_id: int
    video_clip_id: Optional[int] = None
    analysis_method: str = Field(..., max_length=128)
    summary: str
    result_json: Optional[str] = None
    status: str = "APPROVED"


class MovementAnalysisResponse(BaseModel):
    id: int
    horse_id: int
    video_clip_id: Optional[int] = None
    analysis_method: str
    analysis_timestamp: datetime.datetime
    summary: str
    result_json: Optional[str] = None
    status: str
    created_by: Optional[int] = None
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


# --- Muistiinpanot ---
class HorseNoteCreate(BaseModel):
    content: str = Field(..., min_length=1)


class HorseNoteResponse(BaseModel):
    id: int
    horse_id: int
    content: str
    user_id: Optional[int] = None
    author_username: Optional[str] = None
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


# --- Juomismittaukset ---
class WaterMeasurementResponse(BaseModel):
    id: int
    horse_id: Optional[int] = None
    horse_name: Optional[str] = None
    external_measurement_id: str
    external_water_id: str
    measured_at: datetime.datetime
    liters: float
    raw_data_json: Optional[str] = None
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class WaterDailySummary(BaseModel):
    date: str  # YYYY-MM-DD
    total_liters: float
    measurement_count: int


# --- Talli-ilma ---
class StableAirMeasurementResponse(BaseModel):
    id: int
    sensor_id: str
    location: Optional[str] = None
    measured_at: datetime.datetime
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    ammonia: Optional[float] = None
    co2: Optional[float] = None
    particulate_matter: Optional[float] = None
    raw_data_json: Optional[str] = None
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


# --- Järjestelmätila ---
class SystemStatusResponse(BaseModel):
    status: str
    app_name: str
    version: str
    database_ok: bool
    camera_dir_exists: bool
    video_dir_exists: bool
    antero_configured: bool
    antero_horse_found: bool
    antero_horse_id: Optional[int] = None
    water_external_id: str
    mock_water_enabled: bool
    mock_air_enabled: bool
    mock_camera_fallback_enabled: bool
    video_seconds_before: int
    video_seconds_after: int
    uptime_utc: datetime.datetime


class VideoLinkResponse(BaseModel):
    """Lyhytikäinen latauslinkki ulkoiseen soittimeen (token ei ole käyttäjän istuntotoken)."""
    url: str
    expires_in_seconds: int


# --- Julkinen vain luku -näkymä (hummapp.fi) ---
# Rajattu tarkoituksella: EI omistajan nimeä, NFC-tagien UID:itä, käyttäjätunnuksia
# eikä mittausten raakadataa.
class PublicNote(BaseModel):
    id: int
    horse_id: int
    content: str
    created_at: Optional[datetime.datetime] = None


class PublicAnalysis(BaseModel):
    id: int
    horse_id: int
    analysis_method: str
    analysis_timestamp: Optional[datetime.datetime] = None
    summary: str
    status: str


class PublicHorse(BaseModel):
    id: int
    name: str
    breed: Optional[str] = None
    birth_year: Optional[int] = None
    stall_box: Optional[str] = None
    description: Optional[str] = None
    active: bool
    created_at: Optional[datetime.datetime] = None
    has_nfc_tag: bool
    notes: List[PublicNote] = []
    analyses: List[PublicAnalysis] = []


class PublicWaterMeasurement(BaseModel):
    id: int
    measured_at: datetime.datetime
    liters: float


class PublicAirReading(BaseModel):
    id: int
    location: Optional[str] = None
    measured_at: datetime.datetime
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    ammonia: Optional[float] = None
    co2: Optional[float] = None
    particulate_matter: Optional[float] = None


class PublicNfcEvent(BaseModel):
    id: int
    horse_id: Optional[int] = None
    horse_name: Optional[str] = None
    phone_timestamp: Optional[datetime.datetime] = None
    location: Optional[str] = None
    status: str
    video_clip_id: Optional[int] = None
    video_clip_status: Optional[str] = None


class PublicOverview(BaseModel):
    read_only: bool = True
    generated_at: datetime.datetime
    drinking_horse_name: str
    clip_seconds_before: int
    clip_seconds_after: int
    horses: List[PublicHorse]
    water_daily: List[WaterDailySummary]
    water_measurements: List[PublicWaterMeasurement]
    air_readings: List[PublicAirReading]
    nfc_events: List[PublicNfcEvent]
