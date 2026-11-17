# HummAPP Android - Kotlin / Jetpack Compose -sovellus

Tämä kansio sisältää valmiin HummAPP Android -mobiilisovelluksen, joka on **esikonfiguroitu keskustelemaan suoraan tämän ympäristön ja/tai Synology NASin kanssa**.

## Sovelluksen näkymät (4 päävälilehteä)

1. **Katsaus & Mittaukset (`DashboardScreen.kt`)**
   - Pikatunnusluvut: Anteron tämän päivän juomamäärä, talli-ilman lämpötila ja kosteus, hevosten lukumäärä ja NFC-tapahtumat.
   - Talli-ilman olosuhdemittaukset: Lämpötila (°C), ilmankosteus (%), ammoniakki NH3 (ppm), hiilidioksidi CO2 (ppm) ja pienhiukkaset PM2.5 (µg/m³) raja-arvopalkkeineen.
   - Anteron 7 vrk juomakehityskuvaaja ja viimeisimmät NFC-tapahtumat.
   - Painike tuoreimpien anturiarvojen synkronointiin (`POST /api/stable-air/sync`).

2. **NFC & Videoleikkuri (`NfcAndVideoScreen.kt` + `VideoReviewScreen.kt`)**
   - Puhelimen oman NFC-lukijan tuki (heksamuunnos + 5 sekunnin kaksoislukemisen esto `NfcManager.kt`:ssä).
   - Sisäänrakennetut pikatestauspainikkeet (Antero, Valo, Tuntematon tagi) myös ilman fyysistä tagia testaamiseen.
   - Reaaliaikainen videoleikkauksen tilan seuranta (`WAITING_FOR_RECORDING` -> `PROCESSING` -> `READY`).
   - Sisäänrakennettu autentikoitu ExoPlayer-videosoitin (`OkHttpDataSource` + Bearer-token) sekä **Hyväksy** / **Hylkää** -toiminnot.

3. **Tarkemmat juoma-automaattitiedot (`WaterDetailScreen.kt`)**
   - Yksityiskohtainen näkymä **vain Antero-hevoselle** (`WATER-METER-ANTERO-01`).
   - Tänään juotu kokonaismäärä, vuorokausikeskiarvo ja viimeisimmän juontikerran telemetria (virtausnopeus L/min, kesto sekunteina ja veden lämpötila °C).
   - 14 päivän juomamäärien pylväsdiagrammi ja yksittäisten juomiskertojen loki.
   - Välitön synkronointipainike (`POST /api/water/sync`).

4. **Hevoset, Muistiinpanot & Liikeanalyysit (`HorseListScreen.kt`, `HorseDetailScreen.kt`, `NotesScreen.kt`, `AnalysisScreen.kt`)**
   - Hevosluettelo yhdistettyine NFC-tageineen, uuden hevosen lisäys ja NFC-tagin yhdistäminen puhelimesta.
   - Hevoskohtaisten muistiinpanojen ja liikeanalyysitulosten selaus ja lisäys.

## Yhteys palvelimeen

Kirjautumisruudussa valitaan palvelin: AI Studio -pilottiympäristö tai paikallinen **Synology NAS** (`http://192.168.1.100:8000`). Osoitteen voi myös kirjoittaa itse (esim. reverse proxyn HTTPS-osoite tai Tailscale-osoite).

Tunnuksia ei ole esitäytetty sovellukseen eikä dokumentoitu tähän. Pääkäyttäjän tunnus ja salasana määritetään NASin `.env`-tiedostossa (`ADMIN_USERNAME`, `ADMIN_PASSWORD`).

## Videoleikkeen ajoitus

- Leike rajataan **5 s ennen ja 5 s jälkeen** NFC-leimauksen (talutuksessa hevonen on kameran edessä enintään noin 10 s).
- Sovellus tallentaa tagin **lukuhetken** heti luvussa ja lähettää sen millisekunnin tarkkuudella. Leike osuu oikeaan kohtaan, vaikka NFC-näkymä avautuisi vasta luvun jälkeen tai verkko olisi hidas.
- **Puhelimen automaattisen ajan pitää olla päällä.** Palvelin tallentaa jokaiseen tapahtumaan puhelimen ja palvelimen kelloeron ja kirjaa varoituksen, jos ero on yli 2 s.
- Ulkoiseen soittimeen avattava video käyttää lyhytikäistä, vain kyseiseen leikkeeseen kelpaavaa latauslinkkiä (`POST /api/video-clips/{id}/download-link`). Kirjautumistokenia ei laiteta URL:iin.
- Pikatestipainikkeet (Antero / Valo / Tuntematon) näkyvät vain debug-versiossa ja toimivat vain, jos NASilla on `SEED_DEMO_DATA=true`.

## Kääntäminen ja asentaminen Android-puhelimeen

1. Pura ladattu `hummapp-android.zip` tietokoneellesi.
2. Avaa purettu kansio **Android Studiossa** (File -> Open).
3. Anna Gradlen ladata riippuvuudet automaattisesti.
4. Liitä Android-puhelin USB:llä (USB-virheenkorjaus päällä) ja paina **Run** (`Shift+F10`), tai luo asennustiedosto valikosta:
   `Build -> Build Bundle(s) / APK(s) -> Build APK(s)`.
5. Asenna APK puhelimeen: `adb install -r app/build/outputs/apk/debug/app-debug.apk`.
