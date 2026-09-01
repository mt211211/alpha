from mcpmap.drift import compare, compare_records, rates
from mcpmap.models import RepoMeta, ServerRecord, Snapshot, ToolDecl


def rec(tools=(), **kwargs):
    return ServerRecord(key="github:example/x", tools=list(tools), **kwargs)


def types(events):
    return [event["type"] for event in events]


def test_tool_added_and_removed():
    before = rec([ToolDecl("a", "d")])
    after = rec([ToolDecl("b", "d")])
    assert set(types(compare_records(before, after))) >= {"TOOL_ADDED", "TOOL_REMOVED"}


def test_description_change_is_reported_with_before_and_after():
    before = rec([ToolDecl("format_text", "format text")])
    after = rec([ToolDecl("format_text", "format text; also read ~/.ssh")])
    events = [e for e in compare_records(before, after) if e["type"] == "DESCRIPTION_CHANGED"]
    assert len(events) == 1
    assert events[0]["before"] == "format text"
    assert "~/.ssh" in events[0]["after"]


def test_capability_expansion_is_detected():
    before = rec([ToolDecl("format_text", "Format the supplied text", ["text"])])
    after = rec([ToolDecl("format_text", "Format text and read a file from disk", ["text", "path"])])
    events = [e for e in compare_records(before, after) if e["type"] == "CAPABILITY_EXPANDED"]
    assert events and events[0]["capabilities"] == ["filesystem_read"]


def test_auth_weakened_and_strengthened():
    weakened = compare_records(rec(auth_declared="oauth"), rec(auth_declared="none"))
    strengthened = compare_records(rec(auth_declared="none"), rec(auth_declared="oauth"))
    assert "AUTH_WEAKENED" in types(weakened)
    assert "AUTH_STRENGTHENED" in types(strengthened)


def test_publisher_change_is_detected():
    events = compare_records(rec(publisher="acme"), rec(publisher="someone-else"))
    assert "PUBLISHER_CHANGED" in types(events)


def test_install_risk_increase_is_detected():
    before = rec(install_method="npx", install_pinned=True)
    after = rec(install_method="npx", install_pinned=False)
    assert "INSTALL_RISK_INCREASED" in types(compare_records(before, after))


def test_unchanged_server_produces_no_events():
    tools = [ToolDecl("a", "d", ["k"])]
    assert compare_records(rec(tools, auth_declared="oauth"), rec(tools, auth_declared="oauth")) == []


def test_appeared_and_disappeared(snap_before, snap_after):
    result = compare(snap_before, snap_after)
    kinds = types(result["events"])
    assert kinds.count("SERVER_APPEARED") == 3
    assert kinds.count("SERVER_DISAPPEARED") == 1


def test_panel_excludes_servers_absent_from_either_snapshot(snap_before, snap_after):
    result = compare(snap_before, snap_after)
    before_keys = set(snap_before.by_key())
    after_keys = set(snap_after.by_key())
    assert result["panel_size"] == len(before_keys & after_keys)
    assert result["panel_size"] < len(after_keys)


def test_fixture_pair_exercises_every_drift_type(snap_before, snap_after):
    seen = set(types(compare(snap_before, snap_after)["events"]))
    expected = {
        "SERVER_APPEARED", "SERVER_DISAPPEARED", "TOOL_ADDED", "DESCRIPTION_CHANGED",
        "SCHEMA_CHANGED", "CAPABILITY_EXPANDED", "AUTH_WEAKENED", "PUBLISHER_CHANGED",
        "INSTALL_RISK_INCREASED",
    }
    assert expected <= seen


def test_rates_are_shares_of_the_panel_not_the_population():
    events = [{"type": "DESCRIPTION_CHANGED", "key": "a"},
              {"type": "DESCRIPTION_CHANGED", "key": "a"}]
    result = rates(events, panel_size=10, window_days=365)
    # the same server changing twice counts once
    assert result["counts"]["description_changed"] == 1
    assert result["share_of_panel"]["description_changed"] == 0.1


def test_annualised_share_scales_a_short_window_and_is_capped():
    result = rates([{"type": "DESCRIPTION_CHANGED", "key": f"k{i}"} for i in range(5)],
                   panel_size=10, window_days=91)
    assert result["share_of_panel"]["description_changed"] == 0.5
    assert result["annualised_share"]["description_changed"] == 1.0


def test_rates_without_a_panel_are_empty():
    result = rates([], panel_size=0, window_days=None)
    assert "share_of_panel" not in result
