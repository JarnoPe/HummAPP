import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, field_validator


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str
    user_id: int


class LoginRequest(BaseModel):
    username: str
    password: str


class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "user"


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    active: bool
    created_at: datetime.datetime

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


# --- NFC Tagi ---
class NfcTagCreate(BaseModel):
    nfc_uid: str = Field(..., min_length=4, max_length=64)

    @field_validator("nfc_uid")
    @classmethod
    def normalize_uid(cls, v: str) -> str:
        # Poista välilyönnit, kaksoispisteet ja muuta isolla heksamuotoon
        cleaned = v.replace(" ", "").replace(":", "").upper()
        if not cleaned:
            raise ValueError("NFC UID ei voi olla tyhjä")
        return cleaned


class NfcTagResponse(BaseModel):
    id: int
    horse_id: int
    nfc_uid: str
    active: bool
    created_at: datetime.datetime

    class Config:
        from_attributes = True


# --- NFC Tapahtuma ---
class NfcEventCreate(BaseModel):
    nfc_uid: str = Field(..., min_length=4, max_length=64)
    phone_timestamp: datetime.datetime
    location: Optional[str] = "kuvausalue-1"

    @field_validator("nfc_uid")
    @classmethod
    def normalize_uid(cls, v: str) -> str:
        return v.replace(" ", "").replace(":", "").upper()


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
    video_clip_id: Optional[int] = None
    video_clip_status: Optional[str] = None

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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
    uptime_utc: datetime.datetime
