"""Offline source backed by the fixture snapshots that ship with the repo.

Lets the whole pipeline -- collect, analyse, drift, report -- run and be tested
with no network access, which is what makes the study reproducible by a
reviewer who has only the repository.
"""

from __future__ import annotations

import json
from pathlib import Path

from mcpmap.models import ServerRecord
from mcpmap.sources.base import SourceError

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "snapshots"


class FixtureSource:
    id = "fixtures"

    def __init__(self, path=None):
        self.path = Path(path) if path else None

    def collect(self, limit: int | None = None) -> list[ServerRecord]:
        path = self.path or self._default()
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        records = [ServerRecord.from_dict(item) for item in payload.get("records") or []]
        return records[:limit] if limit else records

    def _default(self) -> Path:
        candidates = sorted(FIXTURE_DIR.glob("*.json"))
        if not candidates:
            raise SourceError(f"no fixture snapshots found in {FIXTURE_DIR}")
        return candidates[-1]
