import React, { useEffect, useState, useCallback, useMemo, useRef, useId } from 'react';
import {
  Droplet,
  Thermometer,
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
  Table as TableIcon,
} from 'lucide-react';
import { METRICS, SOURCES, FINNISH_LAW, LEVEL_META, levelFor, type Level, type MetricDef } from './thresholds';
import { t, metricText, setLang, locale, type Lang } from './i18n';

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
  has_nfc_tag?: boolean;
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

interface PublicOverview {
  read_only: boolean;
  generated_at: string;
  drinking_horse_name: string;
  horses: PublicHorse[];
  water_daily: WaterDailySummary[];
  water_measurements: WaterMeasurement[];
  air_readings: StableAirMeasurement[];
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

const NAV_TABS: PublicTab[] = ['overview', 'horses', 'water', 'environment'];

// --- Kieli: ?lang=en osoitteessa, muuten tallennettu valinta, oletuksena suomi
function initialLang(): Lang {
  const q = new URLSearchParams(window.location.search).get('lang');
  if (q === 'en' || q === 'fi') return q;
  try {
    const saved = window.localStorage.getItem('hummapp-lang');
    if (saved === 'en' || saved === 'fi') return saved;
  } catch {
    // selaimen tallennus ei käytettävissä
  }
  return 'fi';
}

function useLang(): [Lang, (l: Lang) => void] {
  const [lang, setLangState] = useState<Lang>(initialLang);
  setLang(lang);
  useEffect(() => {
    const s = t();
    document.documentElement.lang = lang;
    document.title = s.docTitle;
    document.querySelector('meta[name="description"]')?.setAttribute('content', s.docDescription);
  }, [lang]);
  const change = useCallback((l: Lang) => {
    setLang(l);
    setLangState(l);
    try {
      window.localStorage.setItem('hummapp-lang', l);
    } catch {
      // ei tallennusta
    }
    const url = new URL(window.location.href);
    if (l === 'fi') url.searchParams.delete('lang');
    else url.searchParams.set('lang', l);
    window.history.replaceState(null, '', url.toString());
  }, []);
  return [lang, change];
}

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
const localTimestampFormat = () =>
  new Intl.DateTimeFormat(locale(), {
    timeZone: LOCAL_TIMEZONE,
    day: 'numeric',
    month: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
const dayLabelFormat = () =>
  new Intl.DateTimeFormat(locale(), { weekday: 'short', day: 'numeric', month: 'numeric', timeZone: 'UTC' });
const numberFormat = (decimals: number) =>
  new Intl.NumberFormat(locale(), { minimumFractionDigits: decimals, maximumFractionDigits: decimals });

// Palvelin palauttaa UTC-ajat; aikavyöhyketön ISO-merkkijono tulkitaan UTC:ksi.
function parseUtc(iso: string): Date {
  return new Date(/[zZ]|[+-]\d{2}:\d{2}$/.test(iso) ? iso : `${iso}Z`);
}

function formatLocalTimestamp(iso: string | null | undefined): string {
  if (!iso) return '–';
  const date = parseUtc(iso);
  return Number.isNaN(date.getTime()) ? '–' : localTimestampFormat().format(date);
}

function formatDay(dateKey: string): string {
  const d = new Date(`${dateKey}T12:00:00Z`);
  return Number.isNaN(d.getTime()) ? dateKey : dayLabelFormat().format(d);
}

function fmt(value: number | null | undefined, decimals: number): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '–';
  return numberFormat(decimals).format(value);
}

function statusLabelFi(status: string): { label: string; level: Level | 'neutral' } {
  const L = t().status;
  switch (status) {
    case 'APPROVED':
      return { label: L.APPROVED, level: 'good' };
    case 'READY':
      return { label: L.READY, level: 'neutral' };
    case 'PROCESSING':
    case 'WAITING_FOR_RECORDING':
      return { label: L.PROCESSING, level: 'warn' };
    case 'REJECTED':
      return { label: L.REJECTED, level: 'neutral' };
    default:
      return { label: L.ERROR, level: 'bad' };
  }
}

const CARD = 'relative bg-white border border-[#E3E8EF] rounded-2xl shadow-[0_1px_2px_rgba(16,24,40,0.04)]';
const LINK = 'text-[#C60651] font-medium hover:underline underline-offset-4';

export default function App() {
  const [lang, changeLang] = useLang();
  const s = t();
  const route = useHashRoute();
  const activeTab = route.tab;
  const [data, setData] = useState<PublicOverview | null>(null);
  const [dataSourceMode, setDataSourceMode] = useState<'live' | 'snapshot'>('snapshot');
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [horseSearch, setHorseSearch] = useState('');

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
      setLoadError('error');
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
  const latestAir = airReadings[0] ?? null;
  const drinkingHorse = data?.drinking_horse_name || 'Antero';

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
        {s.skip}
      </a>

      {/* Rahoittajien ja omistajan tunnukset (EU-näkyvyys) */}
      <div className="bg-white">
        <div className="max-w-[1200px] mx-auto px-4 sm:px-6 py-2 sm:py-3 flex items-center justify-between gap-4">
          <EuLogo lang={lang} alt={s.euAlt} />
          <a href={TAB_PATHS.overview} aria-label={s.homeAria} className="min-w-0 min-h-11 flex items-center">
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
            alt={s.kaseAlt}
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
          <nav aria-label={s.navAria} className="flex-1 min-w-0 md:flex-none md:ml-auto overflow-x-auto">
            <ul className="flex items-stretch md:gap-2">
              {NAV_TABS.map((tab) => {
                const isActive = activeTab === tab;
                return (
                  <li key={tab} className="shrink-0">
                    <a
                      href={TAB_PATHS[tab]}
                      aria-current={isActive ? 'page' : undefined}
                      className={`flex items-center min-h-12 md:min-h-14 px-2 md:px-3 text-[15px] font-medium whitespace-nowrap border-b-[3px] ${
                        isActive ? 'border-[#FDBE4F] text-white' : 'border-transparent text-[#C0E1F0] hover:text-white'
                      }`}
                    >
                      {s.nav[tab]}
                    </a>
                  </li>
                );
              })}
            </ul>
          </nav>
          <LangSwitch lang={lang} onChange={changeLang} label={s.langSwitch} />
        </div>
      </header>

      <main id="main" className="flex-1 w-full">
        {loadError && (
          <div className="max-w-[1200px] mx-auto px-4 sm:px-6 pt-6">
            <div role="alert" className={`${CARD} p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4`}>
              <p className="text-base text-[#A1342C]">{s.loadError}</p>
              <button
                type="button"
                onClick={loadPublicData}
                className="inline-flex items-center justify-center gap-2 min-h-11 px-5 rounded-xl bg-[#1B325E] text-white font-medium"
              >
                <RefreshCw className="w-4 h-4" aria-hidden="true" />
                {s.reload}
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
                airReadings={airReadings}
                waterDaily={waterDaily}
                avgWater={avgWater}
                drinkingHorse={drinkingHorse}
                horses={horses}
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
              <EnvironmentPage airReadings={airReadings} updatedAt={updatedAt} />
            )}
          </>
        )}
      </main>

      <footer className="bg-[#1B325E] text-[#C0E1F0] mt-16" aria-labelledby="project-title">
        <div className="max-w-[1200px] mx-auto px-4 sm:px-6 py-12 grid gap-10 md:grid-cols-[1.3fr_1fr_1fr]">
          <div className="space-y-3">
            <p className="text-sm font-medium text-[#FDBE4F]">{s.footProject}</p>
            <h2 id="project-title" className="font-display text-2xl font-semibold text-white">KP AlkIoT</h2>
            <p className="text-[15px] leading-relaxed max-w-[52ch]">{s.footText}</p>
            <a
              href="https://hevostenhyvinvointi.fi/kpalkiot-hankekuvaus/"
              target="_blank"
              rel="noopener noreferrer"
              hrefLang="fi"
              className="inline-flex items-center gap-1.5 min-h-11 text-[15px] font-medium text-white underline underline-offset-4 decoration-white/30 hover:decoration-white"
            >
              {s.footReadMore} <ExternalLink className="w-4 h-4" aria-hidden="true" />
            </a>
          </div>

          <dl className="grid gap-4 text-[15px] content-start">
            {s.footFacts.map((r) => (
              <div key={r.t}>
                <dt className="text-sm text-[#9FC3D6]">{r.t}</dt>
                <dd className="text-white">{r.d}</dd>
              </div>
            ))}
          </dl>

          <div className="space-y-3">
            <p className="text-sm text-[#9FC3D6]">{s.footContacts}</p>
            {s.contacts.map((c) => (
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

// FI / EN -valinta yläpalkissa
function LangSwitch({ lang, onChange, label }: { lang: Lang; onChange: (l: Lang) => void; label: string }) {
  const options: { l: Lang; text: string; title: string }[] = [
    { l: 'fi', text: 'FI', title: 'Suomeksi' },
    { l: 'en', text: 'EN', title: 'In English' },
  ];
  const other = options.find((o) => o.l !== lang)!;
  return (
    <>
      {/* Kapealla näytöllä yksi painike, joka vaihtaa toiseen kieleen */}
      <button
        type="button"
        lang={other.l}
        aria-label={other.title}
        title={other.title}
        onClick={() => onChange(other.l)}
        className="md:hidden shrink-0 min-w-11 min-h-11 px-2 rounded-lg border border-white/25 text-sm font-semibold text-white"
      >
        {other.text}
      </button>
      <div role="group" aria-label={label} className="hidden md:flex items-center shrink-0 ml-2 gap-0.5">
        {options.map((o) => (
          <button
            key={o.l}
            type="button"
            lang={o.l}
            title={o.title}
            aria-pressed={lang === o.l}
            onClick={() => onChange(o.l)}
            className={`min-w-11 min-h-11 px-2 rounded-lg text-sm font-semibold ${
              lang === o.l ? 'bg-white text-[#1B325E]' : 'text-[#C0E1F0] hover:text-white'
            }`}
          >
            {o.text}
          </button>
        ))}
      </div>
    </>
  );
}

// EU-tunnus kielen mukaan. Englanninkielinen tunnus haetaan tiedostosta /assets/eu-cofunded-en.png;
// jos sitä ei ole, näytetään suomenkielinen.
const EU_LOGO_FI = '/assets/aistudio/fi_v_euroopan_unionin_osarahoittama_pos_ea7e28c8.jpg';
const EU_LOGO_EN = '/assets/eu-cofunded-en.png';
function EuLogo({ lang, alt }: { lang: Lang; alt: string }) {
  const [enMissing, setEnMissing] = useState(false);
  const src = lang === 'en' && !enMissing ? EU_LOGO_EN : EU_LOGO_FI;
  return (
    <img
      src={src}
      alt={alt}
      onError={() => lang === 'en' && setEnMissing(true)}
      className="h-12 sm:h-16 w-auto object-contain"
    />
  );
}

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
  if (!level) return <span className="text-sm text-[#6D6E71]">{t().noData}</span>;
  const m = LEVEL_META[level];
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-sm font-medium"
      style={{ background: m.tint, color: m.text }}
    >
      <LevelIcon level={level} />
      {t().levels[level]}
    </span>
  );
}

function UpdatedLine({ updatedAt, dark = false }: { updatedAt: string; dark?: boolean }) {
  return (
    <span className={`inline-flex items-center gap-2 text-sm ${dark ? 'text-[#C0E1F0]' : 'text-[#6D6E71]'}`}>
      <Clock className="w-4 h-4" aria-hidden="true" />
      {t().updated} <span className="tabular-nums">{updatedAt}</span>
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
        aria-label={t().sourcesAria}
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
          aria-label={t().sourcesAria}
          className="absolute left-0 top-full z-30 pt-1"
          style={{ transform: `translateX(${shift}px)` }}
        >
          <div className="w-[320px] max-w-[calc(100vw-2rem)] rounded-xl border border-[#E3E8EF] bg-white p-4 shadow-[0_8px_24px_rgba(16,24,40,0.08)] text-sm">
            <p className="font-medium text-[#1B325E]">{t().sourcesTitle}</p>
            <ul className="mt-2 divide-y divide-[#EDF0F4]">
              {SOURCES.map((src, i) => (
                <li key={src.url} className="py-2">
                  <a href={src.url} target="_blank" rel="noopener noreferrer" className={`${LINK} inline-flex items-start gap-1`}>
                    {t().sources[i]?.title ?? src.title}
                    <ExternalLink className="w-3.5 h-3.5 mt-[3px] shrink-0" aria-hidden="true" />
                  </a>
                  <span className="block text-[#6D6E71]">{t().sources[i]?.note ?? src.note}</span>
                </li>
              ))}
            </ul>
            <p className="mt-2 text-[#6D6E71] leading-snug">
              {t().sourcesLawBefore}{' '}
              <a href={FINNISH_LAW.url} target="_blank" rel="noopener noreferrer" className={LINK}>
                {t().sourcesLawLink}
              </a>{' '}
              {t().sourcesLawAfter}
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
    <div aria-busy="true" aria-label={t().loading}>
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
function RangeGauge({ def, value, instant }: { def: MetricDef; value: number | null; instant?: number | null }) {
  const span = def.scaleMax - def.scaleMin;
  const toPos = (v: number | null | undefined) =>
    v === null || v === undefined ? null : Math.max(0, Math.min(100, ((v - def.scaleMin) / span) * 100));
  const pos = toPos(value);
  const instantPos = toPos(instant);
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
      {instantPos !== null && (
        <div className="absolute top-0 -translate-x-1/2" style={{ left: `${instantPos}%` }}>
          <div className="w-3.5 h-3.5 mt-[2px] rounded-full bg-white border-2 border-[#1B325E]" />
        </div>
      )}
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

// Mittarin arvo luokitusta varten. Jos ohjearvo on vuorokausikeskiarvo (PM2.5), lasketaan saman sijainnin
// mittausten keskiarvo viimeisimmän mittauksen edeltävältä 24 tunnilta.
interface MetricSummary {
  value: number | null;
  level: Level | null;
  avg?: { n: number; spanHours: number };
  /** Viimeisin yksittäinen mittaus (näytetään 24 h -mittareille keskiarvon rinnalla) */
  instant?: number | null;
}

function summarizeMetric(def: MetricDef, readings: StableAirMeasurement[]): MetricSummary {
  const latest = readings[0];
  if (!latest) return { value: null, level: null };
  if (def.averaging !== '24h') {
    const value = latest[def.key] as number | null;
    return { value, level: levelFor(def, value) };
  }
  const end = parseUtc(latest.measured_at).getTime();
  const window = readings.filter((r) => {
    const t = parseUtc(r.measured_at).getTime();
    return r.location === latest.location && t <= end && t > end - 24 * 3600 * 1000 && r[def.key] !== null;
  });
  if (window.length === 0) return { value: null, level: null };
  const values = window.map((r) => r[def.key] as number);
  const value = values.reduce((a, b) => a + b, 0) / values.length;
  const times = window.map((r) => parseUtc(r.measured_at).getTime());
  const spanHours = (Math.max(...times) - Math.min(...times)) / 3600000;
  return {
    value,
    level: levelFor(def, value),
    avg: { n: window.length, spanHours },
    instant: latest[def.key] as number | null,
  };
}

function AvgNote({ def, avg, instant }: { def: MetricDef; avg: NonNullable<MetricSummary['avg']>; instant?: number | null }) {
  const partial = avg.spanHours < 18;
  return (
    <div className="text-sm text-[#6D6E71] leading-snug space-y-2">
      <ul className="space-y-1">
        <li className="flex items-center gap-2">
          <span className="w-[5px] h-3.5 rounded-full bg-[#1B325E] shrink-0" aria-hidden="true" />
          {t().avgLabel(avg.n)}
        </li>
        <li className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-white border-2 border-[#1B325E] shrink-0" aria-hidden="true" />
          <span>
            {t().latestLabel}{' '}
            <span className="font-medium text-[#1B325E] tabular-nums">
              {fmt(instant, def.decimals)} {def.unit}
            </span>
          </span>
        </li>
      </ul>
      {partial && <p>{t().avgPartial}</p>}
    </div>
  );
}

function AirMetricCard({ def, readings }: { def: MetricDef; readings: StableAirMeasurement[] }) {
  const { value, level, avg, instant } = summarizeMetric(def, readings);
  return (
    <div className={`${CARD} p-5 flex flex-col gap-3`}>
      <div className="flex items-start justify-between gap-3">
        <h3 className="text-[15px] font-medium text-[#1B325E]">{metricText(def).label}</h3>
        <StatusChip level={level} />
      </div>
      <p className="font-display text-4xl font-semibold text-[#1B325E] tabular-nums tracking-tight">
        {fmt(value, def.decimals)}
        <span className="ml-1.5 text-base font-normal text-[#6D6E71]">{def.unit}</span>
      </p>
      <RangeGauge def={def} value={value} instant={avg ? instant : undefined} />
      {avg && <AvgNote def={def} avg={avg} instant={instant} />}
      <p className="text-sm text-[#6D6E71] leading-snug">{metricText(def).guide}</p>
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
  // Näppäimistö: kaavio on yksi sarkainpysähdys, ja päivästä toiseen liikutaan nuolinäppäimillä
  const [focusIdx, setFocusIdx] = useState<number | null>(null);
  const [showTable, setShowTable] = useState(false);
  const barRefs = useRef<(HTMLDivElement | null)[]>([]);
  const tableId = useId();
  if (waterDaily.length === 0) {
    return <p className="text-base text-[#6D6E71] py-10 text-center">{t().chartEmpty}</p>;
  }
  const rovingIdx = focusIdx ?? waterDaily.length - 1;
  const onBarsKey = (e: React.KeyboardEvent<HTMLDivElement>) => {
    const last = waterDaily.length - 1;
    const next =
      e.key === 'ArrowRight' || e.key === 'ArrowDown'
        ? Math.min(last, rovingIdx + 1)
        : e.key === 'ArrowLeft' || e.key === 'ArrowUp'
          ? Math.max(0, rovingIdx - 1)
          : e.key === 'Home'
            ? 0
            : e.key === 'End'
              ? last
              : null;
    if (next === null) return;
    e.preventDefault();
    setFocusIdx(next);
    barRefs.current[next]?.focus();
  };
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
              {t().chartAvg} {fmt(avgWater, 1)} l
            </span>
          </div>
          {/* pylväät */}
          <div
            className="absolute inset-0 flex items-end gap-[6px] sm:gap-3"
            role="list"
            aria-label={t().chartListAria}
            onKeyDown={onBarsKey}
          >
            {waterDaily.map((d, idx) => {
              const isLatest = idx === waterDaily.length - 1;
              return (
                <div
                  key={d.date}
                  role="listitem"
                  ref={(el) => {
                    barRefs.current[idx] = el;
                  }}
                  tabIndex={idx === rovingIdx ? 0 : -1}
                  onFocus={() => setFocusIdx(idx)}
                  aria-label={t().chartBarAria(formatDay(d.date), fmt(d.total_liters, 1), d.measurement_count)}
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
                      {formatDay(d.date)} · {t().chartTimes(d.measurement_count)}
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
              <span className="sm:hidden">{t().dayShort(Number(d.date.slice(8)))}</span>
            </span>
          ))}
        </div>
      </div>
      <figcaption className="flex flex-wrap items-center gap-x-5 gap-y-1 mt-4 text-sm text-[#6D6E71]">
        <span className="inline-flex items-center gap-2">
          <span className="w-3 h-3 rounded-[3px] bg-[#135367]" aria-hidden="true" /> {t().chartLegendDay}
        </span>
        <span className="inline-flex items-center gap-2">
          <span className="w-3 h-3 rounded-[3px] bg-[#C60651]" aria-hidden="true" /> {t().chartLegendLatest}
        </span>
        <span className="inline-flex items-center gap-2">
          <span className="w-4 border-t-2 border-dashed border-[#FDBE4F]" aria-hidden="true" /> {t().chartLegendAvg}
        </span>
        <button
          type="button"
          aria-expanded={showTable}
          aria-controls={tableId}
          onClick={() => setShowTable((v) => !v)}
          className={`ml-auto inline-flex items-center gap-1.5 min-h-11 text-[15px] ${LINK}`}
        >
          <TableIcon className="w-4 h-4" aria-hidden="true" />
          {showTable ? t().chartHideTable : t().chartShowTable}
        </button>
      </figcaption>
      {showTable && (
        <div id={tableId} className="mt-3 overflow-x-auto rounded-xl border border-[#E3E8EF]">
          <table className="w-full text-left text-[15px]">
            <thead>
              <tr className="border-b border-[#E3E8EF] text-sm text-[#6D6E71]">
                <th scope="col" className="py-2.5 px-4 font-medium">{t().colDay}</th>
                <th scope="col" className="py-2.5 px-4 font-medium text-right">{t().colLitres}</th>
                <th scope="col" className="py-2.5 px-4 font-medium text-right">{t().colDrinks}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#EDF0F4]">
              {waterDaily.map((d) => (
                <tr key={d.date}>
                  <td className="py-2.5 px-4 tabular-nums">{formatDay(d.date)}</td>
                  <td className="py-2.5 px-4 text-right font-medium text-[#1B325E] tabular-nums">{fmt(d.total_liters, 1)}</td>
                  <td className="py-2.5 px-4 text-right tabular-nums">{d.measurement_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
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
  airReadings,
  waterDaily,
  avgWater,
  drinkingHorse,
  horses,
}: {
  updatedAt: string;
  live: boolean;
  isLoading: boolean;
  onRefresh: () => void;
  latestAir: StableAirMeasurement | null;
  airReadings: StableAirMeasurement[];
  waterDaily: WaterDailySummary[];
  avgWater: number;
  drinkingHorse: string;
  horses: PublicHorse[];
}) {
  const levels = METRICS.map((m) => ({ def: m, ...summarizeMetric(m, airReadings) }));
  const goodCount = levels.filter((l) => l.level === 'good').length;
  const latestWater = waterDaily[waterDaily.length - 1];
  const diff = latestWater ? latestWater.total_liters - avgWater : 0;
  const tempDef = METRICS[0];

  const s = t();
  const headline =
    levels.some((l) => l.level === 'bad')
      ? s.airHeadlineBad
      : levels.every((l) => l.level === 'good')
        ? s.airHeadlineGood
        : s.airHeadlineMostly;

  return (
    <>
      {/* Hero */}
      <section className="bg-[#1B325E] text-white" aria-labelledby="hero-title">
        <PageContainer>
          <div className="grid gap-10 lg:grid-cols-[1.25fr_1fr] items-center pt-12 pb-24 sm:pt-16 sm:pb-28">
            <div className="space-y-5">
              <p className="text-sm font-medium text-[#FDBE4F]">{s.heroEyebrow}</p>
              <h1 id="hero-title" className="font-display text-4xl sm:text-5xl lg:text-[56px] font-semibold leading-[1.08] tracking-tight text-white text-balance">
                {s.heroTitle}
              </h1>
              <p className="text-lg text-[#DCEEF6] leading-relaxed max-w-[56ch]">
                {s.heroText}
              </p>
              <div className="flex flex-wrap items-center gap-x-5 gap-y-3 pt-1">
                {live && (
                  <span className="inline-flex items-center gap-2 text-sm text-white">
                    <span className="w-2 h-2 rounded-full bg-[#00A34D]" aria-hidden="true" />
                    {s.live}
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
                    {s.refresh}
                  </button>
                )}
              </div>
            </div>

            {/* Ilmanlaadun yhteenveto */}
            <div className="rounded-2xl bg-[#22396B] border border-white/10 p-6 sm:p-7">
              <p className="text-sm text-[#C0E1F0]">{s.latestMeasurement}{latestAir?.location ? ` · ${latestAir.location}` : ''}</p>
              <p className="font-display text-2xl font-semibold text-white mt-1">{headline}</p>
              <p className="mt-4 flex items-baseline gap-2">
                <span className="font-display text-6xl font-semibold tabular-nums text-white">{goodCount}</span>
                <span className="text-lg text-[#C0E1F0]">{s.goodOf(METRICS.length)}</span>
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
                {levels.map(({ def, level, value, avg, instant }) => (
                  <li key={def.key} className="flex items-center justify-between gap-3 py-2.5 text-[15px]">
                    <span className="text-white">
                      {metricText(def).label}
                      {avg && (
                        <span className="block text-sm text-[#C0E1F0] tabular-nums">
                          {s.avgNow(`${fmt(instant, def.decimals)} ${def.unit}`)}
                        </span>
                      )}
                    </span>
                    <span className="inline-flex items-center gap-2 text-[#DCEEF6] tabular-nums">
                      {fmt(value, def.decimals)} {def.unit}
                      {level && (
                        <span className="inline-flex items-center gap-1 font-medium text-white">
                          <LevelIcon level={level} />
                          {s.levels[level]}
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
        <section aria-label={s.kpiAria} className="grid grid-cols-1 sm:grid-cols-3 gap-4 -mt-14 relative">
          <KpiTile
            icon={<Droplet className="w-5 h-5" aria-hidden="true" />}
            label={s.kpiDrank(drinkingHorse)}
            value={fmt(latestWater?.total_liters, 1)}
            unit="l"
            foot={
              latestWater
                ? s.kpiDrankFoot(diff >= 0 ? '+' : '−', fmt(Math.abs(diff), 1), latestWater.measurement_count)
                : s.noMeasurements
            }
          />
          <KpiTile
            icon={<Thermometer className="w-5 h-5" aria-hidden="true" />}
            label={s.kpiTemp}
            value={fmt(latestAir?.temperature, 1)}
            unit="°C"
            foot={<StatusChip level={levelFor(tempDef, latestAir?.temperature)} />}
          />
          <KpiTile
            icon={<Users className="w-5 h-5" aria-hidden="true" />}
            label={s.kpiHorses}
            value={String(horses.length)}
            foot={horses.map((h) => h.name).join(', ') || '–'}
          />

        </section>

        {/* Talli-ilma suosituksiin verrattuna */}
        <section className="mt-14" aria-labelledby="air-title">
          <div id="air-title">
            <SectionHeader
              title={s.airSection}
              addon={<SourcesInfo />}
              sub={s.airSectionSub}
              action={<MoreLink href={TAB_PATHS.environment}>{s.allMeasurements}</MoreLink>}
            />
          </div>
          {latestAir ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
              {METRICS.map((m) => (
                <AirMetricCard key={m.key} def={m} readings={airReadings} />
              ))}
            </div>
          ) : (
            <div className={`${CARD} p-8 text-base text-[#6D6E71]`}>{t().noAir}</div>
          )}
        </section>

        {/* Juominen + hevoset */}
        <section className="mt-14 grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className={`${CARD} p-5 sm:p-7 lg:col-span-2`}>
            <SectionHeader
              title={s.waterSection(drinkingHorse)}
              sub={s.waterSectionSub(waterDaily.length)}
              action={<MoreLink href={TAB_PATHS.water}>{s.waterLink}</MoreLink>}
            />
            <div className="pt-8">
              <WaterChart waterDaily={waterDaily} avgWater={avgWater} />
            </div>
          </div>

          <div className={`${CARD} p-5 sm:p-7`}>
            <SectionHeader title={s.horses} action={<MoreLink href={TAB_PATHS.horses}>{s.all}</MoreLink>} />
            {horses.length === 0 ? (
              <p className="text-base text-[#6D6E71]">{s.noHorses}</p>
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
  const s = t();

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
        <h1 className="font-display text-3xl sm:text-4xl font-semibold text-[#1B325E] tracking-tight">{s.horses}</h1>
        <p className="text-base text-[#6D6E71] mt-2 max-w-[65ch]">
          {s.horsesIntro}
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[340px_1fr] gap-6 items-start">
        {/* Lista: kapealla näkyy vain, kun hevosta ei ole valittu */}
        <div className={`${CARD} overflow-hidden ${active ? 'hidden lg:block' : ''}`}>
          <div className="p-4 border-b border-[#EDF0F4]">
            <label htmlFor="horse-search" className="block text-sm font-medium text-[#1B325E] mb-1.5">
              {s.searchLabel}
            </label>
            <div className="relative">
              <Search className="w-4 h-4 text-[#6D6E71] absolute left-3 top-1/2 -translate-y-1/2" aria-hidden="true" />
              <input
                id="horse-search"
                type="search"
                value={search}
                onChange={(e) => onSearch(e.target.value)}
                placeholder={s.searchPlaceholder}
                className="w-full min-h-11 pl-9 pr-3 border border-[#C3C9D3] rounded-xl text-base text-[#1B325E] placeholder:text-[#6D6E71] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#1B325E]"
              />
            </div>
          </div>
          {filteredHorses.length === 0 ? (
            <div className="p-6 text-base text-[#6D6E71]">
              {s.noSearchResults(search)}{' '}
              <button type="button" onClick={() => onSearch('')} className={`${LINK} min-h-11`}>
                {s.clearSearch}
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
                          {[h.breed, h.birth_year ? s.born(h.birth_year) : null].filter(Boolean).join(' · ')}
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
              <ArrowLeft className="w-4 h-4" aria-hidden="true" /> {s.allHorses}
            </a>
          )}
          {shown ? <HorseDetail horse={shown} drinkingHorse={drinkingHorse} /> : (
            <div className={`${CARD} p-8 text-base text-[#6D6E71]`}>{s.pickHorse}</div>
          )}
        </div>
      </div>
    </PageContainer>
  );
}

function HorseDetail({ horse, drinkingHorse }: { horse: PublicHorse; drinkingHorse: string }) {
  const s = t();
  const facts: { label: string; value: string }[] = [
    { label: s.factBreed, value: horse.breed || '–' },
    { label: s.factBirth, value: horse.birth_year ? String(horse.birth_year) : '–' },
    { label: s.factStall, value: horse.stall_box || '–' },
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
                <Droplet className="w-4 h-4" aria-hidden="true" /> {s.drinkerTracks}
              </p>
            )}
          </div>
        </div>
        <dl className="grid grid-cols-2 sm:grid-cols-3 gap-4 mt-6 pt-6 border-t border-[#EDF0F4]">
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
            {s.analyses} <span className="text-[#6D6E71] font-normal tabular-nums">({horse.analyses.length})</span>
          </h3>
          {horse.analyses.length === 0 ? (
            <p className="text-base text-[#6D6E71] mt-3">{s.noAnalyses}</p>
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
            {s.notes} <span className="text-[#6D6E71] font-normal tabular-nums">({horse.notes.length})</span>
          </h3>
          {horse.notes.length === 0 ? (
            <p className="text-base text-[#6D6E71] mt-3">
              {s.noNotes}
            </p>
          ) : (
            <ul className="divide-y divide-[#EDF0F4] mt-2">
              {horse.notes.map((n) => (
                <li key={n.id} className="py-4 space-y-1.5">
                  <p className="text-[15px] leading-relaxed">{n.content}</p>
                  <p className="text-xs text-[#6D6E71] tabular-nums">{s.stableTeam} · {formatLocalTimestamp(n.created_at)}</p>
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
  const s = t();
  const totals = waterDaily.map((d) => d.total_liters);
  const stats = [
    { label: s.statLatest, value: fmt(latestWater?.total_liters, 1) },
    { label: s.statAvg, value: fmt(avgWater, 1) },
    { label: s.statMax, value: totals.length ? fmt(Math.max(...totals), 1) : '–' },
    { label: s.statMin, value: totals.length ? fmt(Math.min(...totals), 1) : '–' },
  ];
  return (
    <PageContainer>
      <div className="pt-10 pb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl sm:text-4xl font-semibold text-[#1B325E] tracking-tight">{s.waterTitle(drinkingHorse)}</h1>
          <p className="text-base text-[#6D6E71] mt-2 max-w-[65ch]">
            {s.waterIntro(drinkingHorse)}
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
        <SectionHeader title={s.waterPerDay} />
        <div className="pt-8">
          <WaterChart waterDaily={waterDaily} avgWater={avgWater} height={280} />
        </div>
      </section>

      <section className="mt-6">
        <SectionHeader title={s.singleDrinks} />
        <div className={`${CARD} overflow-x-auto`}>
          <table className="w-full text-left text-[15px]">
            <thead>
              <tr className="border-b border-[#E3E8EF] text-sm text-[#6D6E71]">
                <th scope="col" className="py-3 px-5 font-medium">{s.colTime}</th>
                <th scope="col" className="py-3 px-5 font-medium text-right">{s.colAmount}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#EDF0F4]">
              {waterList.length === 0 ? (
                <tr>
                  <td colSpan={2} className="py-6 px-5 text-[#6D6E71]">{s.noDrinks}</td>
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
// 4. Talli-ilma (Detail / Record)
// =====================================================================

function ValueCell({ def, value }: { def: MetricDef; value: number | null }) {
  // Vuorokausikeskiarvoon perustuvaa ohjearvoa ei verrata yksittäiseen mittaukseen
  const level = def.averaging === '24h' ? null : levelFor(def, value);
  return (
    <td className="py-3 px-4 text-right tabular-nums whitespace-nowrap">
      <span className="inline-flex items-center gap-1.5 justify-end" style={level ? { color: LEVEL_META[level].text } : undefined}>
        {level && <LevelIcon level={level} />}
        <span className="font-medium">{fmt(value, def.decimals)}</span>
        <span className="sr-only">{level ? `, ${t().levels[level]}` : ''}</span>
      </span>
    </td>
  );
}

function EnvironmentPage({ airReadings, updatedAt }: { airReadings: StableAirMeasurement[]; updatedAt: string }) {
  const latest = airReadings[0] ?? null;
  const s = t();
  return (
    <PageContainer>
      <div className="pt-10 pb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl sm:text-4xl font-semibold text-[#1B325E] tracking-tight">{s.envTitle}</h1>
          <p className="text-base text-[#6D6E71] mt-2 max-w-[65ch]">
            {s.envIntro}
          </p>
        </div>
        <UpdatedLine updatedAt={updatedAt} />
      </div>

      <section aria-labelledby="latest-air">
        <h2 id="latest-air" className="sr-only">{s.latestMeasurement}</h2>
        {latest ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            {METRICS.map((m) => (
              <AirMetricCard key={m.key} def={m} readings={airReadings} />
            ))}
          </div>
        ) : (
          <div className={`${CARD} p-8 text-base text-[#6D6E71]`}>{t().noAir}</div>
        )}
      </section>

      <section className="mt-10">
        <SectionHeader title={s.byLocation} sub={s.byLocationSub} />
        <div className={`${CARD} overflow-x-auto`}>
          <table className="w-full text-left text-[15px] min-w-[760px]">
            <thead>
              <tr className="border-b border-[#E3E8EF] text-sm text-[#6D6E71]">
                <th scope="col" className="py-3 px-4 font-medium">{s.colLocation}</th>
                <th scope="col" className="py-3 px-4 font-medium">{s.colTime}</th>
                {METRICS.map((m) => (
                  <th key={m.key} scope="col" className="py-3 px-4 font-medium text-right whitespace-nowrap">
                    {metricText(m).short} <span className="font-normal">{m.unit}</span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[#EDF0F4]">
              {airReadings.slice(0, 12).map((a) => (
                <tr key={a.id}>
                  <td className="py-3 px-4 font-medium text-[#1B325E]">{a.location || a.sensor_id || s.sensor}</td>
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
        <SectionHeader title={s.limits} addon={<SourcesInfo />} sub={s.limitsSub} />
        <div className={`${CARD} overflow-x-auto`}>
          <table className="w-full text-left text-[15px] min-w-[640px]">
            <thead>
              <tr className="border-b border-[#E3E8EF] text-sm text-[#6D6E71]">
                <th scope="col" className="py-3 px-4 font-medium">{s.colMetric}</th>
                {(['good', 'warn', 'bad'] as Level[]).map((l) => (
                  <th key={l} scope="col" className="py-3 px-4 font-medium">
                    <span className="inline-flex items-center gap-1.5" style={{ color: LEVEL_META[l].text }}>
                      <LevelIcon level={l} /> {s.levels[l]}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[#EDF0F4]">
              {METRICS.map((m) => (
                <tr key={m.key}>
                  <td className="py-3 px-4 font-medium text-[#1B325E] whitespace-nowrap">
                    {metricText(m).label}
                    {m.averaging === '24h' && <span className="block text-sm font-normal text-[#6D6E71]">{s.dailyAvg}</span>}
                  </td>
                  {(['good', 'warn', 'bad'] as Level[]).map((l) => (
                    <td key={l} className="py-3 px-4 tabular-nums">
                      {m.bands
                        .filter((b) => b.level === l)
                        .map((b) => rangeText(m, b.from, b.to))
                        .join(s.or)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

    </PageContainer>
  );
}

function rangeText(m: MetricDef, from: number, to: number): string {
  if (from <= m.scaleMin) return `${t().under} ${fmt(to, 0)} ${m.unit}`;
  if (to >= m.scaleMax) return `${t().over} ${fmt(from, 0)} ${m.unit}`;
  return `${fmt(from, 0)}–${fmt(to, 0)} ${m.unit}`;
}
