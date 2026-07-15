from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, consultations, dashboard, patients
from app.core.config import settings
from app.core.database import Base, engine

# Import models so their tables register on Base.metadata.
import app.models  # noqa: F401


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Dev convenience: auto-create tables. Use Alembic in production.
    Base.metadata.create_all(bind=engine)
    yield


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
