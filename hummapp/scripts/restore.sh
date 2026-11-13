#!/bin/bash
# ==============================================================================
# HummAPP - Synology NAS Tietokannan Palautusskripti
#
# KÄYTTÖOHJE:
# 1. Pysäytä kontti: docker compose stop hummapp
# 2. Aja palautus: ./scripts/restore.sh /backups/hummapp_backup_YYYYMMDD_HHMMSS.db.gz
# 3. Käynnistä kontti: docker compose start hummapp
# ==============================================================================

set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "Käyttö: $0 <varmuuskopiotiedosto.db.gz tai .db>"
    echo "Esimerkki: $0 /backups/hummapp_backup_20261112_120000.db.gz"
    exit 1
fi

BACKUP_SOURCE="$1"
DB_TARGET="${DATABASE_PATH:-/data/hummapp.db}"
LOG_TAG="[HummAPP-Restore]"

if [ ! -f "${BACKUP_SOURCE}" ]; then
    echo "${LOG_TAG} VIRHE: Annettua varmuuskopiotiedostoa ei löydy: ${BACKUP_SOURCE}" >&2
    exit 1
fi

echo "${LOG_TAG} VAROITUS: Tämä toimenpide ylikirjoittaa nykyisen tietokannan: ${DB_TARGET}"
echo "${LOG_TAG} Palautettava tiedosto: ${BACKUP_SOURCE}"
read -p "Haluatko varmasti jatkaa palautusta? (k/E): " CONFIRM
if [[ ! "$CONFIRM" =~ ^[kKyY]$ ]]; then
    echo "${LOG_TAG} Palautus peruutettu."
    exit 0
fi

# Poistetaan vanhat WAL- ja SHM-lukitustiedostot ennen palautusta
TARGET_DIR=$(dirname "${DB_TARGET}")
mkdir -p "${TARGET_DIR}"
rm -f "${DB_TARGET}-wal" "${DB_TARGET}-shm" || true

if [[ "${BACKUP_SOURCE}" == *.gz ]]; then
    echo "${LOG_TAG} Puretaan ja palautetaan pakattu varmuuskopio..."
    gunzip -c "${BACKUP_SOURCE}" > "${DB_TARGET}"
else
    echo "${LOG_TAG} Kopioidaan varmuuskopio kohteeseen..."
    cp -f "${BACKUP_SOURCE}" "${DB_TARGET}"
fi

# Varmistetaan SQLite-tietokannan eheys
echo "${LOG_TAG} Tarkistetaan tietokannan eheys (PRAGMA integrity_check)..."
INTEGRITY=$(sqlite3 "${DB_TARGET}" "PRAGMA integrity_check;")

if [ "${INTEGRITY}" == "ok" ]; then
    echo "${LOG_TAG} Palautus ONNISTUI ja tietokanta on eheä (integrity_check: ok)."
    echo "${LOG_TAG} Voit nyt käynnistää kontin: docker compose start hummapp"
else
    echo "${LOG_TAG} VIRHE: Palautetussa tietokannassa havaittiin virheitä: ${INTEGRITY}" >&2
    exit 1
fi
