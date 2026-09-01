import json

import pytest

from mcpmap import corpus
from mcpmap.models import ServerRecord, Snapshot, ToolDecl


def make(snapshot_id="s1", captured_at="2026-01-01T00:00:00+00:00"):
    return Snapshot(snapshot_id, captured_at,
                    [ServerRecord(key="github:example/x", tools=[ToolDecl("a", "d")])])


def test_save_then_load_roundtrip(tmp_path):
    path = corpus.save(make(), tmp_path)
    loaded = corpus.load(path)
    assert loaded.digest == make().digest


def test_snapshots_are_immutable_on_disk(tmp_path):
    corpus.save(make(), tmp_path)
    with pytest.raises(FileExistsError, match="immutable"):
        corpus.save(make(), tmp_path)


def test_tampered_snapshot_fails_its_integrity_check(tmp_path):
    path = corpus.save(make(), tmp_path)
    payload = json.loads(path.read_text())
    payload["records"][0]["tools"][0]["description"] = "quietly changed"
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="integrity"):
        corpus.load(path)


def test_load_all_orders_by_capture_time(tmp_path):
    corpus.save(make("later", "2026-06-01T00:00:00+00:00"), tmp_path)
    corpus.save(make("earlier", "2026-01-01T00:00:00+00:00"), tmp_path)
    assert [snap.snapshot_id for snap in corpus.load_all(tmp_path)] == ["earlier", "later"]
