"""Ajastetut taustatehtävät (APScheduler)."""
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.database import SessionLocal
from app.services.air_quality import air_quality_service
from app.services.video_review import purge_rejected_clips
from app.services.water import water_service

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def scheduled_water_sync() -> None:
    db = SessionLocal()
    try:
        await water_service.sync_measurements(db)
    finally:
        db.close()


async def scheduled_air_sync() -> None:
    db = SessionLocal()
    try:
        await air_quality_service.sync_air_readings(db)
    finally:
        db.close()


def scheduled_rejected_cleanup() -> None:
    db = SessionLocal()
    try:
        purge_rejected_clips(db)
    finally:
        db.close()


def start_scheduler() -> None:
    if settings.WATER_FETCH_INTERVAL_MINUTES > 0:
        scheduler.add_job(scheduled_water_sync, "interval", minutes=settings.WATER_FETCH_INTERVAL_MINUTES,
                          id="water_sync_job", replace_existing=True)
    if settings.AIR_FETCH_INTERVAL_MINUTES > 0:
        scheduler.add_job(scheduled_air_sync, "interval", minutes=settings.AIR_FETCH_INTERVAL_MINUTES,
                          id="air_sync_job", replace_existing=True)
    if settings.VIDEO_REJECTED_RETENTION_DAYS > 0:
        scheduler.add_job(scheduled_rejected_cleanup, "cron", hour=3, minute=17,
                          id="rejected_clip_cleanup", replace_existing=True)
    scheduler.start()
    logger.info("Ajastetut tehtävät käynnistetty.")


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
