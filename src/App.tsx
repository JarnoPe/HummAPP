import React, { useEffect, useState, useCallback, useMemo } from 'react';
import {
  Download,
  Smartphone,
  Droplet,
  Wind,
  Video,
  Search,
  RefreshCw,
  Globe,
  Server,
  Copy,
  Check,
  Eye,
  Lock
} from 'lucide-react';

declare global {
  interface Window {
    HUMMAPP_PUBLIC_CONFIG?: {
      apiBaseUrl?: string;
      domainName?: string;
    };
  }
}

interface NfcTag {
  id: number;
  nfc_uid: string;
}

interface HorseNote {
  id: number;
  horse_id: number;
  content: string;
  author_username: string | null;
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
  owner_name: string | null;
  stall_box: string | null;
  description: string | null;
  created_at: string;
  nfc_tags: NfcTag[];
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
  horse_id: number | null;
  horse_name: string | null;
  external_measurement_id: string;
  external_water_id: string;
  measured_at: string;
  liters: number;
  raw_data_json: string | null;
}

interface StableAirMeasurement {
  id: number;
  sensor_id: string;
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
  nfc_uid: string;
  phone_timestamp: string;
  location: string | null;
  status: string;
  video_clip_id: number | null;
  video_clip_status: string | null;
}

interface PublicOverview {
  read_only: boolean;
  generated_at: string;
  water_external_id: string;
  drinking_horse_name: string;
  horses: PublicHorse[];
  water_daily: WaterDailySummary[];
  water_measurements: WaterMeasurement[];
  air_readings: StableAirMeasurement[];
  nfc_events: NfcEventItem[];
}

type PublicTab = 'overview' | 'horses' | 'water' | 'environment' | 'deploy';

function formatUtcTimestamp(iso: string | null | undefined): string {
  if (!iso) return '--';
  return iso.slice(0, 16).replace('T', ' ') + ' UTC';
}

function statusLabelFi(status: string): { label: string; colorClass: string } {
  switch (status) {
    case 'APPROVED':
      return { label: 'Hyväksytty', colorClass: 'text-[#00A34D]' };
    case 'READY':
      return { label: 'Valmis', colorClass: 'text-[#135367]' };
    case 'PROCESSING':
    case 'WAITING_FOR_RECORDING':
      return { label: 'Käsittelyssä', colorClass: 'text-[#F89628]' };
    case 'REJECTED':
      return { label: 'Hylätty', colorClass: 'text-[#6D6E71]' };
    default:
      return { label: 'Tuntematon / Virhe', colorClass: 'text-[#A1342C]' };
  }
}

export default function App() {
  const [activeTab, setActiveTab] = useState<PublicTab>('overview');
  const [data, setData] = useState<PublicOverview | null>(null);
  const [dataSourceMode, setDataSourceMode] = useState<'live' | 'snapshot'>('live');
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [selectedHorseId, setSelectedHorseId] = useState<number | null>(null);
  const [horseSearch, setHorseSearch] = useState('');
  const [previewClip, setPreviewClip] = useState<NfcEventItem | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const apiBase = useMemo(() => {
    const raw = window.HUMMAPP_PUBLIC_CONFIG?.apiBaseUrl?.trim() || '';
    return raw.endsWith('/') ? raw.slice(0, -1) : raw;
  }, []);

  const loadPublicData = useCallback(async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const liveUrl = `${apiBase}/api/public/overview`;
      const res = await fetch(liveUrl);
      if (res.ok) {
        const json: PublicOverview = await res.json();
        setData(json);
        setDataSourceMode('live');
        setSelectedHorseId((prev) => prev ?? json.horses[0]?.id ?? null);
        setIsLoading(false);
        return;
      }
      throw new Error(`HTTP ${res.status}`);
    } catch {
      // Jos staattinen GitHub Pages ilman elävää backendiä, käytetään public-data.json tilannekuvaa
      try {
        const snapRes = await fetch('/public-data.json');
        if (snapRes.ok) {
          const json: PublicOverview = await snapRes.json();
          setData(json);
          setDataSourceMode('snapshot');
          setSelectedHorseId((prev) => prev ?? json.horses[0]?.id ?? null);
          setIsLoading(false);
          return;
        }
      } catch {
        // fallback failed
      }
      setLoadError('Julkisen datan lataus epäonnistui. Tarkista palvelimen yhteys.');
      setIsLoading(false);
    }
  }, [apiBase]);

  useEffect(() => {
    loadPublicData();
  }, [loadPublicData]);

  const copyText = (value: string, key: string) => {
    navigator.clipboard.writeText(value);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const horses = data?.horses ?? [];
  const filteredHorses = useMemo(() => {
    const q = horseSearch.trim().toLowerCase();
    if (!q) return horses;
    return horses.filter(
      (h) =>
        h.name.toLowerCase().includes(q) ||
        (h.breed && h.breed.toLowerCase().includes(q)) ||
        (h.owner_name && h.owner_name.toLowerCase().includes(q)) ||
        (h.stall_box && h.stall_box.toLowerCase().includes(q))
    );
  }, [horses, horseSearch]);

  const activeHorse = useMemo(() => {
    return horses.find((h) => h.id === selectedHorseId) ?? filteredHorses[0] ?? null;
  }, [horses, filteredHorses, selectedHorseId]);

  const waterDaily = data?.water_daily ?? [];
  const waterList = data?.water_measurements ?? [];
  const airReadings = data?.air_readings ?? [];
  const nfcEvents = data?.nfc_events ?? [];

  const latestAir = airReadings[0] ?? null;
  const todayStr = new Date().toISOString().slice(0, 10);
  const todayWater = waterDaily.find((d) => d.date === todayStr) ?? waterDaily[waterDaily.length - 1];
  const todayLiters = todayWater ? todayWater.total_liters : 0;
  const todayDrinkCount = todayWater ? todayWater.measurement_count : 0;
  const avgWater =
    waterDaily.length > 0
      ? waterDaily.reduce((acc, item) => acc + item.total_liters, 0) / waterDaily.length
      : 0;

  const envOrigin = typeof window !== 'undefined' ? window.location.origin : 'https://hummapp.fi';

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-[#58595B] flex flex-col">
      {/* 1. EU osarahoittama ja Kaustisen seutukunnan virallinen ylätunniste kaikilla sivuilla */}
      <div className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex items-center justify-between gap-6">
          <a
            href="#top"
            onClick={(e) => {
              e.preventDefault();
              setActiveTab('overview');
            }}
            className="flex items-center shrink-0 focus-visible:outline-2 focus-visible:outline-[#1B325E]"
            aria-label="Euroopan unionin osarahoittama"
          >
            <img
              src="/assets/aistudio/fi_v_euroopan_unionin_osarahoittama_pos_ea7e28c8.jpg"
              alt="Euroopan unionin osarahoittama"
              referrerPolicy="no-referrer"
              className="h-12 sm:h-14 w-auto object-contain"
            />
          </a>

          <div className="hidden lg:block text-center text-xs text-[#6D6E71]">
            Kaustisen seutukunnan hevostalouden pilottihanke · Julkinen tietonäkymä (hummapp.fi)
          </div>

          <a
            href="#top"
            onClick={(e) => {
              e.preventDefault();
              setActiveTab('overview');
            }}
            className="flex items-center shrink-0 focus-visible:outline-2 focus-visible:outline-[#1B325E]"
            aria-label="Kaustisen seutukunta"
          >
            <img
              src="/assets/aistudio/KASE_logo_4a01b836.png"
              alt="Kaustisen seutukunta"
              referrerPolicy="no-referrer"
              className="h-12 sm:h-14 w-auto object-contain"
            />
          </a>
        </div>

        {/* Kaustisen seutukunnan väriaksenttiviiva */}
        <div className="h-1 w-full flex" aria-hidden="true">
          <div className="w-1/4 bg-[#FDBE4F]" />
          <div className="w-1/4 bg-[#C60651]" />
          <div className="w-1/2 bg-[#1B325E]" />
        </div>
      </div>

      {/* 2. Päänavigaatio (3-zone Top Bar Contract) */}
      <header className="bg-[#1B325E] text-white sticky top-0 z-40 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between gap-8">
          <a
            href="#overview"
            onClick={(e) => {
              e.preventDefault();
              setActiveTab('overview');
            }}
            className="text-xl font-bold tracking-tight text-white whitespace-nowrap shrink-0"
            style={{ fontFamily: 'var(--font-display)' }}
          >
            Humm<span className="text-[#FDBE4F]">APP</span>
          </a>

          <nav aria-label="Päävalikko" className="hidden md:flex items-center gap-6 text-sm font-semibold overflow-x-auto">
            <button
              onClick={() => setActiveTab('overview')}
              className={`py-1.5 border-b-2 transition-colors whitespace-nowrap shrink-0 ${
                activeTab === 'overview'
                  ? 'border-[#FDBE4F] text-white'
                  : 'border-transparent text-slate-200 hover:text-white'
              }`}
            >
              Katsaus
            </button>
            <button
              onClick={() => setActiveTab('horses')}
              className={`py-1.5 border-b-2 transition-colors whitespace-nowrap shrink-0 ${
                activeTab === 'horses'
                  ? 'border-[#FDBE4F] text-white'
                  : 'border-transparent text-slate-200 hover:text-white'
              }`}
            >
              Hevoset
            </button>
            <button
              onClick={() => setActiveTab('water')}
              className={`py-1.5 border-b-2 transition-colors whitespace-nowrap shrink-0 ${
                activeTab === 'water'
                  ? 'border-[#FDBE4F] text-white'
                  : 'border-transparent text-slate-200 hover:text-white'
              }`}
            >
              Juoma-automaatti
            </button>
            <button
              onClick={() => setActiveTab('environment')}
              className={`py-1.5 border-b-2 transition-colors whitespace-nowrap shrink-0 ${
                activeTab === 'environment'
                  ? 'border-[#FDBE4F] text-white'
                  : 'border-transparent text-slate-200 hover:text-white'
              }`}
            >
              Talli-ilma ja Videot
            </button>
            <button
              onClick={() => setActiveTab('deploy')}
              className={`py-1.5 border-b-2 transition-colors whitespace-nowrap shrink-0 ${
                activeTab === 'deploy'
                  ? 'border-[#FDBE4F] text-white'
                  : 'border-transparent text-slate-200 hover:text-white'
              }`}
            >
              Julkaisuohje
            </button>
          </nav>

          <div className="flex items-center gap-3 shrink-0">
            <a
              href="/hummapp-android.zip"
              download="hummapp-android.zip"
              className="inline-flex items-center gap-2 px-4 py-2 bg-[#C60651] hover:bg-[#a30542] text-white text-xs font-bold rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              <Smartphone className="w-4 h-4" />
              <span>Lataa Android</span>
            </a>
          </div>
        </div>

        {/* Mobiilivalikko kapeille näytöille */}
        <div className="md:hidden border-t border-white/15 px-4 py-2 flex items-center gap-4 overflow-x-auto text-xs font-semibold">
          <button
            onClick={() => setActiveTab('overview')}
            className={`whitespace-nowrap shrink-0 ${activeTab === 'overview' ? 'text-[#FDBE4F]' : 'text-slate-200'}`}
          >
            Katsaus
          </button>
          <button
            onClick={() => setActiveTab('horses')}
            className={`whitespace-nowrap shrink-0 ${activeTab === 'horses' ? 'text-[#FDBE4F]' : 'text-slate-200'}`}
          >
            Hevoset
          </button>
          <button
            onClick={() => setActiveTab('water')}
            className={`whitespace-nowrap shrink-0 ${activeTab === 'water' ? 'text-[#FDBE4F]' : 'text-slate-200'}`}
          >
            Juoma-automaatti
          </button>
          <button
            onClick={() => setActiveTab('environment')}
            className={`whitespace-nowrap shrink-0 ${activeTab === 'environment' ? 'text-[#FDBE4F]' : 'text-slate-200'}`}
          >
            Talli-ilma ja Videot
          </button>
          <button
            onClick={() => setActiveTab('deploy')}
            className={`whitespace-nowrap shrink-0 ${activeTab === 'deploy' ? 'text-[#FDBE4F]' : 'text-slate-200'}`}
          >
            Julkaisuohje
          </button>
        </div>
      </header>

      {/* Pääsisältö */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Julkisen vain luku -näkymän ilmoitusrivi */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200 pb-4 text-xs text-[#6D6E71]">
          <div className="flex items-center gap-2">
            <Lock className="w-3.5 h-3.5 text-[#1B325E] shrink-0" />
            <span>
              Julkinen vain luku -näkymä ({dataSourceMode === 'live' ? 'Live-yhteys tietokantaan' : 'Staattinen tilannekuva'})
              {' · '}Tietojen muokkaus on estetty verkkosivustolla
            </span>
          </div>
          <div className="flex items-center gap-4">
            <span className="font-mono tabular-nums">Päivitetty: {formatUtcTimestamp(data?.generated_at)}</span>
            <button
              onClick={loadPublicData}
              className="inline-flex items-center gap-1.5 text-[#1B325E] hover:text-[#C60651] font-semibold transition-colors whitespace-nowrap shrink-0"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
              <span>Päivitä</span>
            </button>
          </div>
        </div>

        {loadError && (
          <div className="p-4 bg-white border border-[#A1342C] rounded-xl text-sm text-[#A1342C]">
            {loadError}
          </div>
        )}

        {/* =============================================================== */}
        {/* 1. KATSAUS */}
        {/* =============================================================== */}
        {activeTab === 'overview' && (
          <div className="space-y-8">
            {/* Hero-esittely */}
            <section className="bg-white border border-slate-200 rounded-xl p-6 sm:p-8 flex flex-col lg:flex-row lg:items-center justify-between gap-8">
              <div className="space-y-3 max-w-2xl">
                <p className="text-xs font-semibold text-[#C60651]">
                  Kaustisen seutukunta · Euroopan unionin osarahoittama pilotti
                </p>
                <h1 className="text-3xl sm:text-4xl font-bold text-[#1B325E] tracking-tight text-balance">
                  Hevosten hyvinvoinnin ja talliolosuhteiden julkinen seuranta
                </h1>
                <p className="text-base text-[#58595B] leading-relaxed">
                  Tämä sivu näyttää HummAPP-pilotin keräämät mittaustulokset, talli-ilman olosuhteet,
                  NFC-videointitapahtumat sekä Antero-hevosen juoma-automaatin tiedot. Tiedot päivittyvät
                  automaattisesti, ja kaikki tietojen muokkaus tapahtuu erikseen valtuutetussa Android-sovelluksessa.
                </p>
              </div>
              <div className="flex flex-col sm:flex-row gap-3 shrink-0">
                <button
                  onClick={() => setActiveTab('horses')}
                  className="px-5 py-2.5 bg-[#1B325E] hover:bg-[#135367] text-white text-sm font-semibold rounded-lg transition-colors whitespace-nowrap shrink-0"
                >
                  Selaa hevosia
                </button>
                <a
                  href="/hummapp-android.zip"
                  download="hummapp-android.zip"
                  className="px-5 py-2.5 border border-slate-300 hover:border-[#1B325E] text-[#1B325E] text-sm font-semibold rounded-lg transition-colors inline-flex items-center justify-center gap-2 whitespace-nowrap shrink-0"
                >
                  <Download className="w-4 h-4" />
                  <span>Android-sovellus (.zip)</span>
                </a>
              </div>
            </section>

            {/* 4-sarakkeinen KPI-rivi */}
            <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-2">
                <div className="flex items-center justify-between text-xs text-[#6D6E71]">
                  <span className="font-semibold text-[#135367]">Anteron juominen</span>
                  <Droplet className="w-4 h-4 text-[#135367]" />
                </div>
                <div className="text-3xl font-bold text-[#1B325E] font-mono tabular-nums">
                  {todayLiters.toFixed(1)} <span className="text-sm font-normal text-[#6D6E71]">L</span>
                </div>
                <p className="text-xs text-[#6D6E71] tabular-nums">
                  {todayDrinkCount} mittausta · {todayWater?.date ?? '--'}
                </p>
              </div>

              <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-2">
                <div className="flex items-center justify-between text-xs text-[#6D6E71]">
                  <span className="font-semibold text-[#00A34D]">Talli-ilma</span>
                  <Wind className="w-4 h-4 text-[#00A34D]" />
                </div>
                <div className="text-3xl font-bold text-[#1B325E] font-mono tabular-nums">
                  {latestAir?.temperature ?? '--'} <span className="text-sm font-normal text-[#6D6E71]">°C</span>
                </div>
                <p className="text-xs text-[#6D6E71] tabular-nums">
                  Kosteus {latestAir?.humidity ?? '--'} % · {latestAir?.location ?? 'Päätalli'}
                </p>
              </div>

              <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-2">
                <div className="flex items-center justify-between text-xs text-[#6D6E71]">
                  <span className="font-semibold text-[#1B325E]">Seurattavat hevoset</span>
                  <Eye className="w-4 h-4 text-[#1B325E]" />
                </div>
                <div className="text-3xl font-bold text-[#1B325E] font-mono tabular-nums">{horses.length}</div>
                <p className="text-xs text-[#6D6E71]">
                  Vain luku · profiilit ja muistiinpanot
                </p>
              </div>

              <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-2">
                <div className="flex items-center justify-between text-xs text-[#6D6E71]">
                  <span className="font-semibold text-[#C60651]">NFC-videointikerrat</span>
                  <Video className="w-4 h-4 text-[#C60651]" />
                </div>
                <div className="text-3xl font-bold text-[#1B325E] font-mono tabular-nums">{nfcEvents.length}</div>
                <p className="text-xs text-[#6D6E71]">
                  50 s leikkeet kameralta
                </p>
              </div>
            </section>

            {/* Anteron juomakuvaaja + Talli-ilman palkit */}
            <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2 bg-white border border-slate-200 rounded-xl p-6 space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-lg font-bold text-[#1B325E]">Anteron päivittäinen juomamäärä</h2>
                    <p className="text-xs text-[#6D6E71]">
                      Laite: <span className="font-mono">{data?.water_external_id || 'WATER-METER-ANTERO-01'}</span> · Keskiarvo {avgWater.toFixed(1)} L/vrk
                    </p>
                  </div>
                  <button
                    onClick={() => setActiveTab('water')}
                    className="text-xs font-semibold text-[#C60651] hover:underline whitespace-nowrap shrink-0"
                  >
                    Näytä kaikki mittaukset →
                  </button>
                </div>

                <div className="h-52 flex items-end justify-between gap-2 pt-6 pb-2 border-b border-slate-200">
                  {waterDaily.map((item, idx) => {
                    const maxL = Math.max(45, ...waterDaily.map((d) => d.total_liters));
                    const heightPct = Math.min(100, Math.max(8, Math.round((item.total_liters / maxL) * 100)));
                    const isLatest = idx === waterDaily.length - 1;
                    return (
                      <div key={item.date} className="flex-1 flex flex-col items-center gap-1.5 h-full justify-end">
                        <span className="text-[11px] font-mono font-semibold text-[#58595B] tabular-nums">
                          {item.total_liters.toFixed(0)}L
                        </span>
                        <div
                          style={{ height: `${heightPct}%` }}
                          className={`w-full rounded-t transition-colors ${
                            isLatest ? 'bg-[#C60651]' : 'bg-[#135367] hover:bg-[#1B325E]'
                          }`}
                        />
                        <span className="text-[11px] font-mono text-[#6D6E71] tabular-nums">{item.date.slice(5)}</span>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-bold text-[#1B325E]">Talli-ilman tilanne</h2>
                  <button
                    onClick={() => setActiveTab('environment')}
                    className="text-xs font-semibold text-[#135367] hover:underline"
                  >
                    Historia →
                  </button>
                </div>

                {latestAir ? (
                  <div className="space-y-3.5 text-xs">
                    <AirBar
                      label="Lämpötila"
                      value={`${latestAir.temperature ?? '--'} °C`}
                      target="Optimi 8–14 °C"
                      pct={((latestAir.temperature ?? 11) / 25) * 100}
                      colorClass="bg-[#F89628]"
                    />
                    <AirBar
                      label="Ilmankosteus"
                      value={`${latestAir.humidity ?? '--'} %`}
                      target="Optimi 60–80 %"
                      pct={latestAir.humidity ?? 68}
                      colorClass="bg-[#135367]"
                    />
                    <AirBar
                      label="Ammoniakki (NH₃)"
                      value={`${latestAir.ammonia ?? '--'} ppm`}
                      target="Suositus < 10 ppm"
                      pct={((latestAir.ammonia ?? 3) / 12) * 100}
                      colorClass={(latestAir.ammonia ?? 0) > 10 ? 'bg-[#A1342C]' : 'bg-[#FDBE4F]'}
                    />
                    <AirBar
                      label="Hiilidioksidi (CO₂)"
                      value={`${latestAir.co2 ?? '--'} ppm`}
                      target="Suositus < 1500 ppm"
                      pct={((latestAir.co2 ?? 800) / 2000) * 100}
                      colorClass="bg-[#1B325E]"
                    />
                    <AirBar
                      label="Pienhiukkaset (PM2.5)"
                      value={`${latestAir.particulate_matter ?? '--'} µg/m³`}
                      target="Pölykuorma"
                      pct={((latestAir.particulate_matter ?? 20) / 60) * 100}
                      colorClass="bg-[#00A34D]"
                    />
                  </div>
                ) : (
                  <p className="text-xs text-[#6D6E71]">Ei mittaustietoja saatavilla.</p>
                )}
              </div>
            </section>

            {/* Viimeisimmät hevoshavainnot */}
            <section className="bg-white border border-slate-200 rounded-xl p-6 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-bold text-[#1B325E]">Hevoset ja viimeisimmät muistiinpanot</h2>
                <button
                  onClick={() => setActiveTab('horses')}
                  className="text-xs font-semibold text-[#C60651] hover:underline"
                >
                  Avaa hevosluettelo →
                </button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {horses.slice(0, 3).map((h) => (
                  <button
                    key={h.id}
                    onClick={() => {
                      setSelectedHorseId(h.id);
                      setActiveTab('horses');
                    }}
                    className="text-left p-4 rounded-lg border border-slate-200 hover:border-[#1B325E] transition-colors space-y-2 bg-slate-50/50"
                  >
                    <div className="flex items-baseline justify-between gap-2">
                      <span className="text-base font-bold text-[#1B325E]">{h.name}</span>
                      <span className="text-xs text-[#6D6E71]">{h.stall_box || 'Talli'}</span>
                    </div>
                    <p className="text-xs text-[#6D6E71]">
                      {[h.breed, h.birth_year ? `s. ${h.birth_year}` : null].filter(Boolean).join(' · ') || 'Hevosen perustiedot'}
                    </p>
                    <p className="text-xs text-[#58595B] line-clamp-2">
                      {h.notes[0]?.content || h.description || 'Ei viimeisimpiä muistiinpanoja.'}
                    </p>
                  </button>
                ))}
              </div>
            </section>
          </div>
        )}

        {/* =============================================================== */}
        {/* 2. HEVOSET & MUISTIINPANOT (VAIN LUKU) */}
        {/* =============================================================== */}
        {activeTab === 'horses' && (
          <div className="space-y-6">
            <div className="bg-white border border-slate-200 rounded-xl p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h1 className="text-2xl font-bold text-[#1B325E]">Hevoset, muistiinpanot ja liikeanalyysit</h1>
                <p className="text-xs text-[#6D6E71] mt-1">
                  Julkinen katselutila · Tietojen muokkaus ja uusien muistiinpanojen kirjaus tehdään mobiilisovelluksella.
                </p>
              </div>
              <div className="relative w-full sm:w-64">
                <Search className="w-4 h-4 text-[#939598] absolute left-3 top-2.5" />
                <input
                  type="text"
                  value={horseSearch}
                  onChange={(e) => setHorseSearch(e.target.value)}
                  placeholder="Hae hevosen nimellä..."
                  className="w-full pl-9 pr-3 py-2 border border-slate-300 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-[#1B325E]"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Hevosluettelo */}
              <div className="bg-white border border-slate-200 rounded-xl divide-y divide-slate-100 h-fit">
                {filteredHorses.length === 0 ? (
                  <div className="p-6 text-xs text-[#6D6E71]">Hakuehdoilla ei löytynyt hevosia.</div>
                ) : (
                  filteredHorses.map((h) => {
                    const isSelected = activeHorse?.id === h.id;
                    return (
                      <button
                        key={h.id}
                        onClick={() => setSelectedHorseId(h.id)}
                        className={`w-full text-left p-4 transition-colors ${
                          isSelected ? 'bg-[#1B325E] text-white' : 'hover:bg-slate-50'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className={`font-bold text-base ${isSelected ? 'text-white' : 'text-[#1B325E]'}`}>
                            {h.name}
                          </span>
                          <span className={`text-xs font-mono ${isSelected ? 'text-[#FDBE4F]' : 'text-[#6D6E71]'}`}>
                            {h.stall_box || `#${h.id}`}
                          </span>
                        </div>
                        <div className={`text-xs mt-1 ${isSelected ? 'text-slate-200' : 'text-[#6D6E71]'}`}>
                          {[h.breed, h.birth_year ? `s. ${h.birth_year}` : null].filter(Boolean).join(' · ') || 'Perustiedot'}
                        </div>
                      </button>
                    );
                  })
                )}
              </div>

              {/* Valitun hevosen vain luku -näkymä */}
              <div className="lg:col-span-2 space-y-6">
                {activeHorse ? (
                  <>
                    <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4">
                      <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-2 border-b border-slate-100 pb-4">
                        <div>
                          <h2 className="text-2xl font-bold text-[#1B325E]">{activeHorse.name}</h2>
                          <p className="text-xs text-[#6D6E71] mt-1">
                            {[
                              activeHorse.breed,
                              activeHorse.birth_year ? `Syntymävuosi ${activeHorse.birth_year}` : null,
                              activeHorse.stall_box,
                            ]
                              .filter(Boolean)
                              .join(' · ') || `Hevos-ID #${activeHorse.id}`}
                          </p>
                        </div>
                        {activeHorse.name.toLowerCase() === 'antero' && (
                          <span className="text-xs font-semibold text-[#135367]">
                            Juoma-automaatti aktiivinen
                          </span>
                        )}
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                        <div>
                          <div className="text-[#6D6E71]">Omistaja / Talli</div>
                          <div className="font-semibold text-[#1B325E] mt-0.5">
                            {activeHorse.owner_name || 'Ei määritetty'}
                          </div>
                        </div>
                        <div>
                          <div className="text-[#6D6E71]">NFC-riimutunniste</div>
                          <div className="font-mono text-[#1B325E] mt-0.5">
                            {activeHorse.nfc_tags.length > 0
                              ? activeHorse.nfc_tags.map((t) => t.nfc_uid).join(', ')
                              : 'Ei liitettyä tagia'}
                          </div>
                        </div>
                      </div>

                      {activeHorse.description && (
                        <p className="text-sm text-[#58595B] leading-relaxed pt-1">{activeHorse.description}</p>
                      )}
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      {/* Muistiinpanot (vain luku) */}
                      <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-3">
                        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                          <h3 className="text-base font-bold text-[#1B325E]">Muistiinpanot</h3>
                          <span className="text-xs font-mono text-[#6D6E71]">{activeHorse.notes.length} kpl</span>
                        </div>
                        {activeHorse.notes.length === 0 ? (
                          <p className="text-xs text-[#6D6E71]">Ei kirjattuja muistiinpanoja.</p>
                        ) : (
                          <div className="divide-y divide-slate-100">
                            {activeHorse.notes.map((n) => (
                              <div key={n.id} className="py-3 first:pt-0 last:pb-0 space-y-1">
                                <p className="text-sm text-[#58595B] leading-relaxed">{n.content}</p>
                                <div className="text-[11px] text-[#6D6E71]">
                                  {n.author_username || 'Tallitiimi'} · {formatUtcTimestamp(n.created_at)}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>

                      {/* Liikeanalyysit (vain luku) */}
                      <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-3">
                        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                          <h3 className="text-base font-bold text-[#1B325E]">Liikeanalyysit</h3>
                          <span className="text-xs font-mono text-[#6D6E71]">{activeHorse.analyses.length} kpl</span>
                        </div>
                        {activeHorse.analyses.length === 0 ? (
                          <p className="text-xs text-[#6D6E71]">Ei tallennettuja liikeanalyysejä.</p>
                        ) : (
                          <div className="divide-y divide-slate-100">
                            {activeHorse.analyses.map((a) => (
                              <div key={a.id} className="py-3 first:pt-0 last:pb-0 space-y-1">
                                <div className="flex items-center justify-between gap-2">
                                  <span className="text-xs font-bold text-[#1B325E]">{a.analysis_method}</span>
                                  <span className={`text-[11px] font-semibold ${statusLabelFi(a.status).colorClass}`}>
                                    {statusLabelFi(a.status).label}
                                  </span>
                                </div>
                                <p className="text-xs text-[#58595B] leading-relaxed">{a.summary}</p>
                                <div className="text-[11px] text-[#6D6E71]">
                                  {formatUtcTimestamp(a.analysis_timestamp)}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="bg-white border border-slate-200 rounded-xl p-6 text-sm text-[#6D6E71]">
                    Valitse hevonen vasemmalta nähdäksesi tiedot.
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* =============================================================== */}
        {/* 3. ANTERON JUOMA-AUTOMAATTI (VAIN LUKU) */}
        {/* =============================================================== */}
        {activeTab === 'water' && (
          <div className="space-y-6">
            <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-2 border-b border-slate-100 pb-4">
                <div>
                  <h1 className="text-2xl font-bold text-[#1B325E]">Juoma-automaatin seuranta: Antero</h1>
                  <p className="text-xs text-[#6D6E71] mt-1">
                    Laitetunnus <span className="font-mono">{data?.water_external_id || 'WATER-METER-ANTERO-01'}</span> · Pilotissa juoma-automaatti on vain Anterolla.
                  </p>
                </div>
                <div className="text-right font-mono tabular-nums">
                  <div className="text-2xl font-bold text-[#135367]">{todayLiters.toFixed(1)} L</div>
                  <div className="text-xs text-[#6D6E71]">Tänään · {todayDrinkCount} juomiskertaa</div>
                </div>
              </div>

              <div className="h-52 flex items-end justify-between gap-2 pt-4 pb-2 border-b border-slate-200">
                {waterDaily.map((item, idx) => {
                  const maxL = Math.max(45, ...waterDaily.map((d) => d.total_liters));
                  const heightPct = Math.min(100, Math.max(8, Math.round((item.total_liters / maxL) * 100)));
                  const isLatest = idx === waterDaily.length - 1;
                  return (
                    <div key={item.date} className="flex-1 flex flex-col items-center gap-1.5 h-full justify-end">
                      <span className="text-[11px] font-mono font-semibold text-[#58595B] tabular-nums">
                        {item.total_liters.toFixed(1)}
                      </span>
                      <div
                        style={{ height: `${heightPct}%` }}
                        className={`w-full rounded-t ${isLatest ? 'bg-[#C60651]' : 'bg-[#135367]'}`}
                      />
                      <span className="text-[11px] font-mono text-[#6D6E71] tabular-nums">{item.date.slice(5)}</span>
                    </div>
                  );
                })}
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-slate-200 text-[#6D6E71] font-semibold">
                      <th className="py-2.5 px-3">Mittaus-ID</th>
                      <th className="py-2.5 px-3">Aikaleima</th>
                      <th className="py-2.5 px-3 text-right">Määrä</th>
                      <th className="py-2.5 px-3">Virtaus / Kesto / Lämpötila</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {waterList.map((m) => {
                      let tel: { flow_rate_lpm?: number; duration_sec?: number; temp_celsius?: number } | null = null;
                      try {
                        tel = m.raw_data_json ? JSON.parse(m.raw_data_json) : null;
                      } catch {
                        tel = null;
                      }
                      return (
                        <tr key={m.id} className="hover:bg-slate-50">
                          <td className="py-2.5 px-3 font-mono text-[#58595B]">{m.external_measurement_id}</td>
                          <td className="py-2.5 px-3 font-mono text-[#6D6E71] tabular-nums">
                            {formatUtcTimestamp(m.measured_at)}
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono font-bold text-[#1B325E] tabular-nums">
                            {m.liters.toFixed(1)} L
                          </td>
                          <td className="py-2.5 px-3 font-mono text-[#6D6E71] tabular-nums">
                            {tel
                              ? `${tel.flow_rate_lpm ?? '--'} L/min · ${tel.duration_sec ?? '--'} s · ${tel.temp_celsius ?? '--'} °C`
                              : '--'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* =============================================================== */}
        {/* 4. TALLI-ILMA & NFC-VIDEOT (VAIN LUKU) */}
        {/* =============================================================== */}
        {activeTab === 'environment' && (
          <div className="space-y-6">
            {/* Talli-ilma taulukko */}
            <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4">
              <div>
                <h1 className="text-2xl font-bold text-[#1B325E]">Talli-ilman olosuhdemittaukset</h1>
                <p className="text-xs text-[#6D6E71] mt-1">
                  Lämpötila, suhteellinen kosteus, ammoniakki (NH₃), hiilidioksidi (CO₂) ja pienhiukkaset (PM2.5).
                </p>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-slate-200 text-[#6D6E71] font-semibold">
                      <th className="py-2.5 px-3">Anturi / Sijainti</th>
                      <th className="py-2.5 px-3">Aikaleima</th>
                      <th className="py-2.5 px-3 text-right">Lämpö</th>
                      <th className="py-2.5 px-3 text-right">Kosteus</th>
                      <th className="py-2.5 px-3 text-right">NH₃</th>
                      <th className="py-2.5 px-3 text-right">CO₂</th>
                      <th className="py-2.5 px-3 text-right">PM2.5</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {airReadings.slice(0, 12).map((a) => (
                      <tr key={a.id} className="hover:bg-slate-50">
                        <td className="py-2.5 px-3 font-semibold text-[#1B325E]">{a.location || a.sensor_id}</td>
                        <td className="py-2.5 px-3 font-mono text-[#6D6E71] tabular-nums">
                          {formatUtcTimestamp(a.measured_at)}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums">{a.temperature ?? '--'} °C</td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums">{a.humidity ?? '--'} %</td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums">{a.ammonia ?? '--'} ppm</td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums">{a.co2 ?? '--'} ppm</td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums">{a.particulate_matter ?? '--'} µg/m³</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* NFC-tapahtumat ja julkiset leikkeet (vain katselu) */}
            <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4">
              <div>
                <h2 className="text-lg font-bold text-[#1B325E]">NFC-videointitapahtumat (vain katselu)</h2>
                <p className="text-xs text-[#6D6E71] mt-1">
                  Valmiit ja hyväksytyt videoleikkeet voidaan toistaa tässä. Hyväksyntä ja hylkäys tehdään mobiilisovelluksessa.
                </p>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-slate-200 text-[#6D6E71] font-semibold">
                      <th className="py-2.5 px-3">Tapahtuma</th>
                      <th className="py-2.5 px-3">Hevonen</th>
                      <th className="py-2.5 px-3">Sijainti</th>
                      <th className="py-2.5 px-3">Aika</th>
                      <th className="py-2.5 px-3">Tila</th>
                      <th className="py-2.5 px-3 text-right">Video</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {nfcEvents.map((ev) => {
                      const st = statusLabelFi(ev.status);
                      const canPlay =
                        ev.video_clip_id &&
                        dataSourceMode === 'live' &&
                        (ev.video_clip_status === 'READY' || ev.video_clip_status === 'APPROVED');
                      return (
                        <tr key={ev.id} className="hover:bg-slate-50">
                          <td className="py-2.5 px-3 font-mono font-semibold text-[#1B325E]">#{ev.id}</td>
                          <td className="py-2.5 px-3 font-semibold text-[#1B325E]">{ev.horse_name || 'Tuntematon'}</td>
                          <td className="py-2.5 px-3 text-[#6D6E71]">{ev.location || 'kuvausalue-1'}</td>
                          <td className="py-2.5 px-3 font-mono text-[#6D6E71] tabular-nums">
                            {formatUtcTimestamp(ev.phone_timestamp)}
                          </td>
                          <td className={`py-2.5 px-3 font-semibold ${st.colorClass}`}>{st.label}</td>
                          <td className="py-2.5 px-3 text-right">
                            {canPlay ? (
                              <button
                                onClick={() => setPreviewClip(ev)}
                                className="px-3 py-1 bg-[#1B325E] hover:bg-[#135367] text-white font-semibold rounded text-xs transition-colors"
                              >
                                Katso leike
                              </button>
                            ) : (
                              <span className="text-[#939598]">—</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {previewClip && previewClip.video_clip_id && (
                <div className="mt-4 bg-[#1B325E] text-white p-5 rounded-xl space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="text-sm font-bold">
                      Leike #{previewClip.video_clip_id} · {previewClip.horse_name}
                    </div>
                    <button
                      onClick={() => setPreviewClip(null)}
                      className="text-xs px-3 py-1 bg-white/10 hover:bg-white/20 rounded"
                    >
                      Sulje soitin
                    </button>
                  </div>
                  <video
                    key={previewClip.video_clip_id}
                    controls
                    autoPlay
                    className="w-full max-h-96 rounded-lg bg-black"
                    src={`${apiBase}/api/public/video-clips/${previewClip.video_clip_id}/stream`}
                  />
                </div>
              )}
            </div>
          </div>
        )}

        {/* =============================================================== */}
        {/* 5. HUMMAPP.FI JULKAISU & ANDROID-LATAUKSET */}
        {/* =============================================================== */}
        {activeTab === 'deploy' && (
          <div className="space-y-6">
            <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-5">
              <div>
                <h1 className="text-2xl font-bold text-[#1B325E]">Julkinen hummapp.fi-verkkosivusto ja Android-sovellus</h1>
                <p className="text-sm text-[#58595B] mt-1">
                  Kaikki tarvittavat paketit ovat ladattavissa suoraan alta. GitHub Pages riittää julkisen
                  hummapp.fi-sivuston ilmaiseen julkaisuun ilman erillistä web-hotellia.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="border border-slate-200 rounded-xl p-5 space-y-3 flex flex-col justify-between">
                  <div className="space-y-1.5">
                    <div className="flex items-center gap-2 text-[#1B325E] font-bold">
                      <Globe className="w-4 h-4 text-[#C60651]" />
                      <span>hummapp.fi-verkkosivupaketti</span>
                    </div>
                    <p className="text-xs text-[#6D6E71] leading-relaxed">
                      Valmis staattinen verkkosivusto GitHub Pagesiin: sisältää CNAME-tiedoston (hummapp.fi), EU- ja KASE-logot, vain luku -näkymän ja config.js-osoiteasetuksen.
                    </p>
                  </div>
                  <a
                    href="/hummapp-fi-website.zip"
                    download="hummapp-fi-website.zip"
                    className="w-full py-2 px-4 bg-[#C60651] hover:bg-[#a30542] text-white text-xs font-bold rounded-lg text-center transition-colors inline-flex items-center justify-center gap-2"
                  >
                    <Download className="w-4 h-4" />
                    <span>Lataa hummapp-fi-website.zip</span>
                  </a>
                </div>

                <div className="border border-slate-200 rounded-xl p-5 space-y-3 flex flex-col justify-between">
                  <div className="space-y-1.5">
                    <div className="flex items-center gap-2 text-[#1B325E] font-bold">
                      <Smartphone className="w-4 h-4 text-[#135367]" />
                      <span>Android Kotlin -sovellus</span>
                    </div>
                    <p className="text-xs text-[#6D6E71] leading-relaxed">
                      EU- ja Kaustisen seutukunta -brändätty Android Studio -projekti. Sisältää hevostietojen muokkauksen, muistiinpanojen lisäyksen, NFC-luvun ja juoma-automaatin.
                    </p>
                  </div>
                  <a
                    href="/hummapp-android.zip"
                    download="hummapp-android.zip"
                    className="w-full py-2 px-4 bg-[#1B325E] hover:bg-[#135367] text-white text-xs font-bold rounded-lg text-center transition-colors inline-flex items-center justify-center gap-2"
                  >
                    <Download className="w-4 h-4" />
                    <span>Lataa hummapp-android.zip</span>
                  </a>
                </div>

                <div className="border border-slate-200 rounded-xl p-5 space-y-3 flex flex-col justify-between">
                  <div className="space-y-1.5">
                    <div className="flex items-center gap-2 text-[#1B325E] font-bold">
                      <Server className="w-4 h-4 text-[#00A34D]" />
                      <span>Synology NAS -taustajärjestelmä</span>
                    </div>
                    <p className="text-xs text-[#6D6E71] leading-relaxed">
                      Docker + FastAPI + SQLite WAL + FFmpeg -paketti Synology NASille. Käsittelee kameratallenteet, NFC-rajapinnan ja mittausdatan.
                    </p>
                  </div>
                  <a
                    href="/hummapp.zip"
                    download="hummapp.zip"
                    className="w-full py-2 px-4 border border-slate-300 hover:border-[#1B325E] text-[#1B325E] text-xs font-bold rounded-lg text-center transition-colors inline-flex items-center justify-center gap-2"
                  >
                    <Download className="w-4 h-4" />
                    <span>Lataa hummapp.zip</span>
                  </a>
                </div>
              </div>
            </div>

            {/* DNS ja GitHub Pages ohjeet */}
            <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4">
              <h2 className="text-lg font-bold text-[#1B325E]">Käyttöönotto hummapp.fi-verkkotunnukselle ilman web-hotellia</h2>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 text-xs text-[#58595B] leading-relaxed">
                <div className="space-y-3">
                  <h3 className="text-sm font-bold text-[#1B325E]">1. GitHub Pages julkiselle sivustolle</h3>
                  <p>
                    <strong>GitHub Pages riittää ilmaiseksi</strong> julkisen sivuston (HTML/CSS/JS) hostaukseen. Se ei aja tietokantaa, joten live-data haetaan Synology NASilta tai tämän ympäristön osoitteesta:
                  </p>
                  <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg font-mono flex items-center justify-between gap-2">
                    <span className="truncate text-[#1B325E]">{envOrigin}</span>
                    <button
                      onClick={() => copyText(envOrigin, 'origin')}
                      className="p-1.5 hover:bg-slate-200 rounded shrink-0"
                      title="Kopioi osoite"
                    >
                      {copiedKey === 'origin' ? <Check className="w-3.5 h-3.5 text-[#00A34D]" /> : <Copy className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                  <ol className="list-decimal pl-5 space-y-1">
                    <li>Luo GitHubiin julkinen repositorio (esim. <code className="font-mono">hummapp-fi</code>) ja pura siihen <code className="font-mono">hummapp-fi-website.zip</code>.</li>
                    <li>Avaa <code className="font-mono">Settings → Pages</code> ja valitse haara <code className="font-mono">main</code> (<code className="font-mono">/ (root)</code>).</li>
                    <li>Syötä Custom domain -kenttään <code className="font-mono">hummapp.fi</code> ja ota käyttöön <strong>Enforce HTTPS</strong>.</li>
                  </ol>
                </div>

                <div className="space-y-3">
                  <h3 className="text-sm font-bold text-[#1B325E]">2. Domain-palveluntarjoajan DNS-tietueet</h3>
                  <p>Lisää verkkotunnuksen hallintapaneeliin seuraavat DNS-ohjaukset:</p>
                  <div className="overflow-x-auto border border-slate-200 rounded-lg">
                    <table className="w-full text-left font-mono text-[11px]">
                      <thead className="bg-slate-50 border-b border-slate-200 text-[#6D6E71]">
                        <tr>
                          <th className="py-2 px-3">Tyyppi</th>
                          <th className="py-2 px-3">Nimi</th>
                          <th className="py-2 px-3">Arvo</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        <tr><td className="py-1.5 px-3">A</td><td className="py-1.5 px-3">@</td><td className="py-1.5 px-3">185.199.108.153</td></tr>
                        <tr><td className="py-1.5 px-3">A</td><td className="py-1.5 px-3">@</td><td className="py-1.5 px-3">185.199.109.153</td></tr>
                        <tr><td className="py-1.5 px-3">A</td><td className="py-1.5 px-3">@</td><td className="py-1.5 px-3">185.199.110.153</td></tr>
                        <tr><td className="py-1.5 px-3">A</td><td className="py-1.5 px-3">@</td><td className="py-1.5 px-3">185.199.111.153</td></tr>
                        <tr><td className="py-1.5 px-3">CNAME</td><td className="py-1.5 px-3">www</td><td className="py-1.5 px-3">&lt;tunnuksesi&gt;.github.io</td></tr>
                        <tr><td className="py-1.5 px-3">CNAME</td><td className="py-1.5 px-3">api</td><td className="py-1.5 px-3">&lt;oma-nas&gt;.synology.me</td></tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Alapalkki */}
      <footer className="bg-white border-t border-slate-200 py-5 text-xs text-[#6D6E71]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row justify-between items-center gap-3">
          <div>
            HummAPP Pilotti · Kaustisen seutukunta · Euroopan unionin osarahoittama · hummapp.fi
          </div>
          <div className="flex items-center gap-4">
            <a href="/hummapp-fi-website.zip" download className="text-[#C60651] hover:underline font-semibold">
              hummapp.fi-sivupaketti (.zip)
            </a>
            <a href="/hummapp-android.zip" download className="text-[#1B325E] hover:underline font-semibold">
              Android-sovellus (.zip)
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}

function AirBar({
  label,
  value,
  target,
  pct,
  colorClass,
}: {
  label: string;
  value: string;
  target: string;
  pct: number;
  colorClass: string;
}) {
  const clamped = Math.max(4, Math.min(100, pct));
  return (
    <div className="space-y-1">
      <div className="flex justify-between items-baseline">
        <span className="font-semibold text-[#1B325E]">
          {label}: <span className="font-mono tabular-nums">{value}</span>
        </span>
        <span className="text-[#6D6E71]">{target}</span>
      </div>
      <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
        <div className={`${colorClass} h-2 rounded-full`} style={{ width: `${clamped}%` }} />
      </div>
    </div>
  );
}
