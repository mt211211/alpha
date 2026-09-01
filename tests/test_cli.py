import json

from mcpmap.cli import main

FIXTURE_BEFORE = "fixtures/snapshots/2026-06-01-synthetic.json"
FIXTURE_AFTER = "fixtures/snapshots/2026-09-01-synthetic.json"


def test_collect_from_fixtures_writes_a_snapshot(tmp_path, capsys):
    assert main(["collect", "--source", "fixtures", "--out", str(tmp_path), "--id", "test"]) == 0
    written = tmp_path / "test.json"
    assert written.exists()
    assert "digest" in capsys.readouterr().out


def test_collect_refuses_to_overwrite_a_snapshot(tmp_path, capsys):
    main(["collect", "--source", "fixtures", "--out", str(tmp_path), "--id", "test"])
    assert main(["collect", "--source", "fixtures", "--out", str(tmp_path), "--id", "test"]) == 2
    assert "immutable" in capsys.readouterr().err


def test_collect_honours_a_limit(tmp_path):
    main(["collect", "--source", "fixtures", "--out", str(tmp_path), "--id", "small", "--limit", "3"])
    payload = json.loads((tmp_path / "small.json").read_text())
    assert len(payload["records"]) == 3


def test_analyse_emits_json(capsys):
    assert main(["analyse", FIXTURE_AFTER, "--json", "--now", "2026-09-01T00:00:00+00:00"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["denominators"]["population"] > 0


def test_analyse_emits_markdown_by_default(capsys):
    assert main(["analyse", FIXTURE_AFTER]) == 0
    assert "# The map" in capsys.readouterr().out


def test_drift_summarises_the_panel(capsys):
    assert main(["drift", FIXTURE_BEFORE, FIXTURE_AFTER]) == 0
    out = capsys.readouterr().out
    assert "panel" in out
    assert "description_changed" in out


def test_report_writes_markdown_with_drift(tmp_path, capsys):
    target = tmp_path / "report.md"
    assert main(["report", FIXTURE_AFTER, "--drift-from", FIXTURE_BEFORE, "-o", str(target)]) == 0
    text = target.read_text()
    assert "## Drift" in text
    assert "Panel (present in both)" in text


def test_validate_reports_accuracy(capsys):
    assert main(["validate"]) == 0
    assert "Capability inference accuracy" in capsys.readouterr().out


def test_validate_fails_below_the_f1_threshold(capsys):
    assert main(["validate", "--min-f1", "0.99"]) == 1
    assert "below threshold" in capsys.readouterr().err


def test_validate_passes_a_reachable_threshold():
    assert main(["validate", "--min-f1", "0.80"]) == 0


def test_missing_snapshot_is_an_error_not_a_traceback(capsys):
    assert main(["analyse", "does-not-exist.json"]) == 2
    assert "error:" in capsys.readouterr().err
