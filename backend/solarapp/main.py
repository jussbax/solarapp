from __future__ import annotations

import logging
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from sqlmodel import Session

from .api import appliances, assessments, auth_routes, data_routes, pricing_routes, quick_routes, settings_routes
from .config import Settings, get_settings
from .core.dataset import NasaReference, PvgisDataset
from .db import init_engine
from .pricing.store import ensure_seeded


DEFAULT_SECRET = "change-me-to-a-long-random-string"
DEFAULT_PASSWORD = "change-me"
# the back office may load its own bundle, inline styles (charts), map tiles, and nothing else
OFFICE_CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: https://tile.openstreetmap.org; "
              "font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'")
EMBEDDABLE = ("/estimate", "/widget/", "/assets/", "/brand/")


def prepare_secrets(settings: Settings) -> Settings:
    """Refuse the example password; replace a missing or example secret key with one generated once on the data volume."""
    if settings.app_password in ("", DEFAULT_PASSWORD):
        raise RuntimeError("Set SOLARAPP_APP_PASSWORD in .env before starting the app.")
    if settings.secret_key in ("", DEFAULT_SECRET) or len(settings.secret_key) < 32:
        key_file = settings.data_dir / "secret.key"
        if not key_file.is_file():
            settings.data_dir.mkdir(parents=True, exist_ok=True)
            key_file.write_text(secrets.token_hex(32))
            key_file.chmod(0o600)
        settings.secret_key = key_file.read_text().strip()
    return settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = prepare_secrets(settings or get_settings())
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

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
    public_hosts = set(settings.public_hosts)
    office_hosts = set(settings.office_hosts)
    PUBLIC_PATHS = ("/api/quick/", "/assets/", "/widget/", "/brand/", "/favicon", "/apple-touch-icon", "/api/health")

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        path = request.url.path
        if not path.startswith(EMBEDDABLE):
            response.headers.setdefault("X-Frame-Options", "DENY")
            response.headers.setdefault("Content-Security-Policy", OFFICE_CSP)
        if path.startswith("/api/") and not path.startswith("/api/quick/") and path != "/api/health":
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    @app.middleware("http")
    async def same_origin_writes(request: Request, call_next):
        """A write to the back office must come from the back office itself: no cross-site and no same-site page may post with the cookie."""
        if request.method in ("POST", "PUT", "PATCH", "DELETE") and not request.url.path.startswith("/api/quick/"):
            site = request.headers.get("sec-fetch-site")
            origin = request.headers.get("origin")
            host = (request.headers.get("host") or "").split(":")[0].strip().rstrip(".").lower()
            if site not in (None, "same-origin", "none") or (origin and (urlparse(origin).hostname or "").lower() != host):
                return JSONResponse({"detail": "Cross-site request refused"}, status_code=403)
        return await call_next(request)

    @app.middleware("http")
    async def estimate_only_host(request: Request, call_next):
        """On the public hostname only the estimate and what it needs exist; the login, the API and the documents do not."""
        host = (request.headers.get("host") or "").split(":")[0].strip().rstrip(".").lower()
        # fail closed: with a public hostname configured, a missing, odd or unknown hostname gets the public treatment too
        treat_public = bool(public_hosts) and (host in public_hosts or not host or (office_hosts and host not in office_hosts))
        if treat_public:
            path = request.url.path
            if path not in ("/", "/estimate", "/estimate/") and not path.startswith(PUBLIC_PATHS):
                return JSONResponse({"detail": "Not found"}, status_code=404)
        return await call_next(request)

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
    static_root = static.resolve()

    def estimate_html() -> Response:
        """The public page, with absolute addresses in its link-preview tags when the public address is known."""
        html = estimate_page.read_text(encoding="utf-8")
        base = settings.estimate_url.rstrip("/").removesuffix("/estimate") if settings.estimate_url else ""
        if base:
            html = html.replace('content="/brand/', f'content="{base}/brand/')
        return Response(html, media_type="text/html", headers={"Cache-Control": "no-cache"})

    if index.is_file():
        if (static / "assets").is_dir():
            app.mount("/assets", StaticFiles(directory=static / "assets"), name="assets")
        if (static / "widget").is_dir():
            app.mount("/widget", StaticFiles(directory=static / "widget"), name="widget")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str, request: Request):
            if path.startswith("api/"):
                return JSONResponse({"detail": "Not found"}, status_code=404)
            host = (request.headers.get("host") or "").split(":")[0].strip().rstrip(".").lower()
            if estimate_page.is_file() and (path in ("estimate", "estimate/", "quick") or (path == "" and public_hosts and host not in office_hosts and (host in public_hosts or not host or office_hosts))):
                return estimate_html()  # public page: its own bundle, no login shell
            # only files inside the build folder are ever served; a path that resolves outside it falls through to the app shell
            candidate = (static / path).resolve()
            if path and candidate.is_file() and static_root in candidate.parents:
                return FileResponse(candidate)
            return FileResponse(index)

    return app


# Built on first use (uvicorn asks for `app`), so importing the module never needs the production secrets.
_app = None


def __getattr__(name: str):
    global _app
    if name == "app":
        if _app is None:
            _app = create_app()
        return _app
    raise AttributeError(name)
