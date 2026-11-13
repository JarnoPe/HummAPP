import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";
import { DatabaseSync } from "node:sqlite";
import express from "express";
import type { Request, Response, NextFunction } from "express";
import { createServer as createViteServer } from "vite";

const PORT = Number(process.env.PORT || 3000);
const SECRET_KEY =
  process.env.SECRET_KEY || "hummapp-pilot-secret-key-change-in-production-32chars";
const DRINKING_HORSE_NAME = process.env.DRINKING_HORSE_NAME || "Antero";
const WATER_EXTERNAL_ID = process.env.WATER_EXTERNAL_ID || "WATER-METER-ANTERO-01";
const ADMIN_USERNAME = process.env.ADMIN_USERNAME || "admin";
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || "Tallipaallikko2026!";

const DATA_DIR = path.resolve(process.cwd(), "data");
const VIDEO_DIR = path.resolve(process.cwd(), "videos");
const PUBLIC_DIR = path.resolve(process.cwd(), "public");
const DB_PATH = path.join(DATA_DIR, "hummapp-env.db");

fs.mkdirSync(DATA_DIR, { recursive: true });
fs.mkdirSync(VIDEO_DIR, { recursive: true });
fs.mkdirSync(PUBLIC_DIR, { recursive: true });

// --- SQLite WAL alustus ---
const db = new DatabaseSync(DB_PATH);
db.exec("PRAGMA journal_mode=WAL;");
db.exec("PRAGMA busy_timeout=5000;");
db.exec("PRAGMA foreign_keys=ON;");

db.exec(`
  CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
  );

  CREATE TABLE IF NOT EXISTS horses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    breed TEXT,
    birth_year INTEGER,
    owner_name TEXT,
    stall_box TEXT,
    description TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
  );

  CREATE TABLE IF NOT EXISTS nfc_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    horse_id INTEGER NOT NULL REFERENCES horses(id) ON DELETE CASCADE,
    nfc_uid TEXT UNIQUE NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
  );

  CREATE TABLE IF NOT EXISTS nfc_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    horse_id INTEGER REFERENCES horses(id) ON DELETE SET NULL,
    nfc_uid TEXT NOT NULL,
    phone_timestamp TEXT NOT NULL,
    server_timestamp TEXT NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    location TEXT,
    status TEXT NOT NULL DEFAULT 'RECEIVED',
    error_message TEXT
  );

  CREATE TABLE IF NOT EXISTS video_clips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nfc_event_id INTEGER NOT NULL REFERENCES nfc_events(id) ON DELETE CASCADE,
    relative_file_path TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'READY',
    created_at TEXT NOT NULL,
    approved_at TEXT,
    rejected_at TEXT,
    deleted_at TEXT
  );

  CREATE TABLE IF NOT EXISTS movement_analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    horse_id INTEGER NOT NULL REFERENCES horses(id) ON DELETE CASCADE,
    video_clip_id INTEGER REFERENCES video_clips(id) ON DELETE SET NULL,
    analysis_method TEXT NOT NULL,
    analysis_timestamp TEXT NOT NULL,
    summary TEXT NOT NULL,
    result_json TEXT,
    status TEXT NOT NULL DEFAULT 'APPROVED',
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL
  );

  CREATE TABLE IF NOT EXISTS water_measurements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    horse_id INTEGER REFERENCES horses(id) ON DELETE SET NULL,
    external_measurement_id TEXT UNIQUE NOT NULL,
    external_water_id TEXT NOT NULL,
    measured_at TEXT NOT NULL,
    liters REAL NOT NULL,
    raw_data_json TEXT,
    created_at TEXT NOT NULL
  );

  CREATE TABLE IF NOT EXISTS stable_air_measurements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sensor_id TEXT NOT NULL,
    location TEXT,
    measured_at TEXT NOT NULL,
    temperature REAL,
    humidity REAL,
    ammonia REAL,
    co2 REAL,
    particulate_matter REAL,
    raw_data_json TEXT,
    created_at TEXT NOT NULL
  );

  CREATE TABLE IF NOT EXISTS horse_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    horse_id INTEGER NOT NULL REFERENCES horses(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL
  );

  CREATE TABLE IF NOT EXISTS system_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    level TEXT NOT NULL,
    event_type TEXT NOT NULL,
    message TEXT NOT NULL,
    details_json TEXT,
    created_at TEXT NOT NULL
  );
`);

// Turvallinen sarakkeiden lisäys olemassa olevaan SQLite-tietokantaan
const horseCols = (db.prepare("PRAGMA table_info(horses)").all() as Array<{ name: string }>).map((c) => c.name);
const extraHorseCols: Array<[string, string]> = [
  ["breed", "TEXT"],
  ["birth_year", "INTEGER"],
  ["owner_name", "TEXT"],
  ["stall_box", "TEXT"],
  ["description", "TEXT"],
];
for (const [col, colType] of extraHorseCols) {
  if (!horseCols.includes(col)) {
    db.exec(`ALTER TABLE horses ADD COLUMN ${col} ${colType};`);
  }
}

// --- Salasanan hajautus & JWT (HS256) ---
function hashPassword(password: string): string {
  const salt = crypto.randomBytes(16).toString("hex");
  const hash = crypto.scryptSync(password, salt, 64).toString("hex");
  return `scrypt:${salt}:${hash}`;
}

function verifyPassword(password: string, stored: string): boolean {
  if (!stored.startsWith("scrypt:")) return false;
  const parts = stored.split(":");
  if (parts.length !== 3) return false;
  const [, salt, originalHash] = parts;
  const candidate = crypto.scryptSync(password, salt, 64).toString("hex");
  return crypto.timingSafeEqual(Buffer.from(candidate, "hex"), Buffer.from(originalHash, "hex"));
}

function base64UrlEncode(input: Buffer | string): string {
  const buf = typeof input === "string" ? Buffer.from(input, "utf8") : input;
  return buf.toString("base64").replace(/=/g, "").replace(/\+/g, "-").replace(/\//g, "_");
}

function signJwt(payload: Record<string, unknown>, expiresMinutes = 43200): string {
  const header = base64UrlEncode(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const exp = Math.floor(Date.now() / 1000) + expiresMinutes * 60;
  const body = base64UrlEncode(JSON.stringify({ ...payload, exp }));
  const sig = base64UrlEncode(
    crypto.createHmac("sha256", SECRET_KEY).update(`${header}.${body}`).digest()
  );
  return `${header}.${body}.${sig}`;
}

function verifyJwt(token: string): Record<string, unknown> | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    const [header, body, sig] = parts;
    const expectedSig = base64UrlEncode(
      crypto.createHmac("sha256", SECRET_KEY).update(`${header}.${body}`).digest()
    );
    if (sig !== expectedSig) return null;
    const decoded = JSON.parse(Buffer.from(body, "base64url").toString("utf8")) as Record<string, unknown>;
    if (typeof decoded.exp === "number" && decoded.exp < Math.floor(Date.now() / 1000)) {
      return null;
    }
    return decoded;
  } catch {
    return null;
  }
}

function utcIsoNow(offsetSeconds = 0): string {
  return new Date(Date.now() + offsetSeconds * 1000).toISOString();
}

function validateAndResolveVideoPath(relativePath: string): string {
  if (!relativePath || relativePath.includes("..") || relativePath.startsWith("/") || relativePath.startsWith("\\")) {
    throw new Error("Luvaton suhteellinen polku (Path Traversal estetty).");
  }
  const resolved = path.resolve(VIDEO_DIR, relativePath);
  if (!resolved.startsWith(VIDEO_DIR + path.sep)) {
    throw new Error("Polku osoittaa sallitun videohakemiston ulkopuolelle.");
  }
  return resolved;
}

function generateMockClipMp4(destPath: string, durationSec = 8): Promise<boolean> {
  return new Promise((resolve) => {
    fs.mkdirSync(path.dirname(destPath), { recursive: true });
    const proc = spawn("ffmpeg", [
      "-y",
      "-f",
      "lavfi",
      "-i",
      `testsrc=duration=${durationSec}:size=640x360:rate=25`,
      "-c:v",
      "libx264",
      "-pix_fmt",
      "yuv420p",
      "-movflags",
      "+faststart",
      destPath,
    ]);
    proc.on("close", (code) => resolve(code === 0));
    proc.on("error", () => resolve(false));
  });
}

// --- Alustusdatan siemenlys (Seed) ---
async function seedInitialData() {
  const now = utcIsoNow();

  // 1. Käyttäjät
  const adminExists = db.prepare("SELECT id FROM users WHERE username = ?").get(ADMIN_USERNAME) as { id: number } | undefined;
  if (!adminExists) {
    db.prepare(
      "INSERT INTO users (username, password_hash, role, active, created_at) VALUES (?, ?, 'admin', 1, ?)"
    ).run(ADMIN_USERNAME, hashPassword(ADMIN_PASSWORD), now);
    db.prepare(
      "INSERT INTO users (username, password_hash, role, active, created_at) VALUES (?, ?, 'user', 1, ?)"
    ).run("tallityontekija", hashPassword("HummAPP2026!"), now);
  }

  // 2. Hevoset & NFC-tagit
  const horseCountRow = db.prepare("SELECT COUNT(*) as cnt FROM horses").get() as { cnt: number };
  if (horseCountRow.cnt === 0) {
    const r1 = db
      .prepare(
        "INSERT INTO horses (name, breed, birth_year, owner_name, stall_box, description, active, created_at) VALUES (?, ?, ?, ?, ?, ?, 1, ?)"
      )
      .run(
        DRINKING_HORSE_NAME,
        "Suomenhevonen",
        2018,
        "Kaustisen Ravikoulu",
        "Karsina 4",
        "Pilottihankkeen juoma-automaatin seurantakohde. Rauhallinen ja tasainen juomarytmi.",
        now
      );
    const anteroId = Number(r1.lastInsertRowid);
    db.prepare("INSERT INTO nfc_tags (horse_id, nfc_uid, active, created_at) VALUES (?, ?, 1, ?)").run(
      anteroId,
      "04A31B92C56F80",
      now
    );

    const r2 = db
      .prepare(
        "INSERT INTO horses (name, breed, birth_year, owner_name, stall_box, description, active, created_at) VALUES (?, ?, ?, ?, ?, ?, 1, ?)"
      )
      .run(
        "Valo",
        "Lämminverinen ravihevonen",
        2020,
        "Kaustisen Ravikoulu",
        "Karsina 2",
        "Liikeanalyysin ja NFC-videokuvauksen säännöllinen seurantaryhmä.",
        now
      );
    const valoId = Number(r2.lastInsertRowid);
    db.prepare("INSERT INTO nfc_tags (horse_id, nfc_uid, active, created_at) VALUES (?, ?, 1, ?)").run(
      valoId,
      "04E24589F10123",
      now
    );

    const r3 = db
      .prepare(
        "INSERT INTO horses (name, breed, birth_year, owner_name, stall_box, description, active, created_at) VALUES (?, ?, ?, ?, ?, ?, 1, ?)"
      )
      .run(
        "Sisu",
        "Suomenhevonen",
        2017,
        "Kaustisen Seudun Tallit",
        "Karsina 7",
        "Kuvausalueen testikohde ja harjoitusravaaja.",
        now
      );
    const sisuId = Number(r3.lastInsertRowid);
    db.prepare("INSERT INTO nfc_tags (horse_id, nfc_uid, active, created_at) VALUES (?, ?, 1, ?)").run(
      sisuId,
      "04F19C32A81204",
      now
    );

    // Alustavat muistiinpanot
    db.prepare("INSERT INTO horse_notes (horse_id, content, user_id, created_at) VALUES (?, ?, 1, ?)").run(
      anteroId,
      "Antero joi aamulla hyvin. Juoma-automaatin virtaus tarkastettu.",
      utcIsoNow(-7200)
    );
    db.prepare("INSERT INTO horse_notes (horse_id, content, user_id, created_at) VALUES (?, ?, 1, ?)").run(
      valoId,
      "Valo siirretty kuvausalueelle kevyen verryttelyn jälkeen.",
      utcIsoNow(-3600)
    );

    // Alustava liikeanalyysi
    db.prepare(
      "INSERT INTO movement_analyses (horse_id, video_clip_id, analysis_method, analysis_timestamp, summary, result_json, status, created_by, created_at) VALUES (?, NULL, ?, ?, ?, ?, 'APPROVED', 1, ?)"
    ).run(
      anteroId,
      "Visuaalinen askellusanalyysi",
      utcIsoNow(-86400),
      "Symmetrinen ja puhdas ravi molempiin suuntiin, ei ontumishavaintoja.",
      JSON.stringify({ symmetry_score: 0.96, stride_length_m: 2.84 }),
      utcIsoNow(-86400)
    );

    // Anteron viimeisen 8 päivän juomadata
    const dailySamples = [
      { daysAgo: 7, liters: [8.1, 7.4, 9.2, 7.3] },
      { daysAgo: 6, liters: [9.0, 8.5, 10.1, 8.9] },
      { daysAgo: 5, liters: [7.2, 8.1, 6.8, 7.7] },
      { daysAgo: 4, liters: [9.5, 9.8, 10.4, 8.5] },
      { daysAgo: 3, liters: [8.4, 8.6, 9.1, 7.9] },
      { daysAgo: 2, liters: [10.2, 9.9, 11.1, 10.3] },
      { daysAgo: 1, liters: [8.7, 9.0, 8.8, 8.6] },
      { daysAgo: 0, liters: [5.9, 6.8, 7.4, 8.2, 5.9] },
    ];

    let idx = 1;
    for (const day of dailySamples) {
      const baseDate = new Date(Date.now() - day.daysAgo * 86400 * 1000);
      day.liters.forEach((l, slot) => {
        const dt = new Date(baseDate);
        dt.setUTCHours(5 + slot * 3, 15 + (slot * 11) % 40, 12, 0);
        if (dt.getTime() > Date.now()) {
          dt.setTime(Date.now() - (slot + 1) * 1800 * 1000);
        }
        const measId = `MOCK-WTR-SEED-${day.daysAgo}-${slot}-${idx++}`;
        const raw = JSON.stringify({
          source: "MockWaterDispenserV1",
          device_serial: WATER_EXTERNAL_ID,
          flow_rate_lpm: Number((7.8 + (slot % 3) * 0.4).toFixed(1)),
          duration_sec: Math.round(l * 7.4),
          temp_celsius: Number((11.8 + (slot % 2) * 0.6).toFixed(1)),
          raw_timestamp: dt.toISOString(),
        });
        db.prepare(
          "INSERT OR IGNORE INTO water_measurements (horse_id, external_measurement_id, external_water_id, measured_at, liters, raw_data_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)"
        ).run(anteroId, measId, WATER_EXTERNAL_ID, dt.toISOString(), l, raw, now);
      });
    }

    // Talli-ilman mittaushistoria (viimeiset 10 tuntia)
    for (let h = 9; h >= 0; h--) {
      const mTime = utcIsoNow(-h * 3600);
      const sensors = [
        { id: "SENSOR-STABLE-MAIN", loc: "Päätalli / Karsinakäytävä", tempBase: 11.4, humBase: 67, nh3Base: 3.1, co2Base: 820, pmBase: 19 },
        { id: "SENSOR-STABLE-BOX-ANTERO", loc: "Karsina 4 (Antero)", tempBase: 12.1, humBase: 69, nh3Base: 3.6, co2Base: 880, pmBase: 22 },
      ];
      for (const s of sensors) {
        const temp = Number((s.tempBase + Math.sin(h) * 0.6).toFixed(1));
        const hum = Number((s.humBase + Math.cos(h) * 2.5).toFixed(1));
        const nh3 = Number((s.nh3Base + Math.abs(Math.sin(h * 0.7)) * 0.8).toFixed(2));
        const co2 = Number((s.co2Base + Math.sin(h * 0.5) * 65).toFixed(0));
        const pm = Number((s.pmBase + Math.abs(Math.cos(h)) * 4.5).toFixed(1));
        db.prepare(
          "INSERT INTO stable_air_measurements (sensor_id, location, measured_at, temperature, humidity, ammonia, co2, particulate_matter, raw_data_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        ).run(s.id, s.loc, mTime, temp, hum, nh3, co2, pm, JSON.stringify({ sensor: s.id, battery_mv: 3280 }), now);
      }
    }

    // Alustavat NFC-tapahtumat & oikeat MP4-testileikkeet
    const ev1Time = utcIsoNow(-5400);
    const ev1 = db
      .prepare(
        "INSERT INTO nfc_events (horse_id, nfc_uid, phone_timestamp, server_timestamp, user_id, location, status) VALUES (?, ?, ?, ?, 1, 'kuvausalue-1', 'APPROVED')"
      )
      .run(anteroId, "04A31B92C56F80", ev1Time, ev1Time);
    const ev1Id = Number(ev1.lastInsertRowid);
    const rel1 = `${anteroId}/2026/11/event_${ev1Id}_seed.mp4`;
    await generateMockClipMp4(validateAndResolveVideoPath(rel1), 6);
    db.prepare(
      "INSERT INTO video_clips (nfc_event_id, relative_file_path, status, created_at, approved_at) VALUES (?, ?, 'APPROVED', ?, ?)"
    ).run(ev1Id, rel1, ev1Time, ev1Time);

    const ev2Time = utcIsoNow(-1800);
    const ev2 = db
      .prepare(
        "INSERT INTO nfc_events (horse_id, nfc_uid, phone_timestamp, server_timestamp, user_id, location, status) VALUES (?, ?, ?, ?, 1, 'kuvausalue-1', 'READY')"
      )
      .run(valoId, "04E24589F10123", ev2Time, ev2Time);
    const ev2Id = Number(ev2.lastInsertRowid);
    const rel2 = `${valoId}/2026/11/event_${ev2Id}_seed.mp4`;
    await generateMockClipMp4(validateAndResolveVideoPath(rel2), 6);
    db.prepare(
      "INSERT INTO video_clips (nfc_event_id, relative_file_path, status, created_at) VALUES (?, ?, 'READY', ?)"
    ).run(ev2Id, rel2, ev2Time);

    db.prepare(
      "INSERT INTO system_events (level, event_type, message, created_at) VALUES ('INFO', 'SYSTEM', ?, ?)"
    ).run("HummAPP pilottiympäristö alustettu onnistuneesti (SQLite WAL).", now);
  } else {
    // Täydennetään olemassa olevien pilottihevosten perustiedot, jos sarakkeet lisättiin migraatiossa NULL-arvoina
    const backfillStmt = db.prepare(
      `UPDATE horses
       SET breed = COALESCE(breed, ?),
           birth_year = COALESCE(birth_year, ?),
           owner_name = COALESCE(owner_name, ?),
           stall_box = COALESCE(stall_box, ?),
           description = COALESCE(description, ?)
       WHERE name = ?`
    );
    backfillStmt.run(
      "Suomenhevonen",
      2018,
      "Kaustisen Ravikoulu",
      "Karsina 4",
      "Pilottihankkeen juoma-automaatin seurantakohde. Rauhallinen ja tasainen juomarytmi.",
      DRINKING_HORSE_NAME
    );
    backfillStmt.run(
      "Lämminverinen ravihevonen",
      2020,
      "Kaustisen Ravikoulu",
      "Karsina 2",
      "Liikeanalyysin ja NFC-videokuvauksen säännöllinen seurantaryhmä.",
      "Valo"
    );
    backfillStmt.run(
      "Suomenhevonen",
      2017,
      "Kaustisen Seudun Tallit",
      "Karsina 7",
      "Kuvausalueen testikohde ja harjoitusravaaja.",
      "Sisu"
    );
  }
}

// --- Express Auth Middleware ---
interface AuthedUser {
  id: number;
  username: string;
  role: string;
}

interface AuthedRequest extends Request {
  user?: AuthedUser;
}

function getAuthToken(req: Request): string | null {
  const authHeader = req.headers.authorization;
  if (authHeader && authHeader.startsWith("Bearer ")) {
    return authHeader.slice(7).trim();
  }
  const queryToken = req.query.token;
  if (typeof queryToken === "string" && queryToken.length > 0) {
    return queryToken;
  }
  return null;
}

function requireAuth(req: AuthedRequest, res: Response, next: NextFunction) {
  const token = getAuthToken(req);
  if (!token) {
    res.status(401).json({ detail: "Kirjautumistieto puuttuu tai se on vanhentunut" });
    return;
  }
  const payload = verifyJwt(token);
  if (!payload || typeof payload.sub !== "string") {
    res.status(401).json({ detail: "Virheellinen tai vanhentunut token" });
    return;
  }
  const user = db
    .prepare("SELECT id, username, role, active FROM users WHERE username = ? AND active = 1")
    .get(payload.sub) as { id: number; username: string; role: string; active: number } | undefined;
  if (!user) {
    res.status(401).json({ detail: "Käyttäjää ei löydy tai tili on passivoitu" });
    return;
  }
  req.user = { id: user.id, username: user.username, role: user.role };
  next();
}

function requireRole(roles: string[]) {
  return (req: AuthedRequest, res: Response, next: NextFunction) => {
    if (!req.user || !roles.includes(req.user.role)) {
      res.status(403).json({ detail: `Toiminto vaatii jonkin rooleista: ${roles.join(", ")}` });
      return;
    }
    next();
  };
}

async function startServer() {
  await seedInitialData();

  const app = express();

  // CORS-otsikot Android- ja selainyhteyksille
  app.use((req, res, next) => {
    res.header("Access-Control-Allow-Origin", "*");
    res.header("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS");
    res.header("Access-Control-Allow-Headers", "Origin, X-Requested-With, Content-Type, Accept, Authorization");
    if (req.method === "OPTIONS") {
      res.sendStatus(204);
      return;
    }
    next();
  });

  app.use(express.json());

  // --- API: Autentikointi ---
  app.post("/api/login", (req: Request, res: Response) => {
    const { username, password } = req.body || {};
    if (!username || !password) {
      res.status(400).json({ detail: "Anna käyttäjätunnus ja salasana" });
      return;
    }
    const user = db
      .prepare("SELECT id, username, password_hash, role, active FROM users WHERE username = ?")
      .get(String(username).trim()) as
      | { id: number; username: string; password_hash: string; role: string; active: number }
      | undefined;

    if (!user || !verifyPassword(String(password), user.password_hash)) {
      res.status(401).json({ detail: "Virheellinen käyttäjätunnus tai salasana" });
      return;
    }
    if (!user.active) {
      res.status(403).json({ detail: "Käyttäjätili on passivoitu" });
      return;
    }

    const access_token = signJwt({ sub: user.username, role: user.role, uid: user.id });
    res.json({
      access_token,
      token_type: "bearer",
      role: user.role,
      username: user.username,
      user_id: user.id,
    });
  });

  app.get("/api/me", requireAuth, (req: AuthedRequest, res: Response) => {
    const user = db
      .prepare("SELECT id, username, role, active, created_at FROM users WHERE id = ?")
      .get(req.user!.id) as Record<string, unknown>;
    res.json({ ...user, active: Boolean(user.active) });
  });

  // --- API: Health & System Status ---
  app.get("/api/health", (_req: Request, res: Response) => {
    try {
      db.prepare("SELECT 1").get();
      res.json({
        status: "ok",
        app: "HummAPP",
        database: "healthy",
        timestamp: utcIsoNow(),
      });
    } catch (err) {
      res.status(500).json({ status: "degraded", error: String(err) });
    }
  });

  app.get("/api/system/status", (_req: Request, res: Response) => {
    const antero = db
      .prepare("SELECT id FROM horses WHERE name = ?")
      .get(DRINKING_HORSE_NAME) as { id: number } | undefined;
    res.json({
      status: antero ? "operational" : "attention_required",
      app_name: "HummAPP",
      version: "1.0.0",
      database_ok: true,
      camera_dir_exists: true,
      video_dir_exists: fs.existsSync(VIDEO_DIR),
      antero_configured: true,
      antero_horse_found: Boolean(antero),
      antero_horse_id: antero ? antero.id : null,
      water_external_id: WATER_EXTERNAL_ID,
      mock_water_enabled: true,
      mock_air_enabled: true,
      uptime_utc: utcIsoNow(),
    });
  });

  // --- API: Hevoset & NFC-tagit ---
  function serializeHorse(h: Record<string, unknown>) {
    const tags = db
      .prepare("SELECT id, horse_id, nfc_uid, active, created_at FROM nfc_tags WHERE horse_id = ? AND active = 1")
      .all(Number(h.id)) as Array<{ id: number; horse_id: number; nfc_uid: string; active: number; created_at: string }>;
    return {
      id: Number(h.id),
      name: String(h.name),
      breed: h.breed ? String(h.breed) : null,
      birth_year: h.birth_year !== null && h.birth_year !== undefined ? Number(h.birth_year) : null,
      owner_name: h.owner_name ? String(h.owner_name) : null,
      stall_box: h.stall_box ? String(h.stall_box) : null,
      description: h.description ? String(h.description) : null,
      active: Boolean(h.active),
      created_at: String(h.created_at),
      nfc_tags: tags.map((t) => ({ ...t, active: Boolean(t.active) })),
    };
  }

  app.get("/api/horses", requireAuth, (_req: Request, res: Response) => {
    const horses = db
      .prepare("SELECT * FROM horses WHERE active = 1 ORDER BY name ASC")
      .all() as Array<Record<string, unknown>>;
    res.json(horses.map(serializeHorse));
  });

  app.post("/api/horses", requireAuth, requireRole(["admin", "user"]), (req: Request, res: Response) => {
    const name = String(req.body?.name || "").trim();
    if (!name) {
      res.status(400).json({ detail: "Hevosen nimi vaaditaan." });
      return;
    }
    const existing = db.prepare("SELECT id FROM horses WHERE name = ?").get(name);
    if (existing) {
      res.status(400).json({ detail: `Hevonen nimellä '${name}' on jo olemassa.` });
      return;
    }
    const breed = req.body?.breed ? String(req.body.breed).trim() : null;
    const birthYear = req.body?.birth_year ? Number(req.body.birth_year) : null;
    const ownerName = req.body?.owner_name ? String(req.body.owner_name).trim() : null;
    const stallBox = req.body?.stall_box ? String(req.body.stall_box).trim() : null;
    const description = req.body?.description ? String(req.body.description).trim() : null;
    const now = utcIsoNow();
    const info = db
      .prepare(
        "INSERT INTO horses (name, breed, birth_year, owner_name, stall_box, description, active, created_at) VALUES (?, ?, ?, ?, ?, ?, 1, ?)"
      )
      .run(name, breed, Number.isFinite(birthYear) ? birthYear : null, ownerName, stallBox, description, now);
    const created = db
      .prepare("SELECT * FROM horses WHERE id = ?")
      .get(Number(info.lastInsertRowid)) as Record<string, unknown>;
    res.status(201).json(serializeHorse(created));
  });

  app.get("/api/horses/:id", requireAuth, (req: Request, res: Response) => {
    const horse = db
      .prepare("SELECT * FROM horses WHERE id = ?")
      .get(Number(req.params.id)) as Record<string, unknown> | undefined;
    if (!horse) {
      res.status(404).json({ detail: "Hevosta ei löydy." });
      return;
    }
    res.json(serializeHorse(horse));
  });

  const handleUpdateHorse = (req: Request, res: Response) => {
    const horseId = Number(req.params.id);
    const existing = db
      .prepare("SELECT * FROM horses WHERE id = ?")
      .get(horseId) as Record<string, unknown> | undefined;
    if (!existing) {
      res.status(404).json({ detail: "Hevosta ei löydy." });
      return;
    }
    const body = req.body || {};
    const nextName = body.name !== undefined ? String(body.name).trim() : String(existing.name);
    if (!nextName) {
      res.status(400).json({ detail: "Hevosen nimi ei voi olla tyhjä." });
      return;
    }
    const dup = db.prepare("SELECT id FROM horses WHERE name = ? AND id != ?").get(nextName, horseId);
    if (dup) {
      res.status(400).json({ detail: `Hevonen nimellä '${nextName}' on jo olemassa.` });
      return;
    }

    const nextBreed: string | null =
      body.breed !== undefined
        ? body.breed
          ? String(body.breed).trim()
          : null
        : existing.breed != null
          ? String(existing.breed)
          : null;
    const rawYear = body.birth_year !== undefined ? body.birth_year : existing.birth_year;
    const nextBirthYear: number | null =
      rawYear !== null && rawYear !== undefined && rawYear !== "" && Number.isFinite(Number(rawYear))
        ? Number(rawYear)
        : null;
    const nextOwner: string | null =
      body.owner_name !== undefined
        ? body.owner_name
          ? String(body.owner_name).trim()
          : null
        : existing.owner_name != null
          ? String(existing.owner_name)
          : null;
    const nextStall: string | null =
      body.stall_box !== undefined
        ? body.stall_box
          ? String(body.stall_box).trim()
          : null
        : existing.stall_box != null
          ? String(existing.stall_box)
          : null;
    const nextDesc: string | null =
      body.description !== undefined
        ? body.description
          ? String(body.description).trim()
          : null
        : existing.description != null
          ? String(existing.description)
          : null;
    const nextActive: number = body.active !== undefined ? (body.active ? 1 : 0) : Number(existing.active);

    db.prepare(
      "UPDATE horses SET name = ?, breed = ?, birth_year = ?, owner_name = ?, stall_box = ?, description = ?, active = ? WHERE id = ?"
    ).run(nextName, nextBreed, nextBirthYear, nextOwner, nextStall, nextDesc, nextActive, horseId);

    const updated = db.prepare("SELECT * FROM horses WHERE id = ?").get(horseId) as Record<string, unknown>;
    res.json(serializeHorse(updated));
  };

  app.put("/api/horses/:id", requireAuth, requireRole(["admin", "user"]), handleUpdateHorse);
  app.patch("/api/horses/:id", requireAuth, requireRole(["admin", "user"]), handleUpdateHorse);

  app.post("/api/horses/:id/nfc-tag", requireAuth, requireRole(["admin", "user"]), (req: Request, res: Response) => {
    const horseId = Number(req.params.id);
    const horse = db.prepare("SELECT id FROM horses WHERE id = ?").get(horseId);
    if (!horse) {
      res.status(404).json({ detail: "Hevosta ei löydy." });
      return;
    }
    const rawUid = String(req.body?.nfc_uid || "");
    const uid = rawUid.replace(/[\s:]/g, "").toUpperCase();
    if (uid.length < 4) {
      res.status(400).json({ detail: "Virheellinen NFC UID." });
      return;
    }
    const existing = db.prepare("SELECT id FROM nfc_tags WHERE nfc_uid = ?").get(uid) as { id: number } | undefined;
    if (existing) {
      db.prepare("UPDATE nfc_tags SET horse_id = ?, active = 1 WHERE id = ?").run(horseId, existing.id);
      const updated = db.prepare("SELECT * FROM nfc_tags WHERE id = ?").get(existing.id) as Record<string, unknown>;
      res.status(201).json({ ...updated, active: Boolean(updated.active) });
      return;
    }
    const now = utcIsoNow();
    const info = db
      .prepare("INSERT INTO nfc_tags (horse_id, nfc_uid, active, created_at) VALUES (?, ?, 1, ?)")
      .run(horseId, uid, now);
    const created = db.prepare("SELECT * FROM nfc_tags WHERE id = ?").get(Number(info.lastInsertRowid)) as Record<string, unknown>;
    res.status(201).json({ ...created, active: Boolean(created.active) });
  });

  app.get("/api/horses/:id/nfc-tag", requireAuth, (req: Request, res: Response) => {
    const tags = db
      .prepare("SELECT * FROM nfc_tags WHERE horse_id = ? AND active = 1")
      .all(Number(req.params.id)) as Array<Record<string, unknown>>;
    res.json(tags.map((t) => ({ ...t, active: Boolean(t.active) })));
  });

  // --- API: NFC-tapahtumat & Taustavideoleikkaus ---
  function serializeNfcEvent(ev: Record<string, unknown>) {
    const horse = ev.horse_id
      ? (db.prepare("SELECT name FROM horses WHERE id = ?").get(Number(ev.horse_id)) as { name: string } | undefined)
      : undefined;
    const clip = db
      .prepare("SELECT id, status FROM video_clips WHERE nfc_event_id = ? AND status != 'DELETED' ORDER BY id DESC LIMIT 1")
      .get(Number(ev.id)) as { id: number; status: string } | undefined;
    return {
      ...ev,
      horse_name: horse ? horse.name : null,
      video_clip_id: clip ? clip.id : null,
      video_clip_status: clip ? clip.status : null,
    };
  }

  app.get("/api/nfc-events", requireAuth, (req: Request, res: Response) => {
    const limit = Math.min(100, Number(req.query.limit || 50));
    const horseId = req.query.horse_id ? Number(req.query.horse_id) : null;
    const rows = horseId
      ? (db
          .prepare("SELECT * FROM nfc_events WHERE horse_id = ? ORDER BY id DESC LIMIT ?")
          .all(horseId, limit) as Array<Record<string, unknown>>)
      : (db.prepare("SELECT * FROM nfc_events ORDER BY id DESC LIMIT ?").all(limit) as Array<Record<string, unknown>>);
    res.json(rows.map(serializeNfcEvent));
  });

  app.get("/api/nfc-events/:id", requireAuth, (req: Request, res: Response) => {
    const ev = db.prepare("SELECT * FROM nfc_events WHERE id = ?").get(Number(req.params.id)) as
      | Record<string, unknown>
      | undefined;
    if (!ev) {
      res.status(404).json({ detail: "Tapahtumaa ei löydy." });
      return;
    }
    res.json(serializeNfcEvent(ev));
  });

  app.post("/api/nfc-events", requireAuth, (req: AuthedRequest, res: Response) => {
    const rawUid = String(req.body?.nfc_uid || "");
    const uid = rawUid.replace(/[\s:]/g, "").toUpperCase();
    const phoneTimestamp = String(req.body?.phone_timestamp || utcIsoNow());
    const location = String(req.body?.location || "kuvausalue-1");

    if (uid.length < 4) {
      res.status(400).json({ detail: "Virheellinen NFC UID." });
      return;
    }

    const now = utcIsoNow();
    const tenSecAgo = utcIsoNow(-10);

    // 1. Debounce-tarkistus (10 sekuntia)
    const duplicate = db
      .prepare("SELECT * FROM nfc_events WHERE nfc_uid = ? AND server_timestamp >= ? ORDER BY id DESC LIMIT 1")
      .get(uid, tenSecAgo) as Record<string, unknown> | undefined;

    if (duplicate) {
      res.status(201).json(serializeNfcEvent(duplicate));
      return;
    }

    // 2. Tagin haku
    const tag = db
      .prepare("SELECT horse_id FROM nfc_tags WHERE nfc_uid = ? AND active = 1")
      .get(uid) as { horse_id: number } | undefined;

    if (!tag) {
      db.prepare(
        "INSERT INTO nfc_events (horse_id, nfc_uid, phone_timestamp, server_timestamp, user_id, location, status, error_message) VALUES (NULL, ?, ?, ?, ?, ?, 'FAILED', ?)"
      ).run(uid, phoneTimestamp, now, req.user!.id, location, "UNKNOWN_TAG: Tagia ei ole yhdistetty hevoseen");
      res.status(404).json({
        detail: "UNKNOWN_TAG: Luettua NFC-tagia ei ole yhdistetty yhteenkään hevoseen.",
      });
      return;
    }

    // 3. Luo tapahtuma ja käynnistä FFmpeg-taustaleikkaus
    const info = db
      .prepare(
        "INSERT INTO nfc_events (horse_id, nfc_uid, phone_timestamp, server_timestamp, user_id, location, status) VALUES (?, ?, ?, ?, ?, ?, 'WAITING_FOR_RECORDING')"
      )
      .run(tag.horse_id, uid, phoneTimestamp, now, req.user!.id, location);

    const eventId = Number(info.lastInsertRowid);
    const created = db.prepare("SELECT * FROM nfc_events WHERE id = ?").get(eventId) as Record<string, unknown>;

    // Taustaprosessi: WAITING_FOR_RECORDING -> PROCESSING -> READY (FFmpeg MP4 luonti)
    setTimeout(async () => {
      try {
        db.prepare("UPDATE nfc_events SET status = 'PROCESSING' WHERE id = ?").run(eventId);
        const dateObj = new Date();
        const yearStr = String(dateObj.getUTCFullYear());
        const monthStr = String(dateObj.getUTCMonth() + 1).padStart(2, "0");
        const relPath = `${tag.horse_id}/${yearStr}/${monthStr}/event_${eventId}_${Date.now()}.mp4`;
        const absPath = validateAndResolveVideoPath(relPath);
        const ok = await generateMockClipMp4(absPath, 8);
        if (ok) {
          db.prepare(
            "INSERT INTO video_clips (nfc_event_id, relative_file_path, status, created_at) VALUES (?, ?, 'READY', ?)"
          ).run(eventId, relPath, utcIsoNow());
          db.prepare("UPDATE nfc_events SET status = 'READY' WHERE id = ?").run(eventId);
        } else {
          db.prepare("UPDATE nfc_events SET status = 'FAILED', error_message = ? WHERE id = ?").run(
            "FFmpeg leikkaus epäonnistui",
            eventId
          );
        }
      } catch (err) {
        db.prepare("UPDATE nfc_events SET status = 'FAILED', error_message = ? WHERE id = ?").run(String(err), eventId);
      }
    }, 1500);

    res.status(201).json(serializeNfcEvent(created));
  });

  // --- API: Videoleikkeet ---
  app.get("/api/video-clips", requireAuth, (_req: Request, res: Response) => {
    const clips = db
      .prepare(
        `SELECT vc.*, ne.horse_id, ne.nfc_uid, ne.phone_timestamp, ne.location, h.name as horse_name
         FROM video_clips vc
         JOIN nfc_events ne ON vc.nfc_event_id = ne.id
         LEFT JOIN horses h ON ne.horse_id = h.id
         WHERE vc.status != 'DELETED'
         ORDER BY vc.id DESC LIMIT 50`
      )
      .all();
    res.json(clips);
  });

  app.get("/api/video-clips/:id", requireAuth, (req: Request, res: Response) => {
    const clip = db.prepare("SELECT * FROM video_clips WHERE id = ?").get(Number(req.params.id)) as
      | Record<string, unknown>
      | undefined;
    if (!clip || clip.status === "DELETED") {
      res.status(404).json({ detail: "Videoleikettä ei löydy." });
      return;
    }
    res.json(clip);
  });

  app.get("/api/video-clips/:id/download", requireAuth, (req: Request, res: Response) => {
    const clip = db.prepare("SELECT * FROM video_clips WHERE id = ?").get(Number(req.params.id)) as
      | { id: number; relative_file_path: string; status: string }
      | undefined;
    if (!clip || clip.status === "DELETED") {
      res.status(404).json({ detail: "Videoleikettä ei löydy." });
      return;
    }
    let absPath: string;
    try {
      absPath = validateAndResolveVideoPath(clip.relative_file_path);
    } catch (err) {
      res.status(400).json({ detail: String(err) });
      return;
    }
    if (!fs.existsSync(absPath)) {
      res.status(404).json({ detail: "Videotiedostoa ei löydy levyltä." });
      return;
    }

    const stat = fs.statSync(absPath);
    const fileSize = stat.size;
    const range = req.headers.range;
    if (range) {
      const parts = range.replace(/bytes=/, "").split("-");
      const start = parseInt(parts[0], 10);
      const end = parts[1] ? parseInt(parts[1], 10) : fileSize - 1;
      const chunksize = end - start + 1;
      const stream = fs.createReadStream(absPath, { start, end });
      res.writeHead(206, {
        "Content-Range": `bytes ${start}-${end}/${fileSize}`,
        "Accept-Ranges": "bytes",
        "Content-Length": chunksize,
        "Content-Type": "video/mp4",
      });
      stream.pipe(res);
    } else {
      res.writeHead(200, {
        "Content-Length": fileSize,
        "Content-Type": "video/mp4",
        "Accept-Ranges": "bytes",
      });
      fs.createReadStream(absPath).pipe(res);
    }
  });

  app.post("/api/video-clips/:id/approve", requireAuth, requireRole(["admin", "user"]), (req: Request, res: Response) => {
    const id = Number(req.params.id);
    const clip = db.prepare("SELECT * FROM video_clips WHERE id = ?").get(id) as
      | { id: number; nfc_event_id: number; status: string }
      | undefined;
    if (!clip || clip.status === "DELETED") {
      res.status(404).json({ detail: "Videoleikettä ei löydy." });
      return;
    }
    const now = utcIsoNow();
    db.prepare("UPDATE video_clips SET status = 'APPROVED', approved_at = ?, rejected_at = NULL WHERE id = ?").run(now, id);
    db.prepare("UPDATE nfc_events SET status = 'APPROVED' WHERE id = ?").run(clip.nfc_event_id);
    const updated = db.prepare("SELECT * FROM video_clips WHERE id = ?").get(id);
    res.json(updated);
  });

  app.post("/api/video-clips/:id/reject", requireAuth, requireRole(["admin", "user"]), (req: Request, res: Response) => {
    const id = Number(req.params.id);
    const clip = db.prepare("SELECT * FROM video_clips WHERE id = ?").get(id) as
      | { id: number; nfc_event_id: number; status: string }
      | undefined;
    if (!clip || clip.status === "DELETED") {
      res.status(404).json({ detail: "Videoleikettä ei löydy." });
      return;
    }
    const now = utcIsoNow();
    db.prepare("UPDATE video_clips SET status = 'REJECTED', rejected_at = ? WHERE id = ?").run(now, id);
    db.prepare("UPDATE nfc_events SET status = 'REJECTED' WHERE id = ?").run(clip.nfc_event_id);
    const updated = db.prepare("SELECT * FROM video_clips WHERE id = ?").get(id);
    res.json(updated);
  });

  app.delete("/api/video-clips/:id", requireAuth, requireRole(["admin"]), (req: Request, res: Response) => {
    const id = Number(req.params.id);
    const clip = db.prepare("SELECT * FROM video_clips WHERE id = ?").get(id) as
      | { id: number; relative_file_path: string }
      | undefined;
    if (!clip) {
      res.status(404).json({ detail: "Videoleikettä ei löydy." });
      return;
    }
    try {
      const absPath = validateAndResolveVideoPath(clip.relative_file_path);
      if (fs.existsSync(absPath)) fs.unlinkSync(absPath);
    } catch {
      // ignore
    }
    db.prepare("UPDATE video_clips SET status = 'DELETED', deleted_at = ? WHERE id = ?").run(utcIsoNow(), id);
    res.status(204).send();
  });

  // --- API: Muistiinpanot ---
  app.get("/api/horses/:id/notes", requireAuth, (req: Request, res: Response) => {
    const horseId = Number(req.params.id);
    const horse = db.prepare("SELECT id FROM horses WHERE id = ?").get(horseId);
    if (!horse) {
      res.status(404).json({ detail: "Hevosta ei löydy." });
      return;
    }
    const notes = db
      .prepare(
        `SELECT n.*, u.username as author_username
         FROM horse_notes n
         LEFT JOIN users u ON n.user_id = u.id
         WHERE n.horse_id = ?
         ORDER BY n.id DESC`
      )
      .all(horseId);
    res.json(notes);
  });

  app.post("/api/horses/:id/notes", requireAuth, requireRole(["admin", "user"]), (req: AuthedRequest, res: Response) => {
    const horseId = Number(req.params.id);
    const horse = db.prepare("SELECT id FROM horses WHERE id = ?").get(horseId);
    if (!horse) {
      res.status(404).json({ detail: "Hevosta ei löydy." });
      return;
    }
    const content = String(req.body?.content || "").trim();
    if (!content) {
      res.status(400).json({ detail: "Muistiinpano ei voi olla tyhjä." });
      return;
    }
    const now = utcIsoNow();
    const info = db
      .prepare("INSERT INTO horse_notes (horse_id, content, user_id, created_at) VALUES (?, ?, ?, ?)")
      .run(horseId, content, req.user!.id, now);
    res.status(201).json({
      id: Number(info.lastInsertRowid),
      horse_id: horseId,
      content,
      user_id: req.user!.id,
      author_username: req.user!.username,
      created_at: now,
    });
  });

  // --- API: Liikeanalyysit ---
  app.get("/api/horses/:id/analyses", requireAuth, (req: Request, res: Response) => {
    const horseId = Number(req.params.id);
    const horse = db.prepare("SELECT id FROM horses WHERE id = ?").get(horseId);
    if (!horse) {
      res.status(404).json({ detail: "Hevosta ei löydy." });
      return;
    }
    const rows = db
      .prepare("SELECT * FROM movement_analyses WHERE horse_id = ? ORDER BY id DESC")
      .all(horseId);
    res.json(rows);
  });

  app.post("/api/analyses", requireAuth, requireRole(["admin", "user"]), (req: AuthedRequest, res: Response) => {
    const { horse_id, video_clip_id, analysis_method, summary, result_json, status: st } = req.body || {};
    const horseId = Number(horse_id);
    if (!horseId || !analysis_method || !summary) {
      res.status(400).json({ detail: "horse_id, analysis_method ja summary vaaditaan." });
      return;
    }
    const now = utcIsoNow();
    const info = db
      .prepare(
        "INSERT INTO movement_analyses (horse_id, video_clip_id, analysis_method, analysis_timestamp, summary, result_json, status, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
      )
      .run(
        horseId,
        video_clip_id ? Number(video_clip_id) : null,
        String(analysis_method).trim(),
        now,
        String(summary).trim(),
        result_json ? String(result_json) : null,
        String(st || "APPROVED"),
        req.user!.id,
        now
      );
    const created = db.prepare("SELECT * FROM movement_analyses WHERE id = ?").get(Number(info.lastInsertRowid));
    res.status(201).json(created);
  });

  // --- API: Anteron juomismittaukset ---
  app.get("/api/water", requireAuth, (req: Request, res: Response) => {
    const limit = Math.min(200, Number(req.query.limit || 100));
    const rows = db
      .prepare(
        `SELECT wm.*, h.name as horse_name
         FROM water_measurements wm
         LEFT JOIN horses h ON wm.horse_id = h.id
         ORDER BY wm.measured_at DESC
         LIMIT ?`
      )
      .all(limit) as Array<Record<string, unknown>>;
    res.json(
      rows.map((r) => ({
        ...r,
        horse_name: r.horse_name || "Tunnistamaton / Ei yhdistetty",
      }))
    );
  });

  app.get("/api/water/daily", requireAuth, (req: Request, res: Response) => {
    const days = Math.min(60, Number(req.query.days || 14));
    const antero = db.prepare("SELECT id FROM horses WHERE name = ?").get(DRINKING_HORSE_NAME) as
      | { id: number }
      | undefined;
    if (!antero) {
      res.json([]);
      return;
    }
    const rows = db
      .prepare("SELECT measured_at, liters FROM water_measurements WHERE horse_id = ? ORDER BY measured_at ASC")
      .all(antero.id) as Array<{ measured_at: string; liters: number }>;

    const map = new Map<string, { total: number; count: number }>();
    for (const r of rows) {
      const dayKey = r.measured_at.slice(0, 10);
      const prev = map.get(dayKey) || { total: 0, count: 0 };
      prev.total += r.liters;
      prev.count += 1;
      map.set(dayKey, prev);
    }
    const keys = Array.from(map.keys()).sort().slice(-days);
    res.json(
      keys.map((k) => ({
        date: k,
        total_liters: Number(map.get(k)!.total.toFixed(1)),
        measurement_count: map.get(k)!.count,
      }))
    );
  });

  app.post("/api/water/sync", requireAuth, requireRole(["admin", "user"]), (_req: Request, res: Response) => {
    const antero = db.prepare("SELECT id FROM horses WHERE name = ?").get(DRINKING_HORSE_NAME) as
      | { id: number }
      | undefined;
    const now = utcIsoNow();
    const liters = Number((4.5 + Math.random() * 5.0).toFixed(2));
    const measId = `MOCK-WTR-${Date.now()}`;
    const raw = JSON.stringify({
      source: "MockWaterDispenserV1",
      device_serial: WATER_EXTERNAL_ID,
      flow_rate_lpm: Number((7.8 + Math.random() * 0.9).toFixed(1)),
      duration_sec: Math.round(liters * 7.2),
      temp_celsius: Number((11.6 + Math.random() * 1.2).toFixed(1)),
      raw_timestamp: now,
    });
    db.prepare(
      "INSERT INTO water_measurements (horse_id, external_measurement_id, external_water_id, measured_at, liters, raw_data_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)"
    ).run(antero ? antero.id : null, measId, WATER_EXTERNAL_ID, now, liters, raw, now);
    res.json({ message: "Juomadata synkronoitu", new_records: 1, liters });
  });

  // --- API: Talli-ilma ---
  app.get("/api/stable-air", requireAuth, (req: Request, res: Response) => {
    const limit = Math.min(200, Number(req.query.limit || 50));
    const rows = db
      .prepare("SELECT * FROM stable_air_measurements ORDER BY measured_at DESC, id DESC LIMIT ?")
      .all(limit);
    res.json(rows);
  });

  app.post("/api/stable-air/sync", requireAuth, requireRole(["admin", "user"]), (_req: Request, res: Response) => {
    const now = utcIsoNow();
    const locations = [
      { id: "SENSOR-STABLE-MAIN", loc: "Päätalli / Karsinakäytävä" },
      { id: "SENSOR-STABLE-BOX-ANTERO", loc: "Karsina 4 (Antero)" },
    ];
    for (const l of locations) {
      const temp = Number((9.5 + Math.random() * 4.0).toFixed(1));
      const hum = Number((63.0 + Math.random() * 11.0).toFixed(1));
      const nh3 = Number((2.0 + Math.random() * 3.0).toFixed(2));
      const co2 = Number((720 + Math.random() * 300).toFixed(0));
      const pm = Number((15.0 + Math.random() * 13.0).toFixed(1));
      db.prepare(
        "INSERT INTO stable_air_measurements (sensor_id, location, measured_at, temperature, humidity, ammonia, co2, particulate_matter, raw_data_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
      ).run(l.id, l.loc, now, temp, hum, nh3, co2, pm, JSON.stringify({ sensor: l.id, battery_mv: 3275 }), now);
    }
    res.json({ message: "Talli-ilman mittaukset synkronoitu", new_records: 2 });
  });

  // --- JULKINEN VAIN LUKU -RAJAPINTA (hummapp.fi) ---
  // Huom: Ei sisällä autentikoituja käyttäjätietoja eikä minkäänlaisia muokkausreittejä.
  app.get("/api/public/overview", (_req: Request, res: Response) => {
    const horsesRaw = db
      .prepare("SELECT * FROM horses WHERE active = 1 ORDER BY name ASC")
      .all() as Array<Record<string, unknown>>;

    const horses = horsesRaw.map((h) => {
      const base = serializeHorse(h);
      const notes = db
        .prepare(
          `SELECT n.id, n.horse_id, n.content, n.created_at, u.username as author_username
           FROM horse_notes n
           LEFT JOIN users u ON n.user_id = u.id
           WHERE n.horse_id = ?
           ORDER BY n.id DESC LIMIT 20`
        )
        .all(base.id);
      const analyses = db
        .prepare(
          `SELECT id, horse_id, video_clip_id, analysis_method, analysis_timestamp, summary, result_json, status
           FROM movement_analyses
           WHERE horse_id = ?
           ORDER BY id DESC LIMIT 20`
        )
        .all(base.id);
      return { ...base, notes, analyses };
    });

    const antero = db
      .prepare("SELECT id FROM horses WHERE name = ?")
      .get(DRINKING_HORSE_NAME) as { id: number } | undefined;

    let waterDaily: Array<{ date: string; total_liters: number; measurement_count: number }> = [];
    if (antero) {
      const rows = db
        .prepare("SELECT measured_at, liters FROM water_measurements WHERE horse_id = ? ORDER BY measured_at ASC")
        .all(antero.id) as Array<{ measured_at: string; liters: number }>;
      const map = new Map<string, { total: number; count: number }>();
      for (const r of rows) {
        const dayKey = r.measured_at.slice(0, 10);
        const prev = map.get(dayKey) || { total: 0, count: 0 };
        prev.total += r.liters;
        prev.count += 1;
        map.set(dayKey, prev);
      }
      const keys = Array.from(map.keys()).sort().slice(-14);
      waterDaily = keys.map((k) => ({
        date: k,
        total_liters: Number(map.get(k)!.total.toFixed(1)),
        measurement_count: map.get(k)!.count,
      }));
    }

    const waterMeasurements = db
      .prepare(
        `SELECT wm.id, wm.horse_id, wm.external_measurement_id, wm.external_water_id, wm.measured_at, wm.liters, wm.raw_data_json, h.name as horse_name
         FROM water_measurements wm
         LEFT JOIN horses h ON wm.horse_id = h.id
         ORDER BY wm.measured_at DESC
         LIMIT 30`
      )
      .all();

    const airReadings = db
      .prepare(
        `SELECT id, sensor_id, location, measured_at, temperature, humidity, ammonia, co2, particulate_matter
         FROM stable_air_measurements
         ORDER BY measured_at DESC, id DESC
         LIMIT 30`
      )
      .all();

    const nfcEvents = db
      .prepare("SELECT * FROM nfc_events ORDER BY id DESC LIMIT 25")
      .all() as Array<Record<string, unknown>>;

    res.json({
      read_only: true,
      generated_at: utcIsoNow(),
      water_external_id: WATER_EXTERNAL_ID,
      drinking_horse_name: DRINKING_HORSE_NAME,
      horses,
      water_daily: waterDaily,
      water_measurements: waterMeasurements,
      air_readings: airReadings,
      nfc_events: nfcEvents.map(serializeNfcEvent),
    });
  });

  app.get("/api/public/video-clips/:id/stream", (req: Request, res: Response) => {
    const clip = db
      .prepare("SELECT * FROM video_clips WHERE id = ? AND status IN ('READY', 'APPROVED')")
      .get(Number(req.params.id)) as { id: number; relative_file_path: string; status: string } | undefined;
    if (!clip) {
      res.status(404).json({ detail: "Julkista videoleikettä ei löydy." });
      return;
    }
    let absPath: string;
    try {
      absPath = validateAndResolveVideoPath(clip.relative_file_path);
    } catch (err) {
      res.status(400).json({ detail: String(err) });
      return;
    }
    if (!fs.existsSync(absPath)) {
      res.status(404).json({ detail: "Videotiedostoa ei löydy." });
      return;
    }

    const stat = fs.statSync(absPath);
    const fileSize = stat.size;
    const range = req.headers.range;
    if (range) {
      const parts = range.replace(/bytes=/, "").split("-");
      const start = parseInt(parts[0], 10);
      const end = parts[1] ? parseInt(parts[1], 10) : fileSize - 1;
      const chunksize = end - start + 1;
      const stream = fs.createReadStream(absPath, { start, end });
      res.writeHead(206, {
        "Content-Range": `bytes ${start}-${end}/${fileSize}`,
        "Accept-Ranges": "bytes",
        "Content-Length": chunksize,
        "Content-Type": "video/mp4",
      });
      stream.pipe(res);
    } else {
      res.writeHead(200, {
        "Content-Length": fileSize,
        "Content-Type": "video/mp4",
        "Accept-Ranges": "bytes",
      });
      fs.createReadStream(absPath).pipe(res);
    }
  });

  // --- Staattiset ZIP-lataukset (Android-sovellus ja täysi NAS-paketti) ---
  app.use(express.static(PUBLIC_DIR));

  // --- Vite dev middleware tai tuotannon dist ---
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: {
        middlewareMode: true,
        hmr: false,
        ws: false,
      },
      appType: "spa",
    });

    // Estetään Vite 8:n @vite/client -moduulia yrittämästä WebSocket-yhteyttä porttiin 24678, kun HMR on pois päältä
    app.get("/@vite/client", (_req: Request, res: Response) => {
      res.setHeader("Content-Type", "application/javascript; charset=utf-8");
      res.setHeader("Cache-Control", "no-store");
      res.send(`
const sheetsMap = new Map();
export function updateStyle(id, content) {
  let style = sheetsMap.get(id);
  if (!style) {
    style = document.createElement("style");
    style.setAttribute("type", "text/css");
    style.setAttribute("data-vite-dev-id", id);
    style.textContent = content;
    document.head.appendChild(style);
  } else if (style.textContent !== content) {
    style.textContent = content;
  }
  sheetsMap.set(id, style);
}
export function removeStyle(id) {
  const style = sheetsMap.get(id);
  if (style) {
    document.head.removeChild(style);
    sheetsMap.delete(id);
  }
}
export function createHotContext() {
  return {
    data: {},
    accept() {},
    acceptExports() {},
    dispose() {},
    prune() {},
    invalidate() {},
    decline() {},
    on() {},
    off() {},
    send() {},
  };
}
export function injectQuery(url, queryToInject) {
  if (!url || (url[0] !== "." && url[0] !== "/")) return url;
  const pathname = url.replace(/[?#].*$/, "");
  const { search, hash } = new URL(url, window.location.origin);
  return \`\${pathname}?\${queryToInject}\${search ? "&" + search.slice(1) : ""}\${hash || ""}\`;
}
export class ErrorOverlay extends HTMLElement {}
`);
    });

    app.use(vite.middlewares);
  } else {
    const distDir = path.resolve(process.cwd(), "dist");
    app.use(express.static(distDir));
    app.get("*", (_req: Request, res: Response) => {
      res.sendFile(path.join(distDir, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`HummAPP palvelin käynnissä: http://0.0.0.0:${PORT}`);
  });
}

startServer().catch((err) => {
  console.error("Virhe palvelimen käynnistyksessä:", err);
  process.exit(1);
});
