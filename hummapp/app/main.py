"""HummAPP – sovelluksen kokoaminen. Logiikka on moduuleissa api/, web/, services/."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.air import router as air_router
from app.api.analyses import router as analyses_router
from app.api.auth import router as auth_router
from app.api.horses import router as horses_router
from app.api.nfc import router as nfc_router
from app.api.notes import router as notes_router
from app.api.public import router as public_router
from app.api.system import APP_VERSION
from app.api.system import router as system_router
from app.api.videos import router as videos_router
from app.api.water import router as water_router
from app.config import settings
from app.logging_setup import configure_logging
from app.scheduler import start_scheduler, stop_scheduler
from app.startup import initialize_application
from app.web.routes import LOGIN_URL, WebLoginRequired
from app.web.routes import router as web_router

configure_logging()
logger = logging.getLogger("hummapp")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Käynnistetään %s (ympäristö: %s, leike %s s + %s s)...", settings.APP_NAME, settings.APP_ENV,
                settings.VIDEO_SECONDS_BEFORE, settings.VIDEO_SECONDS_AFTER)
    if settings.ENABLE_MOCK_CAMERA_FALLBACK:
        logger.warning("ENABLE_MOCK_CAMERA_FALLBACK=true: puuttuva kameratallenne korvataan testivideolla!")
    await initialize_application()
    start_scheduler()
    yield
    logger.info("Sammutetaan HummAPP...")
    stop_scheduler()


app = FastAPI(
    title=settings.APP_NAME,
    version=APP_VERSION,
    description="HummAPP - Hevosten hyvinvointi ja talliseuranta (Synology NAS Pilotti)",
    lifespan=lifespan,
)

if settings.cors_origins:
    wildcard = settings.cors_origins == ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=not wildcard,  # selaimet hylkäävät "*" + credentials -yhdistelmän
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )


@app.exception_handler(WebLoginRequired)
async def redirect_to_login(request: Request, exc: WebLoginRequired):
    return RedirectResponse(url=LOGIN_URL, status_code=302)


app.mount("/static", StaticFiles(directory=str(Path(__file__).resolve().parent / "static")), name="static")

for router in (
    auth_router,
    system_router,
    horses_router,
    nfc_router,
    videos_router,
    notes_router,
    analyses_router,
    water_router,
    air_router,
    public_router,
    web_router,
):
    app.include_router(router)
