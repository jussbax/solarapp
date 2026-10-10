"""One cache policy for everything the two processes serve from disk, so a redeploy shows at once.

The pages are revalidated on every visit. The stylesheet, the site script and the widget script are referenced
with a content stamp (``/static/site.css?v=1a2b3c4d``, written by ``site/build.py``), so a stamped address can be
kept for a year: the next build changes the stamp, and the browser and the CDN fetch the new file under its new
address. Fonts, photos and brand marks change rarely and may be kept for a day. Anything else is revalidated.
"""
from __future__ import annotations

IMMUTABLE = "public, max-age=31536000, immutable"
A_DAY = "public, max-age=86400"
REVALIDATE = "no-cache"

STAMPED = ("/static/", "/widget/", "/assets/")      # /assets/ is Vite's build output, hashed in the file name
A_DAY_PREFIXES = ("/static/fonts/", "/static/photos/", "/brand/")


def cache_control_for(path: str, query: str = "") -> str | None:
    """The Cache-Control for a static address, or None when the response decides for itself (pages, the API)."""
    if path.startswith("/assets/"):
        return IMMUTABLE
    if path.startswith(STAMPED) and _stamped(query):
        return IMMUTABLE
    if path.startswith(A_DAY_PREFIXES):
        return A_DAY
    if path.startswith(STAMPED):
        return REVALIDATE
    return None


def _stamped(query: str) -> bool:
    return any(part.startswith("v=") and len(part) > 2 for part in query.split("&"))
