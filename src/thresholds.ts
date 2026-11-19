// Talli-ilman suositusrajat ja tilaluokitus (vihreä = hyvä, keltainen = rajalla, punainen = huono).
//
// Hevosten hyvinvointiasetus (VNA 321/2025, 12 §) ei anna numeerisia raja-arvoja, vaan edellyttää,
// ettei kosteus, ammoniakki, hiilidioksidi tai pöly nouse "haitallisen korkealle". Rajat on koottu
// alla mainituista lähteistä; muuta niitä vain tähän tiedostoon, niin sivu päivittyy kaikkialla.

export type Level = 'good' | 'warn' | 'bad';

export interface Band {
  from: number;
  to: number;
  level: Level;
}

export interface MetricDef {
  key: 'temperature' | 'humidity' | 'ammonia' | 'co2' | 'particulate_matter';
  label: string;
  shortLabel: string;
  unit: string;
  decimals: number;
  scaleMin: number;
  scaleMax: number;
  bands: Band[];
  /** Lyhyt selitys suosituksesta, näytetään mittarin alla */
  guide: string;
  /** Lähteet raja-arvoille (indeksit SOURCES-listaan) */
  sources: number[];
}

export const METRICS: MetricDef[] = [
  {
    key: 'temperature',
    label: 'Lämpötila',
    shortLabel: 'Lämpö',
    unit: '°C',
    decimals: 1,
    scaleMin: -5,
    scaleMax: 30,
    bands: [
      { from: -5, to: 0, level: 'bad' },
      { from: 0, to: 8, level: 'warn' },
      { from: 8, to: 12, level: 'good' },
      { from: 12, to: 24, level: 'warn' },
      { from: 24, to: 30, level: 'bad' },
    ],
    guide: 'Optimi 8–12 °C. Hevonen sietää viileää hyvin, kuumaa huonommin.',
    sources: [0, 2],
  },
  {
    key: 'humidity',
    label: 'Ilmankosteus',
    shortLabel: 'Kosteus',
    unit: '%',
    decimals: 1,
    scaleMin: 20,
    scaleMax: 100,
    bands: [
      { from: 20, to: 40, level: 'bad' },
      { from: 40, to: 50, level: 'warn' },
      { from: 50, to: 65, level: 'good' },
      { from: 65, to: 80, level: 'warn' },
      { from: 80, to: 100, level: 'bad' },
    ],
    guide: 'Optimi 50–65 %. Kostea ilma kuormittaa hengitysteitä.',
    sources: [0, 1],
  },
  {
    key: 'ammonia',
    label: 'Ammoniakki (NH₃)',
    shortLabel: 'NH₃',
    unit: 'ppm',
    decimals: 1,
    scaleMin: 0,
    scaleMax: 20,
    bands: [
      { from: 0, to: 5, level: 'good' },
      { from: 5, to: 10, level: 'warn' },
      { from: 10, to: 20, level: 'bad' },
    ],
    guide: 'Alle 5 ppm hyvä. Yli 10 ppm on haitallista hevoselle.',
    sources: [3, 4],
  },
  {
    key: 'co2',
    label: 'Hiilidioksidi (CO₂)',
    shortLabel: 'CO₂',
    unit: 'ppm',
    decimals: 0,
    scaleMin: 0,
    scaleMax: 4000,
    bands: [
      { from: 0, to: 1500, level: 'good' },
      { from: 1500, to: 3000, level: 'warn' },
      { from: 3000, to: 4000, level: 'bad' },
    ],
    guide: 'Alle 1 500 ppm hyvä. Eläinsuojan ohjearvo on 3 000 ppm.',
    sources: [4],
  },
  {
    key: 'particulate_matter',
    label: 'Pienhiukkaset (PM2.5)',
    shortLabel: 'PM2.5',
    unit: 'µg/m³',
    decimals: 1,
    scaleMin: 0,
    scaleMax: 60,
    bands: [
      { from: 0, to: 15, level: 'good' },
      { from: 15, to: 30, level: 'warn' },
      { from: 30, to: 60, level: 'bad' },
    ],
    guide: 'Alle 15 µg/m³ (WHO:n vuorokausiohjearvo). Yli 30 on huono.',
    sources: [5],
  },
];

export const SOURCES: { title: string; url: string }[] = [
  { title: 'Nokian kaupunki: Hevostalliohje (2017)', url: 'https://www.nokiankaupunki.fi/wp-content/uploads/2017/11/Hevostalliohje-2017.pdf' },
  { title: 'Animals 15/22 (2025): The Indoor Environment at the University Equestrian Facility', url: 'https://www.mdpi.com/2076-2615/15/22/3322' },
  { title: 'Penn State Extension: Horse Stable Ventilation', url: 'https://extension.psu.edu/horse-stable-ventilation' },
  { title: 'Kentucky Equine Research: Clean, airy stalls', url: 'https://ker.com/?p=10911' },
  { title: 'Suomen maataloustieteellisen seuran tiedote 19: eläinsuojan ohjearvot (NH₃ 10 ppm, CO₂ 3 000 ppm)', url: 'https://journal.fi/smst/article/download/77089/38232/108512' },
  { title: 'WHO:n ilmanlaatuohjeet 2021 (PM2.5 vuorokausi 15 µg/m³)', url: 'https://www.iqair.com/newsroom/2021-who-air-quality-guidelines' },
  { title: 'Valtioneuvoston asetus hevosten hyvinvoinnista 321/2025, 12 §', url: 'https://finlex.fi/api/media/statute/677061/mainPdf/main.pdf' },
];

export function levelFor(def: MetricDef, value: number | null | undefined): Level | null {
  if (value === null || value === undefined || Number.isNaN(value)) return null;
  for (const b of def.bands) {
    if (value >= b.from && value < b.to) return b.level;
  }
  // Asteikon ulkopuolella: käytetään lähimmän reunan tasoa
  return value < def.bands[0].from ? def.bands[0].level : def.bands[def.bands.length - 1].level;
}

export const LEVEL_META: Record<Level, { label: string; mark: string; text: string; tint: string }> = {
  // KASE-ohjeiston värit: vihreä #00A34D, oranssi #F89628, tiilenpunainen #A1342C
  good: { label: 'Hyvä', mark: '#00A34D', text: '#006B33', tint: '#E6F6EE' },
  warn: { label: 'Rajalla', mark: '#F89628', text: '#8A4B00', tint: '#FEF1E2' },
  bad: { label: 'Huono', mark: '#A1342C', text: '#A1342C', tint: '#F8E7E5' },
};
