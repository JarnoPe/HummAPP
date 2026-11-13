# ==============================================================================
# HummAPP Dockerfile - Synology NAS -yhteensopiva kevyt yksittäiskontti
# Sisältää: Python 3.11, FastAPI, FFmpeg videoleikkaukseen, SQLite3-työkalut
# ==============================================================================

FROM python:3.11-slim

# Estä Pythonin .pyc-tiedostojen luonti ja pakota puskuroimaton stdout/stderr lokitukseen
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Asenna FFmpeg videonkäsittelyä varten, sqlite3 varmuuskopiointia varten ja curl healthcheckiin
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    sqlite3 \
    curl \
    tzdata \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Luo työskentelyhakemisto ja tarvittavat NAS-liitospisteet
WORKDIR /app
RUN mkdir -p /data /videos /camera /logs /backups

# Kopioi riippuvuusmääritykset ja asenna
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopioi sovelluksen lähdekoodi ja skriptit
COPY app /app/app
COPY scripts /app/scripts
RUN chmod +x /app/scripts/*.sh

# Luo sovelluskäyttäjä (Synology Container Manager yhteensopiva UID 1000)
RUN useradd -u 1000 -U -d /app -s /bin/bash hummapp && \
    chown -R hummapp:hummapp /app /data /videos /logs /backups

# Vaihda hummapp-käyttäjäksi
USER hummapp

# Oletusportti
EXPOSE 8000

# Synology NAS -kontin kunnonvalvonta (Healthcheck)
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:8000/api/health || exit 1

# Käynnistä FastAPI Uvicorn-palvelimella
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
