// Käyttöliittymän tekstit suomeksi ja englanniksi.
// Hevosten kuvaukset, rodut, sijainnit ja muistiinpanot tulevat datasta sellaisinaan (suomeksi).

import type { Level, MetricDef } from './thresholds';

export type Lang = 'fi' | 'en';

let current: Lang = 'fi';
export const setLang = (l: Lang) => {
  current = l;
};
export const getLang = () => current;
export const locale = () => (current === 'en' ? 'en-GB' : 'fi-FI');

const fi = {
  skip: 'Siirry sisältöön',
  langSwitch: 'Kieli',
  homeAria: 'HummAPP – etusivu',
  euAlt: 'Euroopan unionin osarahoittama',
  kaseAlt: 'Kaustisen seutukunta',
  navAria: 'Päävalikko',
  nav: { overview: 'Katsaus', horses: 'Hevoset', water: 'Juominen', environment: 'Talli-ilma' },
  loading: 'Ladataan tietoja',
  loadError: 'Tietoja ei saatu ladattua. Yritä hetken päästä uudelleen.',
  reload: 'Lataa uudelleen',
  updated: 'Päivitetty',
  live: 'Reaaliaikainen',
  refresh: 'Päivitä tiedot',
  noData: 'Ei tietoa',
  levels: { good: 'Hyvä', warn: 'Rajalla', bad: 'Huono' } as Record<Level, string>,

  heroEyebrow: 'Kaustisen seutukunnan hevostallipilotti',
  heroTitle: 'Miten tallin hevoset voivat?',
  heroText:
    'HummAPP kokoaa tallin anturien, juoma-automaatin ja NFC-kuvausten tiedot yhteen. Näet yhdellä silmäyksellä, juovatko hevoset normaalisti ja onko talli-ilma suositusten mukaista.',
  airHeadlineBad: 'Talli-ilmassa on korjattavaa',
  airHeadlineGood: 'Talli-ilma on suositusten mukainen',
  airHeadlineMostly: 'Talli-ilma on pääosin hyvä',
  latestMeasurement: 'Viimeisin mittaus',
  goodOf: (n: number) => `/ ${n} mittaria hyvällä tasolla`,
  avgNow: (now: string) => `vrk:n keskiarvo · nyt ${now}`,
  kpiAria: 'Tunnusluvut',
  kpiDrank: (h: string) => `${h} joi viimeisimpänä vuorokautena`,
  kpiDrankFoot: (sign: string, diff: string, n: number) => `${sign}${diff} l keskiarvoon · ${n} juomiskertaa`,
  noMeasurements: 'Ei mittauksia',
  kpiTemp: 'Tallin lämpötila',
  kpiHorses: 'Seurattavat hevoset',
  kpiNfc: 'NFC-kuvaukset',
  kpiNfcFoot: (s: number) => `Jokaisesta leimauksesta ${s} sekunnin videoleike`,
  airSection: 'Talli-ilma suosituksiin verrattuna',
  airSectionSub: 'Osoitin näyttää viimeisimmän mittauksen. Vihreä = hyvä, oranssi = rajalla, punainen = huono.',
  allMeasurements: 'Kaikki mittaukset',
  noAir: 'Talli-ilman mittauksia ei ole vielä saatavilla.',
  waterSection: (h: string) => `${h}n juominen`,
  waterSectionSub: (n: number) => `Juoma-automaatin mittaama vesimäärä vuorokaudessa, ${n} viimeisintä vuorokautta`,
  waterLink: 'Juomaseuranta',
  horses: 'Hevoset',
  all: 'Kaikki',
  noHorses: 'Pilottiin ei ole vielä lisätty hevosia.',

  chartEmpty: 'Juomamittauksia ei ole vielä kirjattu.',
  chartAvg: 'ka',
  chartBarAria: (day: string, l: string, n: number) => `${day}: ${l} litraa, ${n} juomiskertaa`,
  chartTimes: (n: number) => `${n} kertaa`,
  chartLegendDay: 'Litraa vuorokaudessa',
  chartLegendLatest: 'Viimeisin vuorokausi',
  chartLegendAvg: 'Keskiarvo',
  dayShort: (d: number) => `${d}.`,
  chartListAria: 'Juomamäärä vuorokausittain. Siirry päivästä toiseen nuolinäppäimillä.',
  chartShowTable: 'Näytä taulukkona',
  chartHideTable: 'Piilota taulukko',
  colDay: 'Päivä',
  colLitres: 'Litraa',
  colDrinks: 'Juomiskertoja',

  avgLabel: (n: number) => `Vuorokauden keskiarvo (${n} ${n === 1 ? 'mittaus' : 'mittausta'})`,
  latestLabel: 'Viimeisin mittaus',
  avgPartial: 'Mittauksia on alle vuorokauden ajalta, joten keskiarvo on suuntaa antava.',

  sourcesAria: 'Suositusrajojen lähteet',
  sourcesTitle: 'Mistä rajat tulevat?',
  sourcesLawBefore: 'Suomen',
  sourcesLawLink: 'hevosasetus',
  sourcesLawAfter:
    'ei anna lukuarvoja. Vihreä noudattaa lähteiden suositusta; keltaisen ja punaisen rajat ovat HummAPPin tulkinta.',

  horsesIntro: 'Pilotissa seurattavat hevoset, niiden liikeanalyysit ja tallin kirjaamat muistiinpanot.',
  searchLabel: 'Hae hevosta',
  searchPlaceholder: 'Nimi, rotu tai karsina',
  noSearchResults: (q: string) => `Haulla “${q}” ei löytynyt hevosia.`,
  clearSearch: 'Tyhjennä haku',
  allHorses: 'Kaikki hevoset',
  pickHorse: 'Valitse hevonen listasta.',
  born: (y: number) => `s. ${y}`,
  factBreed: 'Rotu',
  factBirth: 'Syntymävuosi',
  factStall: 'Karsina',
  factNfc: 'NFC-riimutunniste',
  inUse: 'Käytössä',
  notInUse: 'Ei käytössä',
  drinkerTracks: 'Juoma-automaatti seuraa juomista',
  analyses: 'Liikeanalyysit',
  noAnalyses: 'Hevoselle ei ole vielä tehty liikeanalyysiä.',
  notes: 'Muistiinpanot',
  noNotes: 'Ei julkisia muistiinpanoja. Talli kirjaa muistiinpanot omalla HummAPP-sovelluksellaan.',
  stableTeam: 'Tallitiimi',

  waterTitle: (h: string) => `${h}n juominen`,
  waterIntro: (h: string) => `Juoma-automaatti mittaa jokaisen juomiskerran. Pilotissa automaatti on käytössä hevosella ${h}.`,
  statLatest: 'Viimeisin vuorokausi',
  statAvg: 'Keskiarvo',
  statMax: 'Enimmillään',
  statMin: 'Vähimmillään',
  waterPerDay: 'Vesimäärä vuorokaudessa',
  singleDrinks: 'Yksittäiset juomiskerrat',
  colTime: 'Aika',
  colAmount: 'Määrä',
  noDrinks: 'Ei kirjattuja juomiskertoja.',

  envTitle: 'Talli-ilma ja kuvaukset',
  envIntro:
    'Anturit mittaavat lämpötilaa, kosteutta, ammoniakkia, hiilidioksidia ja pienhiukkasia. Arvoja verrataan hevostallien suositusrajoihin.',
  byLocation: 'Mittaukset sijainneittain',
  byLocationSub:
    'Kuvake ja väri kertovat, onko arvo suositusrajojen sisällä. Pienhiukkasia ei luokitella yksittäisistä mittauksista, koska niiden ohjearvo on vuorokauden keskiarvo.',
  colLocation: 'Sijainti',
  sensor: 'Anturi',
  limits: 'Suositusrajat',
  limitsSub: 'Vihreä = suosituksen mukainen, oranssi = lähellä rajaa tai hieman yli, punainen = selvästi yli.',
  colMetric: 'Mittari',
  dailyAvg: 'vuorokauden keskiarvo',
  or: ' tai ',
  under: 'alle',
  over: 'yli',
  nfcTitle: 'NFC-kuvaukset',
  nfcSub: (all: number, b: number, a: number) =>
    `Kun hevonen leimataan kuvausalueella, kamerasta tallentuu ${all} sekunnin leike (${b} s ennen ja ${a} s jälkeen). Leikkeet tarkastetaan tallin sovelluksessa.`,
  colHorse: 'Hevonen',
  colArea: 'Kuvausalue',
  colClip: 'Leikkeen tila',
  colActions: 'Toiminnot',
  noNfc: 'Kuvauksia ei ole vielä tehty.',
  unknown: 'Tuntematon',
  watchClip: 'Katso leike',
  closeVideo: 'Sulje video',
  status: {
    APPROVED: 'Hyväksytty',
    READY: 'Valmis tarkastettavaksi',
    PROCESSING: 'Käsittelyssä',
    REJECTED: 'Hylätty',
    ERROR: 'Virhe',
  },

  footProject: 'Hanke',
  footText:
    'HummAPP on osa KP AlkIoT -hanketta, joka parantaa hevosten hyvinvointia Keski-Pohjanmaalla. Hankkeessa kehitetään ja pilotoidaan IoT-ratkaisuja, joilla hevosten hyvinvointia voi seurata reaaliajassa.',
  footReadMore: 'Lue hankekuvaus',
  footFacts: [
    { t: 'Toteuttajat', d: 'Kaustisen seutukunta ja Kpedu (EIP-yhteistyöhanke)' },
    { t: 'Rahoittaja', d: 'Pohjanmaan ELY-keskus, Euroopan maaseuturahasto' },
    { t: 'Toteutusaika', d: '1.1.2025–30.6.2027' },
    { t: 'Kohderyhmä', d: 'Keski-Pohjanmaan hevostilat, eläinlääkärit ja ohjelmistoyritykset' },
  ],
  footContacts: 'Yhteystiedot',
  contacts: [
    { n: 'Jarno Peltola', r: 'Projektipäällikkö, Kaustisen seutukunta', e: 'jarno.peltola@kaustisenseutukunta.fi' },
    { n: 'Marika Kuutti', r: 'Projektikoordinaattori, Kpedu', e: 'marika.kuutti@kpedu.fi' },
  ],

  metrics: {
    temperature: { label: 'Lämpötila', short: 'Lämpö', guide: 'Hyvä 5–25 °C. Tällä alueella hevonen pitää lämpönsä vaivatta.' },
    humidity: { label: 'Ilmankosteus', short: 'Kosteus', guide: 'Suositus 60–80 %.' },
    ammonia: { label: 'Ammoniakki (NH₃)', short: 'NH₃', guide: 'Enintään 10 ppm, ja sekin saa ylittyä vain hetkellisesti.' },
    co2: {
      label: 'Hiilidioksidi (CO₂)',
      short: 'CO₂',
      guide: 'Suositus alle 1 000 ppm. Korkea arvo kertoo heikosta ilmanvaihdosta.',
    },
    particulate_matter: {
      label: 'Pienhiukkaset (PM2.5)',
      short: 'PM2.5',
      guide: 'Ohjearvo alle 15 µg/m³ (WHO). Hevosille ei ole omaa lukua.',
    },
  } as Record<MetricDef['key'], { label: string; short: string; guide: string }>,
  sources: [
    { title: 'Saksan maatalousministeriö (BMEL): hevostallien arviointiohje', note: 'Kosteus, ammoniakki ja hiilidioksidi' },
    { title: 'Agroscope (Sveitsin maatalouden tutkimuslaitos), 2024', note: 'Lämpötila' },
    { title: 'WHO:n ilmanlaatuohjeet, 2021', note: 'Pienhiukkaset' },
  ],

  docTitle: 'HummAPP · hummapp.fi | Kaustisen seutukunnan hevosten hyvinvointipilotti',
  docDescription:
    'Euroopan unionin osarahoittama Kaustisen seutukunnan HummAPP-pilotti: hevosten juominen, talli-ilman laatu suositusrajoihin verrattuna ja NFC-kuvaukset yhdellä sivulla.',
};

export type Strings = typeof fi;

const en: Strings = {
  skip: 'Skip to content',
  langSwitch: 'Language',
  homeAria: 'HummAPP – home',
  euAlt: 'Co-funded by the European Union',
  kaseAlt: 'Kaustinen sub-region',
  navAria: 'Main menu',
  nav: { overview: 'Overview', horses: 'Horses', water: 'Drinking', environment: 'Stable air' },
  loading: 'Loading data',
  loadError: 'The data could not be loaded. Please try again in a moment.',
  reload: 'Reload',
  updated: 'Updated',
  live: 'Live',
  refresh: 'Refresh data',
  noData: 'No data',
  levels: { good: 'Good', warn: 'Borderline', bad: 'Poor' },

  heroEyebrow: 'Horse stable pilot in the Kaustinen sub-region',
  heroTitle: 'How are the horses in the stable doing?',
  heroText:
    'HummAPP brings together data from the stable’s sensors, the automatic drinker and NFC recordings. At a glance you can see whether the horses are drinking normally and whether the stable air meets the recommendations.',
  airHeadlineBad: 'The stable air needs attention',
  airHeadlineGood: 'The stable air meets the recommendations',
  airHeadlineMostly: 'The stable air is mostly good',
  latestMeasurement: 'Latest measurement',
  goodOf: (n: number) => `/ ${n} indicators at a good level`,
  avgNow: (now: string) => `24 h average · now ${now}`,
  kpiAria: 'Key figures',
  kpiDrank: (h: string) => `Water drunk by ${h} on the latest day`,
  kpiDrankFoot: (sign: string, diff: string, n: number) => `${sign}${diff} l vs. average · ${n} drinks`,
  noMeasurements: 'No measurements',
  kpiTemp: 'Stable temperature',
  kpiHorses: 'Horses monitored',
  kpiNfc: 'NFC recordings',
  kpiNfcFoot: (s: number) => `Every tag scan saves a video clip of ${s} seconds`,
  airSection: 'Stable air compared with recommendations',
  airSectionSub: 'The marker shows the latest measurement. Green = good, orange = borderline, red = poor.',
  allMeasurements: 'All measurements',
  noAir: 'No stable air measurements are available yet.',
  waterSection: (h: string) => `${h}’s drinking`,
  waterSectionSub: (n: number) => `Daily water intake measured by the automatic drinker, last ${n} days`,
  waterLink: 'Drinking data',
  horses: 'Horses',
  all: 'All',
  noHorses: 'No horses have been added to the pilot yet.',

  chartEmpty: 'No drinking measurements have been recorded yet.',
  chartAvg: 'avg',
  chartBarAria: (day: string, l: string, n: number) => `${day}: ${l} litres, ${n} drinks`,
  chartTimes: (n: number) => `${n} drinks`,
  chartLegendDay: 'Litres per day',
  chartLegendLatest: 'Latest day',
  chartLegendAvg: 'Average',
  dayShort: (d: number) => `${d}`,
  chartListAria: 'Daily water intake. Use the arrow keys to move between days.',
  chartShowTable: 'Show as table',
  chartHideTable: 'Hide table',
  colDay: 'Day',
  colLitres: 'Litres',
  colDrinks: 'Drinks',

  avgLabel: (n: number) => `24-hour average (${n} ${n === 1 ? 'measurement' : 'measurements'})`,
  latestLabel: 'Latest measurement',
  avgPartial: 'The measurements cover less than 24 hours, so the average is indicative.',

  sourcesAria: 'Sources for the recommended limits',
  sourcesTitle: 'Where do the limits come from?',
  sourcesLawBefore: 'The Finnish',
  sourcesLawLink: 'Horse Welfare Decree',
  sourcesLawAfter:
    'gives no numerical values. Green follows the sources’ recommendations; the orange and red limits are HummAPP’s interpretation.',

  horsesIntro: 'The horses monitored in the pilot, their movement analyses and the notes recorded by the stable.',
  searchLabel: 'Search horses',
  searchPlaceholder: 'Name, breed or stall',
  noSearchResults: (q: string) => `No horses found for “${q}”.`,
  clearSearch: 'Clear search',
  allHorses: 'All horses',
  pickHorse: 'Select a horse from the list.',
  born: (y: number) => `b. ${y}`,
  factBreed: 'Breed',
  factBirth: 'Year of birth',
  factStall: 'Stall',
  factNfc: 'NFC halter tag',
  inUse: 'In use',
  notInUse: 'Not in use',
  drinkerTracks: 'Drinking is tracked by the automatic drinker',
  analyses: 'Movement analyses',
  noAnalyses: 'No movement analysis has been done for this horse yet.',
  notes: 'Notes',
  noNotes: 'No public notes. The stable records notes in its own HummAPP app.',
  stableTeam: 'Stable team',

  waterTitle: (h: string) => `${h}’s drinking`,
  waterIntro: (h: string) => `The automatic drinker measures every drink. In the pilot, the drinker is used by ${h}.`,
  statLatest: 'Latest day',
  statAvg: 'Average',
  statMax: 'Highest',
  statMin: 'Lowest',
  waterPerDay: 'Water intake per day',
  singleDrinks: 'Individual drinks',
  colTime: 'Time',
  colAmount: 'Amount',
  noDrinks: 'No drinks recorded.',

  envTitle: 'Stable air and recordings',
  envIntro:
    'Sensors measure temperature, humidity, ammonia, carbon dioxide and fine particles. The values are compared with recommended limits for horse stables.',
  byLocation: 'Measurements by location',
  byLocationSub:
    'The icon and colour show whether a value is within the recommended limits. Fine particles are not rated from single measurements, because their guideline is a 24-hour average.',
  colLocation: 'Location',
  sensor: 'Sensor',
  limits: 'Recommended limits',
  limitsSub: 'Green = meets the recommendation, orange = close to the limit or slightly over, red = clearly over.',
  colMetric: 'Indicator',
  dailyAvg: '24-hour average',
  or: ' or ',
  under: 'under',
  over: 'over',
  nfcTitle: 'NFC recordings',
  nfcSub: (all: number, b: number, a: number) =>
    `When a horse’s tag is scanned in the recording area, the camera saves a clip of ${all} seconds (${b} s before and ${a} s after). Clips are reviewed in the stable’s app.`,
  colHorse: 'Horse',
  colArea: 'Recording area',
  colClip: 'Clip status',
  colActions: 'Actions',
  noNfc: 'No recordings yet.',
  unknown: 'Unknown',
  watchClip: 'Watch clip',
  closeVideo: 'Close video',
  status: {
    APPROVED: 'Approved',
    READY: 'Ready for review',
    PROCESSING: 'Processing',
    REJECTED: 'Rejected',
    ERROR: 'Error',
  },

  footProject: 'Project',
  footText:
    'HummAPP is part of the KP AlkIoT project, which improves the welfare of horses in Central Ostrobothnia. The project develops and pilots IoT solutions for monitoring horse welfare in real time.',
  footReadMore: 'Read the project description (in Finnish)',
  footFacts: [
    { t: 'Implemented by', d: 'Kaustinen sub-region and Kpedu (EIP cooperation project)' },
    { t: 'Funded by', d: 'ELY Centre for Ostrobothnia, European Agricultural Fund for Rural Development' },
    { t: 'Duration', d: '1 Jan 2025 – 30 Jun 2027' },
    { t: 'Target group', d: 'Horse farms, veterinarians and software companies in Central Ostrobothnia' },
  ],
  footContacts: 'Contacts',
  contacts: [
    { n: 'Jarno Peltola', r: 'Project Manager, Kaustinen sub-region', e: 'jarno.peltola@kaustisenseutukunta.fi' },
    { n: 'Marika Kuutti', r: 'Project Coordinator, Kpedu', e: 'marika.kuutti@kpedu.fi' },
  ],

  metrics: {
    temperature: { label: 'Temperature', short: 'Temp.', guide: 'Good 5–25 °C. In this range a horse keeps warm without effort.' },
    humidity: { label: 'Humidity', short: 'Humidity', guide: 'Recommended 60–80 %.' },
    ammonia: { label: 'Ammonia (NH₃)', short: 'NH₃', guide: 'At most 10 ppm, and even that may only be exceeded briefly.' },
    co2: {
      label: 'Carbon dioxide (CO₂)',
      short: 'CO₂',
      guide: 'Recommended under 1,000 ppm. A high value indicates poor ventilation.',
    },
    particulate_matter: {
      label: 'Fine particles (PM2.5)',
      short: 'PM2.5',
      guide: 'Guideline under 15 µg/m³ (WHO). There is no separate value for horses.',
    },
  },
  sources: [
    {
      title: 'German Federal Ministry of Agriculture (BMEL): guidelines for assessing horse husbandry',
      note: 'Humidity, ammonia and carbon dioxide',
    },
    { title: 'Agroscope (Swiss agricultural research centre), 2024', note: 'Temperature' },
    { title: 'WHO Global Air Quality Guidelines, 2021', note: 'Fine particles' },
  ],

  docTitle: 'HummAPP · hummapp.fi | Horse welfare pilot in the Kaustinen sub-region',
  docDescription:
    'HummAPP pilot in the Kaustinen sub-region, co-funded by the European Union: horses’ drinking, stable air quality compared with recommended limits and NFC recordings on one page.',
};

const STRINGS: Record<Lang, Strings> = { fi, en };

/** Nykyisen kielen tekstit */
export const t = (): Strings => STRINGS[current];

/** Mittarin nimi ja ohje nykyisellä kielellä */
export const metricText = (def: MetricDef) => STRINGS[current].metrics[def.key];
