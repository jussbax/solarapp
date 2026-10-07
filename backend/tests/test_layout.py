from solarapp.core.layout import fit_panels


def test_owner_example():
    # 10.1 x 6.4 roof, subtract 0.6 each -> 9.5 x 5.8; panel 2.7 x 1.3 -> 7 x 2
    r = fit_panels(10.1, 6.4, 2.7, 1.3)
    assert abs(r.usable_length_m - 9.5) < 1e-9 and abs(r.usable_width_m - 5.8) < 1e-9
    assert r.best.count == 14 and r.best.orientation == "landscape"
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
