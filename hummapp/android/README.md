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

## Yhteys tähän ympäristöön

Sovelluksessa on esiasetettuna tämän pilottiympäristön osoite:
`https://ais-pre-jjufdm4idfqg3xxnq6pytl-1003724038923.europe-west2.run.app`

Kirjautumistiedot:
- Käyttäjätunnus: `admin`
- Salasana: `Tallipaallikko2026!`

Voit vaihtaa kirjautumisruudussa yhdellä napautuksella myös paikalliseen **Synology NAS** -osoitteeseen (`http://192.168.1.100:8000`).

## Kääntäminen ja asentaminen Android-puhelimeen

1. Pura ladattu `hummapp-android.zip` tietokoneellesi.
2. Avaa purettu kansio **Android Studiossa** (File -> Open).
3. Anna Gradlen ladata riippuvuudet automaattisesti.
4. Liitä Android-puhelin USB:llä (USB-virheenkorjaus päällä) ja paina **Run** (`Shift+F10`), tai luo asennustiedosto valikosta:
   `Build -> Build Bundle(s) / APK(s) -> Build APK(s)`.
5. Asenna APK puhelimeen: `adb install -r app/build/outputs/apk/debug/app-debug.apk`.
