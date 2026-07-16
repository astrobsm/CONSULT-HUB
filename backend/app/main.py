import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    attachments,
    auth,
    consultations,
    dashboard,
    escalation,
    notifications,
    org,
    patients,
    users,
)
from app.core.config import settings
from app.core.database import Base, engine
from app.core.escalation import run_escalations_job

# Import models so their tables register on Base.metadata.
import app.models  # noqa: F401

logger = logging.getLogger("consulthub")


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Dev convenience: auto-create tables. Use Alembic in production.
    Base.metadata.create_all(bind=engine)

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


app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(patients.router, prefix=settings.api_prefix)
app.include_router(consultations.router, prefix=settings.api_prefix)
app.include_router(dashboard.router, prefix=settings.api_prefix)
app.include_router(escalation.router, prefix=settings.api_prefix)
app.include_router(notifications.router, prefix=settings.api_prefix)
app.include_router(users.router, prefix=settings.api_prefix)
app.include_router(org.router, prefix=settings.api_prefix)
app.include_router(attachments.router, prefix=settings.api_prefix)
