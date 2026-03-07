"""
SteerPlane API — Main Application

FastAPI entry point with CORS, routes, and database initialization.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db.database import init_db
from .routes.runs import router as runs_router
from .routes.telemetry import router as telemetry_router


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Agent Control Plane for Autonomous Systems — Runtime API",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow dashboard to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(runs_router)
app.include_router(telemetry_router)


@app.on_event("startup")
def on_startup():
    """Initialize database on startup."""
    init_db()
    print(f"\n[STARTED] {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"   Database: {settings.DATABASE_URL}")
    print(f"   Docs: http://localhost:8000/docs\n")


@app.get("/health")
def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
