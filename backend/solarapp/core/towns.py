"""Towns the public estimate can pick from, with approximate centroids.

The quick estimate only needs the PVGIS cell (about 27 km across) and the trip
distance from the office, so a town centre is precise enough; the roof visit
settles the exact location. Coordinates are approximate town-centre values.
"""
from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

Town = tuple[str, str, float, float]  # name, province, lat, lon

TOWNS: list[Town] = [
    # Laguna
    ("Alaminos", "Laguna", 14.063, 121.246), ("Bay", "Laguna", 14.183, 121.286), ("Biñan", "Laguna", 14.333, 121.083),
    ("Cabuyao", "Laguna", 14.278, 121.125), ("Calamba", "Laguna", 14.211, 121.165), ("Calauan", "Laguna", 14.150, 121.316),
    ("Cavinti", "Laguna", 14.245, 121.506), ("Famy", "Laguna", 14.437, 121.448), ("Kalayaan", "Laguna", 14.329, 121.481),
    ("Liliw", "Laguna", 14.131, 121.436), ("Los Baños", "Laguna", 14.170, 121.241), ("Luisiana", "Laguna", 14.185, 121.511),
    ("Lumban", "Laguna", 14.297, 121.459), ("Mabitac", "Laguna", 14.426, 121.429), ("Magdalena", "Laguna", 14.199, 121.429),
    ("Majayjay", "Laguna", 14.146, 121.473), ("Nagcarlan", "Laguna", 14.136, 121.416), ("Paete", "Laguna", 14.365, 121.483),
    ("Pagsanjan", "Laguna", 14.273, 121.455), ("Pakil", "Laguna", 14.381, 121.478), ("Pangil", "Laguna", 14.403, 121.467),
    ("Pila", "Laguna", 14.233, 121.365), ("Rizal", "Laguna", 14.108, 121.395), ("San Pablo", "Laguna", 14.070, 121.325),
    ("San Pedro", "Laguna", 14.358, 121.047), ("Santa Cruz", "Laguna", 14.278, 121.416), ("Santa Maria", "Laguna", 14.471, 121.426),
    ("Santa Rosa", "Laguna", 14.312, 121.112), ("Siniloan", "Laguna", 14.422, 121.446), ("Victoria", "Laguna", 14.228, 121.329),
    # Batangas
    ("Agoncillo", "Batangas", 13.934, 120.928), ("Alitagtag", "Batangas", 13.865, 121.004), ("Balayan", "Batangas", 13.937, 120.732),
    ("Balete", "Batangas", 13.973, 121.095), ("Batangas City", "Batangas", 13.757, 121.058), ("Bauan", "Batangas", 13.792, 121.009),
    ("Calaca", "Batangas", 13.930, 120.813), ("Calatagan", "Batangas", 13.832, 120.632), ("Cuenca", "Batangas", 13.907, 121.051),
    ("Ibaan", "Batangas", 13.819, 121.133), ("Laurel", "Batangas", 14.049, 120.906), ("Lemery", "Batangas", 13.890, 120.912),
    ("Lian", "Batangas", 14.037, 120.650), ("Lipa", "Batangas", 13.941, 121.164), ("Lobo", "Batangas", 13.654, 121.212),
    ("Mabini", "Batangas", 13.757, 120.939), ("Malvar", "Batangas", 14.043, 121.159), ("Mataasnakahoy", "Batangas", 13.966, 121.097),
    ("Nasugbu", "Batangas", 14.072, 120.632), ("Padre Garcia", "Batangas", 13.878, 121.215), ("Rosario", "Batangas", 13.846, 121.206),
    ("San Jose", "Batangas", 13.879, 121.105), ("San Juan", "Batangas", 13.826, 121.396), ("San Luis", "Batangas", 13.854, 120.934),
    ("San Nicolas", "Batangas", 13.925, 120.952), ("San Pascual", "Batangas", 13.808, 121.033), ("Santa Teresita", "Batangas", 13.869, 120.981),
    ("Santo Tomas", "Batangas", 14.108, 121.141), ("Taal", "Batangas", 13.879, 120.923), ("Talisay", "Batangas", 14.095, 121.020),
    ("Tanauan", "Batangas", 14.086, 121.150), ("Taysan", "Batangas", 13.769, 121.197), ("Tingloy", "Batangas", 13.660, 120.870),
    ("Tuy", "Batangas", 14.018, 120.729),
]


def towns_payload() -> list[dict]:
    return [{"name": n, "province": p, "lat": la, "lon": lo} for n, p, la, lo in TOWNS]


def _km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    a = sin(radians(lat2 - lat1) / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * asin(sqrt(a))


def nearest_town(lat: float, lon: float) -> tuple[Town, float]:
    """The listed town closest to a point and its distance in km."""
    best = min(TOWNS, key=lambda t: _km(lat, lon, t[2], t[3]))
    return best, _km(lat, lon, best[2], best[3])


def find_town(name: str, province: str = "") -> Town | None:
    key = (name or "").strip().lower()
    for t in TOWNS:
        if t[0].lower() == key and (not province or t[1].lower() == province.strip().lower()):
            return t
    return None
