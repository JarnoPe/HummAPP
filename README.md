# HummAPP – hevosten hyvinvoinnin ja tallin seurannan pilotti

HummAPP on avoimen lähdekoodin pilottijärjestelmä, jolla talli kerää hevoskohtaista seurantatietoa arjen työn ohessa. Taluttaja leimaa hevosen NFC-tagin puhelimella, kun hevonen kulkee kameran ohi. Järjestelmä leikkaa tallikameran tallenteesta lyhyen videon juuri siitä hetkestä ja liittää sen hevosen tietoihin. Samaan näkymään kootaan juoma-automaatin kulutustiedot ja talli-ilman olosuhdemittaukset.

Pilotti toteutetaan Kaustisen seutukunnassa (KASE), ja sitä osarahoittaa Euroopan unioni. Julkinen esittelysivu on osoitteessa [hummapp.fi](https://hummapp.fi).

Tämä README on tarkoitettu organisaatioille ja kehittäjille, jotka harkitsevat järjestelmän kokeilua, jatkokehitystä tai osien hyödyntämistä omassa toiminnassaan.

## Mitä järjestelmä tekee

- **NFC-leimaus ja videoleike.** Android-sovellus lukee hevosen NFC-tagin ja lähettää leimauksen tallin palvelimelle. Palvelin etsii kameratallenteen, leikkaa siitä 18 sekunnin leikkeen (5 s ennen ja 13 s jälkeen leimauksen) ja liittää sen hevoseen. Rajaus on säädettävissä.
- **Videoiden tarkastus.** Tallin henkilökunta hyväksyy tai hylkää leikkeet. Hylätyt leikkeet poistuvat automaattisesti säilytysajan jälkeen.
- **Hevosrekisteri.** Hevoset, karsinat, NFC-tagit ja hevoskohtaiset muistiinpanot.
- **Juomaseuranta.** Juoma-automaatin mittaukset ja vuorokausikulutus. Pilotissa seurataan yhtä hevosta.
- **Talli-ilma.** Lämpötila, kosteus, hiilidioksidi, ammoniakki ja pienhiukkaset tavoitearvoineen.
- **Julkinen esittelysivu.** Koottu, vain luku -tilainen näkymä pilotin tilanteesta ilman videoita ja henkilötietoja.

## Arkkitehtuuri

```
  Tallipuhelin (Android, NFC)                      hummapp.fi (GitHub Pages)
            │  HTTPS/HTTP, JWT                              │  vain /api/public/*
            ▼                                               ▼  (valinnainen)
  ┌────────────────────────────────── Synology NAS ──────────────────────────────┐
  │  Docker-kontti: FastAPI + Jinja2-web-UI + APScheduler + FFmpeg                │
  │    ├─ REST-rajapinta  /api/*                                                  │
  │    ├─ Web-käyttöliittymä /web/* (henkilökunta ja ylläpito)                     │
  │    ├─ Ajastetut työt: videoleikkaus, mittausten haku, siivous                  │
  │    └─ SQLite (WAL)                                                            │
  │  Kameratallenteet /camera (vain luku)  →  leikkeet /videos                    │
  └───────────────────────────────────────────────────────────────────────────────┘
            ▲
            │ etäyhteys esim. Tailscalella (ei avoimia portteja)
```

Kaikki data ja videot pysyvät tallin omalla NAS-laitteella. Pilvipalveluja ei tarvita; julkinen sivusto on staattinen ja näyttää joko tilannekuvan tai NASin julkisen rajapinnan koosteen.

### Teknologiat

| Osa | Tekniikka |
| --- | --- |
| Palvelin | Python 3.11, FastAPI, SQLAlchemy, SQLite (WAL), APScheduler, FFmpeg/ffprobe |
| Web-käyttöliittymä | Jinja2-pohjat, kevyt CSS ja JavaScript, mobiilisovitettu |
| Mobiilisovellus | Kotlin, Jetpack Compose, Android NFC API |
| Julkinen sivusto | React 19, Vite, Tailwind CSS, GitHub Pages |
| Ajoympäristö | Docker Compose, Synology Container Manager |
| CI | GitHub Actions: APK-käännös ja sivuston julkaisu |

## Tietosuoja ja tietoturva

Järjestelmä on suunniteltu niin, että tallin sisäinen tieto ei päädy julkisuuteen vahingossa.

- **Ei avointa rekisteröitymistä.** Vain ylläpitäjä luo käyttäjätunnukset web-käyttöliittymässä. Ensimmäinen ylläpitäjä luodaan ympäristömuuttujista ensimmäisellä käynnistyksellä.
- **Roolit.** *Ylläpitäjä* hallitsee käyttäjiä ja järjestelmää, *tallin käyttäjä* leimaa ja käsittelee videoita ja hevostietoja, *katselija* näkee tiedot mutta ei voi muuttaa niitä. Oikeudet tarkistetaan palvelimella sekä rajapinnassa että web-käyttöliittymässä.
- **Istuntojen mitätöinti.** Salasanan vaihto, roolin muutos ja passivointi mitätöivät käyttäjän olemassa olevat tunnisteet (JWT:n versiokenttä). Kadonneen puhelimen pääsy katkeaa passivoimalla käyttäjä.
- **Pakolliset salaisuudet.** Palvelin ei käynnisty ilman satunnaista `SECRET_KEY`-arvoa ja vahvaa ylläpitäjän salasanaa. Esimerkkiarvoja tai tunnettuja oletussalasanoja ei hyväksytä. Salasanat tallennetaan bcrypt-tiivisteinä.
- **Videot eivät ole julkisia.** Leikkeissä näkyy taluttaja, joten ne ovat henkilötietoa. Videoita toistetaan vain kirjautuneille käyttäjille, ja ulkoisen soittimen latauslinkit ovat lyhytikäisiä. Julkinen rajapinta kertoo vain, onko leike olemassa ja mikä sen tila on.
- **Julkinen rajapinta on suppea.** `/api/public/*` palauttaa vain koosteen. Hevosten muistiinpanot jätetään pois oletuksena, koska ne voivat sisältää terveystietoja (`PUBLIC_INCLUDE_NOTES=false`).
- **Kameratallenteet vain luku -tilassa.** Kameran alkuperäiset tallenteet liitetään konttiin vain luku -tilassa.
- **Etäkäyttö ilman avoimia portteja.** Suositeltu tapa on yksityinen verkko (esim. Tailscale), jossa puhelimet näkevät vain palvelimen sovellusportin.

## Hakemistorakenne

```
.
├── hummapp/                 Tuotantojärjestelmä (Synology NAS)
│   ├── app/
│   │   ├── api/             REST-rajapinnat (auth, horses, nfc, videos, water, air, public, system)
│   │   ├── web/             Web-käyttöliittymän reitit ja apufunktiot
│   │   ├── services/        Sovelluslogiikka (videoleikkaus, lähdetallenteen haku, käyttäjät, mittaukset)
│   │   ├── providers/       Mittauslaitteiden liitännät (rajapinta + testitoteutus)
│   │   ├── templates/       Jinja2-pohjat
│   │   ├── static/          Tyylit ja skriptit
│   │   ├── models.py        Tietokantamalli
│   │   ├── migrations.py    Kevyet skeemamuutokset käynnistyksessä
│   │   └── scheduler.py     Ajastetut työt
│   ├── android/             Android-sovellus (Kotlin, Compose)
│   ├── scripts/             backup.sh, restore.sh, smoke_test.sh
│   ├── tests/               pytest-testit
│   ├── Dockerfile
│   ├── compose.yaml
│   └── .env.example         Kaikki asetukset kommentoituina
├── src/, public/, index.html  Julkinen esittelysivu (React + Vite)
├── server.ts                Kehitys- ja esikatselupalvelin (Node), ei tuotantokäyttöön
└── .github/workflows/       android.yml (APK), pages.yml (hummapp.fi)
```

## Käyttöönotto pääpiirteissään

1. **Palvelin.** Kopioi `hummapp/`-kansio NAS-laitteelle, luo `data`, `videos`, `logs` ja `backups` -kansiot (omistaja UID 1000), liitä kameran tallennekansio `compose.yaml`-tiedostossa vain luku -tilassa, täytä `.env` mallin `.env.example` mukaan ja käynnistä `docker compose up -d --build`. Tarkista toiminta: `bash scripts/smoke_test.sh http://localhost:8000`.
2. **Kellot ja kamera.** Leikkeen osuminen oikeaan kohtaan edellyttää, että kamera, NAS ja puhelimet ovat samassa ajassa (NTP). Kameran tiedostonimien aikavyöhyke asetetaan `CAMERA_TIMEZONE`-muuttujalla, ja tallenteen valmistumisen odotusaika sovitetaan kameran tallennepätkän pituuteen.
3. **Käyttäjät ja hevoset.** Kirjaudu web-käyttöliittymään (`http://<nas>:8000/web`), luo henkilökunnalle tunnukset, lisää hevoset ja yhdistä NFC-tagit.
4. **Puhelimet.** Asenna Android-sovellus (GitHub Actions kääntää APK:n), aseta palvelimen osoite ja kirjaudu. Jos tallin verkkoon ei ole langatonta yhteyttä, käytä yksityistä VPN-verkkoa, kuten Tailscalea.
5. **Varmuuskopiot.** Ajasta `scripts/backup.sh` (SQLiten online-varmuuskopio) kerran vuorokaudessa ja sisällytä videokansio NASin omaan varmuuskopiointiin.
6. **Julkinen sivu (valinnainen).** `pages.yml` kääntää ja julkaisee esittelysivun GitHub Pagesiin. Live-dataa varten NASin julkinen rajapinta tarvitsee HTTPS-osoitteen, ja sivuston osoite lisätään `ALLOWED_ORIGINS`-asetukseen.

### Keskeiset asetukset

Täydellinen, kommentoitu luettelo on tiedostossa [`hummapp/.env.example`](hummapp/.env.example).

| Muuttuja | Tarkoitus |
| --- | --- |
| `SECRET_KEY` | Tunnisteiden allekirjoitusavain (pakollinen, `openssl rand -hex 32`) |
| `ADMIN_USERNAME`, `ADMIN_PASSWORD` | Ensimmäinen ylläpitäjä (pakollinen, vähintään 12 merkkiä) |
| `APP_TIMEZONE`, `CAMERA_TIMEZONE` | Raportoinnin ja kameran tiedostonimien aikavyöhykkeet |
| `VIDEO_SECONDS_BEFORE`, `VIDEO_SECONDS_AFTER` | Leikkeen rajaus leimauksen ympäriltä (oletus 5 ja 13 s) |
| `VIDEO_RETRY_INTERVAL_SECONDS`, `VIDEO_MAX_RETRIES` | Kuinka kauan kameratallenteen valmistumista odotetaan |
| `VIDEO_REJECTED_RETENTION_DAYS` | Hylättyjen leikkeiden säilytysaika |
| `ALLOWED_ORIGINS`, `COOKIE_SECURE` | CORS julkiselle sivulle ja evästeen HTTPS-vaatimus |
| `PUBLIC_INCLUDE_NOTES` | Julkaistaanko muistiinpanot julkisessa koosteessa (oletus ei) |
| `WATER_*`, `AIR_*` | Mittauslaitteiden osoitteet, avaimet ja hakuvälit |
| `ENABLE_MOCK_CAMERA_FALLBACK`, `SEED_DEMO_DATA` | Vain testaukseen: testivideo ja esimerkkidata |

## Kehitys ja testaus

```bash
# Palvelin
cd hummapp
pip install -r requirements-dev.txt
pytest                 # yksikkö-, rajapinta- ja web-testit sekä FFmpeg-leikkauksen päästä päähän -testi
ruff check app tests

# Julkinen sivusto
npm ci
npx tsc --noEmit
npx vite build
```

Android-sovellus käännetään Gradlella (`gradle assembleDebug` kansiossa `hummapp/android`) tai GitHub Actionsissa, joka tallentaa debug-APK:n ajon artefaktiksi.

### Mittauslaitteiden liittäminen

Juoma-automaatti ja ilmanlaatuanturit on erotettu `providers/`-kerrokseen. Pilotissa käytetään testitoteutuksia (`*_mock.py`). Oikean laitteen liittäminen tarkoittaa uuden luokan kirjoittamista `water_base.py`- tai `air_base.py`-rajapinnan mukaan; muu järjestelmä ei muutu.

## Tila ja rajoitukset

- Järjestelmä on **pilotti**. Se on testattu yhden tallin ja yhden kameran kokoonpanolla.
- Android-sovellus jaetaan toistaiseksi debug-APK:na, eikä se päivity automaattisesti.
- Juoma- ja ilmanlaatumittausten tuotantoliitännät odottavat laitevalintaa; nykyiset tiedot ovat testidataa.
- Videoleikkaus olettaa, että kamera tallentaa MP4-pätkiä jaettuun kansioon, josta tiedoston alkuaika voidaan päätellä nimestä. Muut nimeämiskäytännöt vaativat muutoksen lähdetallenteen hakuun (`services/video_source_resolver.py`).
- Tietokanta on SQLite, mikä riittää yhden tallin kuormalle. Usean tallin keskitetty käyttö vaatisi palvelinkannan.

## Yhteistyö

Kiinnostuneet tallit, oppilaitokset, tutkijat ja yritykset voivat ottaa yhteyttä Kaustisen seutukuntaan (KASE) hummapp.fi-sivun kautta. Muutosehdotukset ja virheilmoitukset voi jättää tämän repositorion issueina.

Pilottia osarahoittaa Euroopan unioni.
