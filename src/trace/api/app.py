"""FastAPI application factory for TRACE v0.3."""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from trace.api.routes_sessions import router as sessions_router
from trace.api.routes_profile import router as profile_router
from trace.db.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager initializing database tables on startup."""
    await init_db()
    yield


def create_app() -> FastAPI:
    """Create and configure TRACE FastAPI application."""
    app = FastAPI(
        title="TRACE Debugging API",
        version="0.3.0",
        description="Evidence-driven AI debugging investigation product API for Python students",
        lifespan=lifespan,
    )

    # Enable CORS for local Vite development server
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register Routers
    app.include_router(sessions_router)
    app.include_router(profile_router)

    # Health check endpoint
    @app.get("/api/health", summary="Health check")
    async def health_check():
        return {
            "status": "healthy",
            "version": "0.3.0",
            "product": "TRACE — Evidence Engine & Debugging Investigation",
        }

    # Mount static frontend build if dist directory exists
    frontend_dist = Path(__file__).parent.parent.parent.parent / "frontend" / "dist"
    if frontend_dist.exists():
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="static_frontend")

    # Global Exception Handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "InternalServerError",
                "detail": "An unexpected error occurred during request processing.",
            },
        )

    return app


# Default application instance for Uvicorn
app = create_app()
