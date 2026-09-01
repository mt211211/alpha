"""Command line for the study.

    mcpmap collect  --source fixtures --out snapshots/
    mcpmap analyse  snapshots/2026-09-01.json
    mcpmap drift    snapshots/a.json snapshots/b.json
    mcpmap report   snapshots/b.json --drift-from snapshots/a.json -o report.md
    mcpmap validate
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mcpmap import __version__, corpus, drift as drift_mod, report as report_mod, validate as validate_mod
from mcpmap.collect import build_snapshot
from mcpmap.sources.base import SourceError
from mcpmap.sources.fixtures import FixtureSource


def _build_source(args):
    if args.source == "fixtures":
        return FixtureSource(path=args.fixture)
    if args.source == "github":
        from mcpmap.sources.github import GitHubSource

        return GitHubSource(
            query=args.query,
            request_budget=args.request_budget,
            with_manifests=not args.no_manifests,
        )
    raise SystemExit(f"unknown source {args.source!r}")


def cmd_collect(args) -> int:
    source = _build_source(args)
    snapshot = build_snapshot(
        [source], snapshot_id=args.id, limit=args.limit, notes=args.notes
    )
    path = corpus.save(snapshot, args.out)
    print(f"wrote {path}")
    print(f"  servers   {len(snapshot.records)}")
    print(f"  digest    {snapshot.digest}")
    return 0


def cmd_analyse(args) -> int:
    snapshot = corpus.load(args.snapshot)
    analysis = report_mod.analyse(snapshot, now=args.now)
    if args.json:
        print(json.dumps(analysis, indent=2))
    else:
        print(report_mod.to_markdown(analysis))
    return 0


def cmd_drift(args) -> int:
    before = corpus.load(args.before)
    after = corpus.load(args.after)
    result = drift_mod.compare(before, after)
    if args.json:
        print(json.dumps(result, indent=2))
        return 0
    rates = result["rates"]
    print(f"panel {result['panel_size']} servers over {result['window_days']} days")
    for name, count in rates["counts"].items():
        share = rates.get("share_of_panel", {}).get(name)
        suffix = f"  ({share * 100:.1f}% of panel)" if share is not None else ""
        print(f"  {name:<24} {count}{suffix}")
    print(f"total events: {len(result['events'])}")
    return 0


def cmd_report(args) -> int:
    snapshot = corpus.load(args.snapshot)
    analysis = report_mod.analyse(snapshot, now=args.now)
    comparison = None
    if args.drift_from:
        comparison = drift_mod.compare(corpus.load(args.drift_from), snapshot)
    markdown = report_mod.to_markdown(analysis, comparison)
    if args.out:
        Path(args.out).write_text(markdown, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(markdown)
    return 0


def cmd_validate(args) -> int:
    result = validate_mod.evaluate(validate_mod.load_labels(args.labels))
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(validate_mod.to_markdown(result))
    if args.min_f1 is not None:
        f1 = result["micro"]["f1"] or 0.0
        if f1 < args.min_f1:
            print(f"FAIL: micro F1 {f1} below threshold {args.min_f1}", file=sys.stderr)
            return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mcpmap", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", action="version", version=f"mcpmap {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect = subparsers.add_parser("collect", help="collect a snapshot from a source")
    collect.add_argument("--source", default="fixtures", choices=("fixtures", "github"))
    collect.add_argument("--fixture", help="path to a fixture snapshot (source=fixtures)")
    collect.add_argument("--query", default="topic:mcp-server", help="search query (source=github)")
    collect.add_argument("--request-budget", type=int, default=300,
                         help="hard cap on HTTP requests (source=github)")
    collect.add_argument("--no-manifests", action="store_true",
                         help="skip manifest fetching (cheaper, but no tool surfaces)")
    collect.add_argument("--limit", type=int, help="stop after this many servers")
    collect.add_argument("--id", help="snapshot id (default: snapshot-<date>)")
    collect.add_argument("--notes", default="", help="free text recorded in the snapshot")
    collect.add_argument("--out", default="snapshots", help="output directory")
    collect.set_defaults(func=cmd_collect)

    analyse = subparsers.add_parser("analyse", help="risk distribution for one snapshot")
    analyse.add_argument("snapshot")
    analyse.add_argument("--now", help="reference time for age calculations (ISO 8601)")
    analyse.add_argument("--json", action="store_true")
    analyse.set_defaults(func=cmd_analyse)

    drift = subparsers.add_parser("drift", help="compare two snapshots")
    drift.add_argument("before")
    drift.add_argument("after")
    drift.add_argument("--json", action="store_true")
    drift.set_defaults(func=cmd_drift)

    report = subparsers.add_parser("report", help="full study report as markdown")
    report.add_argument("snapshot")
    report.add_argument("--drift-from", help="earlier snapshot to compare against")
    report.add_argument("--now", help="reference time for age calculations (ISO 8601)")
    report.add_argument("-o", "--out", help="write to a file instead of stdout")
    report.set_defaults(func=cmd_report)

    validate = subparsers.add_parser("validate", help="score capability inference vs hand labels")
    validate.add_argument("--labels", help="path to a label file")
    validate.add_argument("--min-f1", type=float, help="exit 1 if micro F1 falls below this")
    validate.add_argument("--json", action="store_true")
    validate.set_defaults(func=cmd_validate)

    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except SourceError as exc:
        print(f"collection failed: {exc}", file=sys.stderr)
        return 2
    except (FileExistsError, FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
