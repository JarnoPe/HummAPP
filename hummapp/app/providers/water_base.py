from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List
import datetime


@dataclass
class WaterMeasurementDTO:
    """
    Standardisoitu siirto-olio juomamittaukselle.
    """
    external_measurement_id: str
    external_water_id: str
    measured_at: datetime.datetime
    liters: float
    raw_data_json: Optional[str] = None


class AbstractWaterProvider(ABC):
    """
    Rajapinta ulkoiselle juoma-automaattipalvelulle.
    
    ========================================================================
    OHJE TUOTANTOINTEGRAATION TOTEUTTAJALLE:
    Kun juomapalvelun todellinen API-spesifikaatio selviää, toteuta tämä
    rajapinta uuteen luokkaan (esim. `ProductionWaterProvider`).
    
    Tarvittavat tiedot tuotantototeutukseen:
    1. Palvelun API-osoite (BASE_URL ja endpoint, esim. /api/v1/drinks)
    2. Autentikointimenetelmä (API-avain headerissa, Bearer-token tai Basic auth)
    3. Mittausdatan JSON-rakenne (kenttien nimet aikaleimalle, laitetunnukselle ja litroille)
    4. Aikaleimojen aikavyöhyke (onko UTC, Unix-sekunnit vai paikallisaika)
    5. Mahdollinen sivutus (pagination) tai aikavälirajaus (since_timestamp)
    ========================================================================
    """

    @abstractmethod
    async def fetch_recent_measurements(
        self, since: Optional[datetime.datetime] = None
    ) -> List[WaterMeasurementDTO]:
        """
        Hakee tuoreimmat juomismittaukset ulkoisesta palvelusta.
        Palauttaa listan WaterMeasurementDTO-olioita.
        """
        pass
