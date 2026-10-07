from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from sqlmodel import Session

from .api import appliances, assessments, auth_routes, data_routes, pricing_routes, settings_routes
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
    app.include_router(auth_routes.router)
    app.include_router(assessments.router)
    app.include_router(settings_routes.router)
    app.include_router(data_routes.router)
    app.include_router(appliances.router)
    app.include_router(pricing_routes.router)

    @app.get("/api/health")
    def health() -> dict:
        return {"ok": True}

    static = settings.static_dir or Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    index = static / "index.html"
    if index.is_file():
        if (static / "assets").is_dir():
            app.mount("/assets", StaticFiles(directory=static / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str, request: Request):
            if path.startswith("api/"):
                return JSONResponse({"detail": "Not found"}, status_code=404)
            candidate = static / path
            if path and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(index)

    return app


app = create_app()
