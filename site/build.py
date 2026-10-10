"""Build the company website: wrap each page in the shared layout, copy static files (fonts included) and brand marks.

    python site/build.py                                   -> site/dist/
    python site/build.py --base-url https://pldevinc.com   -> absolute og:image and an og:url per page
    python site/build.py --with-placeholders               -> keep the photo placeholders (for a preview)

Plain HTML and CSS on purpose: nothing to update, nothing to exploit, and the
estimate widget does the only dynamic work. Contact details are filled in
at page load from the app's public profile (see static/site.js), so the
owner edits them in Settings, not here.

A page may name its own share image with ``<!-- og_image: /static/photos/x.jpg -->`` and
``<!-- og_image_alt: ... -->``; the default is the home roof for every page.

Every tag with ``data-profile-hide-if-empty`` starts with ``class="is-empty"`` (the build adds it), so a page
never shows the punctuation around an empty profile field before the fetch answers, or when it fails.

``<!-- include: proof -->`` pastes ``site/partials/proof.html`` (the proof strip the four marketing pages share).

Blocks between ``<!-- placeholder:start -->`` and ``<!-- placeholder:end -->``
are placeholders for photos that do not exist yet; the public build drops
them so a visitor never reads "replace this card with a real photo".

The stylesheet, the site script and the estimate widget's script are referenced with a content stamp
(``/static/site.css?v=1a2b3c4d``): a new build changes the stamp, so a browser or a CDN that kept the old file
fetches the new one under its new address, while the pages themselves are always revalidated (see
``solarapp/caching.py``).
"""
from __future__ import annotations

import argparse
import hashlib
import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PAGES = HERE / "pages"
STATIC = HERE / "static"
LAYOUT = HERE / "layout.html"
BRAND = ROOT / "frontend" / "public" / "brand"
ICONS = ROOT / "frontend" / "public"
WIDGET = ROOT / "frontend" / "dist" / "widget"

STAMPABLE = re.compile(r'\b(src|href)="(/static/[^"?#]+\.(?:css|js)|/widget/[^"?#]+\.js)"')


def stamp(html: str, out: Path) -> str:
    """Append ``?v=<content stamp>`` to the stylesheet, the site script and the widget script the page references.

    The stamp is the first eight hex digits of the file's SHA-1, read from the built folder (``/static/...``) or from
    the frontend build (``/widget/...``); a reference to a file that is not there (the widget before ``npm run build``)
    is left as it is, and the server revalidates it on every visit instead."""
    def fix(m: re.Match) -> str:
        attr, url = m.group(1), m.group(2)
        file = (out / url.lstrip("/")) if url.startswith("/static/") else (WIDGET / url[len("/widget/"):])
        if not file.is_file():
            return m.group(0)
        digest = hashlib.sha1(file.read_bytes()).hexdigest()[:8]
        return f'{attr}="{url}?v={digest}"'
    return STAMPABLE.sub(fix, html)

META = re.compile(r"<!--\s*(\w+):\s*(.*?)\s*-->")
HIDE_IF_EMPTY = re.compile(r"<(\w+)([^>]*\bdata-profile-hide-if-empty\b[^>]*)>")


def start_hidden(html: str) -> str:
    """Give every profile-dependent tag ``is-empty`` from the first paint; site.js removes it when the profile has the field."""
    def fix(m: re.Match) -> str:
        tag, attrs = m.group(1), m.group(2)
        cls = re.search(r'\bclass="([^"]*)"', attrs)
        if cls is None:
            return f'<{tag} class="is-empty"{attrs}>'
        if "is-empty" in cls.group(1).split():
            return m.group(0)
        return f'<{tag}{attrs[:cls.start(1)]}is-empty {attrs[cls.start(1):]}>'
    return HIDE_IF_EMPTY.sub(fix, html)


PLACEHOLDER = re.compile(r"[ \t]*<!--\s*placeholder:start\s*-->.*?<!--\s*placeholder:end\s*-->[ \t]*\n?", re.S)
INCLUDE = re.compile(r"<!--\s*include:\s*([\w-]+)\s*-->")
PARTIALS = HERE / "partials"


def include_partials(body: str) -> str:
    """``<!-- include: proof -->`` pastes site/partials/proof.html, so a block shared by several pages is written once."""
    return INCLUDE.sub(lambda m: (PARTIALS / f"{m.group(1)}.html").read_text(encoding="utf-8").strip(), body)


def render_page(layout: str, page: Path, base_url: str = "", with_placeholders: bool = False) -> str:
    """One page in the shared frame. ``base_url`` makes the share image and page address absolute."""
    body = include_partials(page.read_text(encoding="utf-8"))   # before the meta pass, which would eat the include comment
    if not with_placeholders:
        body = PLACEHOLDER.sub("", body)   # before the meta pass, which would eat the marker comments
    meta = {k: v for k, v in META.findall(body) if k != "placeholder"}
    body = META.sub("", body).strip()
    path = meta.get("path", "/" + page.stem)
    base = base_url.rstrip("/")
    html = layout
    html = html.replace("{{og_url}}", f'<meta property="og:url" content="{base}{path}" />' if base else "")
    for key, default in (("title", "PL Development Inc."), ("description", ""), ("path", "/" + page.stem), ("nav", page.stem), ("extra_head", ""), ("extra_body", ""),
                         ("og_image", "/static/photos/og-home.jpg"), ("og_image_alt", "Eight solar panels in two rows on the rib-type roof of a home, seen from above")):
        html = html.replace("{{" + key + "}}", meta.get(key, default))
    html = html.replace("{{base_url}}", base)
    return start_hidden(html.replace("{{body}}", body))


def build(out: Path, base_url: str = "", with_placeholders: bool = False) -> list[str]:
    layout = LAYOUT.read_text(encoding="utf-8")
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    shutil.copytree(STATIC, out / "static")
    if BRAND.is_dir():
        shutil.copytree(BRAND, out / "brand")
    for name in ("favicon.png", "apple-touch-icon.png"):
        if (ICONS / name).is_file():
            shutil.copy(ICONS / name, out / name)
    built = []
    for page in sorted(PAGES.glob("*.html")):
        html = stamp(render_page(layout, page, base_url=base_url, with_placeholders=with_placeholders), out)
        target = out / ("index.html" if page.stem == "index" else f"{page.stem}.html")
        target.write_text(html, encoding="utf-8")
        built.append(target.name)
    return built


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Build the company website into a folder of plain HTML.")
    ap.add_argument("dest", nargs="?", default=str(HERE / "dist"), help="output folder (default: site/dist)")
    ap.add_argument("--base-url", default="", help="the site's public address, e.g. https://pldevinc.com; makes og:image absolute and adds og:url")
    ap.add_argument("--with-placeholders", action="store_true", help="keep the photo placeholder blocks (previews only)")
    args = ap.parse_args(argv)
    pages = build(Path(args.dest), base_url=args.base_url, with_placeholders=args.with_placeholders)
    print(f"built {len(pages)} pages into {args.dest}")


if __name__ == "__main__":
    main()
