"""
SteerPlane API — Main Application

FastAPI entry point with CORS, routes, and database initialization.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db.database import init_db
from .routes.runs import router as runs_router
from .routes.telemetry import router as telemetry_router
from .routes.policies import router as policies_router
from .routes.gateway import router as gateway_router
from .routes.api_keys import router as api_keys_router
from .routes.approvals import router as approvals_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize the database on startup."""
    init_db()
    print(f"\n[STARTED] {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"   Database: {settings.DATABASE_URL}")
    print("   Gateway: http://localhost:8000/gateway/v1")
    print("   Docs: http://localhost:8000/docs\n")
    if settings.ADMIN_TOKEN_SOURCE == "generated":
        print("   Admin auth: enabled with a generated token for this process only")
        print(f"   {settings.ADMIN_TOKEN_HEADER}: {settings.ADMIN_TOKEN}\n")
    else:
        print(f"   Admin auth: enabled via {settings.ADMIN_TOKEN_HEADER}\n")
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Agent Control Plane for Autonomous Systems — Runtime API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
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
app.include_router(policies_router)
app.include_router(gateway_router)
app.include_router(api_keys_router)
app.include_router(approvals_router)


@app.get("/health")
def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
