import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

from mcpmap import corpus

FIXTURES = ROOT / "fixtures" / "snapshots"
NOW = "2026-09-01T00:00:00+00:00"


@pytest.fixture()
def snap_before():
    return corpus.load(FIXTURES / "2026-06-01-synthetic.json")


@pytest.fixture()
def snap_after():
    return corpus.load(FIXTURES / "2026-09-01-synthetic.json")
