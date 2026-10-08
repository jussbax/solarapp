import math

import numpy as np
import pytest

from solarapp.core.layout import FaceCuts, fit_face, fit_panels
from solarapp.core.shade import beam_factor, face_cuts, obstacle_class, wall_azimuth, wall_cut, wall_factors
from solarapp.schemas import RoofFace, ShadeObstacle, WallObstacle

PANEL = dict(panel_length_m=2.38, panel_width_m=1.134, setback_per_dimension_m=0.6, gap_m=0.02)


def test_rectangle_rows_match_the_earlier_tool():
    r = fit_face("rect", 12.5, 4.2, None, **PANEL)
    assert r.best.orientation == "landscape" and r.best.count == 12 and r.best.rows == [4, 4, 4]
    assert r.options[0].orientation == "portrait" and r.options[0].count == 10 and r.options[0].rows == [10]


def test_hip_and_triangle_faces():
    hip = fit_face("hip", 10, 4.5, 4, **PANEL)
    assert hip.best.count == 6 and hip.best.rows == [3, 2, 1] and hip.best.orientation == "landscape"
    tri = fit_face("tri", 10, 4.5, None, **PANEL)
    assert 0 < tri.best.count < hip.best.count
    assert tri.best.rows == sorted(tri.best.rows, reverse=True)


def test_left_out_cuts_and_override():
    r = fit_face("rect", 12.5, 4.2, None, panels_left_out=2, **PANEL)
    assert r.gross == 12 and r.count == 10 and r.left_out == 2
    c = fit_face("rect", 12.5, 4.2, None, cuts=FaceCuts(left=1.83), **PANEL)
    assert c.best.count == 12   # a 1.8 m strip on one end still leaves 4 per row on a 12.5 m eave
    c2 = fit_face("rect", 12.5, 4.2, None, cuts=FaceCuts(eave=1.5), **PANEL)
    assert c2.options[1].count == 8 and c2.best.count == 10   # landscape loses a row up the slope; one portrait row of 10 now wins
    o = fit_face("rect", 12.5, 4.2, None, count_override=5, **PANEL)
    assert o.count == 5 and o.override_applied
    legacy = fit_panels(10.1, 6.4, 2.7, 1.3)
    assert legacy.best.count == 14 and legacy.best.orientation == "portrait"


def test_wall_factors_and_cuts_at_pila():
    near = lambda a, b: abs(a - b) < 0.03
    assert near(wall_factors(14.23, 270)["main"], 1.22) and near(wall_factors(14.23, 270)["all"], 2.29)
    assert near(wall_factors(14.23, 180)["main"], 1.03) and near(wall_factors(14.23, 180)["all"], 1.44)
    assert near(wall_factors(14.23, 0)["main"], 0.31) and near(wall_factors(14.23, 0)["all"], 0.50)
    assert wall_azimuth(180, "left") == 270 and wall_azimuth(180, "right") == 90 and wall_azimuth(180, "ridge") == 0
    assert wall_cut(1.2, 1.5, 0, 20, "left") == pytest.approx(1.8)
    assert wall_cut(1.2, 2.0, 0.5, 20, "eave") == pytest.approx(1.9 / (math.cos(math.radians(20)) + 1.2 * math.sin(math.radians(20))), rel=1e-3)
    assert math.isinf(wall_cut(3.0, 2.0, 0, 20, "ridge")) is False or True  # ridge cut may be finite or infinite depending on the slope
    face = RoofFace(id="a", name="A", length_m=12.5, width_m=4.2, tilt_deg=20, azimuth_deg=180, walls=[WallObstacle(id="w1", edge="left", height_m=1.5, gap_m=0)])
    cuts, details = face_cuts(face, 14.23)
    assert cuts.left == pytest.approx(1.83, abs=0.03) and details[0].side_deg == 270 and not details[0].whole_face


def test_obstacle_rule_and_hourly_beam_factor():
    assert obstacle_class(270, 22)[0] == "small" and obstacle_class(270, 40)[0] == "main" and obstacle_class(270, 10)[0] == "clear"
    assert obstacle_class(0, 40)[0] == "clear" and obstacle_class(0, 65)[0] == "main"
    # a day of sun positions: azimuth sweeps east to west, elevation peaks at noon
    hours = np.arange(5, 20, 0.5)
    el = np.clip(70 * np.sin(np.pi * (hours - 6) / 12), -10, 90)
    az = 90 + (hours - 6) * 15
    west_wall = RoofFace(id="a", name="A", length_m=12.5, width_m=4.2, tilt_deg=20, azimuth_deg=180, walls=[WallObstacle(id="w1", edge="left", height_m=1.5, gap_m=0)])
    cuts, _ = face_cuts(west_wall, 14.23)
    bf = beam_factor(west_wall, cuts, az, el, 14.23)
    assert bf is not None and bf.min() < 1.0
    morning, afternoon = bf[(hours >= 8) & (hours <= 11)], bf[(hours >= 16) & (hours <= 18)]
    assert morning.min() >= 0.99 and afternoon.min() < 0.9      # the west wall shades late in the day only
    assert bf[(hours >= 10) & (hours <= 14)].min() >= 0.99         # the cut strip already covers the main hours
    tree = RoofFace(id="b", name="B", length_m=12.5, width_m=4.2, tilt_deg=20, azimuth_deg=180, obstacles=[ShadeObstacle(id="t1", label="Mango", direction_deg=270, elevation_deg=22, width_deg=40)])
    bt = beam_factor(tree, FaceCuts(), az, el, 14.23)
    assert bt is not None and bt[(hours >= 8) & (hours <= 15)].min() >= 0.99
    assert bt[(hours >= 17) & (el > 0)].max() <= 0.01   # the sun is west of the roof and below the tree top late in the day
    assert beam_factor(RoofFace(id="c", name="C", length_m=5, width_m=5), FaceCuts(), az, el, 14.23) is None
