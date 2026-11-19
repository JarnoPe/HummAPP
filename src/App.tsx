import React, { useEffect, useState, useCallback, useMemo, useRef } from 'react';
import {
  Droplet,
  Thermometer,
  Video,
  Search,
  RefreshCw,
  Clock,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  ChevronRight,
  ArrowLeft,
  ArrowRight,
  Users,
  Info,
  Mail,
  ExternalLink,
} from 'lucide-react';
import { METRICS, SOURCES, FINNISH_LAW, LEVEL_META, levelFor, type Level, type MetricDef } from './thresholds';

declare global {
  interface Window {
    HUMMAPP_PUBLIC_CONFIG?: {
      apiBaseUrl?: string;
      domainName?: string;
    };
  }
}

interface HorseNote {
  id: number;
  horse_id: number;
  content: string;
  created_at: string;
}

interface MovementAnalysis {
  id: number;
  horse_id: number;
  analysis_method: string;
  analysis_timestamp: string;
  summary: string;
  status: string;
}

interface PublicHorse {
  id: number;
  name: string;
  breed: string | null;
  birth_year: number | null;
  stall_box: string | null;
  description: string | null;
  created_at: string;
  has_nfc_tag: boolean;
  notes: HorseNote[];
  analyses: MovementAnalysis[];
}

interface WaterDailySummary {
  date: string;
  total_liters: number;
  measurement_count: number;
}

interface WaterMeasurement {
  id: number;
  measured_at: string;
  liters: number;
}

interface StableAirMeasurement {
  id: number;
  sensor_id?: string;
  location: string | null;
  measured_at: string;
  temperature: number | null;
  humidity: number | null;
  ammonia: number | null;
  co2: number | null;
  particulate_matter: number | null;
}

interface NfcEventItem {
  id: number;
  horse_id: number | null;
  horse_name: string | null;
  phone_timestamp: string;
  location: string | null;
  status: string;
  video_clip_id: number | null;
  video_clip_status: string | null;
}

interface PublicOverview {
  read_only: boolean;
  generated_at: string;
  drinking_horse_name: string;
  clip_seconds_before?: number;
  clip_seconds_after?: number;
  public_video_enabled?: boolean;
  horses: PublicHorse[];
  water_daily: WaterDailySummary[];
  water_measurements: WaterMeasurement[];
  air_readings: StableAirMeasurement[];
  nfc_events: NfcEventItem[];
}

type PublicTab = 'overview' | 'horses' | 'water' | 'environment';

interface Route {
  tab: PublicTab;
  horseId: number | null;
}

// --- Reititys: jokaisella näkymällä on oma osoite (#/hevoset/2 jne.), joten linkit ja takaisin-nappi toimivat
const TAB_PATHS: Record<PublicTab, string> = {
  overview: '#/',
  horses: '#/hevoset',
  water: '#/juoma',
  environment: '#/talli-ilma',
};

const NAV_ITEMS: { tab: PublicTab; label: string }[] = [
  { tab: 'overview', label: 'Katsaus' },
  { tab: 'horses', label: 'Hevoset' },
  { tab: 'water', label: 'Juominen' },
  { tab: 'environment', label: 'Talli-ilma' },
];

function parseRoute(hash: string): Route {
  const parts = hash.replace(/^#\/?/, '').split('/').filter(Boolean);
  switch (parts[0]) {
    case 'hevoset': {
      const id = parts[1] ? Number(parts[1]) : NaN;
      return { tab: 'horses', horseId: Number.isFinite(id) ? id : null };
    }
    case 'juoma':
      return { tab: 'water', horseId: null };
    case 'talli-ilma':
      return { tab: 'environment', horseId: null };
    default:
      return { tab: 'overview', horseId: null };
  }
}

function useHashRoute(): Route {
  const [route, setRoute] = useState<Route>(() => parseRoute(window.location.hash));
  useEffect(() => {
    const onChange = () => {
      setRoute(parseRoute(window.location.hash));
      window.scrollTo(0, 0);
    };
    window.addEventListener('hashchange', onChange);
    return () => window.removeEventListener('hashchange', onChange);
  }, []);
  return route;
}

// --- Muotoilu
const LOCAL_TIMEZONE = 'Europe/Helsinki';
const localTimestampFormat = new Intl.DateTimeFormat('fi-FI', {
  timeZone: LOCAL_TIMEZONE,
  day: 'numeric',
  month: 'numeric',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
});
const dayLabelFormat = new Intl.DateTimeFormat('fi-FI', { weekday: 'short', day: 'numeric', month: 'numeric', timeZone: 'UTC' });
const numberFormat = (decimals: number) =>
  new Intl.NumberFormat('fi-FI', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });

// Palvelin palauttaa UTC-ajat; aikavyöhyketön ISO-merkkijono tulkitaan UTC:ksi.
function parseUtc(iso: string): Date {
  return new Date(/[zZ]|[+-]\d{2}:\d{2}$/.test(iso) ? iso : `${iso}Z`);
}

function formatLocalTimestamp(iso: string | null | undefined): string {
  if (!iso) return '–';
  const date = parseUtc(iso);
  return Number.isNaN(date.getTime()) ? '–' : localTimestampFormat.format(date);
}

function formatDay(dateKey: string): string {
  const d = new Date(`${dateKey}T12:00:00Z`);
  return Number.isNaN(d.getTime()) ? dateKey : dayLabelFormat.format(d);
}

function fmt(value: number | null | undefined, decimals: number): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '–';
  return numberFormat(decimals).format(value);
}

function statusLabelFi(status: string): { label: string; level: Level | 'neutral' } {
  switch (status) {
    case 'APPROVED':
      return { label: 'Hyväksytty', level: 'good' };
    case 'READY':
      return { label: 'Valmis tarkastettavaksi', level: 'neutral' };
    case 'PROCESSING':
    case 'WAITING_FOR_RECORDING':
      return { label: 'Käsittelyssä', level: 'warn' };
    case 'REJECTED':
      return { label: 'Hylätty', level: 'neutral' };
    default:
      return { label: 'Virhe', level: 'bad' };
  }
}

const CARD = 'relative bg-white border border-[#E3E8EF] rounded-2xl shadow-[0_1px_2px_rgba(16,24,40,0.04)]';
const LINK = 'text-[#C60651] font-medium hover:underline underline-offset-4';

export default function App() {
  const route = useHashRoute();
  const activeTab = route.tab;
  const [data, setData] = useState<PublicOverview | null>(null);
  const [dataSourceMode, setDataSourceMode] = useState<'live' | 'snapshot'>('snapshot');
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [horseSearch, setHorseSearch] = useState('');
  const [previewClip, setPreviewClip] = useState<NfcEventItem | null>(null);

  const apiBase = useMemo(() => {
    const raw = window.HUMMAPP_PUBLIC_CONFIG?.apiBaseUrl?.trim() || '';
    return raw.endsWith('/') ? raw.slice(0, -1) : raw;
  }, []);

  const loadPublicData = useCallback(async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const res = await fetch(`${apiBase}/api/public/overview`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json: PublicOverview = await res.json();
      setData(json);
      setDataSourceMode('live');
      setIsLoading(false);
      return;
    } catch {
      // Ilman NAS-yhteyttä (GitHub Pages) käytetään julkaisun mukana tulevaa public-data.json-tiedostoa
      try {
        const snapRes = await fetch('/public-data.json');
        if (snapRes.ok) {
          const json: PublicOverview = await snapRes.json();
          setData(json);
          setDataSourceMode('snapshot');
          setIsLoading(false);
          return;
        }
      } catch {
        // jatketaan virheilmoitukseen
      }
      setLoadError('Tietoja ei saatu ladattua. Yritä hetken päästä uudelleen.');
      setIsLoading(false);
    }
  }, [apiBase]);

  useEffect(() => {
    loadPublicData();
  }, [loadPublicData]);

  const horses = data?.horses ?? [];
  const waterDaily = data?.water_daily ?? [];
  const waterList = data?.water_measurements ?? [];
  const airReadings = data?.air_readings ?? [];
  const nfcEvents = data?.nfc_events ?? [];
  const latestAir = airReadings[0] ?? null;
  const drinkingHorse = data?.drinking_horse_name || 'Antero';
  const clipBefore = data?.clip_seconds_before ?? 5;
  const clipAfter = data?.clip_seconds_after ?? 13;

  const latestWater = waterDaily[waterDaily.length - 1];
  const avgWater = waterDaily.length
    ? waterDaily.reduce((acc, d) => acc + d.total_liters, 0) / waterDaily.length
    : 0;

  const filteredHorses = useMemo(() => {
    const q = horseSearch.trim().toLowerCase();
    if (!q) return horses;
    return horses.filter(
      (h) =>
        h.name.toLowerCase().includes(q) ||
        (h.breed && h.breed.toLowerCase().includes(q)) ||
        (h.stall_box && h.stall_box.toLowerCase().includes(q))
    );
  }, [horses, horseSearch]);

  const updatedAt = formatLocalTimestamp(data?.generated_at);

  return (
    <div className="min-h-screen bg-[#F4F6FA] text-[#58595B] flex flex-col">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:bg-white focus:px-4 focus:py-3 focus:rounded-lg focus:text-[#1B325E]"
      >
        Siirry sisältöön
      </a>

      {/* Rahoittajien ja omistajan tunnukset (EU-näkyvyys) */}
      <div className="bg-white">
        <div className="max-w-[1200px] mx-auto px-4 sm:px-6 py-2 sm:py-3 flex items-center justify-between gap-4">
          <img
            src="/assets/aistudio/fi_v_euroopan_unionin_osarahoittama_pos_ea7e28c8.jpg"
            alt="Euroopan unionin osarahoittama"
            className="h-12 sm:h-16 w-auto object-contain"
          />
          <a href={TAB_PATHS.overview} aria-label="HummAPP – etusivu" className="min-w-0 min-h-11 flex items-center">
            <img
              src="/assets/hummapp-logo.png"
              alt="hummapp.fi"
              width={494}
              height={128}
              className="h-8 sm:h-12 w-auto max-w-full object-contain"
            />
          </a>
          <img
            src="/assets/aistudio/KASE_logo_4a01b836.png"
            alt="Kaustisen seutukunta"
            className="h-12 sm:h-16 w-auto object-contain"
          />
        </div>
        <div className="h-1 w-full flex" aria-hidden="true">
          <div className="w-1/4 bg-[#FDBE4F]" />
          <div className="w-1/4 bg-[#C60651]" />
          <div className="w-1/2 bg-[#1B325E]" />
        </div>
      </div>

      {/* Päänavigaatio */}
      <header className="bg-[#1B325E] text-white sticky top-0 z-40">
        <div className="max-w-[1200px] mx-auto px-2 sm:px-6 flex items-center gap-6">
          <a
            href={TAB_PATHS.overview}
            className="hidden md:flex items-center gap-2 font-display text-lg font-semibold whitespace-nowrap min-h-14"
          >
            <img src="/assets/hummapp-merkki.png" alt="" width={28} height={28} className="h-7 w-7" />
            <span>
              Humm<span className="text-[#FDBE4F]">APP</span>
            </span>
          </a>
          <nav aria-label="Päävalikko" className="flex-1 md:flex-none md:ml-auto overflow-x-auto">
            <ul className="flex items-stretch gap-1 md:gap-2">
              {NAV_ITEMS.map((item) => {
                const isActive = activeTab === item.tab;
                return (
                  <li key={item.tab} className="shrink-0">
                    <a
                      href={TAB_PATHS[item.tab]}
                      aria-current={isActive ? 'page' : undefined}
                      className={`flex items-center min-h-12 md:min-h-14 px-3 text-[15px] font-medium whitespace-nowrap border-b-[3px] ${
                        isActive ? 'border-[#FDBE4F] text-white' : 'border-transparent text-[#C0E1F0] hover:text-white'
                      }`}
                    >
                      {item.label}
                    </a>
                  </li>
                );
              })}
            </ul>
          </nav>
        </div>
      </header>

      <main id="main" className="flex-1 w-full">
        {loadError && (
          <div className="max-w-[1200px] mx-auto px-4 sm:px-6 pt-6">
            <div role="alert" className={`${CARD} p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4`}>
              <p className="text-base text-[#A1342C]">{loadError}</p>
              <button
                type="button"
                onClick={loadPublicData}
                className="inline-flex items-center justify-center gap-2 min-h-11 px-5 rounded-xl bg-[#1B325E] text-white font-medium"
              >
                <RefreshCw className="w-4 h-4" aria-hidden="true" />
                Lataa uudelleen
              </button>
            </div>
          </div>
        )}

        {isLoading && !data ? (
          <LoadingSkeleton />
        ) : (
          <>
            {activeTab === 'overview' && (
              <OverviewPage
                updatedAt={updatedAt}
                live={dataSourceMode === 'live'}
                isLoading={isLoading}
                onRefresh={loadPublicData}
                latestAir={latestAir}
                waterDaily={waterDaily}
                avgWater={avgWater}
                drinkingHorse={drinkingHorse}
                horses={horses}
                nfcCount={nfcEvents.length}
                clipSeconds={clipBefore + clipAfter}
              />
            )}

            {activeTab === 'horses' && (
              <HorsesPage
                horses={horses}
                filteredHorses={filteredHorses}
                search={horseSearch}
                onSearch={setHorseSearch}
                selectedId={route.horseId}
                drinkingHorse={drinkingHorse}
              />
            )}

            {activeTab === 'water' && (
              <WaterPage
                drinkingHorse={drinkingHorse}
                waterDaily={waterDaily}
                waterList={waterList}
                avgWater={avgWater}
                latestWater={latestWater}
                updatedAt={updatedAt}
              />
            )}

            {activeTab === 'environment' && (
              <EnvironmentPage
                airReadings={airReadings}
                nfcEvents={nfcEvents}
                clipBefore={clipBefore}
                clipAfter={clipAfter}
                canPlayVideo={(ev) =>
                  Boolean(
                    ev.video_clip_id &&
                      dataSourceMode === 'live' &&
                      data?.public_video_enabled === true &&
                      (ev.video_clip_status === 'READY' || ev.video_clip_status === 'APPROVED')
                  )
                }
                previewClip={previewClip}
                onPreview={setPreviewClip}
                apiBase={apiBase}
                updatedAt={updatedAt}
              />
            )}
          </>
        )}
      </main>

      <footer className="bg-[#1B325E] text-[#C0E1F0] mt-16" aria-labelledby="project-title">
        <div className="max-w-[1200px] mx-auto px-4 sm:px-6 py-12 grid gap-10 md:grid-cols-[1.3fr_1fr_1fr]">
          <div className="space-y-3">
            <p className="text-sm font-medium text-[#FDBE4F]">Hanke</p>
            <h2 id="project-title" className="font-display text-2xl font-semibold text-white">KP AlkIoT</h2>
            <p className="text-[15px] leading-relaxed max-w-[52ch]">
              HummAPP on osa KP AlkIoT -hanketta, joka parantaa hevosten hyvinvointia Keski-Pohjanmaalla. Hankkeessa
              kehitetään ja pilotoidaan IoT-ratkaisuja, joilla hevosten hyvinvointia voi seurata reaaliajassa.
            </p>
            <a
              href="https://hevostenhyvinvointi.fi/kpalkiot-hankekuvaus/"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 min-h-11 text-[15px] font-medium text-white underline underline-offset-4 decoration-white/30 hover:decoration-white"
            >
              Lue hankekuvaus <ExternalLink className="w-4 h-4" aria-hidden="true" />
            </a>
          </div>

          <dl className="grid gap-4 text-[15px] content-start">
            {[
              { t: 'Toteuttajat', d: 'Kaustisen seutukunta ja Kpedu (EIP-yhteistyöhanke)' },
              { t: 'Rahoittaja', d: 'Pohjanmaan ELY-keskus, Euroopan maaseuturahasto' },
              { t: 'Toteutusaika', d: '1.1.2025–31.12.2026' },
              { t: 'Kohderyhmä', d: 'Keski-Pohjanmaan hevostilat, eläinlääkärit ja ohjelmistoyritykset' },
            ].map((r) => (
              <div key={r.t}>
                <dt className="text-sm text-[#9FC3D6]">{r.t}</dt>
                <dd className="text-white">{r.d}</dd>
              </div>
            ))}
          </dl>

          <div className="space-y-3">
            <p className="text-sm text-[#9FC3D6]">Yhteystiedot</p>
            {[
              { n: 'Jarno Peltola', r: 'Projektipäällikkö, Kaustisen seutukunta', e: 'jarno.peltola@kaustisenseutukunta.fi' },
              { n: 'Marika Kuutti', r: 'Projektikoordinaattori, Kpedu', e: 'marika.kuutti@kpedu.fi' },
            ].map((c) => (
              <div key={c.e} className="text-[15px]">
                <p className="text-white font-medium">{c.n}</p>
                <p>{c.r}</p>
                <a href={`mailto:${c.e}`} className="inline-flex items-center gap-1.5 min-h-11 underline underline-offset-4 decoration-white/30 hover:text-white break-all">
                  <Mail className="w-4 h-4 shrink-0" aria-hidden="true" />
                  {c.e}
                </a>
              </div>
            ))}
          </div>
        </div>
      </footer>
    </div>
  );
}

// =====================================================================
// Yhteiset osat
// =====================================================================

function PageContainer({ children }: { children: React.ReactNode }) {
  return <div className="max-w-[1200px] mx-auto px-4 sm:px-6">{children}</div>;
}

function LevelIcon({ level, className = 'w-4 h-4' }: { level: Level; className?: string }) {
  const color = LEVEL_META[level].mark;
  if (level === 'good') return <CheckCircle2 className={className} style={{ color }} aria-hidden="true" />;
  if (level === 'warn') return <AlertTriangle className={className} style={{ color }} aria-hidden="true" />;
  return <XCircle className={className} style={{ color }} aria-hidden="true" />;
}

function StatusChip({ level }: { level: Level | null }) {
  if (!level) return <span className="text-sm text-[#6D6E71]">Ei tietoa</span>;
  const m = LEVEL_META[level];
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-sm font-medium"
      style={{ background: m.tint, color: m.text }}
    >
      <LevelIcon level={level} />
      {m.label}
    </span>
  );
}

function UpdatedLine({ updatedAt, dark = false }: { updatedAt: string; dark?: boolean }) {
  return (
    <span className={`inline-flex items-center gap-2 text-sm ${dark ? 'text-[#C0E1F0]' : 'text-[#6D6E71]'}`}>
      <Clock className="w-4 h-4" aria-hidden="true" />
      Päivitetty <span className="tabular-nums">{updatedAt}</span>
    </span>
  );
}

function SectionHeader({
  title,
  sub,
  action,
  addon,
}: {
  title: string;
  sub?: string;
  action?: React.ReactNode;
  addon?: React.ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-x-4 gap-y-2 mb-4">
      <div>
        <div className="flex items-center gap-1">
          <h2 className="font-display text-xl sm:text-2xl font-semibold text-[#1B325E] tracking-tight">{title}</h2>
          {addon}
        </div>
        {sub && <p className="text-sm text-[#6D6E71] mt-1">{sub}</p>}
      </div>
      {action}
    </div>
  );
}

// i-ikoni: lähteet näkyvät, kun osoitin viedään päälle. Toimii myös napautuksella ja näppäimistöllä.
function SourcesInfo() {
  const [open, setOpen] = useState(false);
  const [shift, setShift] = useState(0);
  const wrapRef = useRef<HTMLSpanElement>(null);
  const popRef = useRef<HTMLDivElement>(null);
  const id = 'sources-popover';

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false);
    const onDown = (e: PointerEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('keydown', onKey);
    document.addEventListener('pointerdown', onDown);
    return () => {
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('pointerdown', onDown);
    };
  }, [open]);

  // Pidetään ikkuna näytön sisällä kapeallakin näytöllä
  useEffect(() => {
    if (!open || !popRef.current) return;
    const r = popRef.current.getBoundingClientRect();
    const overflow = r.right - (window.innerWidth - 16);
    setShift(overflow > 0 ? -overflow : 0);
  }, [open]);

  return (
    <span
      ref={wrapRef}
      className="relative inline-flex"
      onPointerEnter={(e) => e.pointerType === 'mouse' && setOpen(true)}
      onPointerLeave={(e) => e.pointerType === 'mouse' && setOpen(false)}
    >
      <button
        type="button"
        aria-label="Suositusrajojen lähteet"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((v) => !v)}
        className="grid place-items-center w-11 h-11 rounded-full text-[#6D6E71] hover:text-[#1B325E]"
      >
        <Info className="w-5 h-5" aria-hidden="true" />
      </button>
      {open && (
        <div
          ref={popRef}
          id={id}
          role="dialog"
          aria-label="Suositusrajojen lähteet"
          className="absolute left-0 top-full z-30 pt-1"
          style={{ transform: `translateX(${shift}px)` }}
        >
          <div className="w-[320px] max-w-[calc(100vw-2rem)] rounded-xl border border-[#E3E8EF] bg-white p-4 shadow-[0_8px_24px_rgba(16,24,40,0.08)] text-sm">
            <p className="font-medium text-[#1B325E]">Mistä rajat tulevat?</p>
            <ul className="mt-2 divide-y divide-[#EDF0F4]">
              {SOURCES.map((src) => (
                <li key={src.url} className="py-2">
                  <a href={src.url} target="_blank" rel="noopener noreferrer" className={`${LINK} inline-flex items-start gap-1`}>
                    {src.title}
                    <ExternalLink className="w-3.5 h-3.5 mt-[3px] shrink-0" aria-hidden="true" />
                  </a>
                  <span className="block text-[#6D6E71]">{src.note}</span>
                </li>
              ))}
            </ul>
            <p className="mt-2 text-[#6D6E71] leading-snug">
              Suomen{' '}
              <a href={FINNISH_LAW.url} target="_blank" rel="noopener noreferrer" className={LINK}>
                hevosasetus
              </a>{' '}
              ei anna lukuarvoja. Vihreä noudattaa lähteiden suositusta; keltaisen ja punaisen rajat ovat HummAPPin
              tulkinta.
            </p>
          </div>
        </div>
      )}
    </span>
  );
}

function MoreLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <a href={href} className={`inline-flex items-center gap-1 min-h-11 text-[15px] ${LINK}`}>
      {children}
      <ArrowRight className="w-4 h-4" aria-hidden="true" />
    </a>
  );
}

function LoadingSkeleton() {
  return (
    <div aria-busy="true" aria-label="Ladataan tietoja">
      <div className="bg-[#1B325E] h-72" />
      <PageContainer>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 -mt-10">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className={`${CARD} h-36`} />
          ))}
        </div>
      </PageContainer>
    </div>
  );
}

// --- Talli-ilman mittari: värivyöhykkeet + osoitin arvon kohdalla
function RangeGauge({ def, value }: { def: MetricDef; value: number | null }) {
  const span = def.scaleMax - def.scaleMin;
  const pos = value === null ? null : Math.max(0, Math.min(100, ((value - def.scaleMin) / span) * 100));
  return (
    <div className="relative pt-3" aria-hidden="true">
      <div className="flex h-2.5 gap-[2px]">
        {def.bands.map((b, i) => (
          <div
            key={i}
            className={`h-full ${i === 0 ? 'rounded-l-full' : ''} ${i === def.bands.length - 1 ? 'rounded-r-full' : ''}`}
            style={{ width: `${((b.to - b.from) / span) * 100}%`, background: LEVEL_META[b.level].mark, opacity: 0.85 }}
          />
        ))}
      </div>
      {pos !== null && (
        <div className="absolute top-0 -translate-x-1/2" style={{ left: `${pos}%` }}>
          <div className="w-[5px] h-[22px] -mt-[2px] rounded-full bg-[#1B325E] ring-2 ring-white" />
        </div>
      )}
      <div className="flex justify-between mt-1.5 text-xs text-[#6D6E71] tabular-nums">
        <span>{fmt(def.scaleMin, 0)}</span>
        <span>{fmt(def.scaleMax, 0)} {def.unit}</span>
      </div>
    </div>
  );
}

function AirMetricCard({ def, reading }: { def: MetricDef; reading: StableAirMeasurement | null }) {
  const value = reading ? (reading[def.key] as number | null) : null;
  const level = levelFor(def, value);
  return (
    <div className={`${CARD} p-5 flex flex-col gap-3`}>
      <div className="flex items-start justify-between gap-3">
        <h3 className="text-[15px] font-medium text-[#1B325E]">{def.label}</h3>
        <StatusChip level={level} />
      </div>
      <p className="font-display text-4xl font-semibold text-[#1B325E] tabular-nums tracking-tight">
        {fmt(value, def.decimals)}
        <span className="ml-1.5 text-base font-normal text-[#6D6E71]">{def.unit}</span>
      </p>
      <RangeGauge def={def} value={value} />
      <p className="text-sm text-[#6D6E71] leading-snug">{def.guide}</p>
    </div>
  );
}

// --- Juomamäärä: pylväät alkavat nollasta, keskiarvoviiva, vihjeteksti hiirellä ja näppäimistöllä
function WaterChart({
  waterDaily,
  avgWater,
  height = 240,
}: {
  waterDaily: WaterDailySummary[];
  avgWater: number;
  height?: number;
}) {
  if (waterDaily.length === 0) {
    return <p className="text-base text-[#6D6E71] py-10 text-center">Juomamittauksia ei ole vielä kirjattu.</p>;
  }
  const max = Math.max(...waterDaily.map((d) => d.total_liters), avgWater);
  const top = Math.max(10, Math.ceil((max * 1.1) / 10) * 10);
  const ticks: number[] = [];
  for (let t = 0; t <= top; t += top > 40 ? 20 : 10) ticks.push(t);
  const avgPct = (avgWater / top) * 100;

  return (
    <figure>
      <div className="flex gap-3">
        {/* y-akseli */}
        <div className="relative w-8 shrink-0 text-xs text-[#6D6E71] tabular-nums" style={{ height }} aria-hidden="true">
          {ticks.map((t) => (
            <span key={t} className="absolute right-0" style={{ bottom: `${(t / top) * 100}%`, transform: 'translateY(50%)' }}>
              {t}
            </span>
          ))}
        </div>
        <div className="relative flex-1" style={{ height }}>
          {/* ruudukko */}
          {ticks.map((t) => (
            <div
              key={t}
              className={`absolute inset-x-0 ${t === 0 ? 'border-t border-[#C3C9D3]' : 'border-t border-[#EDF0F4]'}`}
              style={{ bottom: `${(t / top) * 100}%` }}
              aria-hidden="true"
            />
          ))}
          {/* keskiarvo */}
          <div className="absolute inset-x-0 border-t-2 border-dashed border-[#FDBE4F] z-10" style={{ bottom: `${avgPct}%` }} aria-hidden="true">
            <span className="absolute left-0 -top-6 text-xs font-medium text-[#1B325E] bg-white/90 px-1 rounded">
              ka {fmt(avgWater, 1)} l
            </span>
          </div>
          {/* pylväät */}
          <div className="absolute inset-0 flex items-end gap-[6px] sm:gap-3" role="list">
            {waterDaily.map((d, idx) => {
              const isLatest = idx === waterDaily.length - 1;
              return (
                <div
                  key={d.date}
                  role="listitem"
                  tabIndex={0}
                  aria-label={`${formatDay(d.date)}: ${fmt(d.total_liters, 1)} litraa, ${d.measurement_count} juomiskertaa`}
                  className="group relative flex-1 h-full flex items-end rounded-t-[4px]"
                >
                  <div
                    className="relative w-full rounded-t-[4px]"
                    style={{
                      height: `${(d.total_liters / top) * 100}%`,
                      background: isLatest ? '#C60651' : '#135367',
                    }}
                  >
                    {isLatest && (
                      <span className="absolute bottom-full mb-1 left-1/2 -translate-x-1/2 text-sm font-semibold text-[#1B325E] tabular-nums" aria-hidden="true">
                        {fmt(d.total_liters, 1)}
                      </span>
                    )}
                  </div>
                  <div className="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block group-focus:block z-20 whitespace-nowrap rounded-lg bg-[#1B325E] px-3 py-2 text-sm text-white shadow-[0_4px_12px_rgba(16,24,40,0.08)]">
                    <span className="block font-medium tabular-nums">{fmt(d.total_liters, 1)} l</span>
                    <span className="block text-xs text-[#C0E1F0]">
                      {formatDay(d.date)} · {d.measurement_count} kertaa
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
      {/* x-akseli */}
      <div className="flex gap-3 mt-2" aria-hidden="true">
        <div className="w-8 shrink-0" />
        <div className="flex-1 flex gap-[6px] sm:gap-3 text-xs text-[#6D6E71]">
          {waterDaily.map((d) => (
            <span key={d.date} className="flex-1 text-center truncate">
              <span className="hidden sm:inline">{formatDay(d.date)}</span>
              <span className="sm:hidden">{d.date.slice(8).replace(/^0/, '')}.</span>
            </span>
          ))}
        </div>
      </div>
      <figcaption className="flex flex-wrap items-center gap-x-5 gap-y-1 mt-4 text-sm text-[#6D6E71]">
        <span className="inline-flex items-center gap-2">
          <span className="w-3 h-3 rounded-[3px] bg-[#135367]" aria-hidden="true" /> Litraa vuorokaudessa
        </span>
        <span className="inline-flex items-center gap-2">
          <span className="w-3 h-3 rounded-[3px] bg-[#C60651]" aria-hidden="true" /> Viimeisin vuorokausi
        </span>
        <span className="inline-flex items-center gap-2">
          <span className="w-4 border-t-2 border-dashed border-[#FDBE4F]" aria-hidden="true" /> Keskiarvo
        </span>
      </figcaption>
    </figure>
  );
}

// =====================================================================
// 1. Katsaus (Dashboard / Overview)
// =====================================================================

function OverviewPage({
  updatedAt,
  live,
  isLoading,
  onRefresh,
  latestAir,
  waterDaily,
  avgWater,
  drinkingHorse,
  horses,
  nfcCount,
  clipSeconds,
}: {
  updatedAt: string;
  live: boolean;
  isLoading: boolean;
  onRefresh: () => void;
  latestAir: StableAirMeasurement | null;
  waterDaily: WaterDailySummary[];
  avgWater: number;
  drinkingHorse: string;
  horses: PublicHorse[];
  nfcCount: number;
  clipSeconds: number;
}) {
  const levels = METRICS.map((m) => ({ def: m, level: levelFor(m, latestAir ? (latestAir[m.key] as number | null) : null) }));
  const goodCount = levels.filter((l) => l.level === 'good').length;
  const latestWater = waterDaily[waterDaily.length - 1];
  const diff = latestWater ? latestWater.total_liters - avgWater : 0;
  const tempDef = METRICS[0];

  const headline =
    levels.some((l) => l.level === 'bad')
      ? 'Talli-ilmassa on korjattavaa'
      : levels.every((l) => l.level === 'good')
        ? 'Talli-ilma on suositusten mukainen'
        : 'Talli-ilma on pääosin hyvä';

  return (
    <>
      {/* Hero */}
      <section className="bg-[#1B325E] text-white" aria-labelledby="hero-title">
        <PageContainer>
          <div className="grid gap-10 lg:grid-cols-[1.25fr_1fr] items-center pt-12 pb-24 sm:pt-16 sm:pb-28">
            <div className="space-y-5">
              <p className="text-sm font-medium text-[#FDBE4F]">Kaustisen seutukunnan hevostallipilotti</p>
              <h1 id="hero-title" className="font-display text-4xl sm:text-5xl lg:text-[56px] font-semibold leading-[1.08] tracking-tight text-white text-balance">
                Miten tallin hevoset voivat?
              </h1>
              <p className="text-lg text-[#DCEEF6] leading-relaxed max-w-[56ch]">
                HummAPP kokoaa tallin anturien, juoma-automaatin ja NFC-kuvausten tiedot yhteen. Näet yhdellä
                silmäyksellä, juovatko hevoset normaalisti ja onko talli-ilma suositusten mukaista.
              </p>
              <div className="flex flex-wrap items-center gap-x-5 gap-y-3 pt-1">
                {live && (
                  <span className="inline-flex items-center gap-2 text-sm text-white">
                    <span className="w-2 h-2 rounded-full bg-[#00A34D]" aria-hidden="true" />
                    Reaaliaikainen
                  </span>
                )}
                <UpdatedLine updatedAt={updatedAt} dark />
                {live && (
                  <button
                    type="button"
                    onClick={onRefresh}
                    className="inline-flex items-center gap-2 min-h-11 px-4 rounded-xl border border-white/25 text-sm font-medium text-white hover:bg-white/10"
                  >
                    <RefreshCw className={`w-4 h-4 ${isLoading ? 'motion-safe:animate-spin' : ''}`} aria-hidden="true" />
                    Päivitä tiedot
                  </button>
                )}
              </div>
            </div>

            {/* Ilmanlaadun yhteenveto */}
            <div className="rounded-2xl bg-[#22396B] border border-white/10 p-6 sm:p-7">
              <p className="text-sm text-[#C0E1F0]">Viimeisin mittaus{latestAir?.location ? ` · ${latestAir.location}` : ''}</p>
              <p className="font-display text-2xl font-semibold text-white mt-1">{headline}</p>
              <p className="mt-4 flex items-baseline gap-2">
                <span className="font-display text-6xl font-semibold tabular-nums text-white">{goodCount}</span>
                <span className="text-lg text-[#C0E1F0]">/ {METRICS.length} mittaria hyvällä tasolla</span>
              </p>
              <div className="flex gap-[3px] mt-4" aria-hidden="true">
                {levels.map(({ def, level }) => (
                  <div
                    key={def.key}
                    className="h-2 flex-1 rounded-full"
                    style={{ background: level ? LEVEL_META[level].mark : '#6D6E71' }}
                  />
                ))}
              </div>
              <ul className="mt-5 divide-y divide-white/10">
                {levels.map(({ def, level }) => (
                  <li key={def.key} className="flex items-center justify-between gap-3 py-2.5 text-[15px]">
                    <span className="text-white">{def.label}</span>
                    <span className="inline-flex items-center gap-2 text-[#DCEEF6] tabular-nums">
                      {fmt(latestAir ? (latestAir[def.key] as number | null) : null, def.decimals)} {def.unit}
                      {level && (
                        <span className="inline-flex items-center gap-1 font-medium text-white">
                          <LevelIcon level={level} />
                          {LEVEL_META[level].label}
                        </span>
                      )}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </PageContainer>
      </section>

      <PageContainer>
        {/* KPI-rivi nousee herosta */}
        <section aria-label="Tunnusluvut" className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 -mt-14 relative">
          <KpiTile
            icon={<Droplet className="w-5 h-5" aria-hidden="true" />}
            label={`${drinkingHorse} joi viimeisimpänä vuorokautena`}
            value={fmt(latestWater?.total_liters, 1)}
            unit="l"
            foot={
              latestWater
                ? `${diff >= 0 ? '+' : '−'}${fmt(Math.abs(diff), 1)} l keskiarvoon · ${latestWater.measurement_count} juomiskertaa`
                : 'Ei mittauksia'
            }
          />
          <KpiTile
            icon={<Thermometer className="w-5 h-5" aria-hidden="true" />}
            label="Tallin lämpötila"
            value={fmt(latestAir?.temperature, 1)}
            unit="°C"
            foot={<StatusChip level={levelFor(tempDef, latestAir?.temperature)} />}
          />
          <KpiTile
            icon={<Users className="w-5 h-5" aria-hidden="true" />}
            label="Seurattavat hevoset"
            value={String(horses.length)}
            foot={horses.map((h) => h.name).join(', ') || '–'}
          />
          <KpiTile
            icon={<Video className="w-5 h-5" aria-hidden="true" />}
            label="NFC-kuvaukset"
            value={String(nfcCount)}
            foot={`Jokaisesta leimauksesta ${clipSeconds} sekunnin videoleike`}
          />
        </section>

        {/* Talli-ilma suosituksiin verrattuna */}
        <section className="mt-14" aria-labelledby="air-title">
          <div id="air-title">
            <SectionHeader
              title="Talli-ilma suosituksiin verrattuna"
              addon={<SourcesInfo />}
              sub="Osoitin näyttää viimeisimmän mittauksen. Vihreä = hyvä, oranssi = rajalla, punainen = huono."
              action={<MoreLink href={TAB_PATHS.environment}>Kaikki mittaukset</MoreLink>}
            />
          </div>
          {latestAir ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
              {METRICS.map((m) => (
                <AirMetricCard key={m.key} def={m} reading={latestAir} />
              ))}
            </div>
          ) : (
            <div className={`${CARD} p-8 text-base text-[#6D6E71]`}>Talli-ilman mittauksia ei ole vielä saatavilla.</div>
          )}
        </section>

        {/* Juominen + hevoset */}
        <section className="mt-14 grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className={`${CARD} p-5 sm:p-7 lg:col-span-2`}>
            <SectionHeader
              title={`${drinkingHorse}n juominen`}
              sub={`Juoma-automaatin mittaama vesimäärä vuorokaudessa, ${waterDaily.length} viimeisintä vuorokautta`}
              action={<MoreLink href={TAB_PATHS.water}>Juomaseuranta</MoreLink>}
            />
            <div className="pt-8">
              <WaterChart waterDaily={waterDaily} avgWater={avgWater} />
            </div>
          </div>

          <div className={`${CARD} p-5 sm:p-7`}>
            <SectionHeader title="Hevoset" action={<MoreLink href={TAB_PATHS.horses}>Kaikki</MoreLink>} />
            {horses.length === 0 ? (
              <p className="text-base text-[#6D6E71]">Pilottiin ei ole vielä lisätty hevosia.</p>
            ) : (
              <ul className="divide-y divide-[#EDF0F4] -mx-2">
                {horses.slice(0, 5).map((h) => (
                  <li key={h.id}>
                    <a
                      href={`${TAB_PATHS.horses}/${h.id}`}
                      className="flex items-center gap-4 px-2 py-3.5 rounded-xl hover:bg-[#F4F6FA]"
                    >
                      <HorseAvatar name={h.name} />
                      <span className="flex-1 min-w-0">
                        <span className="block text-base font-medium text-[#1B325E]">{h.name}</span>
                        <span className="block text-sm text-[#6D6E71] truncate">
                          {[h.breed, h.stall_box].filter(Boolean).join(' · ')}
                        </span>
                      </span>
                      <ChevronRight className="w-5 h-5 text-[#939598] shrink-0" aria-hidden="true" />
                    </a>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>
      </PageContainer>
    </>
  );
}

function KpiTile({
  icon,
  label,
  value,
  unit,
  foot,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  unit?: string;
  foot: React.ReactNode;
}) {
  return (
    <div className={`${CARD} p-5 flex flex-col gap-2 shadow-[0_4px_12px_rgba(16,24,40,0.06)]`}>
      <div className="flex items-center gap-2 text-[#135367]">
        <span className="grid place-items-center w-9 h-9 rounded-xl bg-[#E8F3F8]">{icon}</span>
        <span className="text-sm font-medium text-[#1B325E] leading-tight">{label}</span>
      </div>
      <p className="font-display text-4xl font-semibold text-[#1B325E] tabular-nums tracking-tight mt-1">
        {value}
        {unit && <span className="ml-1.5 text-base font-normal text-[#6D6E71]">{unit}</span>}
      </p>
      <div className="text-sm text-[#6D6E71]">{foot}</div>
    </div>
  );
}

function HorseAvatar({ name, large = false }: { name: string; large?: boolean }) {
  return (
    <span
      className={`grid place-items-center shrink-0 rounded-full bg-[#1B325E] text-white font-display font-semibold ${
        large ? 'w-16 h-16 text-2xl' : 'w-11 h-11 text-lg'
      }`}
      aria-hidden="true"
    >
      {name.slice(0, 1).toUpperCase()}
    </span>
  );
}

// =====================================================================
// 2. Hevoset (Split Pane; kapealla näytöllä lista → oma tietosivu)
// =====================================================================

function HorsesPage({
  horses,
  filteredHorses,
  search,
  onSearch,
  selectedId,
  drinkingHorse,
}: {
  horses: PublicHorse[];
  filteredHorses: PublicHorse[];
  search: string;
  onSearch: (v: string) => void;
  selectedId: number | null;
  drinkingHorse: string;
}) {
  const active = horses.find((h) => h.id === selectedId) ?? null;
  const shown = active ?? filteredHorses[0] ?? null;
  const listRef = useRef<HTMLUListElement>(null);

  // Nuolinäppäimet siirtävät valintaa listassa
  const onListKey = (e: React.KeyboardEvent<HTMLUListElement>) => {
    if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return;
    const links = Array.from(listRef.current?.querySelectorAll<HTMLAnchorElement>('a') ?? []);
    const i = links.indexOf(document.activeElement as HTMLAnchorElement);
    const next = links[e.key === 'ArrowDown' ? Math.min(links.length - 1, i + 1) : Math.max(0, i - 1)];
    if (next) {
      e.preventDefault();
      next.focus();
      window.location.hash = next.getAttribute('href') ?? '';
    }
  };

  return (
    <PageContainer>
      <div className="pt-10 pb-6">
        <h1 className="font-display text-3xl sm:text-4xl font-semibold text-[#1B325E] tracking-tight">Hevoset</h1>
        <p className="text-base text-[#6D6E71] mt-2 max-w-[65ch]">
          Pilotissa seurattavat hevoset, niiden liikeanalyysit ja tallin kirjaamat muistiinpanot.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[340px_1fr] gap-6 items-start">
        {/* Lista: kapealla näkyy vain, kun hevosta ei ole valittu */}
        <div className={`${CARD} overflow-hidden ${active ? 'hidden lg:block' : ''}`}>
          <div className="p-4 border-b border-[#EDF0F4]">
            <label htmlFor="horse-search" className="block text-sm font-medium text-[#1B325E] mb-1.5">
              Hae hevosta
            </label>
            <div className="relative">
              <Search className="w-4 h-4 text-[#6D6E71] absolute left-3 top-1/2 -translate-y-1/2" aria-hidden="true" />
              <input
                id="horse-search"
                type="search"
                value={search}
                onChange={(e) => onSearch(e.target.value)}
                placeholder="Nimi, rotu tai karsina"
                className="w-full min-h-11 pl-9 pr-3 border border-[#C3C9D3] rounded-xl text-base text-[#1B325E] placeholder:text-[#6D6E71] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#1B325E]"
              />
            </div>
          </div>
          {filteredHorses.length === 0 ? (
            <div className="p-6 text-base text-[#6D6E71]">
              Haulla “{search}” ei löytynyt hevosia.{' '}
              <button type="button" onClick={() => onSearch('')} className={`${LINK} min-h-11`}>
                Tyhjennä haku
              </button>
            </div>
          ) : (
            <ul ref={listRef} onKeyDown={onListKey} className="divide-y divide-[#EDF0F4]">
              {filteredHorses.map((h) => {
                const isSelected = shown?.id === h.id;
                return (
                  <li key={h.id}>
                    <a
                      href={`${TAB_PATHS.horses}/${h.id}`}
                      aria-current={isSelected ? 'true' : undefined}
                      className={`flex items-center gap-4 px-4 py-3.5 ${
                        isSelected ? 'lg:bg-[#EEF2F8] lg:shadow-[inset_3px_0_0_#C60651]' : 'hover:bg-[#F4F6FA]'
                      }`}
                    >
                      <HorseAvatar name={h.name} />
                      <span className="flex-1 min-w-0">
                        <span className="block text-base font-medium text-[#1B325E]">{h.name}</span>
                        <span className="block text-sm text-[#6D6E71] truncate">
                          {[h.breed, h.birth_year ? `s. ${h.birth_year}` : null].filter(Boolean).join(' · ')}
                        </span>
                      </span>
                      <span className="text-sm text-[#6D6E71] whitespace-nowrap">{h.stall_box}</span>
                      <ChevronRight className="w-5 h-5 text-[#939598] shrink-0" aria-hidden="true" />
                    </a>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        {/* Tiedot: kapealla vain, kun hevonen on valittu */}
        <div className={`space-y-6 ${active ? '' : 'hidden lg:block'}`}>
          {active && (
            <a href={TAB_PATHS.horses} className={`lg:hidden inline-flex items-center gap-2 min-h-11 ${LINK}`}>
              <ArrowLeft className="w-4 h-4" aria-hidden="true" /> Kaikki hevoset
            </a>
          )}
          {shown ? <HorseDetail horse={shown} drinkingHorse={drinkingHorse} /> : (
            <div className={`${CARD} p-8 text-base text-[#6D6E71]`}>Valitse hevonen listasta.</div>
          )}
        </div>
      </div>
    </PageContainer>
  );
}

function HorseDetail({ horse, drinkingHorse }: { horse: PublicHorse; drinkingHorse: string }) {
  const facts: { label: string; value: string }[] = [
    { label: 'Rotu', value: horse.breed || '–' },
    { label: 'Syntymävuosi', value: horse.birth_year ? String(horse.birth_year) : '–' },
    { label: 'Karsina', value: horse.stall_box || '–' },
    { label: 'NFC-riimutunniste', value: horse.has_nfc_tag ? 'Käytössä' : 'Ei käytössä' },
  ];
  return (
    <>
      <div className={`${CARD} p-6 sm:p-7`}>
        <div className="flex items-center gap-5">
          <HorseAvatar name={horse.name} large />
          <div>
            <h2 className="font-display text-3xl font-semibold text-[#1B325E] tracking-tight">{horse.name}</h2>
            {horse.name === drinkingHorse && (
              <p className="inline-flex items-center gap-1.5 text-sm text-[#135367] mt-1">
                <Droplet className="w-4 h-4" aria-hidden="true" /> Juoma-automaatti seuraa juomista
              </p>
            )}
          </div>
        </div>
        <dl className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-6 pt-6 border-t border-[#EDF0F4]">
          {facts.map((f) => (
            <div key={f.label}>
              <dt className="text-sm text-[#6D6E71]">{f.label}</dt>
              <dd className="text-base font-medium text-[#1B325E] mt-0.5">{f.value}</dd>
            </div>
          ))}
        </dl>
        {horse.description && <p className="text-base leading-relaxed mt-6 max-w-[65ch]">{horse.description}</p>}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className={`${CARD} p-6`}>
          <h3 className="font-display text-lg font-semibold text-[#1B325E]">
            Liikeanalyysit <span className="text-[#6D6E71] font-normal tabular-nums">({horse.analyses.length})</span>
          </h3>
          {horse.analyses.length === 0 ? (
            <p className="text-base text-[#6D6E71] mt-3">Hevoselle ei ole vielä tehty liikeanalyysiä.</p>
          ) : (
            <ul className="divide-y divide-[#EDF0F4] mt-2">
              {horse.analyses.map((a) => {
                const st = statusLabelFi(a.status);
                return (
                  <li key={a.id} className="py-4 space-y-1.5">
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-base font-medium text-[#1B325E]">{a.analysis_method}</span>
                      {st.level === 'neutral' ? (
                        <span className="text-sm text-[#6D6E71]">{st.label}</span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 text-sm font-medium" style={{ color: LEVEL_META[st.level].text }}>
                          <LevelIcon level={st.level} /> {st.label}
                        </span>
                      )}
                    </div>
                    <p className="text-[15px] leading-relaxed">{a.summary}</p>
                    <p className="text-xs text-[#6D6E71] tabular-nums">{formatLocalTimestamp(a.analysis_timestamp)}</p>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        <div className={`${CARD} p-6`}>
          <h3 className="font-display text-lg font-semibold text-[#1B325E]">
            Muistiinpanot <span className="text-[#6D6E71] font-normal tabular-nums">({horse.notes.length})</span>
          </h3>
          {horse.notes.length === 0 ? (
            <p className="text-base text-[#6D6E71] mt-3">
              Ei julkisia muistiinpanoja. Talli kirjaa muistiinpanot omalla HummAPP-sovelluksellaan.
            </p>
          ) : (
            <ul className="divide-y divide-[#EDF0F4] mt-2">
              {horse.notes.map((n) => (
                <li key={n.id} className="py-4 space-y-1.5">
                  <p className="text-[15px] leading-relaxed">{n.content}</p>
                  <p className="text-xs text-[#6D6E71] tabular-nums">Tallitiimi · {formatLocalTimestamp(n.created_at)}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </>
  );
}

// =====================================================================
// 3. Juominen (Detail / Record)
// =====================================================================

function WaterPage({
  drinkingHorse,
  waterDaily,
  waterList,
  avgWater,
  latestWater,
  updatedAt,
}: {
  drinkingHorse: string;
  waterDaily: WaterDailySummary[];
  waterList: WaterMeasurement[];
  avgWater: number;
  latestWater: WaterDailySummary | undefined;
  updatedAt: string;
}) {
  const totals = waterDaily.map((d) => d.total_liters);
  const stats = [
    { label: 'Viimeisin vuorokausi', value: fmt(latestWater?.total_liters, 1) },
    { label: 'Keskiarvo', value: fmt(avgWater, 1) },
    { label: 'Enimmillään', value: totals.length ? fmt(Math.max(...totals), 1) : '–' },
    { label: 'Vähimmillään', value: totals.length ? fmt(Math.min(...totals), 1) : '–' },
  ];
  return (
    <PageContainer>
      <div className="pt-10 pb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl sm:text-4xl font-semibold text-[#1B325E] tracking-tight">{drinkingHorse}n juominen</h1>
          <p className="text-base text-[#6D6E71] mt-2 max-w-[65ch]">
            Juoma-automaatti mittaa jokaisen juomiskerran. Pilotissa automaatti on käytössä hevosella {drinkingHorse}.
          </p>
        </div>
        <UpdatedLine updatedAt={updatedAt} />
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((s) => (
          <div key={s.label} className={`${CARD} p-5`}>
            <p className="text-sm text-[#6D6E71]">{s.label}</p>
            <p className="font-display text-3xl font-semibold text-[#1B325E] tabular-nums mt-1">
              {s.value}
              <span className="ml-1 text-base font-normal text-[#6D6E71]">l</span>
            </p>
          </div>
        ))}
      </div>

      <section className={`${CARD} p-5 sm:p-7 mt-6`}>
        <SectionHeader title="Vesimäärä vuorokaudessa" />
        <div className="pt-8">
          <WaterChart waterDaily={waterDaily} avgWater={avgWater} height={280} />
        </div>
      </section>

      <section className="mt-6">
        <SectionHeader title="Yksittäiset juomiskerrat" />
        <div className={`${CARD} overflow-x-auto`}>
          <table className="w-full text-left text-[15px]">
            <thead>
              <tr className="border-b border-[#E3E8EF] text-sm text-[#6D6E71]">
                <th scope="col" className="py-3 px-5 font-medium">Aika</th>
                <th scope="col" className="py-3 px-5 font-medium text-right">Määrä</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#EDF0F4]">
              {waterList.length === 0 ? (
                <tr>
                  <td colSpan={2} className="py-6 px-5 text-[#6D6E71]">Ei kirjattuja juomiskertoja.</td>
                </tr>
              ) : (
                waterList.map((m) => (
                  <tr key={m.id}>
                    <td className="py-3 px-5 tabular-nums">{formatLocalTimestamp(m.measured_at)}</td>
                    <td className="py-3 px-5 text-right font-medium text-[#1B325E] tabular-nums">{fmt(m.liters, 1)} l</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </PageContainer>
  );
}

// =====================================================================
// 4. Talli-ilma ja kuvaukset (Detail / Record)
// =====================================================================

function ValueCell({ def, value }: { def: MetricDef; value: number | null }) {
  const level = levelFor(def, value);
  return (
    <td className="py-3 px-4 text-right tabular-nums whitespace-nowrap">
      <span className="inline-flex items-center gap-1.5 justify-end" style={level ? { color: LEVEL_META[level].text } : undefined}>
        {level && <LevelIcon level={level} />}
        <span className="font-medium">{fmt(value, def.decimals)}</span>
        <span className="sr-only">{level ? `, ${LEVEL_META[level].label}` : ''}</span>
      </span>
    </td>
  );
}

function EnvironmentPage({
  airReadings,
  nfcEvents,
  clipBefore,
  clipAfter,
  canPlayVideo,
  previewClip,
  onPreview,
  apiBase,
  updatedAt,
}: {
  airReadings: StableAirMeasurement[];
  nfcEvents: NfcEventItem[];
  clipBefore: number;
  clipAfter: number;
  canPlayVideo: (ev: NfcEventItem) => boolean;
  previewClip: NfcEventItem | null;
  onPreview: (ev: NfcEventItem | null) => void;
  apiBase: string;
  updatedAt: string;
}) {
  const latest = airReadings[0] ?? null;
  return (
    <PageContainer>
      <div className="pt-10 pb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl sm:text-4xl font-semibold text-[#1B325E] tracking-tight">Talli-ilma ja kuvaukset</h1>
          <p className="text-base text-[#6D6E71] mt-2 max-w-[65ch]">
            Anturit mittaavat lämpötilaa, kosteutta, ammoniakkia, hiilidioksidia ja pienhiukkasia. Arvot verrataan
            hevostallien suositusrajoihin.
          </p>
        </div>
        <UpdatedLine updatedAt={updatedAt} />
      </div>

      <section aria-labelledby="latest-air">
        <h2 id="latest-air" className="sr-only">Viimeisin mittaus</h2>
        {latest ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            {METRICS.map((m) => (
              <AirMetricCard key={m.key} def={m} reading={latest} />
            ))}
          </div>
        ) : (
          <div className={`${CARD} p-8 text-base text-[#6D6E71]`}>Talli-ilman mittauksia ei ole vielä saatavilla.</div>
        )}
      </section>

      <section className="mt-10">
        <SectionHeader title="Mittaukset sijainneittain" sub="Kuvake ja väri kertovat, onko arvo suositusrajojen sisällä." />
        <div className={`${CARD} overflow-x-auto`}>
          <table className="w-full text-left text-[15px] min-w-[760px]">
            <thead>
              <tr className="border-b border-[#E3E8EF] text-sm text-[#6D6E71]">
                <th scope="col" className="py-3 px-4 font-medium">Sijainti</th>
                <th scope="col" className="py-3 px-4 font-medium">Aika</th>
                {METRICS.map((m) => (
                  <th key={m.key} scope="col" className="py-3 px-4 font-medium text-right whitespace-nowrap">
                    {m.shortLabel} <span className="font-normal">{m.unit}</span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[#EDF0F4]">
              {airReadings.slice(0, 12).map((a) => (
                <tr key={a.id}>
                  <td className="py-3 px-4 font-medium text-[#1B325E]">{a.location || a.sensor_id || 'Anturi'}</td>
                  <td className="py-3 px-4 tabular-nums whitespace-nowrap">{formatLocalTimestamp(a.measured_at)}</td>
                  {METRICS.map((m) => (
                    <ValueCell key={m.key} def={m} value={a[m.key] as number | null} />
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mt-10">
        <SectionHeader title="Suositusrajat" addon={<SourcesInfo />} sub="Vihreä = suosituksen mukainen, oranssi = lähellä rajaa tai hieman yli, punainen = selvästi yli." />
        <div className={`${CARD} overflow-x-auto`}>
          <table className="w-full text-left text-[15px] min-w-[640px]">
            <thead>
              <tr className="border-b border-[#E3E8EF] text-sm text-[#6D6E71]">
                <th scope="col" className="py-3 px-4 font-medium">Mittari</th>
                {(['good', 'warn', 'bad'] as Level[]).map((l) => (
                  <th key={l} scope="col" className="py-3 px-4 font-medium">
                    <span className="inline-flex items-center gap-1.5" style={{ color: LEVEL_META[l].text }}>
                      <LevelIcon level={l} /> {LEVEL_META[l].label}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[#EDF0F4]">
              {METRICS.map((m) => (
                <tr key={m.key}>
                  <td className="py-3 px-4 font-medium text-[#1B325E] whitespace-nowrap">{m.label}</td>
                  {(['good', 'warn', 'bad'] as Level[]).map((l) => (
                    <td key={l} className="py-3 px-4 tabular-nums">
                      {m.bands
                        .filter((b) => b.level === l)
                        .map((b) => rangeText(m, b.from, b.to))
                        .join(' tai ')}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mt-10">
        <SectionHeader
          title="NFC-kuvaukset"
          sub={`Kun hevonen leimataan kuvausalueella, kamerasta tallentuu ${clipBefore + clipAfter} sekunnin leike (${clipBefore} s ennen ja ${clipAfter} s jälkeen). Leikkeet tarkastetaan tallin sovelluksessa.`}
        />
        <div className={`${CARD} overflow-x-auto`}>
          <table className="w-full text-left text-[15px] min-w-[560px]">
            <thead>
              <tr className="border-b border-[#E3E8EF] text-sm text-[#6D6E71]">
                <th scope="col" className="py-3 px-4 font-medium">Hevonen</th>
                <th scope="col" className="py-3 px-4 font-medium">Aika</th>
                <th scope="col" className="py-3 px-4 font-medium">Kuvausalue</th>
                <th scope="col" className="py-3 px-4 font-medium">Leikkeen tila</th>
                <th scope="col" className="py-3 px-4 font-medium text-right"><span className="sr-only">Toiminnot</span></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#EDF0F4]">
              {nfcEvents.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-6 px-4 text-[#6D6E71]">Kuvauksia ei ole vielä tehty.</td>
                </tr>
              ) : (
                nfcEvents.map((ev) => {
                  const st = statusLabelFi(ev.video_clip_status || ev.status);
                  return (
                    <tr key={ev.id}>
                      <td className="py-3 px-4 font-medium text-[#1B325E]">{ev.horse_name || 'Tuntematon'}</td>
                      <td className="py-3 px-4 tabular-nums whitespace-nowrap">{formatLocalTimestamp(ev.phone_timestamp)}</td>
                      <td className="py-3 px-4">{ev.location || '–'}</td>
                      <td className="py-3 px-4">
                        {st.level === 'neutral' ? (
                          <span className="text-[#58595B]">{st.label}</span>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 font-medium" style={{ color: LEVEL_META[st.level].text }}>
                            <LevelIcon level={st.level} /> {st.label}
                          </span>
                        )}
                      </td>
                      <td className="py-2 px-4 text-right">
                        {canPlayVideo(ev) && (
                          <button
                            type="button"
                            onClick={() => onPreview(ev)}
                            className="inline-flex items-center gap-2 min-h-11 px-4 rounded-xl bg-[#1B325E] text-white text-sm font-medium"
                          >
                            <Video className="w-4 h-4" aria-hidden="true" /> Katso leike
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {previewClip && previewClip.video_clip_id && (
          <div className="mt-4 bg-[#1B325E] text-white p-5 rounded-2xl space-y-3">
            <div className="flex items-center justify-between gap-3">
              <p className="text-base font-medium">
                {previewClip.horse_name} · {formatLocalTimestamp(previewClip.phone_timestamp)}
              </p>
              <button
                type="button"
                onClick={() => onPreview(null)}
                className="min-h-11 px-4 rounded-xl border border-white/25 text-sm font-medium hover:bg-white/10"
              >
                Sulje video
              </button>
            </div>
            <video
              key={previewClip.video_clip_id}
              controls
              className="w-full max-h-96 rounded-xl bg-black"
              src={`${apiBase}/api/public/video-clips/${previewClip.video_clip_id}/stream`}
            />
          </div>
        )}
      </section>
    </PageContainer>
  );
}

function rangeText(m: MetricDef, from: number, to: number): string {
  if (from <= m.scaleMin) return `alle ${fmt(to, 0)} ${m.unit}`;
  if (to >= m.scaleMax) return `yli ${fmt(from, 0)} ${m.unit}`;
  return `${fmt(from, 0)}–${fmt(to, 0)} ${m.unit}`;
}
