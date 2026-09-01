from mcpmap.report import analyse, to_markdown
from mcpmap.models import ServerRecord, Snapshot, ToolDecl

NOW = "2026-09-01T00:00:00+00:00"


def test_denominators_separate_population_from_analysable():
    snapshot = Snapshot("s", NOW, [
        ServerRecord(key="a", manifest_found=True, tools=[ToolDecl("read_file", "Read a file from disk", ["path"])]),
        ServerRecord(key="b", manifest_found=False, tools=[]),
        ServerRecord(key="c", manifest_found=None, tools=[]),
    ])
    result = analyse(snapshot, NOW)
    assert result["denominators"]["population"] == 3
    assert result["denominators"]["analysable"] == 1
    assert result["denominators"]["manifest_absent"] == 1
    assert result["denominators"]["manifest_unknown"] == 1


def test_capability_shares_use_the_analysable_denominator():
    snapshot = Snapshot("s", NOW, [
        ServerRecord(key="a", tools=[ToolDecl("read_file", "Read a file from disk", ["path"])]),
        ServerRecord(key="b", manifest_found=False, tools=[]),
    ])
    result = analyse(snapshot, NOW)
    # one of one analysable server, not one of two observed
    assert result["capabilities"]["filesystem_read"] == {"n": 1, "share": 1.0}


def test_analysis_of_the_fixture_snapshot(snap_after):
    result = analyse(snap_after, NOW)
    assert result["denominators"]["population"] == len(snap_after.records)
    assert result["flags"]["BRIDGE_FS_NET"]["n"] >= 1
    assert result["taxonomy_version"]


def test_markdown_states_the_denominator_caveat(snap_after):
    text = to_markdown(analyse(snap_after, NOW))
    assert "# The map" in text
    assert "analysable" in text
    assert "is not evidence of a server with no" in text
    assert "No MCP server was" in text


def test_markdown_includes_a_drift_section_when_given_one(snap_before, snap_after):
    from mcpmap.drift import compare

    text = to_markdown(analyse(snap_after, NOW), compare(snap_before, snap_after))
    assert "## Drift" in text
    assert "Panel (present in both)" in text
    assert "DESCRIPTION_CHANGED" in text
