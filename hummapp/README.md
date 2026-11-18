# HummAPP - Hevosten Hyvinvointi- ja Talliseuranta
### Valmis Synology NAS -pilottijärjestelmä ja Android-sovellus

HummAPP on hevosalan tutkimus- ja hankepilottikäyttöön suunniteltu kevyt, luotettava ja ylläpidettävä seurantajärjestelmä. Järjestelmä kokoaa yhteen talliolosuhteet, hevosten muistiinpanot, riimutagin NFC-tunnistukseen perustuvan automaattisen videoleikkauksen (18 s leikkeet valvontakamerasta FFmpegillä), liikeanalyysitulokset sekä ainoana automaattimittauksena **Antero-hevosen juomamäärät**.

Tämä paketti on suunniteltu suoraan ajettavaksi **Synology NAS** -verkkolevypalvelimella **Container Managerilla (Docker Compose)** yhtenä ainoana kevyenä konttina ilman raskaita mikropalveluja, Redisiä tai erillisiä tietokantapalvelimia.

---

## SISÄLLYSLUETTELO
1. [Järjestelmän tarkoitus](#1-järjestelmän-tarkoitus)
2. [Toteutuksen rakenne](#2-toteutuksen-rakenne)
3. [Synology NASin vähimmäisvaatimukset](#3-synology-nasin-vähimmäisvaatimukset)
4. [Synology Container Managerin asentaminen](#4-synology-container-managerin-asentaminen)
5. [Projektin siirtäminen NASille](#5-projektin-siirtäminen-nasille)
6. [Tarvittavien hakemistojen luominen](#6-tarvittavien-hakemistojen-luominen)
7. [Oikeiden NAS-polkujen määrittäminen](#7-oikeiden-nas-polkujen-määrittäminen)
8. [.env-tiedoston tekeminen](#8-env-tiedoston-tekeminen)
9. [SECRET_KEY-arvon muodostaminen](#9-secret_key-arvon-muodostaminen)
10. [Ensimmäisen ylläpitäjän luominen](#10-ensimmäisen-ylläpitäjän-luominen)
11. [Docker-imagen rakentaminen](#11-docker-imagen-rakentaminen)
12. [Sovelluksen käynnistäminen](#12-sovelluksen-käynnistäminen)
13. [Tietokannan alustaminen ja WAL-tila](#13-tietokannan-alustaminen-ja-wal-tila)
14. [Anteron luominen ja tarkistaminen](#14-anteron-luominen-ja-tarkistaminen)
15. [Anteron juomapalvelun tunnisteen määrittäminen](#15-anteron-juomapalvelun-tunnisteen-määrittäminen)
16. [NFC-tagin yhdistäminen hevoseen](#16-nfc-tagin-yhdistäminen-hevoseen)
17. [Kamerahakemiston liittäminen (:ro)](#17-kamerahakemiston-liittäminen-ro)
18. [Kameran tiedostonimimallin sovittaminen (Video Source Resolver)](#18-kameran-tiedostonimimallin-sovittaminen-video-source-resolver)
19. [Web-käyttöliittymän avaaminen ja käyttö](#19-web-käyttöliittymän-avaaminen-ja-käyttö)
20. [Android-sovelluksen API-osoitteen määrittäminen](#20-android-sovelluksen-api-osoitteen-määrittäminen)
21. [Synology Reverse Proxyn määrittäminen](#21-synology-reverse-proxyn-määrittäminen)
22. [HTTPS-sertifikaatin käyttöönotto](#22-https-sertifikaatin-käyttöönotto)
23. [Tailscalen käyttäminen etäylläpitoon ja talliyhteyteen](#23-tailscalen-käyttäminen-etäylläpitoon-ja-talliyhteyteen)
24. [Lokien katsominen](#24-lokien-katsominen)
25. [Healthcheckin testaaminen](#25-healthcheckin-testaaminen)
26. [Varmuuskopiointi (Safe SQLite Online Backup)](#26-varmuuskopiointi-safe-sqlite-online-backup)
27. [Tietokannan palauttaminen](#27-tietokannan-palauttaminen)
28. [Sovelluksen päivittäminen](#28-sovelluksen-päivittäminen)
29. [Turvallinen sammuttaminen](#29-turvallinen-sammuttaminen)
30. [Tavallisimmat virhetilanteet ja vianetsintä](#30-tavallisimmat-virhetilanteet-ja-vianetsintä)
31. [Julkinen rajapinta ja tietosuoja](#31-julkinen-rajapinta-ja-tietosuoja)
32. [Kehittäjälle](#32-kehittäjälle)

---

## 1. Järjestelmän tarkoitus
HummAPP kerää, tallentaa ja esittää hevosten hyvinvointiin ja talliolosuhteisiin liittyvää dataa hankepilottia varten:
- **Hevostiedot ja muistiinpanot**: Havainnot, terveysmerkinnät ja toimenpiteet talliympäristössä.
- **NFC-videointitapahtumat**: Kun hevonen talutetaan kuvausalueelle, Android-puhelimella luetaan riimutagi. NAS leikkaa valvontakameran tallenteesta 18 sekunnin leikkeen (5 s ennen lukuhetkeä ja 13 s lukuhetken jälkeen). Rajaus on lyhyt, koska talutuksessa kameran eteen tulee pian jo seuraava eläin, ja pidempi leike sisältäisi väärän hevosen. Rajaus säädetään `.env`-muuttujilla `VIDEO_SECONDS_BEFORE` ja `VIDEO_SECONDS_AFTER`.
- **Videon tarkastus**: Leikkeen katsominen, hyväksyminen (`APPROVED`) tai hylkääminen (`REJECTED`).
- **Liikeanalyysit**: Ulkoisen analyysipalvelun tulosten manuaalinen tallennus hevoselle ja leikkeelle.
- **Juomisseuranta**: **Vain Antero-hevosella** on juoma-automaatti. Muiden hevosten juomista ei mitata, eikä järjestelmässä tarvita monimutkaista water-ID -hallintaa.
- **Talli-ilman olosuhteet**: Lämpötila, kosteus, ammoniakki (NH3), hiilidioksidi (CO2) ja pienhiukkaset (PM2.5/PM10).

---

## 2. Toteutuksen rakenne
```
┌────────────────────────────────────────────────────────┐
│                   ANDROID-PUHELIN                      │
│   • Kirjautuminen (JWT)   • Hevoslista & Muistiinpanot │
│   • NFC-luku (riimutagi)  • Videon tarkastus           │
└──────────────────────────┬─────────────────────────────┘
                           │ HTTPS / Token
                           ▼
┌────────────────────────────────────────────────────────┐
│                SYNOLOGY NAS (DSM 7+)                   │
│                                                        │
│  [Synology Reverse Proxy] (Portti 443 HTTPS -> 8000)   │
│                           │                            │
│  ┌────────────────────────▼─────────────────────────┐  │
│  │         HUMMAPP YKSIKKÖKONTTI (Docker)           │  │
│  │  • FastAPI (Python 3.11) + Uvicorn               │  │
│  │  • SQLite (WAL-tila) SQLAlchemylla                │  │
│  │  • FFmpeg taustaleikkuri (18s leikkeet, 5s+13s)  │  │
│  │  • APScheduler (Anteron juomisen & ilman haku)   │  │
│  │  • Web UI (Jinja2 + Tailwind + Chart.js + HTMX)  │  │
│  └──────────┬─────────────────┬───────────────────┬─┘  │
│             │                 │                   │    │
│       ./data (DB)       ./videos (MP4)      ./camera   │
│     (hummapp.db)      (leikatut leikkeet)   (vain luku)│
└────────────────────────────────────────────────────────┘
```

---

## 3. Synology NASin vähimmäisvaatimukset
- **DSM-versio**: Synology DSM 7.2 tai uudempi.
- **Suoritin**: 64-bittinen x86_64 (Intel Celeron/Xeon, AMD Ryzen) tai ARM64.
- **Keskusmuisti**: Vähintään 2 Gt RAM (suositus 4 Gt tai enemmän, jotta FFmpeg-videoleikkaus toimii sujuvasti).
- **Tallennustila**: Vähintään 10 Gt vapaata tilaa videoille ja tietokannalle.
- **Paketit**: **Container Manager** (Synology DSM Package Centeristä).

---

## 4. Synology Container Managerin asentaminen
1. Avaa selaimesi ja kirjaudu Synology DSM -hallintaan.
2. Avaa **Package Center** (Pakettikeskus).
3. Hae sanalla `Container Manager`.
4. Napsauta **Asenna** (Install).
5. Asennuksen valmistuttua NASin päävalikkoon ilmestyy Container Manager -kuvake.

---

## 5. Projektin siirtäminen NASille
Siirrä `hummapp`-kansio verkkolevylle jommallakummalla tavalla:

### Vaihtoehto A: File Station (Selaimella)
1. Avaa DSM:ssä **File Station**.
2. Siirry haluamaasi jaettuun kansioon (esim. `docker` tai `projects`).
3. Luo uusi kansio: `hummapp`.
4. Pura ladattu ZIP ja vedä tiedostot selaimeen kansioon `/docker/hummapp`.

### Vaihtoehto B: SSH ja SCP / rsync (Komentoriviltä)
```bash
# Esimerkki siirrosta omalta koneelta NASille:
scp -r ./hummapp talliyllapito@192.168.1.100:/volume1/docker/
```

---

## 6. Tarvittavien hakemistojen luominen
Synology NASille tarvitaan pysyvät hakemistot tietokannalle, videoille, kameroille, lokeille ja varmuuskopioille.

Avaa SSH-yhteys NASille tai luo kansiot File Stationissa:
```bash
cd /volume1/docker/hummapp

# Luodaan tarvittavat tallennuskansiot
mkdir -p data videos camera logs backups

# Asetetaan oikeudet kontin käyttäjälle (UID 1000)
sudo chown -R 1000:1000 data videos logs backups
sudo chmod -R 775 data videos logs backups
```

---

## 7. Oikeiden NAS-polkujen määrittäminen
Kameratallenteiden hakemisto yhdistetään `compose.yaml`-tiedostossa. Jos käytät Synology Surveillance Stationia, kameratallenteet löytyvät yleensä polusta:
`/volume1/surveillance` tai `/volume1/tallikamera`.

Muokkaa `compose.yaml`:
```yaml
    volumes:
      - ./data:/data
      - ./videos:/videos
      - /volume1/surveillance:/camera:ro   # <--- Aseta oman kamerasi NAS-polku tähän!
      - ./logs:/logs
      - ./backups:/backups
```
> **TÄRKEÄÄ**: `:ro` (read-only) takaa sen, että HummAPP lukee kameratallenteita vain luku -tilassa eikä voi koskaan vahingossa muuttaa tai poistaa kameran alkuperäisiä tiedostoja.

---

## 8. .env-tiedoston tekeminen
Kopioi `.env.example` uudeksi `.env`-tiedostoksi:
```bash
cd /volume1/docker/hummapp
cp .env.example .env
```

---

## 9. SECRET_KEY-arvon muodostaminen
Luo vahva satunnainen avain terminaalissa:
```bash
openssl rand -hex 32
```
Kopioi tulos `.env`-tiedoston kohtaan:
```env
SECRET_KEY=tahan-luotu-pitka-hex-merkkijono
```
> **Pakollinen.** Sovellus ei käynnisty, jos `SECRET_KEY` puuttuu, on alle 32 merkkiä tai on `.env.example`-tiedoston esimerkkiarvo. Näin julkisesti tunnetulla avaimella ei voi vahingossa ajaa tuotantoa (tunnetulla avaimella kuka tahansa voisi väärentää admin-tokenin).

---

## 10. Ensimmäisen ylläpitäjän luominen
Määritä `.env`-tiedostoon haluamasi pääkäyttäjätunnus ja salasana:
```env
ADMIN_USERNAME=admin
ADMIN_PASSWORD=oma-vahva-salasana-vahintaan-12-merkkia
```
Sovellus luo tämän käyttäjän automaattisesti ensimmäisellä käynnistyksellä, jos sitä ei vielä ole. `ADMIN_PASSWORD` on pakollinen (vähintään 12 merkkiä), eikä aiempia julkisesti dokumentoituja oletussalasanoja hyväksytä. Salasanan vaihto `.env`-tiedostossa ei muuta jo luodun käyttäjän salasanaa.

---

## 11. Docker-imagen rakentaminen
Rakenna HummAPP-konttikomponentti:
```bash
cd /volume1/docker/hummapp
docker compose build
```
Rakennusvaihe asentaa Python 3.11:n, FFmpeg-työkalut, SQLite3-apurit ja sovellusriippuvuudet yhteen ja samaan kevyeen konttiin.

---

## 12. Sovelluksen käynnistäminen
Käynnistä palvelu taustalle:
```bash
docker compose up -d
```
Tarkista käynnistystila:
```bash
docker compose ps
```
Tulosteessa tilan tulee olla `Up` ja healthcheckin tila `healthy`.

---

## 13. Tietokannan alustaminen ja WAL-tila
HummAPP käyttää SQLite-tietokantaa tiedostopolussa `/data/hummapp.db`.
Sovelluskoodi pakottaa yhteyden muodostuessa SQLiten käyttämään **WAL-tilaa (Write-Ahead Logging)**:
```sql
PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=5000;
PRAGMA foreign_keys=ON;
```
Tämä takaa, että luku- ja kirjoitusoperaatiot eivät lukitse toisiaan, ja järjestelmä toimii nopeasti ja vikasietoisesti myös tallin ajoittaisissa sähkökatkoissa.

---

## 14. Anteron luominen ja tarkistaminen
Pilotissa juoma-automaatti on **ainoastaan Anterolla**.
- Kun sovellus käynnistyy, se varmistaa automaattisesti hevosen `Antero` olemassaolon. NFC-tagia ei enää yhdistetä automaattisesti; yhdistä Anteron oikea tagi kohdan 16 mukaisesti. Testausta varten esimerkkihevosen *Valo* ja esimerkkitagit saa luotua asetuksella `SEED_DEMO_DATA=true`.
- Voit tarkistaa tämän avaamalla selaimella Web UI:n sivun `http://NAS-IP:8000/web/horses`.
- Jos haluat nimetä Anteron uudelleen tai asettaa toisen nimen, tee se `.env`-tiedostossa muuttujalla:
  `DRINKING_HORSE_NAME=Antero`

---

## 15. Anteron juomapalvelun tunnisteen määrittäminen
Juoma-automaatin laitetunniste määritetään `.env`-tiedostossa:
```env
WATER_EXTERNAL_ID=WATER-METER-ANTERO-01
WATER_API_URL=https://api.mock-water-service.local/v1/measurements
WATER_API_KEY=oma-api-avain
WATER_FETCH_INTERVAL_MINUTES=15
WATER_USE_MOCK=true
```
- Kun mittausdata saapuu, HummAPP tarkistaa, että laite vastaa `WATER_EXTERNAL_ID`-arvoa.
- Jos laitetunniste ei täsmää, mittaus tallennetaan tunnistamattomana (`horse_id = NULL`), jotta data ei häviä, mutta sitä ei sekoiteta Anteron tilastoihin.
- Duplikaattien esto takaa, ettei samaa mittausta kirjata kahta kertaa.

---

## 16. NFC-tagin yhdistäminen hevoseen
Hevosen riimussa tai karsinassa käytetään passiivista RFID/NFC-tagia (esim. NTAG213, NTAG215 tai ISO 15693).
1. Lue tagi Android-sovelluksella tai katso sen UID (esim. `04A31B92C56F80`).
2. Avaa Web UI -> **Hevoset** (`/web/horses`).
3. Lomakkeessa "Yhdistä NFC-tagi hevoseen":
   - Valitse hevonen (esim. Antero).
   - Syötä tagin heksakoodi (välilyönnit ja pienet kirjaimet siivotaan automaattisesti).
   - Napsauta **Yhdistä tagi**.
4. Jos tagi oli aiemmin yhdistetty toiseen hevoseen, järjestelmä korjaa liitoksen turvallisesti.

---

## 17. Kamerahakemiston liittäminen (:ro)
Kameroiden tallenteet sijaitsevat NASin jaetussa kansiossa. Liitos tehdään vain luku -tilassa:
```yaml
volumes:
  - /volume1/surveillance:/camera:ro
```
Tämä suojaa videovalvontajärjestelmän tiedostoja luvattomalta muokkaukselta.

---

## 18. Kameran tiedostonimimallin sovittaminen (Video Source Resolver)
Leike on vain 18 sekuntia (5 s + 13 s), joten aikojen täytyy täsmätä sekunnin tarkkuudella. Tiedostossa `app/services/video_source_resolver.py` on luokka `SynologyTimestampVideoResolver`, joka:

1. Lukee aikaleiman tiedostonimestä (esim. `CAM01_20261117_120000.mp4` tai Surveillance Stationin `Kamera-20261117-120000-1795420800.mp4`).
2. **Tulkitsee aikaleiman kameran aikavyöhykkeessä** (`CAMERA_TIMEZONE`, oletus `Europe/Helsinki`). Jos kamerasi nimeää tiedostot UTC-ajassa, aseta `CAMERA_TIMEZONE=UTC`.
3. Valitsee lähimmän ennen leikkeen alkua alkaneen tiedoston ja laskee leikkauskohdan sen alusta.
4. Tarkistaa `ffprobe`-työkalulla, että tiedosto on luettavissa ja kattaa koko leikkeen. Kesken oleva tallenne odotetaan valmiiksi (`VIDEO_RETRY_INTERVAL_SECONDS` × `VIDEO_MAX_RETRIES`).
5. Hakee ensin päiväkansioista (esim. `20261117AM`, `2026-11-17`, `2026/11/17`), jotta koko valvontahakemistoa ei käydä läpi joka kerta.

**Tärkeää leikkeen osumatarkkuudelle:**
- **Kellot:** Kameran, NASin ja tallipuhelimen kellot pitää synkronoida (NTP / puhelimen automaattinen aika). HummAPP tallentaa jokaiseen NFC-tapahtumaan puhelimen ja palvelimen kelloeron (`clock_skew_seconds`) ja kirjaa varoituksen, jos ero on yli `NFC_CLOCK_SKEW_WARNING_SECONDS` (oletus 2 s).
- **Tallennepätkän pituus:** Kamera kirjoittaa MP4-tiedoston luettavaksi vasta pätkän lopussa. Lyhyet pätkät (esim. 1–5 min) nopeuttavat leikkeen valmistumista. Aseta odotusaika vähintään pätkän pituiseksi, esim. 5 min pätkille `VIDEO_RETRY_INTERVAL_SECONDS=12` ja `VIDEO_MAX_RETRIES=30`.
- **Testivideo:** `ENABLE_MOCK_CAMERA_FALLBACK=true` korvaa puuttuvan tallenteen testisignaalivideolla. Käytä tätä vain testaukseen. Testivideot merkitään web-UI:ssa `TESTIVIDEO`-merkinnällä.

Jos kamerasi käyttää muuta nimeämistapaa, säädä `FILENAME_TIMESTAMP`-säännöllistä lauseketta tai toteuta oma `VideoSourceResolverBase`-luokka. Aja `pytest tests/test_video_resolver.py`, kun muutat logiikkaa.

---

## 19. Web-käyttöliittymän avaaminen ja käyttö
1. Avaa selaimella: `http://NAS-IP:8000` (tai HTTPS-osoite reverse proxyn kautta).
2. Kirjaudu `.env`-tiedostossa määritetyillä admin-tunnuksilla.
3. Käyttöliittymässä on sivut:
   - **Katsaus** (`/`): huomiota vaativat asiat, Anteron juominen ja talli-ilma.
   - **Hevoset** (`/web/horses`): hevosrekisteri, NFC-kytkennät ja hevoskohtainen sivu muistiinpanoineen.
   - **Videot** (`/web/nfc-events`): leikkeiden tarkastusjono (testisignaalivideot merkitty `TESTIVIDEO`), hyväksyntä, hylkäys ja ylläpitäjän poisto.
   - **Juominen** (`/web/water`): Anteron juomahistoria ja vuorokausitilastot.
   - **Talli-ilma** (`/web/air`): lämpötila, kosteus, NH3, CO2 ja hiukkaset suositusrajoineen.
   - **Käyttäjät** (`/web/users`, vain ylläpitäjä): käyttäjätunnusten luonti, roolit, salasanat ja passivointi (kohta 19.1).
   - **Järjestelmä** (`/web/system`, vain ylläpitäjä): hakemistojen tarkistus, leikeasetukset ja hälytysloki.
   - **Oma tili** (`/web/account`): oman salasanan vaihto. Avautuu yläpalkin nimestä, mobiilissa linkistä Oma tili tai Asetukset.

### 19.1 Käyttäjätunnukset ja roolit
Tunnuksia ei voi luoda sovelluksesta eikä rekisteröitymällä. Ainoastaan ylläpitäjä luo ne web-käyttöliittymän **Käyttäjät**-sivulla. Ensimmäinen ylläpitäjä syntyy NASin ensimmäisellä käynnistyksellä `.env`-tiedoston `ADMIN_USERNAME`- ja `ADMIN_PASSWORD`-arvoilla.

| Rooli | Oikeudet |
|---|---|
| **Ylläpitäjä** | Kaikki toiminnot, käyttäjähallinta, järjestelmäsivu ja videoiden poisto |
| **Tallin käyttäjä** | NFC-leimaus, videoiden hyväksyntä ja hylkäys, hevosten ja tagien lisäys, muistiinpanot |
| **Katselija** | Näkee tiedot ja videot, mutta ei voi muuttaa mitään |

- Luo jokaiselle työntekijälle oma tunnus. Silloin pääkäyttäjän salasanaa ei tarvitse jakaa, ja merkinnöistä näkee, kuka ne teki.
- Salasanassa pitää olla vähintään 10 merkkiä. Käyttäjä voi vaihtaa salasanansa itse Oma tili -sivulla.
- **Passivointi** estää kirjautumisen heti ja päättää käyttäjän avoimet istunnot kaikilla laitteilla. Käyttäjän tekemät merkinnät säilyvät.
- Salasanan vaihto ja roolin muutos kirjaavat käyttäjän ulos muilta laitteilta.
- Viimeistä aktiivista ylläpitäjää ei voi passivoida, eikä ylläpitäjä voi poistaa omaa ylläpitäjän rooliaan.

---

## 20. Android-sovelluksen API-osoitteen määrittäminen
1. Avaa HummAPP puhelimessa.
2. Kirjautumisruudussa syötä **Palvelimen osoite**:
   - Tailscalen kautta (suositus, kun sisäverkkoon ei ole Wi-Fi-yhteyttä): `http://100.x.y.z:8000`, ks. kohta 23
   - Lähiverkossa: `http://192.168.1.100:8000` (sovelluksen oletus)
   - Koko Internetissä (Reverse Proxy / HTTPS): `https://hummapp.oma-talli.synology.me`
3. Syötä käyttäjätunnus ja salasana ja paina **Kirjaudu sisään**.
4. Token tallennetaan salattuna laitteen `EncryptedSharedPreferences`-muistiin.

---

## 21. Synology Reverse Proxyn määrittäminen
Reverse Proxy tarjoaa sovellukselle turvallisen HTTPS-yhteyden ja SSL-salauksen ilman muutoksia konttiin:
1. Avaa DSM:ssä **Control Panel** (Ohjauspaneeli) -> **Login Portal** -> välilehti **Advanced**.
2. Napsauta **Reverse Proxy** -> **Create**.
3. Täytä asetukset:
   - **Source** (Lähde):
     - Protocol: `HTTPS`
     - Hostname: `hummapp.oma-talli.synology.me`
     - Port: `443`
     - Ota käyttöön HSTS tarvittaessa.
   - **Destination** (Kohde):
     - Protocol: `HTTP`
     - Hostname: `localhost`
     - Port: `8000`
4. Siirry välilehdelle **Custom Header** -> **Create** -> **WebSocket** (varmistaa tilapäivitysten toimivuuden).
5. Tallenna painamalla **Save**.

---

## 22. HTTPS-sertifikaatin käyttöönotto
1. Avaa DSM:ssä **Control Panel** -> **Security** -> välilehti **Certificate**.
2. Napsauta **Add** -> **Add a new certificate** -> **Get a certificate from Let's Encrypt**.
3. Syötä verkkotunnuksesi (esim. `hummapp.oma-talli.synology.me`) ja sähköpostiosoitteesi.
4. Kun sertifikaatti on luotu, valitse se listasta, napsauta **Settings** ja aseta uusi sertifikaatti kohtaan `hummapp.oma-talli.synology.me`.

---

## 23. Tailscalen käyttäminen etäylläpitoon ja talliyhteyteen
Tailscale on salattu yksityisverkko. Sen avulla tallipuhelin saa yhteyden NASiin mobiilidatalla myös silloin, kun sisäverkkoon pääsee vain kaapelilla. Reitittimeen ei avata portteja, eikä NAS näy internetiin.

### 23.1 Tailscale NASille
1. Kirjaudu DSM:ään ylläpitäjänä ja avaa **Package Center** (Pakettikeskus).
2. Hae `Tailscale` ja valitse **Install**. Paketti on Tailscalen itse ylläpitämä.
   - Jos pakettia ei löydy NAS-mallillesi, lataa oikea `.spk`-tiedosto Tailscalen pakettipalvelimelta (pkgs.tailscale.com) ja asenna se kohdasta **Manual Install**.
3. Kun asennus on valmis, valitse **Open**. Tailscale avaa kirjautumissivun.
4. Kirjaudu Tailscaleen. Organisaation tiliä varten on suositeltavaa käyttää esim. Microsoft 365- tai Google-työtiliä, jotta verkko ei ole yhden henkilön yksityistilin varassa.
5. Hyväksy NAS Tailscale-verkkoon. Avaa sen jälkeen Tailscalen hallintakonsoli (login.tailscale.com) ja välilehti **Machines**. Sieltä löytyy NASin Tailscale-osoite muotoa `100.x.y.z`.
6. Valitse samalla NASin rivin valikosta **Disable key expiry**. Muuten NAS putoaa verkosta, kun sen avain vanhenee, oletuksena noin 180 päivän välein.
7. Package Center päivittää Tailscalea harvoin. Ota pakettikeskuksen automaattiset päivitykset käyttöön tai päivitä paketti säännöllisesti.

### 23.2 Tallipuhelimet
1. Asenna puhelimeen **Tailscale** Google Playsta.
2. Kirjaudu samaan Tailscale-verkkoon ja hyväksy laite hallintakonsolissa.
3. Avaa HummAPP ja kirjoita palvelimen osoitteeksi `http://100.x.y.z:8000` (NASin Tailscale-osoite).
4. Paina **Testaa yhteys**. Kun yhteys toimii, kirjaudu omalla käyttäjätunnuksellasi.

Tailscalen pitää olla päällä puhelimessa, kun leimataan. Sovelluksen voi asettaa käynnistymään automaattisesti Tailscalen asetuksista.

### 23.3 Pääsyn rajaaminen (suositus)
Oletuksena kaikki Tailscale-verkon laitteet näkevät toisensa. Rajaa tallipuhelimet näkemään vain HummAPPin portti:
1. Hallintakonsolissa **Access controls** -välilehdellä anna NASille tagi (esim. `tag:hummapp-nas`) ja puhelimille tagi `tag:talli`.
2. Lisää sääntö, joka sallii puhelimille vain portin 8000:
   ```json
   {
     "tagOwners": { "tag:hummapp-nas": ["autogroup:admin"], "tag:talli": ["autogroup:admin"] },
     "acls": [
       { "action": "accept", "src": ["tag:talli"], "dst": ["tag:hummapp-nas:8000"] },
       { "action": "accept", "src": ["autogroup:admin"], "dst": ["*:*"] }
     ]
   }
   ```
3. Näin kadonneella tallipuhelimella ei pääse NASin hallintaan (DSM, tiedostot), vaan korkeintaan HummAPPin kirjautumissivulle. Poista kadonnut laite hallintakonsolista ja passivoi sen käyttäjä HummAPPin **Käyttäjät**-sivulla.

---

## 24. Lokien katsominen
Kontin lokit voi tarkistaa kahdella tavalla:

### Komentoriviltä:
```bash
cd /volume1/docker/hummapp
docker compose logs -f --tail=100
```

### Tiedostosta:
```bash
tail -f /volume1/docker/hummapp/logs/hummapp.log
```

---

## 25. Healthcheckin testaaminen
Tarkista kontin kunto suorittamalla:
```bash
bash /volume1/docker/hummapp/scripts/smoke_test.sh http://localhost:8000
```
Skripti lukee admin-salasanan `.env`-tiedostosta (tai kysyy sen) ja tarkistaa automaattisesti:
- `/api/health` -kunnon
- Kirjautumisen ja JWT-tokenin muodostuksen
- `/api/system/status` -diagnostiikan (vaatii admin-tokenin)
- Hevoslistauksen
- Anteron juomamittausten yhteenvedon
- Talli-ilman mittaukset

---

## 26. Varmuuskopiointi (Safe SQLite Online Backup)
Koska SQLite on WAL-tilassa, tiedostoa ei saa kopioida lennossa tavallisella `cp`-komennolla!
Käytä toimitettua varmuuskopiointiskriptiä:
```bash
cd /volume1/docker/hummapp
bash scripts/backup.sh
```
Skripti:
1. Suorittaa SQLiten virallisen online-varmuuskopion (`.backup`).
2. Pakkaa tietokannan gzipillä (`/backups/hummapp_backup_YYYYMMDD_HHMMSS.db.gz`).
3. Poistaa automaattisesti yli 30 päivää vanhat kopiot.

Voit ajastaa tämän DSM:n **Task Schedulerissa** (Tehtävien ajoitus) ajettavaksi kerran vuorokaudessa.

---

## 27. Tietokannan palauttaminen
Jos tietokanta täytyy palauttaa varmuuskopiosta:
```bash
cd /volume1/docker/hummapp

# 1. Pysäytä kontti
docker compose stop hummapp

# 2. Aja palautusskripti valitulla varmuuskopiotiedostolla
bash scripts/restore.sh backups/hummapp_backup_20261112_120000.db.gz

# 3. Käynnistä kontti uudelleen
docker compose start hummapp
```

---

## 28. Sovelluksen päivittäminen
Kun koodiin tehdään parannuksia:
```bash
cd /volume1/docker/hummapp

# 1. Vedä uudet tiedostot tai päivitä koodi
# 2. Rakenna kontti uudelleen
docker compose build

# 3. Käynnistä uudelleen ilman datakatkosta
docker compose up -d
```
Tietokanta ja videot säilyvät koskemattomina pysyvissä hakemistoissa `./data` ja `./videos`.

---

## 29. Turvallinen sammuttaminen
Pysäytä palvelu siististi:
```bash
cd /volume1/docker/hummapp
docker compose down
```

---

## 30. Tavallisimmat virhetilanteet ja vianetsintä

| Ongelma / Oire | Syy | Korjaustoimenpide |
| :--- | :--- | :--- |
| **UNKNOWN_TAG -virhe puhelimessa** | Luettua NFC-tagia ei ole yhdistetty yhteenkään hevoseen. | Avaa Web UI -> **Hevoset** ja yhdistä tagin UID haluamaasi hevoseen. Järjestelmä ei luo hevosia tuntemattomista tageista turvallisuussyistä. |
| **Juomadataa ei kerry Anterolle** | 1) Hevosta `Antero` ei ole luotu tietokantaan, TAI<br>2) Ulkoisen laitteen ID ei vastaa `WATER_EXTERNAL_ID`-arvoa. | Tarkista Web UI -> **Järjestelmä** (`/web/system`). Varmista, että hevonen nimeltä Antero löytyy ja `.env`-tiedoston `WATER_EXTERNAL_ID` täsmää mittalaitteeseen. |
| **Videoleikkaus epäonnistuu (FAILED)** | Kameran tallennetta ei löydy tai se ei valmistu odotusajassa. | Tarkista `compose.yaml`:n kamerahakemiston liitos (`/camera:ro`) ja `CAMERA_TIMEZONE`. Pidennä odotusaikaa kameran tallennepätkän pituiseksi (kohta 18). Jos testaat ilman kameraa, aseta `ENABLE_MOCK_CAMERA_FALLBACK=true`. |
| **Permission Denied / Oikeusvirhe data-kansiossa** | Synology DSM:n kansio-oikeudet eivät salli kontin käyttäjän (UID 1000) kirjoitusta. | Aja NASin terminaalissa: `sudo chown -R 1000:1000 data videos logs backups` ja `sudo chmod -R 775 data videos logs backups`. |
| **Database locked -virhe** | Tietokantaa yritetty käyttää ilman WAL-tilaa tai useasta prosessista. | HummAPP käyttää oletuksena `PRAGMA journal_mode=WAL` ja `busy_timeout=5000`. Varmista, ettei mikään ulkoinen ohjelma lukitse `hummapp.db`-tiedostoa samaan aikaan. |
| **Leike näyttää väärän hevosen / väärän hetken** | Kameran, NASin tai puhelimen kello ei ole synkronoitu, tai `CAMERA_TIMEZONE` on väärä. | Tarkista NFC-tapahtuman `clock_skew_seconds` ja lokin kelloerovaroitukset. Ota NTP käyttöön kamerassa ja NASissa ja automaattinen aika puhelimessa. Tarkista, nimeääkö kamera tiedostot paikallis- vai UTC-ajassa. |
| **Sovellus ei käynnisty: SECRET_KEY / ADMIN_PASSWORD** | Pakollinen arvo puuttuu tai on esimerkkiarvo. | Täytä `.env`-tiedostoon oma `SECRET_KEY` (`openssl rand -hex 32`) ja vähintään 12-merkkinen `ADMIN_PASSWORD`. |
| **Puhelin ei lue NFC-tagia** | Puhelimen NFC-siru on pois päältä tai suojakuori estää signaalin. | Tarkista puhelimen pika-asetuksista, että NFC on päällä. Vie tagi puhelimen yläosan antennialueelle. |
| **Path Traversal estetty** | Käyttäjä tai ulkoinen kutsu yrittänyt viitata videohakemiston ulkopuolelle. | Järjestelmä estää `..`-viittaukset ja sallii vain polut, jotka pysyvät `/videos`-kansiossa. |

---

## 31. Julkinen rajapinta ja tietosuoja
`/api/public/overview` on kirjautumaton vain luku -rajapinta hummapp.fi-sivustolle. Se on rajattu tarkoituksella, eikä palauta:
- hevosten omistajien nimiä (henkilötieto)
- NFC-tagien UID-tunnisteita (tagin voisi kloonata)
- käyttäjätunnuksia tai mittausten raakadataa
- muistiinpanoja, ellei `PUBLIC_INCLUDE_NOTES=true` (muistiinpanot voivat sisältää terveysmerkintöjä)

Videoleikkeitä ei jaeta julkisesti, koska taluttaja näkyy kuvassa. Julkiselle sivustolle tarvitaan CORS-asetus, esim. `ALLOWED_ORIGINS=https://hummapp.fi`.

## 32. Kehittäjälle
```bash
pip install -r requirements-dev.txt
pytest            # yksikkö- ja integraatiotestit (videoleikkaustesti vaatii ffmpegin)
ruff check app tests --select F
```
Rakenne: `app/api/` (REST), `app/web/` (Jinja-käyttöliittymä), `app/services/` (yhteinen liiketoimintalogiikka), `app/providers/` (ulkoiset mittauspalvelut), `app/startup.py`, `app/scheduler.py`, `app/migrations.py`.

> Repon juuren `server.ts` on AI Studio -demoympäristön Node-toteutus samasta rajapinnasta. Tuotantoversio on tämä FastAPI-sovellus. Kun muutat rajapintaa, päivitä molemmat tai poista demo-backend.

---
**HummAPP Pilotti** &bull; Valmis hevosseurantaratkaisu Synology NAS -ympäristöön.
