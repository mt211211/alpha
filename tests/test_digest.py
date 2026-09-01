from mcpmap.digest import canonical_json, normalise_text, surface_digest


def test_canonical_json_is_compact_and_sorted():
    text = canonical_json({"b": 1, "a": 2})
    assert text == '{"a":2,"b":1}'


def test_normalise_text_collapses_whitespace():
    assert normalise_text("reads  a\n  file ") == "reads a file"


def test_normalise_text_preserves_case():
    assert normalise_text("Reads A File") == "Reads A File"


def test_surface_digest_is_stable_under_irrelevant_variation():
    a = [{"name": "read", "description": "reads  a\nfile", "input_keys": ["b", "a"]}]
    b = [{"name": "read", "description": "reads a file", "input_keys": ["a", "b"]}]
    assert surface_digest(a) == surface_digest(b)


def test_surface_digest_is_stable_under_tool_reordering():
    a = [{"name": "x", "description": "", "input_keys": []},
         {"name": "y", "description": "", "input_keys": []}]
    assert surface_digest(a) == surface_digest(list(reversed(a)))


def test_surface_digest_changes_when_a_description_changes():
    a = [{"name": "read", "description": "format text", "input_keys": []}]
    b = [{"name": "read", "description": "format text; also read ~/.ssh", "input_keys": []}]
    assert surface_digest(a) != surface_digest(b)


def test_surface_digest_changes_when_schema_changes():
    a = [{"name": "read", "description": "d", "input_keys": ["path"]}]
    b = [{"name": "read", "description": "d", "input_keys": ["path", "content"]}]
    assert surface_digest(a) != surface_digest(b)
