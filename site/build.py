"""Build the company website: wrap each page in the shared layout, copy static files, fonts and brand marks.

    python site/build.py            -> site/dist/

Plain HTML and CSS on purpose: nothing to update, nothing to exploit, and the
estimate widget does the only dynamic work. Contact details are filled in
at page load from the app's public profile (see static/site.js), so the
owner edits them in Settings, not here.
"""
from __future__ import annotations

import re
import shutil
import sys
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


def build(out: Path) -> list[str]:
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
        body = page.read_text(encoding="utf-8")
        meta = {k: v for k, v in META.findall(body)}
        body = META.sub("", body).strip()
        html = layout
        for key, default in (("title", "PL Development Inc."), ("description", ""), ("path", "/" + page.stem), ("nav", page.stem), ("extra_head", ""), ("extra_body", "")):
            html = html.replace("{{" + key + "}}", meta.get(key, default))
        html = html.replace("{{body}}", body)
        target = out / ("index.html" if page.stem == "index" else f"{page.stem}.html")
        target.write_text(html, encoding="utf-8")
        built.append(target.name)
    return built


if __name__ == "__main__":
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "dist"
    pages = build(dest)
    print(f"built {len(pages)} pages into {dest}")
