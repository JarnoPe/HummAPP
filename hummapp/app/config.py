import os
from pathlib import Path
from typing import List, Union
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    APP_NAME: str = "HummAPP"
    APP_ENV: str = "production"
    APP_PORT: int = 8000
    APP_HOST: str = "0.0.0.0"

    # Turvallisuus
    SECRET_KEY: str = "change-this-secret-key-in-production-use-openssl-rand-hex-32"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200  # 30 päivää
    ALGORITHM: str = "HS256"
    ALLOWED_ORIGINS: str = "*"

    # Ylläpitäjän oletustunnukset (ensimmäisellä alustuksella)
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "Tallipaallikko2026!"

    # Tietokanta
    DATABASE_PATH: str = "/data/hummapp.db"

    # Videot ja kamera
    VIDEO_OUTPUT_PATH: str = "/videos"
    CAMERA_SOURCE_PATH: str = "/camera"
    CAMERA_TIMEZONE: str = "Europe/Helsinki"
    VIDEO_SECONDS_BEFORE: int = 10
    VIDEO_SECONDS_AFTER: int = 40
    VIDEO_RETRY_INTERVAL_SECONDS: int = 5
    VIDEO_MAX_RETRIES: int = 12
    VIDEO_REJECTED_RETENTION_DAYS: int = 30
    ENABLE_MOCK_CAMERA_FALLBACK: bool = True

    # Juomismittaus: VAIN ANTERO
    DRINKING_HORSE_NAME: str = "Antero"
    WATER_EXTERNAL_ID: str = "WATER-METER-ANTERO-01"
    WATER_API_URL: str = "https://api.mock-water-service.local/v1/measurements"
    WATER_API_KEY: str = "mock-water-api-key"
    WATER_FETCH_INTERVAL_MINUTES: int = 15
    WATER_USE_MOCK: bool = True

    # Talli-ilman mittaukset
    AIR_API_URL: str = "https://api.mock-air-service.local/v1/readings"
    AIR_API_KEY: str = "mock-air-api-key"
    AIR_FETCH_INTERVAL_MINUTES: int = 10
    AIR_USE_MOCK: bool = True

    # Lokitus
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "/logs/hummapp.log"

    @property
    def cors_origins(self) -> List[str]:
        if self.ALLOWED_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
