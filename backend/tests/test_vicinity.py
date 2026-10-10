"""Round 13, item 4 (docs/audits/round-13/engineer-brief.md 4.1 and 4.3): the vicinity map. The tile maths for the sample
pin; the mosaics composed from the fixture tiles through a fake tile server (the suite never reaches a real one); the
policy as kept (the User-Agent on every request, one request in flight, the 30-day cache, a stop on the first failure);
the failure path (a 429, a timeout, no outside access: no file, the reason on record, the sheet prints the pin, the
address and the reason); the upload (re-encoded without EXIF, capped at 2,400 px, 413 over 8 MB, 422 for a PDF, the
sheet says "uploaded by the office"); the project's folder goes with the record."""
import io
import os
import threading
import time
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from solarapp.config import Settings
from solarapp.data_download.cli import write_synthetic
from solarapp.main import create_app
from solarapp.reports import vicinity as v
from tests.test_drawings import PILA_DOC
from tests.test_plans import _pages, _pdf_text

FIXTURES = Path(__file__).parent / "fixtures" / "tiles"
PIN = (14.2335, 121.3645)
URL = "https://tiles.example/{z}/{x}/{y}.png"
ATTRIBUTION = "Map data © OpenStreetMap contributors, ODbL"
AGENT = "PLDSolarApp/13 (+https://pldevinc.com; office@example.com)"


class FakeTiles:
    """The fake tile server behind an httpx MockTransport: the fixture tiles (a blank tile for any other index), every
    request remembered with its headers, the requests in flight counted, and a failure mode on demand."""

    def __init__(self, mode: str = "ok", delay: float = 0.0):
        self.mode, self.delay = mode, delay
        self.requests: list[httpx.Request] = []
        self.in_flight = self.max_in_flight = 0
        self._lock = threading.Lock()

    def handler(self, req: httpx.Request) -> httpx.Response:
        with self._lock:
            self.requests.append(req)
            self.in_flight += 1
            self.max_in_flight = max(self.max_in_flight, self.in_flight)
        try:
            if self.delay:
                time.sleep(self.delay)
            if self.mode == "429":
                return httpx.Response(429)
            if self.mode == "timeout":
                raise httpx.ReadTimeout("slow", request=req)
            if self.mode == "down":
                raise httpx.ConnectError("refused", request=req)
            z, x, y = req.url.path.strip("/").removesuffix(".png").split("/")
            p = FIXTURES / f"{z}_{x}_{y}.png"
            if p.is_file():
                return httpx.Response(200, content=p.read_bytes(), headers={"content-type": "image/png"})
            buf = io.BytesIO()
            Image.new("RGB", (256, 256), (230, 230, 225)).save(buf, "PNG")
            return httpx.Response(200, content=buf.getvalue(), headers={"content-type": "image/png"})
        finally:
            with self._lock:
                self.in_flight -= 1

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self.handler))


def _prepare(data_dir: Path, server: FakeTiles, state=None, pin=PIN, aid: int = 1, agent: str = AGENT, **kw) -> dict:
    with server.client() as client:
        return v.prepare(pin[0], pin[1], data_dir=data_dir, assessment_id=aid, url_template=URL, attribution=ATTRIBUTION, agent=agent, state=state, client=client, **kw)


# ---- the tile maths (4.3), hand-worked for the Pila sample pin

def test_tile_indices_and_the_pin_pixel_for_the_sample_pin():
    x, y, fx, fy = v.tile_xy(*PIN, 16)
    assert (x, y) == (54861, 30149)
    # the fractional parts place the pin inside its tile; the brief's "0.6" is the round figure, the formula gives these
    assert abs(fx - 0.7332) < 0.001 and abs(fy - 0.8012) < 0.001
    px, py = v.pin_pixel(*PIN, 16)
    assert abs(px - (256 + fx * 256)) < 1e-9 and abs(py - (256 + fy * 256)) < 1e-9 and 256 < px < 512 and 256 < py < 512
    mpp = v.metres_per_pixel(PIN[0], 16)
    assert abs(mpp - 2.315) < 0.001
    assert round(200 / mpp) == 86          # the 200 m scale bar at zoom 16
    assert v.tile_xy(*PIN, 12)[:2] == (3428, 1884)
    assert v.tile_url(URL, 16, 54861, 30149) == "https://tiles.example/16/54861/30149.png" and v.tile_host(URL) == "tiles.example"


def test_the_user_agent_names_the_app_and_a_contact_or_is_blank():
    assert v.user_agent({"email": "office@example.com"}, "https://pldevinc.com") == "PLDSolarApp/13 (+https://pldevinc.com; office@example.com)"
    assert v.user_agent({"email": ""}, "https://pldevinc.com/") == "PLDSolarApp/13 (+https://pldevinc.com)"
    assert v.user_agent({"email": "office@example.com"}, "") == "PLDSolarApp/13 (office@example.com)"
    assert v.user_agent({}, "") == ""


# ---- the composition on the fixture tiles, the cache, the policy

def test_the_mosaics_compose_from_the_fixture_tiles_with_no_network(tmp_path):
    server = FakeTiles()
    state = _prepare(tmp_path, server)
    assert state["source"] == "osm" and state["error"] is None
    osm = state["osm"]
    assert osm["pin"] == [14.2335, 121.3645] and osm["host"] == "tiles.example" and osm["tiles_fetched"] == 18 and osm["tiles_cached"] == 0
    assert len(server.requests) == 18 and all(r.headers["user-agent"] == AGENT for r in server.requests)
    paths = {r.url.path for r in server.requests}
    assert "/16/54861/30149.png" in paths and "/12/3428/1884.png" in paths and len(paths) == 18
    folder = v.project_dir(tmp_path, 1)
    for zoom in ("16", "12"):
        with Image.open(folder / osm["files"][zoom]) as im:
            assert im.size == (768, 768)
            if zoom == "16":
                px, py = v.pin_pixel(*PIN, 16)
                assert im.getpixel((round(px), round(py))) == (17, 17, 17)          # the marker's dot at the pin's pixel
                assert all(c >= 235 for c in im.getpixel((3, 766)))                  # the attribution strip along the bottom
                assert all(c >= 235 for c in im.getpixel((724, 40)))                 # the north arrow's white box, top right (beside the arrow)
                assert im.getpixel((738, 30)) == (17, 17, 17)                        # the arrow itself
    # the tiles are cached by z/x/y with the fetch date as the file's time
    assert (v.tiles_dir(tmp_path) / "16" / "54861" / "30149.png").is_file()
    assert (folder / "vicinity.json").is_file()


def test_a_second_build_fetches_nothing_and_a_moved_pin_refetches(tmp_path):
    server = FakeTiles()
    state = _prepare(tmp_path, server)
    assert len(server.requests) == 18
    # the same pin: the mosaics on record are reused, nothing is fetched
    again = _prepare(tmp_path, server, state=state)
    assert len(server.requests) == 18 and again["osm"]["fetched_at"] == state["osm"]["fetched_at"]
    # "Refresh map": remade from the cache, no request
    forced = _prepare(tmp_path, server, state=state, force=True)
    assert len(server.requests) == 18 and forced["osm"]["tiles_cached"] == 18 and forced["osm"]["tiles_fetched"] == 0
    # the pin moved inside its tile: remade (the pin's pixel moves) from the cache
    assert not v.is_current(state, PIN[0] + 0.00002, PIN[1])
    nearby = _prepare(tmp_path, server, state=state, pin=(PIN[0] + 0.00002, PIN[1]))
    assert len(server.requests) == 18 and nearby["osm"]["pin"] == [round(PIN[0] + 0.00002, 5), PIN[1]]
    # the pin moved by more than a tile: new tiles are fetched (the ones already cached are not)
    moved = _prepare(tmp_path, server, state=state, pin=(PIN[0] + 0.01, PIN[1]))
    assert moved["osm"] and len(server.requests) > 18 and moved["osm"]["tiles_fetched"] > 0
    # a tile older than 30 days is fetched again
    old = v.tiles_dir(tmp_path) / "16" / "54861" / "30149.png"
    stale = (datetime.now(timezone.utc) - timedelta(days=31)).timestamp()
    os.utime(old, (stale, stale))
    n = len(server.requests)
    refreshed = _prepare(tmp_path, server, state=state, force=True)
    assert len(server.requests) == n + 1 and refreshed["osm"]["tiles_fetched"] == 1 and refreshed["osm"]["tiles_cached"] == 17


@pytest.mark.parametrize("mode, requests, reason", [("429", 1, "HTTP 429"), ("timeout", 2, "timeout after 8 s"), ("down", 2, "no outside access")])
def test_a_failure_leaves_no_file_and_records_the_reason(tmp_path, mode, requests, reason):
    """A 429 stops the run at once; a timeout or a dead host is tried once more, then the run stops: no partial map."""
    server = FakeTiles(mode)
    state = _prepare(tmp_path, server)
    assert state["source"] is None and state["osm"] is None and reason in state["error"]["reason"]
    assert len(server.requests) == requests
    assert not v.project_dir(tmp_path, 1).exists() and v.current_file(state, v.project_dir(tmp_path, 1)) is None


def test_without_a_contact_the_fetch_is_refused_rather_than_sent_anonymously(tmp_path):
    server = FakeTiles()
    state = _prepare(tmp_path, server, agent="")
    assert state["osm"] is None and "User-Agent" in state["error"]["reason"] and server.requests == []
    with server.client() as client:
        off = v.prepare(*PIN, data_dir=tmp_path, assessment_id=1, url_template="", attribution="", agent=AGENT, client=client)
    assert "switched off" in off["error"]["reason"] and server.requests == []


def test_at_most_one_request_is_in_flight(tmp_path):
    server = FakeTiles(delay=0.005)
    results: list[dict] = []
    threads = [threading.Thread(target=lambda k: results.append(_prepare(tmp_path, server, aid=k, pin=(PIN[0] + 0.01 * k, PIN[1]))), args=(k,)) for k in (1, 2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(results) == 2 and all(r["osm"] for r in results)
    assert server.max_in_flight == 1 and len(server.requests) >= 18


# ---- through the API: "Prepare the map", the preview, the sheet, the upload, the delete

@pytest.fixture(scope="module")
def client(tmp_path_factory):
    root = tmp_path_factory.mktemp("data")
    write_synthetic(root, (14.0, 14.5, 121.0, 121.5), 0.25)
    settings = Settings(data_dir=root, app_username="u", app_password="p", secret_key="s" * 32, cookie_secure=False, static_dir=root / "nostatic",
                        website_url="https://pldevinc.com", map_tiles_url=URL)
    app = create_app(settings)
    with TestClient(app) as c:
        c.post("/api/auth/login", json={"username": "u", "password": "p"})
        c.put("/api/settings", json={"company_name": "Test Solar", "email": "office@example.com"})
        c.data_dir = root
        yield c


def _computed(client: TestClient, pin: tuple[float, float] = PIN) -> int:
    doc = deepcopy(PILA_DOC)
    doc["lat"], doc["lon"] = pin
    aid = client.post("/api/assessments", json=doc).json()["id"]
    assert client.post(f"/api/assessments/{aid}/compute").status_code == 200
    return aid


def _sheet(client: TestClient, aid: int) -> str:
    r = client.get(f"/api/assessments/{aid}/plans.pdf")
    assert r.status_code == 200, r.text
    pages = _pages(_pdf_text(r.content))
    return " ".join(pages[1].split())


def test_prepare_the_map_through_the_api_and_the_sheet_prints_it(client, monkeypatch):
    server = FakeTiles()
    monkeypatch.setattr(v, "make_client", server.client)
    aid = _computed(client)
    assert client.get(f"/api/assessments/{aid}").json()["vicinity_map"] is None
    assert client.get(f"/api/assessments/{aid}/vicinity-map.png").status_code == 404
    r = client.post(f"/api/assessments/{aid}/vicinity-map/fetch")
    assert r.status_code == 200, r.text
    vm = r.json()["vicinity_map"]
    assert vm["source"] == "osm" and vm["osm"]["tiles_fetched"] == 18 and vm["osm"]["host"] == "tiles.example" and vm["error"] is None
    assert all(r.headers["user-agent"] == "PLDSolarApp/13 (+https://pldevinc.com; office@example.com)" for r in server.requests)
    # the preview serves the main mosaic
    png = client.get(f"/api/assessments/{aid}/vicinity-map.png")
    assert png.status_code == 200 and png.headers["content-type"] == "image/png"
    with Image.open(io.BytesIO(png.content)) as im:
        assert im.size == (768, 768)
    assert client.get(f"/api/assessments/{aid}/vicinity-map.png?which=z12").status_code == 200
    # pressing again fetches nothing (the record is current); "Refresh map" remakes it from the cache
    n = len(server.requests)
    assert client.post(f"/api/assessments/{aid}/vicinity-map/fetch").json()["vicinity_map"]["osm"]["fetched_at"] == vm["osm"]["fetched_at"]
    forced = client.post(f"/api/assessments/{aid}/vicinity-map/fetch?force=true").json()["vicinity_map"]
    assert len(server.requests) == n and forced["osm"]["tiles_cached"] == 18
    # the sheet: the attribution and the source, the pin, the address; a second build fetches nothing
    sheet = _sheet(client, aid)
    assert "Map data © OpenStreetMap contributors, ODbL — tiles.example, fetched" in sheet and "main map zoom 16" in sheet
    assert "pin 14.23350, 121.36450" in sheet and "Brgy. Labuin, Pila, Laguna" in sheet and "Pila, Laguna" in sheet
    assert "not fetched" not in sheet and len(server.requests) == n
    # the folder goes with the record
    folder = v.project_dir(client.data_dir, aid)
    assert folder.is_dir() and (folder / "vicinity-z16.png").is_file()
    assert client.delete(f"/api/assessments/{aid}").status_code == 204
    assert not folder.exists()


def test_the_failure_path_prints_the_pin_the_address_and_the_reason(client, monkeypatch):
    server = FakeTiles("429")
    monkeypatch.setattr(v, "make_client", server.client)
    aid = _computed(client, pin=(14.2635, 121.3945))     # a pin whose tiles the earlier tests did not cache
    vm = client.post(f"/api/assessments/{aid}/vicinity-map/fetch").json()["vicinity_map"]
    assert vm["source"] is None and vm["osm"] is None and "HTTP 429" in vm["error"]["reason"] and len(server.requests) == 1
    assert client.get(f"/api/assessments/{aid}/vicinity-map.png").status_code == 404
    sheet = _sheet(client, aid)
    assert "vicinity map: not fetched (HTTP 429: the tile server asks for fewer requests; try again later)" in sheet
    assert "the office may upload a screen grab (Site plan card › Vicinity map)" in sheet
    assert "The pin 14.26350, 121.39450, Brgy. Labuin, Pila, Laguna; nearest town centre" in sheet
    # never fetched during the build: the request count stands
    assert len(server.requests) == 1
    # before any attempt the sheet says so too
    fresh = _computed(client)
    assert "vicinity map: not fetched (not prepared yet: press Prepare the map on the Site plan card)" in _sheet(client, fresh)
    # no pin, no map
    doc = client.get(f"/api/assessments/{fresh}").json()["doc"]
    doc["lat"] = doc["lon"] = None
    client.put(f"/api/assessments/{fresh}", json=doc)
    assert client.post(f"/api/assessments/{fresh}/vicinity-map/fetch").status_code == 409


def _jpeg_with_exif(w: int, h: int) -> bytes:
    im = Image.new("RGB", (w, h), (200, 190, 160))
    exif = Image.Exif()
    exif[0x0110] = "a phone"            # the model tag
    exif[0x0132] = "2026:10:10 09:00:00"
    buf = io.BytesIO()
    im.save(buf, "JPEG", exif=exif.tobytes())
    data = buf.getvalue()
    assert Image.open(io.BytesIO(data)).getexif().get(0x0110) == "a phone"
    return data


def test_the_upload_is_re_encoded_capped_and_printed_in_place_of_the_fetched_map(client, monkeypatch):
    server = FakeTiles()
    monkeypatch.setattr(v, "make_client", server.client)
    aid = _computed(client)
    assert client.post(f"/api/assessments/{aid}/vicinity-map/fetch").json()["vicinity_map"]["source"] == "osm"
    r = client.post(f"/api/assessments/{aid}/vicinity-map", files={"file": ("grab.jpg", _jpeg_with_exif(3000, 2000), "image/jpeg")},
                    data={"note": "screen grab of the office map, © OpenStreetMap contributors"})
    assert r.status_code == 200, r.text
    vm = r.json()["vicinity_map"]
    assert vm["source"] == "upload" and vm["upload"]["width"] == 2400 and vm["upload"]["height"] == 1600 and vm["osm"] is not None
    stored = v.project_dir(client.data_dir, aid) / "vicinity-upload.png"
    with Image.open(stored) as im:
        assert im.format == "PNG" and im.size == (2400, 1600) and dict(im.getexif()) == {} and "exif" not in im.info
    # the preview serves the upload now; the fetched map is still there on request
    with Image.open(io.BytesIO(client.get(f"/api/assessments/{aid}/vicinity-map.png").content)) as im:
        assert im.size == (2400, 1600)
    with Image.open(io.BytesIO(client.get(f"/api/assessments/{aid}/vicinity-map.png?which=z16").content)) as im:
        assert im.size == (768, 768)
    sheet = _sheet(client, aid)
    assert "vicinity map: uploaded by the office on" in sheet and "screen grab of the office map, © OpenStreetMap contributors" in sheet
    assert "the upload is printed because it is present" in sheet
    # removing the upload brings the fetched map back
    vm = client.delete(f"/api/assessments/{aid}/vicinity-map").json()["vicinity_map"]
    assert vm["source"] == "osm" and vm["upload"] is None and not stored.exists()
    assert "uploaded by the office" not in _sheet(client, aid)
    # a small PNG is kept at its size, over white where it was transparent
    buf = io.BytesIO()
    Image.new("RGBA", (300, 200), (0, 0, 0, 0)).save(buf, "PNG")
    vm = client.post(f"/api/assessments/{aid}/vicinity-map", files={"file": ("grab.png", buf.getvalue(), "image/png")}).json()["vicinity_map"]
    assert vm["upload"]["width"] == 300 and vm["upload"]["note"] == ""
    with Image.open(stored) as im:
        assert im.getpixel((10, 10)) == (255, 255, 255)


def test_an_oversized_or_wrong_upload_is_refused(client):
    aid = _computed(client)
    big = b"\x89PNG\r\n\x1a\n" + b"\0" * (9 * 1024 * 1024)
    assert client.post(f"/api/assessments/{aid}/vicinity-map", files={"file": ("big.png", big, "image/png")}).status_code == 413
    r = client.post(f"/api/assessments/{aid}/vicinity-map", files={"file": ("map.pdf", b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n", "application/pdf")})
    assert r.status_code == 422 and "PNG or JPEG" in r.json()["detail"]
    buf = io.BytesIO()
    Image.new("RGB", (10, 10)).save(buf, "GIF")
    r = client.post(f"/api/assessments/{aid}/vicinity-map", files={"file": ("map.gif", buf.getvalue(), "image/gif")})
    assert r.status_code == 422 and "GIF" in r.json()["detail"]
    assert client.get(f"/api/assessments/{aid}").json()["vicinity_map"] is None
