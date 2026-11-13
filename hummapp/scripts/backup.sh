#!/bin/bash
# ==============================================================================
# HummAPP - Synology NAS Turvallinen Varmuuskopiointiskripti
#
# Tämä skripti hyödyntää SQLite3:n online-backup -toimintoa (.backup),
# joka takaa eheän varmuuskopion myös silloin, kun tietokanta on aktiivisessa
# käytössä ja WAL-tilassa (Write-Ahead Logging).
# Älä koskaan kopioi lennossa suoraan pelkkää hummapp.db -tiedostoa!
# ==============================================================================

set -euo pipefail

# Asetukset (kontin sisäiset tai NASin paikalliset polut)
DB_PATH="${DATABASE_PATH:-/data/hummapp.db}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/hummapp_backup_${TIMESTAMP}.db"
LOG_TAG="[HummAPP-Backup]"

echo "${LOG_TAG} Aloitetaan tietokannan varmuuskopiointi: $(date)"

# Varmista kohdehakemisto
mkdir -p "${BACKUP_DIR}"

if [ ! -f "${DB_PATH}" ]; then
    echo "${LOG_TAG} VIRHE: Tietokantatiedostoa ${DB_PATH} ei löydy!" >&2
    exit 1
fi

# Suorita turvallinen SQLite online-backup
echo "${LOG_TAG} Suoritetaan SQLite online-varmuuskopio kohteeseen: ${BACKUP_FILE}"
sqlite3 "${DB_PATH}" ".backup '${BACKUP_FILE}'"

# Pakkaa varmuuskopiotiedosto tilan säästämiseksi
echo "${LOG_TAG} Pakataan varmuuskopio gzip-muotoon..."
gzip -f "${BACKUP_FILE}"

FINAL_BACKUP="${BACKUP_FILE}.gz"
BACKUP_SIZE=$(ls -lh "${FINAL_BACKUP}" | awk '{print $5}')
echo "${LOG_TAG} Varmuuskopiointi onnistui: ${FINAL_BACKUP} (Koko: ${BACKUP_SIZE})"

# Säilytyskäytäntö: Poista yli 30 päivää vanhat varmuuskopiot
echo "${LOG_TAG} Siivotaan yli 30 päivää vanhat kopiot..."
find "${BACKUP_DIR}" -name "hummapp_backup_*.db.gz" -type f -mtime +30 -delete || true

echo "${LOG_TAG} Valmis: $(date)"
