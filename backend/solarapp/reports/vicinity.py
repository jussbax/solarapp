"""The vicinity map of the plan set (round 13, item 4, docs/audits/round-13/engineer-brief.md 4.1): map tiles fetched
under the OpenStreetMap tile usage policy and composed with Pillow into the two mosaics the sheet prints, with the
office's upload as the override and the fallback.

The policy, as this module keeps it: a descriptive User-Agent that names the app and a contact (the company's website
and its e-mail from the profile; without either the fetch is refused rather than sent anonymously); a few tiles per
project (two 3 × 3 mosaics, 18 tiles), fetched one at a time (one thread: `FETCH_LOCK`), each with an 8 s timeout and
one retry; a 429 stops the run at once; every tile is cached under {data_dir}/tiles/{z}/{x}/{y}.png and reused for 30
days (the policy's seven-day floor, generously); nothing is prefetched; the attribution and licence line is burned
into every mosaic and printed on the sheet. The tile address is a setting (`map_tiles_url`, with {z}/{x}/{y}) so
another provider can take the place of tile.openstreetmap.org without a code change.

Nothing here runs inside the request that builds the PDF: the office presses "Prepare the map" (or the page presses
it for them before the first plans download), the result is kept with the project under {data_dir}/projects/{id}/,
and the sheet prints what is on record. A failure is recorded with its reason, and the sheet prints the pin, the
address and that reason instead of a map, never a placeholder that looks like one.
"""
from __future__ import annotations

import io
import json
import logging
import math
import threading
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import httpx
from PIL import Image, ImageDraw, ImageFont

from .. import APP_VERSION
from .brand import ASSETS

log = logging.getLogger("solarapp.audit")

TILE_PX = 256
MOSAIC_N = 3                                  # 3 × 3 tiles per mosaic, the pin's tile in the middle
MOSAIC_PX = TILE_PX * MOSAIC_N                # 768
MOSAICS: tuple[tuple[int, float], ...] = ((16, 200.0), (12, 5000.0))   # (zoom, the scale bar's length in metres)
TILE_CACHE_DAYS = 30
TIMEOUT_S = 8.0
RETRIES = 1
EQUATOR_M_PER_PX = 156543.03                  # metres per pixel at zoom 0 on the equator (Web Mercator, 256 px tiles)
UPLOAD_MAX_BYTES = 8 * 1024 * 1024            # the body cap on the upload route (main.py) and the check inside it
UPLOAD_MAX_SIDE = 2400                        # the longer side of the stored upload
UPLOAD_FILE = "vicinity-upload.png"
GOLD, GOLD_DARK, INK = (201, 162, 39), (164, 132, 28), (17, 17, 17)

# at most one tile request in flight for the whole process (the policy's "no more than two threads", kept at one)
FETCH_LOCK = threading.Lock()


class TileError(Exception):
    """A tile could not be had: the reason the record keeps and the sheet prints."""


class UploadError(Exception):
    """The upload is not a PNG or JPEG the server can decode."""


# ---- tile maths (Web Mercator, as the brief gives it)

def tile_xy(lat: float, lon: float, zoom: int) -> tuple[int, int, float, float]:
    """The tile a point falls in at a zoom and the point's fractional position inside it: (x, y, fx, fy)."""
    n = 2 ** int(zoom)
    phi = math.radians(float(lat))
    xf = (float(lon) + 180.0) / 360.0 * n
    yf = (1.0 - math.log(math.tan(phi) + 1.0 / math.cos(phi)) / math.pi) / 2.0 * n
    x, y = int(math.floor(xf)), int(math.floor(yf))
    return x, y, xf - x, yf - y


def metres_per_pixel(lat: float, zoom: int) -> float:
    return EQUATOR_M_PER_PX * math.cos(math.radians(float(lat))) / (2 ** int(zoom))


def pin_pixel(lat: float, lon: float, zoom: int) -> tuple[float, float]:
    """Where the pin sits in the 3 × 3 mosaic centred on its tile, in pixels from the top-left corner."""
    _x, _y, fx, fy = tile_xy(lat, lon, zoom)
    return TILE_PX + fx * TILE_PX, TILE_PX + fy * TILE_PX


def tile_url(template: str, zoom: int, x: int, y: int) -> str:
    return template.replace("{z}", str(zoom)).replace("{x}", str(x)).replace("{y}", str(y))


def tile_host(template: str) -> str:
    return urlparse(template.replace("{z}", "0").replace("{x}", "0").replace("{y}", "0")).hostname or ""


# ---- the policy's User-Agent and the project's folder

def user_agent(company: dict, website: str) -> str:
    """PLDSolarApp/<round> (+website; email): the policy asks that the application and a contact be named. Blank when
    neither the website nor the company e-mail is known: the caller then refuses to fetch rather than send an anonymous
    request."""
    email = str((company or {}).get("email") or "").strip()
    site = str(website or "").strip().rstrip("/")
    parts = ([f"+{site}"] if site else []) + ([email] if email else [])
    if not parts:
        return ""
    return f"PLDSolarApp/{APP_VERSION} ({'; '.join(parts)})"


def project_dir(data_dir: Path, assessment_id: int) -> Path:
    return Path(data_dir) / "projects" / str(int(assessment_id))


def tiles_dir(data_dir: Path) -> Path:
    return Path(data_dir) / "tiles"


def remove_project_files(data_dir: Path, assessment_id: int) -> None:
    """The project's folder (the composed maps and the upload) goes with the record."""
    import shutil

    d = project_dir(data_dir, assessment_id)
    if d.is_dir():
        shutil.rmtree(d, ignore_errors=True)


# ---- the fetch with the cache

def make_client() -> httpx.Client:
    """The HTTP client the app fetches tiles with: the environment's proxy settings apply, as to every outbound call. The
    tests replace this with a client on a MockTransport, so the suite never reaches a tile server."""
    return httpx.Client()


class TileSource:
    """Tiles from the cache, else from the tile server one request at a time with the policy's headers. `client` is any
    httpx.Client (the tests pass one with a MockTransport; the app passes one that honours the environment's proxy)."""

    def __init__(self, url_template: str, agent: str, cache_dir: Path, client: httpx.Client, now: Optional[datetime] = None):
        self.url_template = url_template
        self.agent = agent
        self.cache_dir = Path(cache_dir)
        self.client = client
        self.now = now or datetime.now(timezone.utc)
        self.fetched = 0
        self.cached = 0

    def _cache_path(self, zoom: int, x: int, y: int) -> Path:
        return self.cache_dir / str(zoom) / str(x) / f"{y}.png"

    def get(self, zoom: int, x: int, y: int) -> bytes:
        p = self._cache_path(zoom, x, y)
        if p.is_file():
            age_days = (self.now.timestamp() - p.stat().st_mtime) / 86400.0
            if age_days <= TILE_CACHE_DAYS:
                self.cached += 1
                return p.read_bytes()
        data = self._fetch(tile_url(self.url_template, zoom, x, y))
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        self.fetched += 1
        return data

    def _fetch(self, url: str) -> bytes:
        last: Optional[TileError] = None
        for _attempt in range(RETRIES + 1):
            try:
                r = self.client.get(url, headers={"User-Agent": self.agent, "Accept": "image/png,image/*;q=0.8"}, timeout=TIMEOUT_S)
            except httpx.TimeoutException:
                last = TileError(f"timeout after {TIMEOUT_S:g} s")
                continue
            except httpx.TransportError as e:
                last = TileError(f"no outside access ({type(e).__name__})")
                continue
            if r.status_code == 200 and r.content:
                try:
                    im = Image.open(io.BytesIO(r.content))
                    im.load()
                except Exception:  # noqa: BLE001
                    raise TileError("the tile server answered with something other than an image")
                if im.size != (TILE_PX, TILE_PX):
                    raise TileError(f"the tile server answered with a {im.size[0]} × {im.size[1]} image, not a {TILE_PX} px tile")
                return r.content
            if r.status_code == 429:
                raise TileError("HTTP 429: the tile server asks for fewer requests; try again later")
            last = TileError(f"HTTP {r.status_code} from the tile server")
            if 400 <= r.status_code < 500:
                break       # a missing tile or a refused request does not change on a retry
        assert last is not None
        raise last


# ---- the composition

def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype(str(ASSETS / "fonts" / "Montserrat-600.ttf"), size)
    except Exception:  # noqa: BLE001
        return ImageFont.load_default()


def _marker(draw: ImageDraw.ImageDraw, px: float, py: float) -> None:
    """The brand's marker at the pin's pixel: a filled gold circle with a white ring on a stem down to the point."""
    head_r, lift = 9, 22
    cx, cy = px, py - lift
    draw.line([(px, py), (cx, cy + head_r - 2)], fill=(255, 255, 255), width=5)
    draw.line([(px, py), (cx, cy + head_r - 2)], fill=INK, width=2)
    draw.ellipse([cx - head_r - 3, cy - head_r - 3, cx + head_r + 3, cy + head_r + 3], fill=(255, 255, 255))
    draw.ellipse([cx - head_r, cy - head_r, cx + head_r, cy + head_r], fill=GOLD, outline=GOLD_DARK, width=1)
    draw.ellipse([px - 3, py - 3, px + 3, py + 3], fill=INK, outline=(255, 255, 255), width=1)


def _north_arrow(draw: ImageDraw.ImageDraw, cx: float, cy: float) -> None:
    """Tiles are north-up, so a straight arrow in the top-right corner."""
    font = _font(14)
    draw.rounded_rectangle([cx - 16, cy - 30, cx + 16, cy + 22], radius=6, fill=(255, 255, 255), outline=(200, 200, 196))
    draw.polygon([(cx, cy - 22), (cx - 7, cy + 2), (cx, cy - 3), (cx + 7, cy + 2)], fill=INK)
    draw.text((cx, cy + 10), "N", fill=INK, font=font, anchor="mm")


def _scale_bar(draw: ImageDraw.ImageDraw, x: float, y: float, length_px: float, label: str) -> None:
    font = _font(12)
    w = draw.textlength(label, font=font)
    draw.rounded_rectangle([x - 6, y - 22, x + max(length_px, w) + 8, y + 8], radius=4, fill=(255, 255, 255))
    draw.line([(x, y), (x + length_px, y)], fill=INK, width=3)
    for xx in (x, x + length_px):
        draw.line([(xx, y - 6), (xx, y + 4)], fill=INK, width=2)
    draw.text((x, y - 9), label, fill=INK, font=font, anchor="ls")


def _attribution_strip(im: Image.Image, text: str) -> None:
    font = _font(12)
    strip = Image.new("RGBA", (im.width, 18), (255, 255, 255, 225))
    im.paste(strip, (0, im.height - 18), strip)
    draw = ImageDraw.Draw(im)
    draw.text((6, im.height - 4), text, fill=INK, font=font, anchor="ls")


def compose_mosaic(tiles: dict[tuple[int, int], bytes], lat: float, lon: float, zoom: int, scale_m: float, attribution: str, host: str,
                   fetched: date) -> Image.Image:
    """One 768 × 768 mosaic from nine tiles keyed (column, row) 0..2, with the pin, the north arrow, the scale bar and the
    attribution strip."""
    im = Image.new("RGB", (MOSAIC_PX, MOSAIC_PX), (245, 245, 243))
    for (c, r), data in tiles.items():
        t = Image.open(io.BytesIO(data)).convert("RGB")
        im.paste(t, (c * TILE_PX, r * TILE_PX))
    draw = ImageDraw.Draw(im)
    px, py = pin_pixel(lat, lon, zoom)
    _marker(draw, px, py)
    _north_arrow(draw, MOSAIC_PX - 30, 40)
    bar_px = scale_m / metres_per_pixel(lat, zoom)
    label = f"{scale_m / 1000:g} km" if scale_m >= 1000 else f"{scale_m:g} m"
    _scale_bar(draw, 14, MOSAIC_PX - 34, bar_px, label)
    _attribution_strip(im, f"{attribution} — {host}, fetched {fetched.isoformat()}, zoom {zoom}")
    return im


def _round_pin(lat: float, lon: float) -> tuple[float, float]:
    return round(float(lat), 5), round(float(lon), 5)


def fetch_mosaics(lat: float, lon: float, source: TileSource, out_dir: Path, attribution: str, today: Optional[date] = None) -> dict:
    """Both mosaics for the pin, written under `out_dir` only when every tile came; the `osm` block of the record. Raises
    TileError on the first tile that fails after its retry: the run stops there, so a dead server costs at most two
    timeouts, and no partial map is kept."""
    today = today or source.now.date()
    host = tile_host(source.url_template)
    images: dict[int, Image.Image] = {}
    for zoom, scale_m in MOSAICS:
        x0, y0, _fx, _fy = tile_xy(lat, lon, zoom)
        tiles: dict[tuple[int, int], bytes] = {}
        for r in range(MOSAIC_N):
            for c in range(MOSAIC_N):
                tiles[(c, r)] = source.get(zoom, x0 - 1 + c, y0 - 1 + r)
        images[zoom] = compose_mosaic(tiles, lat, lon, zoom, scale_m, attribution, host, today)
    out_dir.mkdir(parents=True, exist_ok=True)
    files: dict[str, str] = {}
    for zoom, im in images.items():
        name = f"vicinity-z{zoom}.png"
        im.save(out_dir / name, "PNG", optimize=True)
        files[str(zoom)] = name
    block = {
        "files": files, "fetched_at": source.now.isoformat(), "pin": list(_round_pin(lat, lon)), "host": host, "attribution": attribution,
        "tiles_fetched": source.fetched, "tiles_cached": source.cached,
    }
    (out_dir / "vicinity.json").write_text(json.dumps(block, indent=1))
    return block


def is_current(state: Optional[dict], lat: Optional[float], lon: Optional[float]) -> bool:
    """Whether the fetched mosaics on record were made for this pin (rounded to five decimals)."""
    osm = (state or {}).get("osm") or {}
    if not osm or lat is None or lon is None:
        return False
    pin = osm.get("pin") or []
    return len(pin) == 2 and tuple(pin) == _round_pin(lat, lon)


def _with_source(state: dict) -> dict:
    state["source"] = "upload" if state.get("upload") else "osm" if state.get("osm") else None
    return state


def prepare(lat: float, lon: float, *, data_dir: Path, assessment_id: int, url_template: str, attribution: str, agent: str,
            state: Optional[dict] = None, client: Optional[httpx.Client] = None, now: Optional[datetime] = None, force: bool = False) -> dict:
    """"Prepare the map": the record's vicinity block after the fetch, reused when the mosaics on record were made for this
    pin (unless `force`), with `error` set and the old mosaics dropped when the fetch fails. Serialised on FETCH_LOCK."""
    state = dict(state or {})
    now = now or datetime.now(timezone.utc)
    if not force and is_current(state, lat, lon) and all((project_dir(data_dir, assessment_id) / f).is_file() for f in (state["osm"].get("files") or {}).values()):
        return _with_source(state)
    with FETCH_LOCK:
        try:
            if not url_template.strip():
                raise TileError("the tile fetch is switched off (no SOLARAPP_MAP_TILES_URL)")
            if not agent:
                raise TileError("no contact for the tile server's User-Agent: type the company e-mail under Settings › Company (or set SOLARAPP_WEBSITE_URL)")
            own = client is None
            c = client or httpx.Client()
            try:
                source = TileSource(url_template, agent, tiles_dir(data_dir), c, now=now)
                block = fetch_mosaics(lat, lon, source, project_dir(data_dir, assessment_id), attribution)
            finally:
                if own:
                    c.close()
            state["osm"] = block
            state["error"] = None
            log.info("vicinity map prepared id=%s host=%s fetched=%s cached=%s", assessment_id, block["host"], block["tiles_fetched"], block["tiles_cached"])
        except TileError as e:
            state["osm"] = None
            state["error"] = {"reason": str(e), "at": now.isoformat()}
            log.info("vicinity map not fetched id=%s reason=%s", assessment_id, e)
    return _with_source(state)


# ---- the upload

def store_upload(data: bytes, note: str, out_dir: Path, *, state: Optional[dict] = None, now: Optional[datetime] = None) -> dict:
    """The office's screen grab: decoded and re-encoded with Pillow (EXIF and every other chunk dropped, the orientation
    applied first), the longer side capped at 2,400 px, stored as PNG; the record's block with the upload set."""
    now = now or datetime.now(timezone.utc)
    if len(data) > UPLOAD_MAX_BYTES:
        raise UploadError("The image is larger than 8 MB.")
    try:
        im = Image.open(io.BytesIO(data))
        fmt = im.format
        im.load()
    except Image.DecompressionBombError:
        raise UploadError("The image is unreasonably large inside.")
    except Exception:  # noqa: BLE001
        raise UploadError("Upload a PNG or JPEG image.")
    if fmt not in ("PNG", "JPEG"):
        raise UploadError(f"Upload a PNG or JPEG image (this is {fmt or 'not an image'}).")
    from PIL import ImageOps

    im = ImageOps.exif_transpose(im)
    im = im.convert("RGBA") if im.mode in ("RGBA", "LA", "P") else im.convert("RGB")
    if im.mode == "RGBA":
        flat = Image.new("RGB", im.size, (255, 255, 255))
        flat.paste(im, mask=im.getchannel("A"))
        im = flat
    if max(im.size) > UPLOAD_MAX_SIDE:
        im.thumbnail((UPLOAD_MAX_SIDE, UPLOAD_MAX_SIDE), Image.Resampling.LANCZOS)
    clean = Image.new("RGB", im.size)      # a fresh image carries no info chunks, so nothing from the original survives
    clean.paste(im)
    out_dir.mkdir(parents=True, exist_ok=True)
    clean.save(out_dir / UPLOAD_FILE, "PNG", optimize=True)
    state = dict(state or {})
    state["upload"] = {"file": UPLOAD_FILE, "uploaded_at": now.isoformat(), "note": str(note or "").strip()[:200], "width": clean.width, "height": clean.height}
    return _with_source(state)


def remove_upload(state: Optional[dict], out_dir: Path) -> dict:
    state = dict(state or {})
    p = out_dir / UPLOAD_FILE
    if p.is_file():
        p.unlink()
    state["upload"] = None
    return _with_source(state)


def current_file(state: Optional[dict], out_dir: Optional[Path], which: str = "") -> Optional[Path]:
    """The file the sheet (or the preview) shows: the upload when present, else the main mosaic; `which` asks for
    "upload", "z16" or "z12" outright. None when the file is not on disk."""
    if not state or out_dir is None:
        return None
    up, osm = state.get("upload") or {}, state.get("osm") or {}
    cands: list[str] = []
    if which == "upload":
        cands = [up.get("file") or ""]
    elif which in ("z16", "z12"):
        cands = [(osm.get("files") or {}).get(which[1:]) or ""]
    else:
        cands = [up.get("file") or "", (osm.get("files") or {}).get("16") or ""]
    for name in cands:
        if name and (Path(out_dir) / name).is_file():
            return Path(out_dir) / name
    return None
