"""Longitudinal drift between two snapshots.

This is the part of the study that does not exist elsewhere. A single scan
says what the ecosystem looks like today; two scans say how it *moves* --
whether published tool surfaces change under users after adoption, how often,
and in which direction.

Rates are computed over the panel (servers present in BOTH snapshots), never
over the whole population, because a server that appeared after the first
snapshot cannot be observed to have drifted.

Pure functions. No I/O.
"""

from __future__ import annotations

from mcpmap.indicators import capability_union, days_since, install_risk
from mcpmap.models import ServerRecord, Snapshot

EVENT_TYPES = (
    "SERVER_APPEARED",
    "SERVER_DISAPPEARED",
    "TOOL_ADDED",
    "TOOL_REMOVED",
    "DESCRIPTION_CHANGED",
    "SCHEMA_CHANGED",
    "CAPABILITY_EXPANDED",
    "CAPABILITY_REDUCED",
    "AUTH_WEAKENED",
    "AUTH_STRENGTHENED",
    "PUBLISHER_CHANGED",
    "INSTALL_RISK_INCREASED",
)

# Ordered weakest-to-strongest so a move down this ladder is "weakened".
AUTH_STRENGTH = {"unknown": 0, "none": 1, "token": 2, "oauth": 3}

# Ordered least-to-most exposed, for install method changes.
INSTALL_EXPOSURE = {
    "unknown": 0,
    "source": 1,
    "binary": 1,
    "container": 2,
    "remote_exec_pinned": 3,
    "remote_exec_unknown_pin": 4,
    "remote_exec_unpinned": 5,
}


def _event(event_type: str, key: str, detail: str, **extra) -> dict:
    return {"type": event_type, "key": key, "detail": detail, **extra}


def compare_records(before: ServerRecord, after: ServerRecord) -> list[dict]:
    """Drift events for one server observed in both snapshots."""
    events: list[dict] = []
    key = after.key

    before_tools = before.tool_by_name()
    after_tools = after.tool_by_name()

    for name in sorted(set(after_tools) - set(before_tools)):
        events.append(_event("TOOL_ADDED", key, f"tool {name!r} was added", tool=name))
    for name in sorted(set(before_tools) - set(after_tools)):
        events.append(_event("TOOL_REMOVED", key, f"tool {name!r} was removed", tool=name))

    for name in sorted(set(before_tools) & set(after_tools)):
        old, new = before_tools[name], after_tools[name]
        if old.description != new.description:
            events.append(
                _event(
                    "DESCRIPTION_CHANGED",
                    key,
                    f"description of tool {name!r} changed",
                    tool=name,
                    before=old.description,
                    after=new.description,
                )
            )
        if old.input_keys != new.input_keys:
            events.append(
                _event(
                    "SCHEMA_CHANGED",
                    key,
                    f"input schema of tool {name!r} changed",
                    tool=name,
                    before=old.input_keys,
                    after=new.input_keys,
                )
            )

    gained = capability_union(after) - capability_union(before)
    lost = capability_union(before) - capability_union(after)
    if gained:
        events.append(
            _event(
                "CAPABILITY_EXPANDED",
                key,
                f"gained capability: {', '.join(sorted(gained))}",
                capabilities=sorted(gained),
            )
        )
    if lost:
        events.append(
            _event(
                "CAPABILITY_REDUCED",
                key,
                f"lost capability: {', '.join(sorted(lost))}",
                capabilities=sorted(lost),
            )
        )

    old_auth = AUTH_STRENGTH.get(before.auth_declared, 0)
    new_auth = AUTH_STRENGTH.get(after.auth_declared, 0)
    if new_auth < old_auth:
        events.append(
            _event(
                "AUTH_WEAKENED",
                key,
                f"declared auth moved {before.auth_declared} -> {after.auth_declared}",
                before=before.auth_declared,
                after=after.auth_declared,
            )
        )
    elif new_auth > old_auth:
        events.append(
            _event(
                "AUTH_STRENGTHENED",
                key,
                f"declared auth moved {before.auth_declared} -> {after.auth_declared}",
                before=before.auth_declared,
                after=after.auth_declared,
            )
        )

    if before.publisher and after.publisher and before.publisher != after.publisher:
        events.append(
            _event(
                "PUBLISHER_CHANGED",
                key,
                f"publisher moved {before.publisher} -> {after.publisher}",
                before=before.publisher,
                after=after.publisher,
            )
        )

    old_install = INSTALL_EXPOSURE.get(install_risk(before), 0)
    new_install = INSTALL_EXPOSURE.get(install_risk(after), 0)
    if new_install > old_install:
        events.append(
            _event(
                "INSTALL_RISK_INCREASED",
                key,
                f"install method moved {install_risk(before)} -> {install_risk(after)}",
                before=install_risk(before),
                after=install_risk(after),
            )
        )

    return events


def compare(before: Snapshot, after: Snapshot) -> dict:
    """Full drift analysis between two snapshots, with panel-based rates."""
    before_by_key = before.by_key()
    after_by_key = after.by_key()
    panel = sorted(set(before_by_key) & set(after_by_key))

    events: list[dict] = []
    for key in sorted(set(after_by_key) - set(before_by_key)):
        events.append(_event("SERVER_APPEARED", key, "first observed in the later snapshot"))
    for key in sorted(set(before_by_key) - set(after_by_key)):
        events.append(_event("SERVER_DISAPPEARED", key, "no longer observed"))
    for key in panel:
        events.extend(compare_records(before_by_key[key], after_by_key[key]))

    window_days = days_since(before.captured_at, after.captured_at)
    return {
        "before": {"snapshot_id": before.snapshot_id, "captured_at": before.captured_at,
                   "digest": before.digest, "size": len(before.records)},
        "after": {"snapshot_id": after.snapshot_id, "captured_at": after.captured_at,
                  "digest": after.digest, "size": len(after.records)},
        "window_days": window_days,
        "panel_size": len(panel),
        "events": events,
        "rates": rates(events, len(panel), window_days),
    }


def _keys_with(events, event_types) -> set[str]:
    return {
        event["key"] for event in events if event["type"] in event_types
    }


def rates(events, panel_size: int, window_days: int | None) -> dict:
    """Headline drift rates, per panel and annualised where a window is known."""
    surface_changed = _keys_with(
        events, {"TOOL_ADDED", "TOOL_REMOVED", "DESCRIPTION_CHANGED", "SCHEMA_CHANGED"}
    )
    measures = {
        "surface_changed": len(surface_changed),
        "description_changed": len(_keys_with(events, {"DESCRIPTION_CHANGED"})),
        "capability_expanded": len(_keys_with(events, {"CAPABILITY_EXPANDED"})),
        "auth_weakened": len(_keys_with(events, {"AUTH_WEAKENED"})),
        "publisher_changed": len(_keys_with(events, {"PUBLISHER_CHANGED"})),
        "install_risk_increased": len(_keys_with(events, {"INSTALL_RISK_INCREASED"})),
    }

    out: dict = {"panel_size": panel_size, "window_days": window_days, "counts": measures}
    if panel_size:
        out["share_of_panel"] = {
            name: round(count / panel_size, 4) for name, count in measures.items()
        }
        if window_days:
            scale = 365.0 / window_days
            out["annualised_share"] = {
                name: round(min(1.0, (count / panel_size) * scale), 4)
                for name, count in measures.items()
            }
    return out
