"""Shared fixtures. pythonpath=src is set in pyproject, so `import vireo` works."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from vireo import clean, load  # noqa: E402

DATA = ROOT / "data" / "raw"


@pytest.fixture(scope="session")
def raw():
    return load.load_raw(DATA)


@pytest.fixture(scope="session")
def cleaned(raw):
    return clean.clean_tickets(raw.tickets, raw.agents)
