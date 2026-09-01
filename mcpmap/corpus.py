"""Snapshot storage.

Snapshots are immutable JSON documents on disk. They are the study's primary
data: every figure the report prints must be reproducible from a snapshot file
and a taxonomy version, with no network access.
"""

from __future__ import annotations

import json
from pathlib import Path

from mcpmap.models import Snapshot


def save(snapshot: Snapshot, directory) -> Path:
    """Write a snapshot as <directory>/<snapshot_id>.json. Refuses to overwrite."""
    target = Path(directory)
    target.mkdir(parents=True, exist_ok=True)
    path = target / f"{snapshot.snapshot_id}.json"
    if path.exists():
        raise FileExistsError(
            f"{path} already exists; snapshots are immutable, choose another id"
        )
    path.write_text(
        json.dumps(snapshot.to_dict(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def load(path) -> Snapshot:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    snapshot = Snapshot.from_dict(payload)
    recorded = payload.get("digest")
    if recorded and recorded != snapshot.digest:
        raise ValueError(
            f"{path} failed its integrity check: recorded digest {recorded[:12]} "
            f"but content hashes to {snapshot.digest[:12]}"
        )
    return snapshot


def load_all(directory) -> list[Snapshot]:
    """Every snapshot in a directory, oldest capture first."""
    snapshots = [load(path) for path in sorted(Path(directory).glob("*.json"))]
    return sorted(snapshots, key=lambda snap: (snap.captured_at, snap.snapshot_id))
