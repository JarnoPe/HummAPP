#!/bin/bash
# ==============================================================================
# HummAPP Smoke Test - Asennuksen ja rajapintojen toiminnan pikavarmennus
#
# Aja tämä skripti Synology NASilla kontin käynnistyksen jälkeen:
# bash scripts/smoke_test.sh [API_BASE_URL]
# Esimerkki: bash scripts/smoke_test.sh http://localhost:8000
# ==============================================================================

set -e

BASE_URL="${1:-http://localhost:8000}"
ADMIN_USER="${ADMIN_USERNAME:-admin}"
ADMIN_PASS="${ADMIN_PASSWORD:-Tallipaallikko2026!}"

echo "========================================================"
echo "HummAPP NAS Smoke Test"
echo "Kohdeosoite: ${BASE_URL}"
echo "Testikäyttäjä: ${ADMIN_USER}"
echo "========================================================"

# 1. Kunnonvalvonta (Healthcheck)
echo -n "1. Tarkistetaan /api/health... "
HEALTH_RESP=$(curl -s -f "${BASE_URL}/api/health")
echo "OK -> ${HEALTH_RESP}"

# 2. Järjestelmätila (System Status)
echo -n "2. Tarkistetaan /api/system/status... "
STATUS_RESP=$(curl -s -f "${BASE_URL}/api/system/status")
echo "OK"

# 3. Kirjautuminen ja JWT-tokenin saaminen
echo -n "3. Testataan kirjautuminen (/api/login)... "
LOGIN_PAYLOAD=$(printf '{"username":"%s","password":"%s"}' "$ADMIN_USER" "$ADMIN_PASS")
LOGIN_RESP=$(curl -s -X POST "${BASE_URL}/api/login" \
  -H "Content-Type: application/json" \
  -d "$LOGIN_PAYLOAD")

TOKEN=$(echo "$LOGIN_RESP" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo "VIRHE: Kirjautuminen epäonnistui! Vastaus:"
    echo "$LOGIN_RESP"
    exit 1
fi
echo "OK (Token vastaanotettu)"

# 4. Hevoslistaus autentikoidulla pyynnöllä
echo -n "4. Haetaan hevoset (/api/horses)... "
HORSES_RESP=$(curl -s -f -H "Authorization: Bearer ${TOKEN}" "${BASE_URL}/api/horses")
echo "OK -> ${HORSES_RESP}"

# 5. Anteron juomamittausten yhteenveto
echo -n "5. Tarkistetaan Anteron juomadata (/api/water/daily)... "
WATER_RESP=$(curl -s -f -H "Authorization: Bearer ${TOKEN}" "${BASE_URL}/api/water/daily")
echo "OK -> ${WATER_RESP}"

# 6. Talli-ilman mittaukset
echo -n "6. Tarkistetaan talli-ilman mittaukset (/api/stable-air)... "
AIR_RESP=$(curl -s -f -H "Authorization: Bearer ${TOKEN}" "${BASE_URL}/api/stable-air?limit=2")
echo "OK"

echo "========================================================"
echo "KAIKKI SMOKE TEST -TARKISTUKSET MENIVÄT LÄPI ONNISTUNEESTI!"
echo "HummAPP on valmis ja toimintakunnossa Synology NASilla."
echo "========================================================"
