import pytest

from solarapp.core.synthetic import synthetic_tmy

MANILA = (14.5995, 120.9842, 10.0)


@pytest.fixture(scope="session")
def manila_tmy():
    return synthetic_tmy(*MANILA)
