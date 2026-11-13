# HummAPP - Hevosten Hyvinvointi- ja Talliseuranta
### Valmis Synology NAS -pilottijärjestelmä ja Android-sovellus

HummAPP on hevosalan tutkimus- ja hankepilottikäyttöön suunniteltu kevyt, luotettava ja ylläpidettävä seurantajärjestelmä. Järjestelmä kokoaa yhteen talliolosuhteet, hevosten muistiinpanot, riimutagin NFC-tunnistukseen perustuvan automaattisen videoleikkauksen (50s leikkeet valvontakamerasta FFmpegillä), liikeanalyysitulokset sekä ainoana automaattimittauksena **Antero-hevosen juomamäärät**.

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

---

## 1. Järjestelmän tarkoitus
HummAPP kerää, tallentaa ja esittää hevosten hyvinvointiin ja talliolosuhteisiin liittyvää dataa hankepilottia varten:
- **Hevostiedot ja muistiinpanot**: Havainnot, terveysmerkinnät ja toimenpiteet talliympäristössä.
- **NFC-videointitapahtumat**: Kun hevonen talutetaan kuvausalueelle, Android-puhelimella luetaan riimutagi. NAS leikkaa valvontakameran tallenteesta 50 sekunnin leikkeen (10s ennen lukuhetkeä ja 40s lukuhetken jälkeen).
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
│  │  • FFmpeg taustaleikkuri (50s leikkeet)          │  │
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

---

## 10. Ensimmäisen ylläpitäjän luominen
Määritä `.env`-tiedostoon haluamasi pääkäyttäjätunnus ja salasana:
```env
ADMIN_USERNAME=admin
ADMIN_PASSWORD=VaihdaTamaSalasana2026!
```
Sovellus luo tämän käyttäjän automaattisesti ensimmäisellä käynnistyksellä, jos kanta on tyhjä.

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
- Kun sovellus käynnistyy, se varmistaa automaattisesti hevosen `Antero` olemassaolon.
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
Kamerat tallentavat usein videoita leikkeinä (esim. `CAM01_YYYYMMDD_HHMMSS.mp4`).
Tiedostossa `app/services/video_source_resolver.py` on eristetty luokka `SynologyTimestampVideoResolver`.

Jos kamerasi käyttää poikkeavaa tiedostonimimuotoa:
1. Katso esimerkkikoodi `app/services/video_source_resolver.py`.
2. Säädä tarvittaessa säännöllistä lauseketta (regex) vastaamaan kamerasi nimeämistapaa.
3. Testaa leikkausta luomalla NFC-tapahtuma.

---

## 19. Web-käyttöliittymän avaaminen ja käyttö
1. Avaa selaimella: `http://NAS-IP:8000` (tai HTTPS-osoite reverse proxyn kautta).
2. Kirjaudu `.env`-tiedostossa määritetyillä admin-tunnuksilla.
3. Käyttöliittymässä on sivut:
   - **Katsaus** (`/`): Tallin pikanäkymät, Anteron 24h juomakuvaaja, tuoreimmat leikkeet ja ilmanlaatu.
   - **Hevoset** (`/web/horses`): Hevosrekisteri, NFC-kytkennät ja hevoskohtainen sivu muistiinpanoineen.
   - **NFC & Videot** (`/web/nfc-events`): Kaikki leikatut 50s videot, hyväksyntä (`Hyväksy`), hylkäys (`Hylkää`) ja ylläpidon poisto.
   - **Juominen** (`/web/water`): Anteron juomahistoria, vuorokausitilastot ja Chart.js -kuvaaja.
   - **Talli-ilma** (`/web/air`): Lämpötila, kosteus, NH3, CO2 ja hiukkaset.
   - **Järjestelmä** (`/web/system`): Tietokannan WAL-tila, hakemistojen eheys ja hälytysloki.

---

## 20. Android-sovelluksen API-osoitteen määrittäminen
1. Avaa HummAPP puhelimessa.
2. Kirjautumisruudussa syötä **Palvelimen osoite (NAS)**:
   - Lähiverkossa: `http://192.168.1.100:8000`
   - Koko Internetissä (Reverse Proxy / HTTPS): `https://hummapp.oma-talli.synology.me`
   - Tailscale-verkossa: `http://100.x.y.z:8000`
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
Jos tallilla ei ole julkista IP-osoitetta tai et halua avata portteja reitittimeen:
1. Asenna **Tailscale** Synology Package Centeristä.
2. Kirjaudu Tailscaleen ja ota NAS mukaan VPN-verkkoosi.
3. Asenna Tailscale tallipuhelimeen ja omaan tietokoneeseesi.
4. Voit nyt käyttää HummAPPia turvallisesti missä tahansa suoraan NASin Tailscale-osoitteella (esim. `http://100.x.y.z:8000`).

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
Skripti tarkistaa automaattisesti:
- `/api/health` -kunnon
- `/api/system/status` -diagnostiikan
- Kirjautumisen ja JWT-tokenin muodostuksen
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
| **Videoleikkaus epäonnistuu (FAILED)** | Kameran tallennetta ei löydy määritetyssä ajassa. | Tarkista `compose.yaml`:n kamerahakemiston liitos (`/camera:ro`). Jos testaat ilman kameraa, aseta `.env`-tiedostoon `ENABLE_MOCK_CAMERA_FALLBACK=true`. |
| **Permission Denied / Oikeusvirhe data-kansiossa** | Synology DSM:n kansio-oikeudet eivät salli kontin käyttäjän (UID 1000) kirjoitusta. | Aja NASin terminaalissa: `sudo chown -R 1000:1000 data videos logs backups` ja `sudo chmod -R 775 data videos logs backups`. |
| **Database locked -virhe** | Tietokantaa yritetty käyttää ilman WAL-tilaa tai useasta prosessista. | HummAPP käyttää oletuksena `PRAGMA journal_mode=WAL` ja `busy_timeout=5000`. Varmista, ettei mikään ulkoinen ohjelma lukitse `hummapp.db`-tiedostoa samaan aikaan. |
| **Puhelin ei lue NFC-tagia** | Puhelimen NFC-siru on pois päältä tai suojakuori estää signaalin. | Tarkista puhelimen pika-asetuksista, että NFC on päällä. Vie tagi puhelimen yläosan antennialueelle. |
| **Path Traversal estetty** | Käyttäjä tai ulkoinen kutsu yrittänyt viitata videohakemiston ulkopuolelle. | Järjestelmä estää `..`-viittaukset ja sallii vain polut, jotka pysyvät `/videos`-kansiossa. |

---
**HummAPP Pilotti** &bull; Valmis hevosseurantaratkaisu Synology NAS -ympäristöön.
