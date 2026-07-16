import asyncio
import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Query, WebSocket, WebSocketException, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocketDisconnect

from app.api.routes import (
    attachments,
    auth,
    consultations,
    dashboard,
    escalation,
    messages,
    notifications,
    org,
    patients,
    users,
)
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.escalation import run_escalations_job
from app.core.realtime import manager as realtime
from app.core.security import decode_access_token
from app.models.entities import User

# Import models so their tables register on Base.metadata.
import app.models  # noqa: F401

logger = logging.getLogger("consulthub")


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Dev convenience: auto-create tables. Use Alembic in production.
    Base.metadata.create_all(bind=engine)

    # Capture the running loop so sync code can push over WebSockets.
    realtime.set_loop(asyncio.get_running_loop())

    scheduler: BackgroundScheduler | None = None
    if settings.escalation_enabled:
        scheduler = BackgroundScheduler(timezone="UTC")
        scheduler.add_job(
            run_escalations_job,
            trigger="interval",
            seconds=settings.escalation_interval_seconds,
            id="escalation",
            max_instances=1,
            coalesce=True,
        )
        scheduler.start()
        logger.info(
            "Escalation scheduler started (every %ss)",
            settings.escalation_interval_seconds,
        )

    try:
        yield
    finally:
        if scheduler is not None:
            scheduler.shutdown(wait=False)


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
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

    db = SessionLocal()
    try:
        user = db.get(User, user_id)
    finally:
        db.close()
    if user is None or not user.is_active:
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
