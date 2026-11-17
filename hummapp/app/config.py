from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Tunnetut esimerkki-/oletusarvot, joilla tuotanto ei saa käynnistyä.
_FORBIDDEN_SECRETS = {
    "change-this-secret-key-in-production-use-openssl-rand-hex-32",
    "vaihda-tama-salaisuus-openssl-rand-hex-32-arvolla-tuotantoon",
    "hummapp-pilot-secret-key-change-in-production-32chars",
}
_FORBIDDEN_PASSWORDS = {"Tallipaallikko2026!", "Tallipäällikkö2026!", "HummAPP2026!"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "HummAPP"
    APP_ENV: str = "production"
    APP_TIMEZONE: str = "Europe/Helsinki"

    # --- Turvallisuus (pakolliset .env-arvot, ei oletuksia) ---
    SECRET_KEY: str = Field(..., min_length=32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200  # 30 päivää
    ALGORITHM: str = "HS256"
    # Tyhjä = CORS pois päältä (Android ja oma web-UI eivät tarvitse CORSia).
    # Julkiselle hummapp.fi-sivustolle: ALLOWED_ORIGINS=https://hummapp.fi
    ALLOWED_ORIGINS: str = ""
    # Aseta true, kun palvelu on HTTPS:n (reverse proxy) takana
    COOKIE_SECURE: bool = False
    VIDEO_LINK_EXPIRE_MINUTES: int = 10

    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = Field(..., min_length=12)

    # --- Tietokanta ---
    DATABASE_PATH: str = "/data/hummapp.db"

    # --- Videot ja kamera ---
    VIDEO_OUTPUT_PATH: str = "/videos"
    CAMERA_SOURCE_PATH: str = "/camera"
    CAMERA_TIMEZONE: str = "Europe/Helsinki"
    # Leike 5 s ennen ja 13 s jälkeen NFC-leimauksen (yhteensä 18 s). Rajaus on lyhyt,
    # koska talutuksessa kameran eteen tulee pian jo seuraava eläin.
    VIDEO_SECONDS_BEFORE: int = Field(5, ge=0, le=60)
    VIDEO_SECONDS_AFTER: int = Field(13, ge=1, le=60)
    # Kameran yksittäisen tallennetiedoston maksimipituus (sekuntia)
    CAMERA_FILE_MAX_DURATION_SECONDS: int = 3600
    VIDEO_RETRY_INTERVAL_SECONDS: int = 5
    VIDEO_MAX_RETRIES: int = 12
    VIDEO_REJECTED_RETENTION_DAYS: int = 30
    # Jos puhelimen ja palvelimen kello eroavat tätä enemmän, kirjataan varoitus
    NFC_CLOCK_SKEW_WARNING_SECONDS: int = 2
    # Testisignaalivideo, jos kameratallennetta ei löydy. VAIN testaukseen.
    ENABLE_MOCK_CAMERA_FALLBACK: bool = False

    # --- Demo-/alustusdata ---
    # true = luodaan esimerkkihevonen "Valo" ja esimerkki-NFC-tagit pilottitestausta varten
    SEED_DEMO_DATA: bool = False

    # --- Julkinen vain luku -rajapinta (hummapp.fi) ---
    # Muistiinpanot voivat sisältää terveysmerkintöjä -> oletuksena ei julkaista
    PUBLIC_INCLUDE_NOTES: bool = False

    # --- Juomismittaus: VAIN ANTERO ---
    DRINKING_HORSE_NAME: str = "Antero"
    WATER_EXTERNAL_ID: str = "WATER-METER-ANTERO-01"
    # TODO: käytetään, kun tuotannon juomapalvelun provider toteutetaan
    WATER_API_URL: str = ""
    WATER_API_KEY: str = ""
    WATER_FETCH_INTERVAL_MINUTES: int = 15
    WATER_USE_MOCK: bool = True

    # --- Talli-ilma ---
    # TODO: käytetään, kun tuotannon ilmanlaatupalvelun provider toteutetaan
    AIR_API_URL: str = ""
    AIR_API_KEY: str = ""
    AIR_FETCH_INTERVAL_MINUTES: int = 10
    AIR_USE_MOCK: bool = True

    # --- Lokitus ---
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "/logs/hummapp.log"

    @field_validator("SECRET_KEY")
    @classmethod
    def _reject_example_secret(cls, v: str) -> str:
        if v in _FORBIDDEN_SECRETS:
            raise ValueError("SECRET_KEY on esimerkkiarvo. Luo oma: openssl rand -hex 32")
        return v

    @field_validator("ADMIN_PASSWORD")
    @classmethod
    def _reject_known_password(cls, v: str) -> str:
        if v in _FORBIDDEN_PASSWORDS:
            raise ValueError("ADMIN_PASSWORD on julkisesti tunnettu oletussalasana. Vaihda se .env-tiedostossa.")
        return v

    @property
    def cors_origins(self) -> List[str]:
        if self.ALLOWED_ORIGINS.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def cookie_max_age_seconds(self) -> int:
        return self.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    @property
    def clip_duration_seconds(self) -> int:
        return self.VIDEO_SECONDS_BEFORE + self.VIDEO_SECONDS_AFTER


settings = Settings()
