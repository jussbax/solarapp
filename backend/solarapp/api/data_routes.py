from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_user
from ..core.dataset import NasaReference, PvgisDataset
from .deps import get_nasa, get_pvgis

router = APIRouter(prefix="/api/data", tags=["data"], dependencies=[Depends(require_user)])


@router.get("/status")
def status(pvgis: PvgisDataset = Depends(get_pvgis), nasa: NasaReference = Depends(get_nasa)) -> dict:
    return {"pvgis": pvgis.info(), "nasa": nasa.info()}


@router.get("/cell")
def cell(lat: float, lon: float, pvgis: PvgisDataset = Depends(get_pvgis)) -> dict:
    c = pvgis.nearest_cell(lat, lon)
    if c is None:
        raise HTTPException(status_code=404, detail="Weather dataset not downloaded yet.")
    return {**c.to_dict(), "synthetic": pvgis.synthetic}
