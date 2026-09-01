"""Offline unit tests for the GitHub source. No network access is made."""

from mcpmap.sources.github import (
    GitHubSource,
    _auth_from_manifest,
    _install_from_manifest,
    _tools_from_manifest,
    _transport_from_manifest,
)


def test_tools_parsed_from_a_list_manifest():
    manifest = {"tools": [{"name": "read_file", "description": "Read a file",
                           "inputSchema": {"properties": {"path": {}, "encoding": {}}}}]}
    tools = _tools_from_manifest(manifest)
    assert tools[0].name == "read_file"
    assert tools[0].input_keys == ["encoding", "path"]


def test_tools_parsed_from_a_mapping_manifest():
    manifest = {"tools": {"ping": {"description": "Return pong"}}}
    assert [tool.name for tool in _tools_from_manifest(manifest)] == ["ping"]


def test_unnamed_tools_are_dropped():
    assert _tools_from_manifest({"tools": [{"description": "no name"}]}) == []


def test_missing_or_malformed_tools_yield_nothing():
    assert _tools_from_manifest({}) == []
    assert _tools_from_manifest({"tools": "not a list"}) == []


def test_auth_type_normalisation():
    assert _auth_from_manifest({"auth": {"type": "oauth2"}}) == "oauth"
    assert _auth_from_manifest({"auth": "bearer-token"}) == "token"
    assert _auth_from_manifest({"authentication": {"scheme": "none"}}) == "none"
    assert _auth_from_manifest({}) == "unknown"


def test_transport_normalisation():
    assert _transport_from_manifest({"transport": "STDIO"}) == "stdio"
    assert _transport_from_manifest({"transport": "streamable-http"}) == "http"
    assert _transport_from_manifest({}) == "unknown"


def test_unpinned_and_pinned_remote_execution_are_distinguished():
    assert _install_from_manifest({"runtime": {"command": "npx", "args": ["-y", "some-server"]}}) == ("npx", False)
    assert _install_from_manifest({"runtime": {"command": "npx", "args": ["some-server@1.2.3"]}}) == ("npx", True)


def test_container_and_source_installs():
    assert _install_from_manifest({"runtime": {"command": "docker"}}) == ("docker", None)
    assert _install_from_manifest({"runtime": {"command": "python3"}}) == ("source", None)
    assert _install_from_manifest({}) == ("unknown", None)


def test_request_budget_is_enforced_before_any_request(tmp_path):
    source = GitHubSource(cache_dir=tmp_path, request_budget=0)
    try:
        source._get("https://api.github.com/search/repositories")
    except Exception as exc:  # SourceError
        assert "budget" in str(exc)
    else:
        raise AssertionError("expected the budget to be enforced")


def test_cached_responses_are_reused_without_spending_budget(tmp_path):
    source = GitHubSource(cache_dir=tmp_path, request_budget=0)
    cached = source._cache_path("https://example.invalid/x")
    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_text('{"url": "https://example.invalid/x", "body": {"ok": true}}')
    assert source._get("https://example.invalid/x") == {"ok": True}
