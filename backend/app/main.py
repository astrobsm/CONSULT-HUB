import asyncio
import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Query, WebSocket, WebSocketException, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocketDisconnect

from app.api.routes import (
    appointments,
    attachments,
    auth,
    clinics,
    consultations,
    dashboard,
    escalation,
    fhir,
    messages,
    notifications,
    org,
    patients,
    portal,
    users,
)
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.escalation import run_escalations_job
from app.services.waiting_reminders import run_reminders_job
from app.core.realtime import manager as realtime
from app.core.security import decode_access_token, token_is_current
from app.models.entities import User

# Import models so their tables register on Base.metadata.
import app.models  # noqa: F401

logger = logging.getLogger("consulthub")


@asynccontextmanager
async def lifespan(_: FastAPI):
    for warning in settings.startup_warnings():
        logger.warning("CONFIG: %s", warning)

    # Dev convenience: auto-create tables. Use Alembic in production.
    Base.metadata.create_all(bind=engine)

    # Capture the running loop so sync code can push over WebSockets.
    realtime.set_loop(asyncio.get_running_loop())

    scheduler: BackgroundScheduler | None = None
    if settings.escalation_enabled or settings.reminders_enabled:
        scheduler = BackgroundScheduler(timezone="UTC")
        if settings.escalation_enabled:
            scheduler.add_job(
                run_escalations_job,
                trigger="interval",
                seconds=settings.escalation_interval_seconds,
                id="escalation",
                max_instances=1,
                coalesce=True,
            )
        if settings.reminders_enabled:
            scheduler.add_job(
                run_reminders_job,
                trigger="interval",
                seconds=settings.reminder_interval_seconds,
                id="reminders",
                max_instances=1,
                coalesce=True,
            )
        scheduler.start()
        logger.info("Background scheduler started")

    try:
        yield
    finally:
        if scheduler is not None:
            scheduler.shutdown(wait=False)


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

# We send credentials cross-origin, so a wildcard origin is forbidden — the
# combination would let any site make authenticated calls on a user's behalf.
_cors_origins = settings.cors_origins_list
if "*" in _cors_origins:
    raise RuntimeError(
        "CORS_ORIGINS must list explicit origins, not '*', because "
        "allow_credentials is enabled."
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(f"{settings.api_prefix}/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


@app.websocket(f"{settings.api_prefix}/ws")
async def websocket_endpoint(
    websocket: WebSocket, token: str = Query(default="")
) -> None:
    """Authenticated push channel. Token is passed as a query param since
    browsers can't set headers on a WebSocket handshake."""
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except Exception:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)

    # Only staff access tokens open this channel — reject patient/purpose tokens
    # (which would otherwise resolve to the User row sharing that id).
    if payload.get("typ") != "staff":
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)

    db = SessionLocal()
    try:
        user = db.get(User, user_id)
    finally:
        db.close()
    if (
        user is None
        or not user.is_active
        or not token_is_current(payload, user.token_version)
    ):
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)

    await realtime.connect(user_id, websocket)
    try:
        while True:
            # We don't expect client messages; this keeps the socket open and
            # detects disconnects.
            await websocket.receive_text()
    except WebSocketDisconnect:
        realtime.disconnect(user_id, websocket)
    except Exception:
        realtime.disconnect(user_id, websocket)


app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(patients.router, prefix=settings.api_prefix)
app.include_router(consultations.router, prefix=settings.api_prefix)
app.include_router(dashboard.router, prefix=settings.api_prefix)
app.include_router(escalation.router, prefix=settings.api_prefix)
app.include_router(notifications.router, prefix=settings.api_prefix)
app.include_router(users.router, prefix=settings.api_prefix)
app.include_router(org.router, prefix=settings.api_prefix)
app.include_router(attachments.router, prefix=settings.api_prefix)
app.include_router(messages.router, prefix=settings.api_prefix)
app.include_router(fhir.router, prefix=settings.api_prefix)
app.include_router(clinics.router, prefix=settings.api_prefix)
app.include_router(appointments.router, prefix=settings.api_prefix)
app.include_router(portal.router, prefix=settings.api_prefix)
