// Talli-ilman suositusrajat ja tilaluokitus (vihreä = hyvä, keltainen = rajalla, punainen = huono).
//
// Suomen hevosasetus (VNA 321/2025, 12 §) ei anna lukuarvoja. Vihreän alueen rajat tulevat SOURCES-listan
// lähteistä (pääasiassa Saksan maatalousministeriön hevostalliohjeesta). Keltainen = lähellä rajaa tai hieman
// yli, punainen = selvästi yli; nämä marginaalit ovat HummAPPin tulkinta. Muuta rajoja vain tähän tiedostoon.

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
    scaleMin: -10,
    scaleMax: 35,
    bands: [
      { from: -10, to: -5, level: 'bad' },
      { from: -5, to: 5, level: 'warn' },
      { from: 5, to: 25, level: 'good' },
      { from: 25, to: 30, level: 'warn' },
      { from: 30, to: 35, level: 'bad' },
    ],
    guide: 'Hyvä 5–25 °C. Tällä alueella hevonen pitää lämpönsä vaivatta.',
    sources: [1],
  },
  {
    key: 'humidity',
    label: 'Ilmankosteus',
    shortLabel: 'Kosteus',
    unit: '%',
    decimals: 1,
    scaleMin: 30,
    scaleMax: 100,
    bands: [
      { from: 30, to: 50, level: 'bad' },
      { from: 50, to: 60, level: 'warn' },
      { from: 60, to: 80, level: 'good' },
      { from: 80, to: 90, level: 'warn' },
      { from: 90, to: 100, level: 'bad' },
    ],
    guide: 'Suositus 60–80 %.',
    sources: [0],
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
      { from: 0, to: 8, level: 'good' },
      { from: 8, to: 10, level: 'warn' },
      { from: 10, to: 20, level: 'bad' },
    ],
    guide: 'Enintään 10 ppm, ja sekin saa ylittyä vain hetkellisesti.',
    sources: [0],
  },
  {
    key: 'co2',
    label: 'Hiilidioksidi (CO₂)',
    shortLabel: 'CO₂',
    unit: 'ppm',
    decimals: 0,
    scaleMin: 0,
    scaleMax: 3000,
    bands: [
      { from: 0, to: 1000, level: 'good' },
      { from: 1000, to: 1500, level: 'warn' },
      { from: 1500, to: 3000, level: 'bad' },
    ],
    guide: 'Suositus alle 1 000 ppm. Korkea arvo kertoo heikosta ilmanvaihdosta.',
    sources: [0],
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
    guide: 'Alle 15 µg/m³ (WHO:n vuorokausiohjearvo). Hevosille ei ole omaa lukua.',
    sources: [2],
  },
];

/** Pääsääntö: vihreä = suosituksen mukainen. Keltaisen ja punaisen rajat ovat HummAPPin tulkinta. */
export const SOURCES: { title: string; note: string; url: string }[] = [
  {
    title: 'Saksan maatalousministeriö (BMEL): hevostallien arviointiohje',
    note: 'Kosteus, ammoniakki ja hiilidioksidi',
    url: 'https://www.bmel.de/DE/Tier/Tierschutz/Tierschutzgutachten/_texte/TierschutzPferdehaltung.html',
  },
  {
    title: 'Agroscope (Sveitsin maatalouden tutkimuslaitos), 2024',
    note: 'Lämpötila',
    url: 'https://www.agroscope.admin.ch/agroscope/en/home/news/newsroom/2024/08-26_Pferdestallklima.html',
  },
  {
    title: 'WHO:n ilmanlaatuohjeet, 2021',
    note: 'Pienhiukkaset',
    url: 'https://www.who.int/publications/i/item/9789240034228',
  },
];

/** Suomen hevosasetus edellyttää vain, ettei pitoisuuksia ole "haitallisen korkealla", eikä anna lukuja. */
export const FINNISH_LAW = {
  title: 'Valtioneuvoston asetus hevosten hyvinvoinnista 321/2025',
  url: 'https://finlex.fi/api/media/statute/677061/mainPdf/main.pdf',
};

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
