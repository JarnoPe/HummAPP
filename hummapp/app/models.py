import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Float,
    Text,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship
from app.database import Base


def utc_now():
    """Palauttaa nykyisen ajan UTC-muodossa ilman aikavyöhykettä SQLite-yhteensopivasti."""
    return datetime.datetime.now(datetime.timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(32), nullable=False, default="user")  # admin, user, viewer
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    notes = relationship("HorseNote", back_populates="author")
    nfc_events = relationship("NfcEvent", back_populates="user")
    analyses = relationship("MovementAnalysis", back_populates="author")


class Horse(Base):
    __tablename__ = "horses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False, index=True)
    breed = Column(String(128), nullable=True)
    birth_year = Column(Integer, nullable=True)
    owner_name = Column(String(128), nullable=True)
    stall_box = Column(String(64), nullable=True)
    description = Column(Text, nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    nfc_tags = relationship("NfcTag", back_populates="horse", cascade="all, delete-orphan")
    nfc_events = relationship("NfcEvent", back_populates="horse")
    notes = relationship("HorseNote", back_populates="horse", cascade="all, delete-orphan")
    analyses = relationship("MovementAnalysis", back_populates="horse")
    water_measurements = relationship("WaterMeasurement", back_populates="horse")


class NfcTag(Base):
    __tablename__ = "nfc_tags"

    id = Column(Integer, primary_key=True, index=True)
    horse_id = Column(Integer, ForeignKey("horses.id", ondelete="CASCADE"), nullable=False, index=True)
    nfc_uid = Column(String(64), unique=True, nullable=False, index=True)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    horse = relationship("Horse", back_populates="nfc_tags")


class NfcEvent(Base):
    __tablename__ = "nfc_events"

    id = Column(Integer, primary_key=True, index=True)
    horse_id = Column(Integer, ForeignKey("horses.id", ondelete="SET NULL"), nullable=True, index=True)
    nfc_uid = Column(String(64), nullable=False, index=True)
    phone_timestamp = Column(DateTime, nullable=False)
    server_timestamp = Column(DateTime, default=utc_now, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    location = Column(String(128), nullable=True)
    status = Column(String(32), default="RECEIVED", nullable=False, index=True)
    # Tilat: RECEIVED, WAITING_FOR_RECORDING, PROCESSING, READY, FAILED, APPROVED, REJECTED
    error_message = Column(Text, nullable=True)

    horse = relationship("Horse", back_populates="nfc_events")
    user = relationship("User", back_populates="nfc_events")
    video_clips = relationship("VideoClip", back_populates="nfc_event", cascade="all, delete-orphan")


class VideoClip(Base):
    __tablename__ = "video_clips"

    id = Column(Integer, primary_key=True, index=True)
    nfc_event_id = Column(Integer, ForeignKey("nfc_events.id", ondelete="CASCADE"), nullable=False, index=True)
    relative_file_path = Column(String(512), nullable=False)
    status = Column(String(32), default="READY", nullable=False, index=True)
    # Tilat: PROCESSING, READY, FAILED, APPROVED, REJECTED, DELETED
    created_at = Column(DateTime, default=utc_now, nullable=False)
    approved_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)

    nfc_event = relationship("NfcEvent", back_populates="video_clips")
    analyses = relationship("MovementAnalysis", back_populates="video_clip")


class MovementAnalysis(Base):
    __tablename__ = "movement_analyses"

    id = Column(Integer, primary_key=True, index=True)
    horse_id = Column(Integer, ForeignKey("horses.id", ondelete="CASCADE"), nullable=False, index=True)
    video_clip_id = Column(Integer, ForeignKey("video_clips.id", ondelete="SET NULL"), nullable=True, index=True)
    analysis_method = Column(String(128), nullable=False)  # esim. "Manual-Observation", "Pose-Estimation-V1"
    analysis_timestamp = Column(DateTime, default=utc_now, nullable=False)
    summary = Column(Text, nullable=False)
    result_json = Column(Text, nullable=True)  # Joustava JSON-rakenne analyysipisteille
    status = Column(String(32), default="APPROVED", nullable=False)  # APPROVED, REJECTED, PENDING
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    horse = relationship("Horse", back_populates="analyses")
    video_clip = relationship("VideoClip", back_populates="analyses")
    author = relationship("User", back_populates="analyses")


class WaterMeasurement(Base):
    __tablename__ = "water_measurements"

    id = Column(Integer, primary_key=True, index=True)
    horse_id = Column(Integer, ForeignKey("horses.id", ondelete="SET NULL"), nullable=True, index=True)
    external_measurement_id = Column(String(128), unique=True, nullable=False, index=True)
    external_water_id = Column(String(128), nullable=False, index=True)
    measured_at = Column(DateTime, nullable=False, index=True)
    liters = Column(Float, nullable=False)
    raw_data_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    horse = relationship("Horse", back_populates="water_measurements")


class StableAirMeasurement(Base):
    __tablename__ = "stable_air_measurements"

    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(String(64), nullable=False, index=True)
    location = Column(String(128), nullable=True)
    measured_at = Column(DateTime, nullable=False, index=True)
    temperature = Column(Float, nullable=True)  # Celsius
    humidity = Column(Float, nullable=True)     # %
    ammonia = Column(Float, nullable=True)      # ppm
    co2 = Column(Float, nullable=True)          # ppm
    particulate_matter = Column(Float, nullable=True)  # µg/m³ (PM2.5 / PM10)
    raw_data_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)


class HorseNote(Base):
    __tablename__ = "horse_notes"

    id = Column(Integer, primary_key=True, index=True)
    horse_id = Column(Integer, ForeignKey("horses.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    horse = relationship("Horse", back_populates="notes")
    author = relationship("User", back_populates="notes")


class SystemEvent(Base):
    __tablename__ = "system_events"

    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(16), nullable=False, index=True)  # INFO, WARNING, ERROR
    event_type = Column(String(32), nullable=False, index=True)  # NFC, VIDEO, WATER, AIR, AUTH, SYSTEM
    message = Column(Text, nullable=False)
    details_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
