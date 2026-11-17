# HummAPP 1.1 – muutokset koodin laatuarvion pohjalta

Haara: `korjaukset-koodiarvio` · Pohja: `4ec6f94` · Päivämäärä: 17.11.2026

## Tärkein toiminnallinen muutos: videoleike 10 s (5 s + 5 s)

Talutuksessa hevonen on kameran edessä enintään noin 10 sekuntia, jonka jälkeen kuvaan tulee jo seuraava eläin. Leike on nyt **5 s ennen ja 5 s jälkeen NFC-leimauksen** (aiemmin 10 s + 40 s = 50 s, jolloin samaan leikkeeseen osui useampi hevonen).

- Muutos koskee FastAPI-oletuksia (`VIDEO_SECONDS_BEFORE=5`, `VIDEO_SECONDS_AFTER=5`), `.env.example`-tiedostoa, Node-demoa (`server.ts`), testivideoita, web-UI:n tekstejä, julkista sivua ja Android-sovellusta.
- Lyhyt leike vaatii sekunnin tarkat ajat, joten samalla korjattiin ajoitukseen liittyvät virheet:
  - Kameratiedostojen nimissä olevat ajat tulkitaan kameran aikavyöhykkeessä (`CAMERA_TIMEZONE`). Aiemmin ne tulkittiin UTC:ksi, mikä aiheutti 2–3 tunnin virheen.
  - Android lähettää tagin **lukuhetken** millisekunnin tarkkuudella. Aiemmin aikaleimana oli lähetyshetki, josta sekunnin osat katkaistiin.
  - Puhelimen ja palvelimen kelloero tallennetaan jokaiseen tapahtumaan (`clock_skew_seconds`), ja yli 2 s erosta kirjataan varoitus.

## Arvion löydökset ja niiden tila

### Korkea prioriteetti

| # | Löydös | Tila | Toteutus |
|---|---|---|---|
| 1 | FFmpeg jäädytti palvelimen | ✅ Korjattu | `asyncio.create_subprocess_exec`, kamerahaku ja ffprobe säikeessä (`services/video.py`). Testi varmistaa, ettei event loop pysähdy. |
| 2 | Kameratiedoston täsmäys | ✅ Korjattu | `video_source_resolver.py` uusittu: aikavyöhyke, lähin edeltävä tiedosto, ffprobe-tarkistus keskeneräiselle tallenteelle, tiedostonvaihdon vajaa leike, päiväkansiorajaus (myös Surveillance Stationin `YYYYMMDDAM`). mtime-arvaus poistettu. 8 uutta testiä. |
| 3 | "Tänään" UTC-ajassa | ✅ Korjattu | `app/timeutils.py`: vuorokausirajat Suomen ajassa (kesäaika huomioitu). Käytössä web-UI:ssa, API:ssa, julkisessa näkymässä, `server.ts`:ssä, React-sivulla ja Androidissa. Templatejen kellonajat näytetään paikallisaikana. |
| 4 | Oletustunnukset ja salaisuudet | ✅ Korjattu koodissa | `SECRET_KEY` ja `ADMIN_PASSWORD` ovat pakollisia, eikä esimerkkiarvoja tai julkisesti tunnettuja salasanoja hyväksytä. Androidista ja README:istä poistettu tunnukset. Node-demo vaihtaa vanhan admin-oletussalasanan ja passivoi `tallityontekija`-käyttäjän. WAL-tiedosto, demovideot ja `.pytest_cache` poistettu versionhallinnasta, `.gitignore` päivitetty. **Git-historia on siivottava erikseen** (ks. alla). |
| 5 | Julkinen rajapinta vuoti tietoja | ✅ Korjattu | Uudet `Public*`-skeemat: ei `owner_name`-kenttää, NFC-UID:itä, käyttäjätunnuksia eikä raakadataa. Muistiinpanot vain asetuksella `PUBLIC_INCLUDE_NOTES=true`. `/api/system/status` vaatii admin-roolin. Demon julkinen videostream on oletuksena pois (`PUBLIC_VIDEO_STREAM`). `public-data.json` päivitetty. |
| 6 | Avoin uudelleenohjaus ja web/API-erot | ✅ Korjattu | `services/video_review.py` on yhteinen API:lle ja web-UI:lle. `safe_next()` estää ulkoiset uudelleenohjaukset. Poistettua leikettä ei voi enää hyväksyä. |
| 7 | Backend kahteen kertaan | ⚠️ Osittain | `server.ts`:ään tehty samat korjaukset (leike, julkinen data, JWT, Range, UID-validointi, kelloero), ja se on merkitty demoksi. **Päätös `server.ts`:n poistamisesta tai korvaamisesta proxylla on tekemättä.** |

### Keskitaso

| # | Löydös | Tila |
|---|---|---|
| 1 | `main.py` god file | ✅ Jaettu: `web/routes.py`, `startup.py`, `scheduler.py`, `migrations.py`, `logging_setup.py`. `main.py` on nyt 84 riviä. |
| 2 | Kirjautumistarkistus 17× | ✅ `require_web_user` / `require_web_admin` -riippuvuudet ja yhteinen `user_from_token()` |
| 3 | Antero-haku 7× | ✅ `services/horses.get_drinking_horse()`. Tunnistus on edelleen nimen perusteella. |
| 4 | Päiväkoonti 2× | ✅ `water_service.daily_summary()` (rajattu aikaväli, Suomen aika) |
| 5 | `WaterMeasurement` 3× ja import tiedoston lopussa | ✅ |
| 6 | Talli-ilman duplikaatit | ✅ Duplikaattiesto (anturi + mittausaika), eräcommit, indeksi |
| 7 | N+1-kyselyt | ✅ `selectinload` julkisessa näkymässä, NFC-listauksessa, muistiinpanoissa ja web-sivuilla |
| 8 | Käsin tehty migraatio | ✅ `migrations.py` (idempotentti lista). Alembiciä ei otettu käyttöön. |
| 9 | Demodata tuotannossa | ✅ `SEED_DEMO_DATA=false` oletuksena |
| 10 | Mock-video oletuksena päällä | ✅ Oletus `false`. Testivideot merkitään (`is_mock`, `TESTIVIDEO` web-UI:ssa ja Androidissa). |
| 11 | Virheiden nieleminen | ✅ Lokitus ja `SystemEvent` (`services/system_events.py`) |
| 12 | Hylättyjen videoiden säilytys | ✅ Yöllinen siivous (`VIDEO_REJECTED_RETENTION_DAYS`) |
| 13 | `App.tsx` 1 200 riviä | ❌ Ei pilkottu komponentteihin. Päivitetty vain uuden julkisen rajapinnan mukaiseksi. |
| 14 | UID-normalisointi 3× | ✅ `app/nfc_uid.py` (myös heksavalidointi, virheellinen → 422) |

### Matala prioriteetti

| # | Löydös | Tila |
|---|---|---|
| 1 | Tilat merkkijonoina | ✅ `app/constants.py` (`EventStatus`, `ClipStatus`, `Role`) |
| 2 | Taikanumerot | ✅ Evästeen ikä johdetaan asetuksesta, leikkeen pituus asetuksista. Ilmanlaadun raja-arvoja ei koottu. |
| 3 | Käyttämätön `is_success` | ✅ `NfcRegistration`-dataclass |
| 4 | 30 vrk token ilman mitätöintiä | ❌ Ennallaan |
| 5 | Web-login ei tarkistanut `active`-tilaa | ✅ |
| 6 | CORS `*` + credentials | ✅ Oletuksena pois, `*` ilman credentialeja |
| 7 | CSRF / secure-eväste | ⚠️ `COOKIE_SECURE`-asetus lisätty, CSRF-tokeneita ei |
| 8 | Pydantic v1 `class Config` | ✅ `ConfigDict` / `SettingsConfigDict` |
| 9 | Nimeäminen (`id`, `today_m`, …) | ✅ Muutetuissa tiedostoissa. `package.json`-nimi on nyt `hummapp-demo`. |
| 10 | Harhaanjohtavat kommentit | ✅ Muutetuissa tiedostoissa |
| 11 | Testiriippuvuudet tuotannossa | ✅ `requirements-dev.txt`, pääversiot rajattu (`apscheduler<4` ym.) |
| 12 | Zipit gitissä | ⚠️ Edelleen gitissä, koska demosivu jakaa ne, mutta **koottu uudelleen uudesta koodista** (vanhoissa oli tunnukset). |

### Kuollut koodi
Poistettu `UserCreate`, käyttämättömät importit (ruff: 0 virhettä), `passlib`, `@google/genai`, `motion`, `static/js/app.js` ja juuren `GEMINI_API_KEY`. Aiemmin käyttämättömät asetukset `CAMERA_TIMEZONE`, `VIDEO_REJECTED_RETENTION_DAYS` ja `LOG_FILE` ovat nyt käytössä. Tuotantoproviderien URL- ja avainasetukset on merkitty TODO-kommentilla.

## Korjauksen aikana löytyneet uudet virheet

1. **Web-käyttöliittymään ei voinut kirjautua lainkaan.** `get_web_user` kutsui riippuvuutta `get_token_from_request(request)` suoraan, joten token oli aina FastAPIn `Depends`-olio ja jokainen sivu ohjasi takaisin kirjautumiseen. Vika toistettiin alkuperäisellä koodilla, ja se on nyt korjattu ja testattu (kaikki 7 sivua).
2. **Androidin "avaa ulkoisessa soittimessa" ei toiminut FastAPIn kanssa.** Sovellus laittoi tokenin URL:iin (`?token=`), jota FastAPI ei tue. Tilalle tuli lyhytikäinen, yhteen leikkeeseen rajattu latauslinkki (`POST /api/video-clips/{id}/download-link`).
3. **`npm install` epäonnistui** esbuildin ja Viten peer-riippuvuusristiriidan takia. Korjattu: `esbuild ^0.28`.
4. **Web-UI:n `/web/system` antoi koko `settings`-olion templatelle**, mukaan lukien `SECRET_KEY`. Nyt templatelle annetaan vain näytettävät arvot, ja sivu on vain adminille.
5. **Android-tagin luku käsiteltiin vasta, kun NFC-näkymä oli auki.** Aikaleima otettiin silloin käsittelyhetkestä eikä lukuhetkestä. Korjattu (`NfcManager.lastReadAtMillis`).

## Tarkistukset

- **Python:** 56 testiä läpi (aiemmin 21). Uusina mukana resolverin aikavyöhyke- ja reunatapaukset, vuorokausiraja ja kesäaika, julkisen datan rajaus, admin-oikeudet, latauslinkin rajaus, avoin uudelleenohjaus, web-sivujen renderöinti sekä päästä päähän -testi, jossa oikea FFmpeg leikkaa 10,0 s leikkeen ja event loop pysyy vapaana.
- **Ajossa:** FastAPI käynnistetty uvicornilla (kirjautuminen, web-UI, NFC → leike, evästelataus). Migraatio testattu alkuperäisen version luomalla tietokannalla.
- **Node-demo:** `tsc --noEmit` puhdas, `vite build` onnistuu, ja `server.ts` ajettu ja testattu curlilla (vanhat salasanat hylätään, `?token=` hylätään, virheellinen Range → 416, julkinen data ei vuoda, leike 10,0 s).
- **Android:** Kotlin-tiedostot jäsentyvät virheettä (ktlint), mutta **Gradle-käännöstä ei voitu ajaa** (ei Android SDK:ta tässä ympäristössä). Käännä ja testaa Android Studiossa ennen asennusta.

## Käyttöönotossa huomioitavaa

1. **NAS:** täytä `.env`-tiedostoon `SECRET_KEY` (`openssl rand -hex 32`) ja vähintään 12-merkkinen `ADMIN_PASSWORD`. Ilman niitä kontti ei käynnisty.
2. **Kamera:** tarkista, nimeääkö kamera tiedostot paikallis- vai UTC-ajassa (`CAMERA_TIMEZONE`). Aseta odotusaika (`VIDEO_RETRY_INTERVAL_SECONDS × VIDEO_MAX_RETRIES`) vähintään kameran tallennepätkän pituiseksi, sillä kamera sulkee MP4-tiedoston vasta pätkän lopussa.
3. **Kellot:** NTP kameraan ja NASiin, automaattinen aika tallipuhelimeen.
4. **Anteron NFC-tagi** ei enää yhdisty automaattisesti esimerkki-UID:llä. Yhdistä oikea tagi web-UI:ssa tai käytä testaukseen asetusta `SEED_DEMO_DATA=true`.
5. **AI Studio -demo:** aseta `ADMIN_PASSWORD`-salaisuus. Jos sitä ei ole, demo luo satunnaisen salasanan, joka näkyy vain palvelimen lokissa.
6. **Julkinen sivu:** live-data vaatii `ALLOWED_ORIGINS=https://hummapp.fi`.
7. **Git-historia:** vanhat tunnukset ja WAL-tiedosto (salasanahashit) ovat yhä historiassa. Vaihda pilottiympäristön salasanat ja siivoa historia (`git filter-repo --path data/hummapp-env.db-wal --invert-paths`) tai tee repo uudelleen.
