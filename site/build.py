"""Build the company website: wrap each page in the shared layout, copy static files, fonts and brand marks.

    python site/build.py                                   -> site/dist/
    python site/build.py --base-url https://pldevinc.com   -> absolute og:image and an og:url per page
    python site/build.py --with-placeholders               -> keep the photo placeholders (for a preview)

Plain HTML and CSS on purpose: nothing to update, nothing to exploit, and the
estimate widget does the only dynamic work. Contact details are filled in
at page load from the app's public profile (see static/site.js), so the
owner edits them in Settings, not here.

Blocks between ``<!-- placeholder:start -->`` and ``<!-- placeholder:end -->``
are placeholders for photos that do not exist yet; the public build drops
them so a visitor never reads "replace this card with a real photo".
"""
from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PAGES = HERE / "pages"
STATIC = HERE / "static"
LAYOUT = HERE / "layout.html"
FONTS = ROOT / "backend" / "solarapp" / "reports" / "assets" / "fonts"
BRAND = ROOT / "frontend" / "public" / "brand"
ICONS = ROOT / "frontend" / "public"

META = re.compile(r"<!--\s*(\w+):\s*(.*?)\s*-->")
PLACEHOLDER = re.compile(r"[ \t]*<!--\s*placeholder:start\s*-->.*?<!--\s*placeholder:end\s*-->[ \t]*\n?", re.S)


def render_page(layout: str, page: Path, base_url: str = "", with_placeholders: bool = False) -> str:
    """One page in the shared frame. ``base_url`` makes the share image and page address absolute."""
    body = page.read_text(encoding="utf-8")
    if not with_placeholders:
        body = PLACEHOLDER.sub("", body)   # before the meta pass, which would eat the marker comments
    meta = {k: v for k, v in META.findall(body) if k != "placeholder"}
    body = META.sub("", body).strip()
    path = meta.get("path", "/" + page.stem)
    base = base_url.rstrip("/")
    html = layout
    html = html.replace("{{og_url}}", f'<meta property="og:url" content="{base}{path}" />' if base else "")
    for key, default in (("title", "PL Development Inc."), ("description", ""), ("path", "/" + page.stem), ("nav", page.stem), ("extra_head", ""), ("extra_body", "")):
        html = html.replace("{{" + key + "}}", meta.get(key, default))
    html = html.replace("{{base_url}}", base)
    return html.replace("{{body}}", body)


def build(out: Path, base_url: str = "", with_placeholders: bool = False) -> list[str]:
    layout = LAYOUT.read_text(encoding="utf-8")
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    shutil.copytree(STATIC, out / "static")
    (out / "static" / "fonts").mkdir(exist_ok=True)
    for f in FONTS.glob("Montserrat-*.ttf"):
        shutil.copy(f, out / "static" / "fonts" / f.name)
    if BRAND.is_dir():
        shutil.copytree(BRAND, out / "brand")
    for name in ("favicon.png", "apple-touch-icon.png"):
        if (ICONS / name).is_file():
            shutil.copy(ICONS / name, out / name)
    built = []
    for page in sorted(PAGES.glob("*.html")):
        html = render_page(layout, page, base_url=base_url, with_placeholders=with_placeholders)
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
