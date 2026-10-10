"""Web versions of a site photo: an exact 4:3 crop at 960 and 480 px wide, WebP and JPEG, camera metadata dropped.

    python site/tools/photos.py IMG_1234.jpg --name rib-roof-eight
    python site/tools/photos.py IMG_1234.jpg --name hip-roof-town --crop 0.05,0.14,0.95,1   # keep this part of the frame first
    python site/tools/photos.py IMG_1234.jpg --og                                           # the 1200 x 630 share image

Files land in site/static/photos/ and the pages reference them by name (see index.html). The originals stay with
the owner; only these web sizes are committed.
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


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("source")
    ap.add_argument("--name", help="file name on the site, e.g. rib-roof-eight")
    ap.add_argument("--crop", help="l,t,r,b as fractions of the frame to keep before the 4:3 crop")
    ap.add_argument("--og", action="store_true", help="write og-home.jpg (1200 x 630) instead")
    a = ap.parse_args()
    im = ImageOps.exif_transpose(Image.open(a.source)).convert("RGB")   # exif_transpose applies the rotation, convert drops the rest
    frac = tuple(float(x) for x in a.crop.split(",")) if a.crop else None
    OUT.mkdir(parents=True, exist_ok=True)
    if a.og:
        og = crop_to(im, 1200 / 630, frac).resize((1200, 630), Image.LANCZOS)
        og.save(OUT / "og-home.jpg", "JPEG", quality=82, optimize=True, progressive=True)
        print(OUT / "og-home.jpg")
        return
    if not a.name:
        ap.error("--name is required unless --og")
    im = crop_to(im, 4 / 3, frac)
    for w in (960, 480):
        small = im.resize((w, w * 3 // 4), Image.LANCZOS)
        small.save(OUT / f"{a.name}-{w}.webp", "WEBP", quality=80, method=6)
        small.save(OUT / f"{a.name}-{w}.jpg", "JPEG", quality=82, optimize=True, progressive=True)
        print(OUT / f"{a.name}-{w}.webp", OUT / f"{a.name}-{w}.jpg")


if __name__ == "__main__":
    main()
