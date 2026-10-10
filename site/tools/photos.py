"""Web versions of a site photo: an exact crop at the named widths, WebP and JPEG, camera metadata dropped.

    python site/tools/photos.py IMG_1234.jpg --name rib-roof-eight                           # 4:3 at 960 and 480 (a card)
    python site/tools/photos.py IMG_1234.jpg --name hip-roof-town --crop 0.05,0.14,0.95,1    # keep this part of the frame first
    python site/tools/photos.py IMG_1234.jpg --name rib-roof-eight-wide --ratio 16:9 --widths 1280,960,640   # a page hero
    python site/tools/photos.py IMG_1234.jpg --name rib-roof-eight-tall --ratio 4:5 --widths 720              # the hero on a phone
    python site/tools/photos.py --from-web rib-roof-eight-angle --widths 720                  # another width of a photo already cut
    python site/tools/photos.py IMG_1234.jpg --og                                             # the 1200 x 630 share image

Files land in site/static/photos/ and the pages reference them by name (see index.html). The originals stay with
the owner; only these web sizes are committed. ``--from-web`` reads the 960 px JPEG already on the site, so a new width
of a card photo keeps the crop the page already shows.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageOps

OUT = Path(__file__).resolve().parent.parent / "static" / "photos"


def crop_to(im: Image.Image, ratio: float, frac: tuple[float, float, float, float] | None) -> Image.Image:
    w, h = im.size
    if frac:
        l, t, r, b = frac
        im = im.crop((int(l * w), int(t * h), int(r * w), int(b * h)))
        w, h = im.size
    if w / h > ratio:
        nw = int(h * ratio)
        return im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    nh = int(w / ratio)
    return im.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))


def parse_ratio(text: str) -> float:
    a, b = text.split(":")
    return float(a) / float(b)


def write_sizes(im: Image.Image, name: str, widths: list[int], ratio: float, quality: int) -> None:
    for w in widths:
        hgt = round(w / ratio)
        if w > im.width:
            raise SystemExit(f"{name}: {w} px asked from a {im.width} px crop; use a smaller width or a wider crop")
        small = im.resize((w, hgt), Image.LANCZOS)
        small.save(OUT / f"{name}-{w}.webp", "WEBP", quality=quality, method=6)
        small.save(OUT / f"{name}-{w}.jpg", "JPEG", quality=quality + 2, optimize=True, progressive=True)
        print(OUT / f"{name}-{w}.webp", OUT / f"{name}-{w}.jpg")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("source", nargs="?", help="the original photo (not needed with --from-web)")
    ap.add_argument("--name", help="file name on the site, e.g. rib-roof-eight")
    ap.add_argument("--crop", help="l,t,r,b as fractions of the frame to keep before the ratio crop")
    ap.add_argument("--ratio", default="4:3", help="the crop's shape, e.g. 4:3 (cards), 16:9 (a wide hero), 4:5 (a phone hero)")
    ap.add_argument("--widths", default="960,480", help="widths to write, largest first, e.g. 1280,960,640")
    ap.add_argument("--quality", type=int, default=80, help="WebP quality (the JPEG is two points higher)")
    ap.add_argument("--from-web", metavar="NAME", help="cut new widths from NAME-960.jpg already in site/static/photos/")
    ap.add_argument("--og", action="store_true", help="write og-home.jpg (1200 x 630) instead")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    widths = [int(x) for x in a.widths.split(",")]
    if a.from_web:
        im = Image.open(OUT / f"{a.from_web}-960.jpg").convert("RGB")
        write_sizes(im, a.from_web, widths, im.width / im.height, a.quality)
        return
    if not a.source:
        ap.error("the original photo is required unless --from-web")
    im = ImageOps.exif_transpose(Image.open(a.source)).convert("RGB")   # exif_transpose applies the rotation, convert drops the rest
    frac = tuple(float(x) for x in a.crop.split(",")) if a.crop else None
    if a.og:
        og = crop_to(im, 1200 / 630, frac).resize((1200, 630), Image.LANCZOS)
        og.save(OUT / "og-home.jpg", "JPEG", quality=82, optimize=True, progressive=True)
        print(OUT / "og-home.jpg")
        return
    if not a.name:
        ap.error("--name is required unless --og")
    ratio = parse_ratio(a.ratio)
    write_sizes(crop_to(im, ratio, frac), a.name, widths, ratio, a.quality)


if __name__ == "__main__":
    main()
