"""One-time dataset download.

    python -m solarapp.data_download --out ../data            # whole Philippines
    python -m solarapp.data_download --out ../data --synthetic  # test data, NOT PVGIS

Resumable: cells already on disk are skipped. Polite to PVGIS: a few
concurrent requests with a small delay (their stated limit is far higher).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

from ..core.dataset import cell_id
from . import grid, nasa, pvgis


def write_cell(frame, file: Path) -> None:
    """Store hourly values as float32 (plenty for W/m2, deg C, m/s); halves the size."""
    frame.astype("float32").reset_index().to_parquet(file, index=False, compression="zstd")


def repack(root: Path) -> None:
    """Rewrite existing cell files in the current storage format."""
    import pandas as pd

    cells_dir = root / "pvgis" / "cells"
    files = sorted(cells_dir.glob("*.parquet"))
    before = sum(f.stat().st_size for f in files)
    for i, f in enumerate(files):
        df = pd.read_parquet(f).set_index("time_utc")
        tmp = f.with_suffix(".parquet.tmp")
        write_cell(df, tmp)
        tmp.replace(f)
        if (i + 1) % 100 == 0:
            print(f"  repacked {i + 1}/{len(files)}", flush=True)
    after = sum(f.stat().st_size for f in files)
    print(f"Repacked {len(files)} files: {before / 1e6:.0f} MB -> {after / 1e6:.0f} MB", flush=True)


def _write_index(root: Path, meta: dict) -> None:
    (root / "pvgis").mkdir(parents=True, exist_ok=True)
    tmp = root / "pvgis" / "index.json.tmp"
    tmp.write_text(json.dumps(meta, indent=1))
    tmp.replace(root / "pvgis" / "index.json")


def _load_index(root: Path) -> dict:
    p = root / "pvgis" / "index.json"
    if p.exists():
        return json.loads(p.read_text())
    return {}


async def download_pvgis(root: Path, bbox, step: float, concurrency: int, delay: float, limit: int | None) -> None:
    cells_dir = root / "pvgis" / "cells"
    cells_dir.mkdir(parents=True, exist_ok=True)
    centers = grid.cell_centers(bbox, step)
    land = grid.land_cells(centers, step)
    if limit:
        land = land[:limit]
    print(f"PVGIS: {len(centers)} cells in box, {len(land)} contain land", flush=True)

    existing = _load_index(root)
    index_cells = {c["id"]: c for c in existing.get("cells", [])}
    skipped = {s["id"]: s for s in existing.get("skipped", [])}
    meta = {
        "source": "PVGIS 5.3 TMY (https://re.jrc.ec.europa.eu/pvg_tools/)",
        "radiation_db": existing.get("radiation_db"),
        "synthetic": False,
        "grid_step_deg": step,
        "bbox": list(bbox),
        "downloaded_at": existing.get("downloaded_at") or datetime.now(timezone.utc).isoformat(),
        "cells": list(index_cells.values()),
        "skipped": list(skipped.values()),
    }

    todo = [c for c in land if cell_id(c.lat, c.lon) not in index_cells and cell_id(c.lat, c.lon) not in skipped]
    print(f"PVGIS: {len(todo)} cells to fetch ({len(index_cells)} already present, {len(skipped)} known empty)", flush=True)
    sem = asyncio.Semaphore(concurrency)
    done = 0
    t0 = time.time()
    lock = asyncio.Lock()

    async def one(client: httpx.AsyncClient, c: grid.GridCell) -> None:
        nonlocal done
        cid = cell_id(c.lat, c.lon)
        async with sem:
            try:
                payload = await pvgis.fetch_tmy(client, c.lat, c.lon)
            except pvgis.NoDataError as e:
                async with lock:
                    skipped[cid] = {"id": cid, "lat": c.lat, "lon": c.lon, "reason": str(e)}
                    done += 1
                await asyncio.sleep(delay)
                return
            except Exception as e:  # noqa: BLE001
                print(f"  {cid}: FAILED {e}", flush=True)
                async with lock:
                    done += 1
                await asyncio.sleep(delay)
                return
            file = cells_dir / f"{cid}.parquet"
            write_cell(payload.frame, file)
            async with lock:
                index_cells[cid] = {
                    "id": cid, "lat": c.lat, "lon": c.lon,
                    "elevation_m": payload.elevation_m, "file": f"cells/{cid}.parquet",
                    "radiation_db": payload.radiation_db, "meteo_db": payload.meteo_db,
                    "year_min": payload.year_min, "year_max": payload.year_max,
                    "months_selected": payload.months_selected,
                    "pvgis_lat": payload.lat, "pvgis_lon": payload.lon,
                    "time_offset_h": payload.time_offset_h,
                }
                meta["radiation_db"] = meta["radiation_db"] or payload.radiation_db
                done += 1
                if done % 10 == 0 or done == len(todo):
                    meta["cells"] = list(index_cells.values())
                    meta["skipped"] = list(skipped.values())
                    _write_index(root, meta)
                    rate = done / max(time.time() - t0, 1e-6)
                    print(f"  {done}/{len(todo)} ({rate*60:.0f}/min), last {cid} {payload.radiation_db}", flush=True)
            await asyncio.sleep(delay)

    headers = {"User-Agent": "solarapp-dataset-download/1.0 (one-time regional fetch)"}
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        await asyncio.gather(*(one(client, c) for c in todo))

    meta["cells"] = list(index_cells.values())
    meta["skipped"] = list(skipped.values())
    meta["downloaded_at"] = datetime.now(timezone.utc).isoformat()
    _write_index(root, meta)
    print(f"PVGIS done: {len(index_cells)} cells on disk, {len(skipped)} without data", flush=True)


async def download_nasa(root: Path, bbox) -> None:
    out = root / "nasa"
    out.mkdir(parents=True, exist_ok=True)
    raw: dict[tuple[float, float], dict] = {}
    headers = {"User-Agent": "solarapp-dataset-download/1.0 (one-time regional fetch)"}
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        for tile in nasa.tiles(bbox):
            print(f"NASA: tile {tile}", flush=True)
            for key, rec in (await nasa.fetch_regional(client, tile)).items():
                raw.setdefault(key, {"lat": rec["lat"], "lon": rec["lon"]}).update(rec)
    points = {(p["lat"], p["lon"]): p for p in nasa.merge_points(raw)}
    data = {
        "source": "NASA POWER climatology, community RE (https://power.larc.nasa.gov/)",
        "parameters": nasa.PARAMETERS,
        "bbox": list(bbox),
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "points": list(points.values()),
    }
    (out / "climatology.json").write_text(json.dumps(data))
    print(f"NASA done: {len(points)} points", flush=True)


def write_synthetic(root: Path, bbox, step: float) -> None:
    from ..core.synthetic import synthetic_tmy

    cells_dir = root / "pvgis" / "cells"
    cells_dir.mkdir(parents=True, exist_ok=True)
    centers = grid.land_cells(grid.cell_centers(bbox, step), step)
    cells = []
    for i, c in enumerate(centers):
        cid = cell_id(c.lat, c.lon)
        df = synthetic_tmy(c.lat, c.lon, 10.0)
        write_cell(df, cells_dir / f"{cid}.parquet")
        cells.append({"id": cid, "lat": c.lat, "lon": c.lon, "elevation_m": 10.0, "file": f"cells/{cid}.parquet", "radiation_db": "SYNTHETIC", "time_offset_h": 0.0})
        if (i + 1) % 25 == 0:
            print(f"  synthetic {i+1}/{len(centers)}", flush=True)
    _write_index(root, {
        "source": "SYNTHETIC clear-sky model with seasonal cloud factor. NOT PVGIS. For testing only.",
        "radiation_db": "SYNTHETIC", "synthetic": True, "grid_step_deg": step, "bbox": list(bbox),
        "downloaded_at": datetime.now(timezone.utc).isoformat(), "cells": cells, "skipped": [],
    })
    nasa_dir = root / "nasa"
    nasa_dir.mkdir(parents=True, exist_ok=True)
    pts = []
    for c in centers:
        df = synthetic_tmy(c.lat, c.lon, 10.0)
        monthly = df["ghi"].groupby(df.index.month).sum() / 1000.0
        days = df.index.to_series().groupby(df.index.month).apply(lambda s: s.dt.date.nunique())
        psh = (monthly / days).tolist()
        pts.append({"lat": c.lat, "lon": c.lon, "ghi_kwh_m2_day": psh, "ghi_annual_kwh_m2_day": float(sum(psh) / 12), "t2m_c": df["temp_air"].groupby(df.index.month).mean().tolist(), "clearness_index": None})
    (nasa_dir / "climatology.json").write_text(json.dumps({
        "source": "SYNTHETIC. NOT NASA POWER. For testing only.", "synthetic": True, "bbox": list(bbox),
        "downloaded_at": datetime.now(timezone.utc).isoformat(), "points": pts,
    }))
    print(f"Synthetic dataset written: {len(cells)} cells", flush=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="One-time weather dataset download for the solar simulator.")
    ap.add_argument("--out", default="data", help="data root directory (default: data)")
    ap.add_argument("--bbox", nargs=4, type=float, metavar=("LAT_MIN", "LAT_MAX", "LON_MIN", "LON_MAX"), default=list(grid.PHILIPPINES_BBOX))
    ap.add_argument("--step", type=float, default=grid.DEFAULT_STEP, help="grid step in degrees (PVGIS ERA5 is 0.25)")
    ap.add_argument("--concurrency", type=int, default=3)
    ap.add_argument("--delay", type=float, default=0.3, help="seconds to wait after each request per worker")
    ap.add_argument("--limit", type=int, default=None, help="fetch at most this many cells (for a quick test)")
    ap.add_argument("--skip-nasa", action="store_true")
    ap.add_argument("--only-nasa", action="store_true")
    ap.add_argument("--synthetic", action="store_true", help="write a synthetic test dataset instead of downloading")
    ap.add_argument("--repack", action="store_true", help="rewrite already downloaded cell files in the current storage format")
    args = ap.parse_args(argv)

    root = Path(args.out)
    bbox = tuple(args.bbox)
    if args.repack:
        repack(root)
        return 0
    if args.synthetic:
        write_synthetic(root, bbox, args.step)
        return 0
    if not args.only_nasa:
        asyncio.run(download_pvgis(root, bbox, args.step, args.concurrency, args.delay, args.limit))
    if not args.skip_nasa:
        asyncio.run(download_nasa(root, bbox))
    return 0


if __name__ == "__main__":
    sys.exit(main())
