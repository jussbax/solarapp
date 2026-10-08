from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from sqlmodel import Session

from .api import appliances, assessments, auth_routes, data_routes, pricing_routes, quick_routes, settings_routes
from .config import Settings, get_settings
from .core.dataset import NasaReference, PvgisDataset
from .db import init_engine
from .pricing.store import ensure_seeded


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        engine = init_engine(settings.database_path)
        with Session(engine) as session:
            ensure_seeded(session)
        app.state.pvgis = PvgisDataset(settings.data_dir)
        app.state.nasa = NasaReference(settings.data_dir)
        yield

    app = FastAPI(title="Solar roof simulator", lifespan=lifespan)
    app.dependency_overrides[get_settings] = lambda: settings
    if settings.origins:
        # The company website embeds the estimate and calls /api/quick/* from its own origin.
        # No credentials are allowed cross-origin, so the login cookie never travels with these calls.
        app.add_middleware(CORSMiddleware, allow_origins=settings.origins, allow_credentials=False, allow_methods=["GET", "POST"],
                           allow_headers=["Content-Type", "X-Visitor", "X-Source"], max_age=3600)
    app.include_router(auth_routes.router)
    app.include_router(assessments.router)
    app.include_router(settings_routes.router)
    app.include_router(data_routes.router)
    app.include_router(appliances.router)
    app.include_router(pricing_routes.router)
    app.include_router(quick_routes.router)

    @app.get("/api/health")
    def health() -> dict:
        return {"ok": True}

    static = settings.static_dir or Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    index = static / "index.html"
    estimate_page = static / "estimate.html"
    if index.is_file():
        if (static / "assets").is_dir():
            app.mount("/assets", StaticFiles(directory=static / "assets"), name="assets")
        if (static / "widget").is_dir():
            app.mount("/widget", StaticFiles(directory=static / "widget"), name="widget")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str, request: Request):
            if path.startswith("api/"):
                return JSONResponse({"detail": "Not found"}, status_code=404)
            if path in ("estimate", "estimate/", "quick") and estimate_page.is_file():
                return FileResponse(estimate_page)  # public page: its own bundle, no login shell
            candidate = static / path
            if path and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(index)

    return app


app = create_app()
