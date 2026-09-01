import pytest

from mcpmap.models import ServerRecord, Snapshot, ToolDecl


def test_snapshot_roundtrip_preserves_digest(snap_after):
    restored = Snapshot.from_dict(snap_after.to_dict())
    assert restored.digest == snap_after.digest
    assert len(restored.records) == len(snap_after.records)


def test_snapshot_digest_ignores_record_order():
    tools = [ToolDecl("a", "x")]
    one = ServerRecord(key="k1", tools=tools)
    two = ServerRecord(key="k2", tools=tools)
    forward = Snapshot("s", "2026-01-01T00:00:00+00:00", [one, two])
    reverse = Snapshot("s", "2026-01-01T00:00:00+00:00", [two, one])
    assert forward.digest == reverse.digest


def test_snapshot_digest_changes_when_a_surface_changes():
    before = Snapshot("s", "t", [ServerRecord(key="k", tools=[ToolDecl("a", "old")])])
    after = Snapshot("s", "t", [ServerRecord(key="k", tools=[ToolDecl("a", "new")])])
    assert before.digest != after.digest


def test_unsupported_schema_version_is_rejected():
    payload = Snapshot("s", "t", []).to_dict()
    payload["schema_version"] = 99
    with pytest.raises(ValueError, match="schema version"):
        Snapshot.from_dict(payload)


def test_manifest_absent_is_distinct_from_no_tools():
    absent = ServerRecord(key="k", manifest_found=False)
    unchecked = ServerRecord(key="k", manifest_found=None)
    assert absent.manifest_found is False
    assert unchecked.manifest_found is None
    assert absent.tools == unchecked.tools == []
