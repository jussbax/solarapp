from __future__ import annotations

from fastapi import Request

from ..core.dataset import NasaReference, PvgisDataset


def get_pvgis(request: Request) -> PvgisDataset:
    return request.app.state.pvgis


def get_nasa(request: Request) -> NasaReference:
    return request.app.state.nasa
