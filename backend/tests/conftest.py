import pytest

from solarapp.core.synthetic import synthetic_tmy

MANILA = (14.5995, 120.9842, 10.0)


@pytest.fixture(scope="session")
def manila_tmy():
    return synthetic_tmy(*MANILA)


def real_weather(aid: int) -> None:
    """Customer PDFs are refused on the synthetic test weather; mark a computed record's results as real to reach the builders."""
    from sqlmodel import Session

    from solarapp.db import get_engine
    from solarapp.models import Assessment

    with Session(get_engine()) as s:
        a = s.get(Assessment, aid)
        a.results = {**a.results, "dataset": {**(a.results.get("dataset") or {}), "synthetic": False}}
        s.add(a)
        s.commit()
