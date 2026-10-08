from solarapp.core.layout import FaceCuts, face_geometry, fit_face, fit_panels, mark_used, shade_marker, string_rule

PANEL = dict(panel_length_m=2.278, panel_width_m=1.134, setback_per_dimension_m=0.6, gap_m=0.02)


def test_owner_example():
    # 10.1 x 6.4 roof, subtract 0.6 each -> 9.5 x 5.8; panel 2.7 x 1.3 -> 7 x 2
    r = fit_panels(10.1, 6.4, 2.7, 1.3)
    assert abs(r.usable_length_m - 9.5) < 1e-9 and abs(r.usable_width_m - 5.8) < 1e-9
    assert r.best.count == 14 and r.best.orientation == "portrait"  # long side up the slope
    assert (r.best.along_length, r.best.along_width) == (7, 2)
    assert r.count == 14
    assert {o.count for o in r.options} == {14, 12}


def test_gap_reduces_count():
    no_gap = fit_panels(10.1, 6.4, 2.278, 1.134, gap_m=0.0)
    gap = fit_panels(10.1, 6.4, 2.278, 1.134, gap_m=0.1)
    assert gap.count <= no_gap.count


def test_override():
    r = fit_panels(10.1, 6.4, 2.7, 1.3, count_override=10)
    assert r.count == 10 and r.override_applied and r.best.count == 14


def test_too_small_roof():
    r = fit_panels(1.0, 1.0, 2.0, 1.0)
    assert r.count == 0


# ---- the plan geometry (contract C3): the fitted rows placed in the fitter's own bands

def _geometry(shape, eave, slope, ridge=None, cuts=None, panels_left_out=0, **extra):
    r = fit_face(shape, eave, slope, ridge, cuts=cuts, panels_left_out=panels_left_out, **PANEL)
    g = face_geometry(face_id="f", name="F", shape=shape, eave_m=eave, slope_m=slope, ridge_m=ridge, azimuth_deg=180, tilt_deg=18,
                      cuts=cuts or FaceCuts(), orientation=r.best.orientation, rows=r.best.rows, count=r.count, gross=r.gross,
                      left_out=r.left_out, **PANEL, **extra)
    return r, g


def _overlap(a, b):
    return a["x"] < b["x"] + b["w"] - 1e-6 and b["x"] < a["x"] + a["w"] - 1e-6 and a["y"] < b["y"] + b["h"] - 1e-6 and b["y"] < a["y"] + a["h"] - 1e-6


def _inside(px, py, poly, tol=1e-6):
    """Point in a convex polygon given counter-clockwise: on the left of (or on) every edge."""
    n = len(poly)
    for i in range(n):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
        if (x2 - x1) * (py - y1) - (y2 - y1) * (px - x1) < -tol:
            return False
    return True


def _assert_sound(r, g):
    panels = g["panels"]
    assert len(panels) == r.count == g["count"]
    assert [p["n"] for p in panels] == list(range(1, len(panels) + 1))
    for i in range(len(panels)):
        for j in range(i + 1, len(panels)):
            assert not _overlap(panels[i], panels[j]), (panels[i], panels[j])
    strips = [o for o in g["obstacles"] if o["kind"] == "wall"]
    for p in panels:
        corners = [(p["x"], p["y"]), (p["x"] + p["w"], p["y"]), (p["x"] + p["w"], p["y"] + p["h"]), (p["x"], p["y"] + p["h"])]
        for cx, cy in corners:
            assert _inside(cx, cy, g["outline"], 1e-3), (p, g["outline"])
            assert _inside(cx, cy, g["usable"], 1e-3), (p, g["usable"])
        for s in strips:
            assert not _overlap(p, s), (p, s)
    # rows from the eave up, as the fitter counted them
    by_row = {}
    for p in panels:
        by_row[p["row"]] = by_row.get(p["row"], 0) + 1
    fitted = [n for n in r.best.rows if n > 0][:len(by_row)] if r.count == r.gross else None
    if fitted is not None:
        assert [by_row[k] for k in sorted(by_row)] == fitted


def test_geometry_rectangle_two_rows():
    r, g = _geometry("rect", 9.0, 5.2)
    assert r.best.orientation == "portrait" and r.best.rows == [7, 7]
    _assert_sound(r, g)
    rows = sorted({p["y"] for p in g["panels"]})
    assert rows == [0.3, 2.598]                                  # the setback inset, then the panel plus the gap
    first = g["panels"][0]
    assert (first["w"], first["h"], first["row"]) == (1.134, 2.278, 1)
    assert abs(first["x"] - (0.3 + (8.4 - (7 * 1.134 + 6 * 0.02)) / 2)) < 1e-3   # centred in the fitter's band
    assert g["outline"] == [[0, 0], [9, 0], [9, 5.2], [0, 5.2]] and g["usable"] == [[0.3, 0.3], [8.7, 0.3], [8.7, 4.9], [0.3, 4.9]]
    assert g["used"] is None and all("used" not in p for p in g["panels"])


def test_geometry_left_wall_strip_keeps_panels_off_the_strip():
    cuts = FaceCuts(left=1.83)
    r, g = _geometry("rect", 12.5, 4.2, cuts=cuts, walls=[{"edge": "left", "height_m": 1.5, "strip_m": 1.83}])
    assert r.best.rows == [4, 4, 4]
    _assert_sound(r, g)
    assert all(p["x"] >= 1.83 - 1e-9 for p in g["panels"])
    strip = next(o for o in g["obstacles"] if o["kind"] == "wall")
    assert (strip["edge"], strip["x"], strip["y"], strip["w"], strip["h"]) == ("left", 0.0, 0.0, 1.83, 4.2)
    assert strip["label"] == "Wall on the left side, 1.5 m above the roof: no panels within 1.8 m of it"
    assert g["cuts"] == {"eave": 0.0, "ridge": 0.0, "left": 1.83, "right": 0.0}
    # a wall that shades the whole face (strip None) covers the face
    _, g2 = _geometry("rect", 12.5, 4.2, cuts=FaceCuts(eave=4.2), walls=[{"edge": "eave", "height_m": 3, "strip_m": None}])
    assert g2["panels"] == [] and next(o for o in g2["obstacles"])["h"] == 4.2


def test_geometry_hip_and_triangle_faces():
    r, g = _geometry("hip", 10, 4.5, 4)
    assert r.best.rows == [3, 2, 1]
    _assert_sound(r, g)
    assert g["outline"] == [[0, 0], [10, 0], [7, 4.5], [3, 4.5]] and len(g["usable"]) == 4
    top = [p for p in g["panels"] if p["row"] == 3]
    assert len(top) == 1 and abs(top[0]["x"] + top[0]["w"] / 2 - 5.0) < 1e-3   # the lone top panel sits on the centre line
    r, g = _geometry("tri", 10, 4.5)
    _assert_sound(r, g)
    assert len(g["outline"]) == 3 and len(g["usable"]) == 3 and g["usable"][2][0] == 5.0


def test_geometry_drops_the_panels_left_out_from_the_top():
    r, g = _geometry("rect", 12.5, 4.2, panels_left_out=2)
    assert r.best.rows == [5, 5, 5] and r.gross == 15 and r.count == 13
    assert len(g["panels"]) == 13 and g["left_out"] == 2 and g["gross"] == 15
    assert g["panels"][-1]["row"] == 3 and sum(1 for p in g["panels"] if p["row"] == 3) == 3   # the two dropped from the top row
    assert [p["n"] for p in g["panels"]] == list(range(1, 14))


def test_shade_markers_sit_on_the_edge_they_shade_from():
    assert shade_marker(180, 180, 9, 5) == ("eave", 4.5, 0.0)
    assert shade_marker(180, 270, 9, 5) == ("left", 0.0, 2.5)
    assert shade_marker(180, 0, 9, 5) == ("ridge", 4.5, 5.0)
    assert shade_marker(180, 90, 9, 5) == ("right", 9.0, 2.5)
    edge, x, y = shade_marker(180, 250, 9, 5)     # west-southwest of a south-facing roof: the left edge, toward the eave
    assert edge == "left" and x == 0.0 and 0 < y < 2.5
    _, g = _geometry("rect", 9.0, 5.0, obstacles=[{"label": "Mango tree", "direction_deg": 250, "elevation_deg": 24, "cls": "small"},
                                                  {"label": "", "direction_deg": 10, "elevation_deg": 0, "cls": "clear"}])
    marks = [o for o in g["obstacles"] if o["kind"] == "shade"]
    assert len(marks) == 1 and marks[0]["edge"] == "left" and marks[0]["label"].startswith("Mango tree, west-southwest, 24° up: small loss")


def test_mark_used_follows_faces_in_order_and_numbers_strings():
    assert string_rule(4, 10) == (1, 4) and string_rule(12, 10) == (2, 6) and string_rule(12, 10, 3) == (3, 4) and string_rule(0, 10) == (1, 0)
    faces = [_geometry("rect", 9.0, 5.0)[1], _geometry("hip", 7, 4, 3)[1]]
    mark_used(faces, 11, 6)
    assert [f["used"] for f in faces] == [9, 2]
    assert [p["string"] for p in faces[0]["panels"]] == [1] * 6 + [2] * 3 and [p.get("string") for p in faces[1]["panels"]] == [2, 2, None]
    assert faces[1]["panels"][2]["used"] is False
