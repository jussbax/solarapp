"""The public website and estimate, as a separate process.

This app holds no database, no customer data and no documents. It serves the
built website (site/dist), the brand marks and the estimate widget, and
forwards only the three estimate calls to the private app over the Docker
network with an internal token. If this process is ever compromised, the
attacker has a static website and two rate-limited endpoints, nothing else.

    uvicorn solarapp.public:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import asyncio
import ipaddress
import time
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import Settings, get_settings

ROOT = Path(__file__).resolve().parent.parent.parent
ALLOWED_QUICK = {"status", "estimate", "lead"}
FORWARDED_HEADERS = ("content-type", "x-visitor", "x-source", "user-agent", "accept-language", "cf-ipcountry")
MAX_BODY = 16_384
ESTIMATES_IN_FLIGHT = 4      # sizings the private app may run at once for the public
STATUS_CACHE_S = 60.0
UNAVAILABLE = "The estimate isn't available right now. Please try again later or message us on Facebook."
# A tight content security policy: the website and the widget are same-origin, the widget injects one style tag.
CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; "
       "connect-src 'self'; frame-ancestors 'self'; base-uri 'self'; form-action 'self'; object-src 'none'")


# The tunnel container reaches us over the Docker network: these are the only peers whose visitor header counts.
_TRUSTED_PEERS = [ipaddress.ip_network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "127.0.0.0/8", "fc00::/7", "::1/128")]


def _trusted_peer(host: str) -> bool:
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return any(ip in n for n in _TRUSTED_PEERS)


def create_public_app(settings: Optional[Settings] = None, transport: Optional[httpx.AsyncBaseTransport] = None) -> FastAPI:
    settings = settings or get_settings()
    if not settings.internal_token:
        raise RuntimeError("SOLARAPP_INTERNAL_TOKEN is required for the public website process.")
    site = settings.site_dir or ROOT / "site" / "dist"
    dist = settings.static_dir or ROOT / "frontend" / "dist"
    site_root = site.resolve()
    client = httpx.AsyncClient(base_url=settings.upstream.rstrip("/"), transport=transport, timeout=httpx.Timeout(90.0, connect=10.0))
    busy = asyncio.Semaphore(ESTIMATES_IN_FLIGHT)
    status_cache: dict[str, object] = {"until": 0.0, "body": b"", "type": "application/json"}
    app = FastAPI(title="PL Development website", docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("Content-Security-Policy", CSP)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "geolocation=(self), camera=(), microphone=(), payment=()")
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response

    @app.get("/api/health")
    def health() -> dict:
        return {"ok": True, "site": site.is_dir()}

    async def read_capped(request: Request) -> Optional[bytes]:
        """The body, or None when it is larger than the cap; never buffers more than the cap."""
        cl = request.headers.get("content-length", "")
        if cl.isdigit() and int(cl) > MAX_BODY:
            return None
        body = b""
        async for chunk in request.stream():
            body += chunk
            if len(body) > MAX_BODY:
                return None
        return body

    @app.api_route("/api/quick/{name}", methods=["GET", "POST"])
    async def quick_proxy(name: str, request: Request) -> Response:
        """Forward the estimate calls to the private app; nothing else crosses."""
        if name not in ALLOWED_QUICK:
            return JSONResponse({"detail": "Not found"}, status_code=404)
        now = time.monotonic()
        if name == "status" and request.method == "GET" and status_cache["until"] > now:
            return Response(status_cache["body"], media_type=str(status_cache["type"]))
        headers = {k: v for k, v in request.headers.items() if k.lower() in FORWARDED_HEADERS}
        # the real visitor address for the private app's rate limiter: the tunnel's header only when the
        # peer is the tunnel (a private or loopback address), never a header a stranger sends to an exposed origin
        peer = request.client.host if request.client else ""
        client_ip = (request.headers.get("cf-connecting-ip") if _trusted_peer(peer) else "") or peer
        if client_ip:
            headers["x-forwarded-for"] = client_ip[:64]
        headers["x-internal-token"] = settings.internal_token
        body = await read_capped(request)
        if body is None:
            return JSONResponse({"detail": "Request too large."}, status_code=413)
        try:
            if name == "estimate":
                if busy.locked():
                    return JSONResponse({"detail": "Lots of people are using the estimate right now. Please try again in a minute."}, status_code=503, headers={"Retry-After": "30"})
                async with busy:
                    upstream = await client.request(request.method, f"/api/quick/{name}", content=body, headers=headers, params=request.query_params)
            else:
                upstream = await client.request(request.method, f"/api/quick/{name}", content=body, headers=headers, params=request.query_params)
        except httpx.HTTPError:
            return JSONResponse({"detail": UNAVAILABLE}, status_code=503)
        media = upstream.headers.get("content-type", "application/json")
        if name == "status" and request.method == "GET" and upstream.status_code == 200:
            status_cache.update(until=now + STATUS_CACHE_S, body=upstream.content, type=media)
        return Response(upstream.content, status_code=upstream.status_code, media_type=media)

    @app.api_route("/api/{rest:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"], include_in_schema=False)
    def no_api(rest: str) -> JSONResponse:
        return JSONResponse({"detail": "Not found"}, status_code=404)

    if (dist / "widget").is_dir():
        app.mount("/widget", StaticFiles(directory=dist / "widget"), name="widget")
    brand_dir = site / "brand" if (site / "brand").is_dir() else ROOT / "frontend" / "public" / "brand"
    if brand_dir.is_dir():
        app.mount("/brand", StaticFiles(directory=brand_dir), name="brand")
    if (site / "static").is_dir():
        app.mount("/static", StaticFiles(directory=site / "static"), name="static")

    @app.get("/{path:path}", include_in_schema=False)
    def page(path: str) -> Response:
        """Clean URLs for the built pages: / -> index.html, /estimate -> estimate.html. Nothing outside the site folder."""
        clean = path.strip("/")
        if clean.endswith(".html"):
            clean = clean[:-5]
        candidate = (site / (f"{clean}.html" if clean else "index.html")).resolve()
        if candidate.is_file() and site_root in candidate.parents:
            return FileResponse(candidate, media_type="text/html", headers={"Cache-Control": "no-cache"})
        asset = (site / clean).resolve() if clean else None
        if asset and asset.is_file() and site_root in asset.parents:
            return FileResponse(asset)
        not_found = site / "404.html"
        if not_found.is_file():
            return FileResponse(not_found, status_code=404, media_type="text/html")
        return JSONResponse({"detail": "Not found"}, status_code=404)

    app.state.client = client
    return app


# Built on first use (uvicorn asks for `app`), so importing the module never needs the production secrets.
_app = None


def __getattr__(name: str):
    global _app
    if name == "app":
        if _app is None:
            _app = create_public_app()
        return _app
    raise AttributeError(name)
