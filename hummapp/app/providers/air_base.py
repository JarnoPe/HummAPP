from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List
import datetime


@dataclass
class AirMeasurementDTO:
    """
    Standardisoitu siirto-olio talli-ilman mittauksille.
    """
    sensor_id: str
    location: Optional[str]
    measured_at: datetime.datetime
    temperature: Optional[float]
    humidity: Optional[float]
    ammonia: Optional[float]  # ppm
    co2: Optional[float]      # ppm
    particulate_matter: Optional[float]  # µg/m³
    raw_data_json: Optional[str] = None


class AbstractAirQualityProvider(ABC):
    """
    Rajapinta ulkoiselle talli-ilman ja olosuhdemittausten palvelulle.
    
    ========================================================================
    OHJE TUOTANTOINTEGRAATION TOTEUTTAJALLE:
    Kun ilmanlaatumittauspalvelun API-spesifikaatio selviää (esim. Ruuvi,
    Airthings, Aranet tai oma IoT-Gateway), peri tämä luokka.
    
    Tarvittavat tiedot tuotantototeutukseen:
    1. Sensorien tunnisteet ja sijainnit tallissa (esim. SENSOR-KARSINA-1)
    2. API-endpoint ja autentikointi
    3. Yksiköt: lämpötila (°C), ilmankosteus (%RH), ammoniakki (ppm tai mg/m³),
       CO2 (ppm) ja hiukkaset PM2.5 / PM10 (µg/m³)
    4. Virhetilanteiden käsittely (esim. anturin katkos tai kalibrointivirhe)
    ========================================================================
    """

    @abstractmethod
    async def fetch_recent_readings(self) -> List[AirMeasurementDTO]:
        """
        Hakee tuoreimmat olosuhde- ja ilmanlaatulukemat.
        """
        pass
