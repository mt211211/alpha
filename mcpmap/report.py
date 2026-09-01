"""Aggregate a snapshot (and optionally a drift comparison) into study output.

Two denominators are reported throughout and never conflated:

  population       every server observed
  analysable       servers that publish a machine-readable tool manifest

Capability and flag prevalence can only be computed over the analysable subset.
Reporting them against the whole population would silently treat "did not
declare" as "does not have", which is the most likely way a study like this
misleads.
"""

from __future__ import annotations

from collections import Counter
from statistics import median

from mcpmap.indicators import UNMAINTAINED_AFTER_DAYS, capability_union, flags_for, install_risk, profile
from mcpmap.models import Snapshot
from mcpmap.taxonomy import CAPABILITY_SIGNALS, TAXONOMY_VERSION


def _share(count: int, total: int) -> float:
    return round(count / total, 4) if total else 0.0


def _distribution(values, total: int) -> dict:
    counts = Counter(values)
    return {
        value: {"n": count, "share": _share(count, total)}
        for value, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    }


def analyse(snapshot: Snapshot, now: str | None = None) -> dict:
    records = snapshot.records
    population = len(records)
    analysable = [record for record in records if record.tools]

    profiles = [profile(record, now) for record in analysable]
    capability_counts = Counter()
    for record in analysable:
        capability_counts.update(capability_union(record))
    flag_counts = Counter()
    for record in analysable:
        flag_counts.update(flags_for(record, now))

    tool_counts = [len(record.tools) for record in analysable]
    push_ages = [item["days_since_push"] for item in profiles if item["days_since_push"] is not None]

    return {
        "snapshot_id": snapshot.snapshot_id,
        "captured_at": snapshot.captured_at,
        "digest": snapshot.digest,
        "taxonomy_version": TAXONOMY_VERSION,
        "unmaintained_after_days": UNMAINTAINED_AFTER_DAYS,
        "denominators": {
            "population": population,
            "analysable": len(analysable),
            "manifest_coverage": _share(len(analysable), population),
            "manifest_absent": sum(1 for record in records if record.manifest_found is False),
            "manifest_unknown": sum(1 for record in records if record.manifest_found is None),
        },
        "tools": {
            "median": median(tool_counts) if tool_counts else 0,
            "max": max(tool_counts) if tool_counts else 0,
            "total": sum(tool_counts),
        },
        "capabilities": {
            capability: {"n": capability_counts.get(capability, 0),
                         "share": _share(capability_counts.get(capability, 0), len(analysable))}
            for capability in sorted(CAPABILITY_SIGNALS)
        },
        "flags": {
            flag: {"n": count, "share": _share(count, len(analysable))}
            for flag, count in sorted(flag_counts.items(), key=lambda item: (-item[1], item[0]))
        },
        "auth_declared": _distribution((r.auth_declared for r in records), population),
        "install_risk": _distribution((install_risk(r) for r in records), population),
        "publisher_kind": _distribution((r.publisher_kind for r in records), population),
        "transport": _distribution((r.transport for r in records), population),
        "maintenance": {
            "median_days_since_push": int(median(push_ages)) if push_ages else None,
            "licensed": _share(sum(1 for r in records if r.repo and r.repo.license), population),
        },
    }


def _pct(value) -> str:
    return f"{value * 100:.1f}%"


def _table(title: str, rows: dict, denominator: str) -> list[str]:
    lines = [f"### {title}", "", f"Denominator: {denominator}.", "",
             "| Value | n | Share |", "| --- | ---: | ---: |"]
    for name, cell in rows.items():
        lines.append(f"| `{name}` | {cell['n']} | {_pct(cell['share'])} |")
    lines.append("")
    return lines


def to_markdown(analysis: dict, drift: dict | None = None) -> str:
    denominators = analysis["denominators"]
    population = denominators["population"]
    analysable = denominators["analysable"]

    lines = [
        f"# The map — MCP ecosystem risk snapshot `{analysis['snapshot_id']}`",
        "",
        f"- Captured: {analysis['captured_at']}",
        f"- Snapshot digest: `{analysis['digest']}`",
        f"- Taxonomy version: `{analysis['taxonomy_version']}`",
        "",
        "## Coverage",
        "",
        f"- Servers observed (population): **{population}**",
        f"- Publishing a machine-readable tool manifest (analysable): "
        f"**{analysable}** ({_pct(denominators['manifest_coverage'])})",
        f"- No manifest found: {denominators['manifest_absent']}; not checked: "
        f"{denominators['manifest_unknown']}",
        "",
        "Capability and flag figures below are shares of the **analysable** subset. "
        "A server that declares no manifest is not evidence of a server with no "
        "capabilities, and is excluded rather than counted as safe.",
        "",
        "## Declared tool surface",
        "",
        f"- Median tools per analysable server: {analysis['tools']['median']}",
        f"- Largest declared surface: {analysis['tools']['max']} tools",
        f"- Total tools observed: {analysis['tools']['total']}",
        "",
        "### Inferred capability prevalence",
        "",
        f"Denominator: {analysable} analysable servers. Capabilities are *inferred* "
        "from names, descriptions and schema keys; run `mcpmap validate` for the "
        "measured accuracy of that inference.",
        "",
        "| Capability | n | Share |",
        "| --- | ---: | ---: |",
    ]
    for capability, cell in analysis["capabilities"].items():
        lines.append(f"| `{capability}` | {cell['n']} | {_pct(cell['share'])} |")
    lines.append("")

    lines += _table("Risk flags", analysis["flags"], f"{analysable} analysable servers")
    lines += _table("Declared authentication", analysis["auth_declared"], f"{population} servers")
    lines += _table("Install exposure", analysis["install_risk"], f"{population} servers")
    lines += _table("Publisher kind", analysis["publisher_kind"], f"{population} servers")

    maintenance = analysis["maintenance"]
    lines += [
        "### Maintenance",
        "",
        f"- Median days since last push: {maintenance['median_days_since_push']}",
        f"- Carrying a licence: {_pct(maintenance['licensed'])}",
        f"- Unmaintained threshold: {analysis['unmaintained_after_days']} days",
        "",
    ]

    if drift:
        lines += _drift_section(drift)

    lines += [
        "---",
        "",
        "Produced by `mcpmap` from published metadata only. No MCP server was "
        "installed, connected to or executed to produce these figures.",
        "",
    ]
    return "\n".join(lines)


def _drift_section(drift: dict) -> list[str]:
    rates = drift["rates"]
    counts = rates["counts"]
    shares = rates.get("share_of_panel", {})
    annual = rates.get("annualised_share", {})

    lines = [
        "## Drift",
        "",
        f"- Earlier snapshot: `{drift['before']['snapshot_id']}` "
        f"({drift['before']['captured_at']}, {drift['before']['size']} servers)",
        f"- Later snapshot: `{drift['after']['snapshot_id']}` "
        f"({drift['after']['captured_at']}, {drift['after']['size']} servers)",
        f"- Observation window: {drift['window_days']} days",
        f"- Panel (present in both): **{drift['panel_size']}** servers",
        "",
        "Rates are shares of the panel. A server first seen in the later snapshot "
        "cannot have been observed to drift and is excluded.",
        "",
        "| Change | n | Share of panel | Annualised |",
        "| --- | ---: | ---: | ---: |",
    ]
    for name in counts:
        annualised = _pct(annual[name]) if name in annual else "n/a"
        share = _pct(shares[name]) if name in shares else "n/a"
        lines.append(f"| `{name}` | {counts[name]} | {share} | {annualised} |")
    lines.append("")

    notable = [
        event for event in drift["events"]
        if event["type"] in ("DESCRIPTION_CHANGED", "CAPABILITY_EXPANDED",
                             "AUTH_WEAKENED", "PUBLISHER_CHANGED")
    ]
    if notable:
        lines += ["### Notable events", "", "| Server | Change | Detail |",
                  "| --- | --- | --- |"]
        for event in notable[:50]:
            lines.append(f"| `{event['key']}` | `{event['type']}` | {event['detail']} |")
        lines.append("")
    return lines
