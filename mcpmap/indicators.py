"""Risk indicators computed over a single observed server.

A deliberate separation of concerns: this module *measures*, it does not judge.
Flags are boolean observations about a published server. Whether a flag is
acceptable in a given deployment is a policy question that depends on context,
and is out of scope for a population study.

Pure functions. No I/O.
"""

from __future__ import annotations

from datetime import datetime, timezone

from mcpmap.models import ServerRecord
from mcpmap.taxonomy import (
    BRIDGE_PAIRS,
    PIN_MARKERS,
    REMOTE_EXEC_INSTALLERS,
    TAXONOMY_VERSION,
    capabilities_of,
    injection_markers_in,
)

# Days without a push after which we treat a server as unmaintained. Chosen to
# match the common "abandoned dependency" threshold; reported alongside results
# so it can be varied.
UNMAINTAINED_AFTER_DAYS = 365

FLAGS = (
    "BRIDGE_FS_NET",
    "BRIDGE_CRED_NET",
    "BRIDGE_DB_NET",
    "SHELL_CAPABLE",
    "UNAUTH_NETWORK",
    "UNPINNED_REMOTE_EXEC",
    "DESCRIPTION_INJECTION_MARKERS",
    "UNMAINTAINED",
    "NO_LICENSE",
    "SINGLE_MAINTAINER",
)

_BRIDGE_FLAG = {
    ("filesystem_read", "network"): "BRIDGE_FS_NET",
    ("credentials", "network"): "BRIDGE_CRED_NET",
    ("database", "network"): "BRIDGE_DB_NET",
}


def _parse_ts(value) -> datetime | None:
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def days_since(value, now: str | None = None) -> int | None:
    stamp = _parse_ts(value)
    if stamp is None:
        return None
    reference = _parse_ts(now) or datetime.now(timezone.utc)
    return max(0, (reference - stamp).days)


def capabilities_by_tool(record: ServerRecord) -> dict[str, list[str]]:
    return {
        tool.name: sorted(capabilities_of(tool.name, tool.description, tool.input_keys))
        for tool in record.tools
    }


def capability_union(record: ServerRecord) -> set[str]:
    union: set[str] = set()
    for capabilities in capabilities_by_tool(record).values():
        union |= set(capabilities)
    return union


def bridges(record: ServerRecord) -> list[str]:
    """Capability pairs held by this one server that together form an exfil path."""
    held = capability_union(record)
    return sorted(
        _BRIDGE_FLAG[pair] for pair in BRIDGE_PAIRS if set(pair) <= held
    )


def injection_markers(record: ServerRecord) -> dict[str, list[str]]:
    found = {}
    for tool in record.tools:
        markers = injection_markers_in(tool.description)
        if markers:
            found[tool.name] = markers
    return found


def install_risk(record: ServerRecord) -> str:
    """Classify how the server's code reaches the machine that runs it."""
    method = (record.install_method or "unknown").lower()
    if method in REMOTE_EXEC_INSTALLERS:
        if record.install_pinned is True:
            return "remote_exec_pinned"
        if record.install_pinned is False:
            return "remote_exec_unpinned"
        return "remote_exec_unknown_pin"
    if method == "docker":
        return "container"
    if method in ("source", "binary"):
        return method
    return "unknown"


def flags_for(record: ServerRecord, now: str | None = None) -> list[str]:
    """The boolean risk observations for one server."""
    found: list[str] = list(bridges(record))
    capabilities = capability_union(record)

    if "shell" in capabilities:
        found.append("SHELL_CAPABLE")
    if "network" in capabilities and record.auth_declared == "none":
        found.append("UNAUTH_NETWORK")
    if install_risk(record) == "remote_exec_unpinned":
        found.append("UNPINNED_REMOTE_EXEC")
    if injection_markers(record):
        found.append("DESCRIPTION_INJECTION_MARKERS")

    repo = record.repo
    if repo is not None:
        stale = days_since(repo.pushed_at, now)
        if repo.archived or (stale is not None and stale > UNMAINTAINED_AFTER_DAYS):
            found.append("UNMAINTAINED")
        if not repo.license:
            found.append("NO_LICENSE")
        if repo.contributors is not None and repo.contributors <= 1:
            found.append("SINGLE_MAINTAINER")

    return sorted(set(found))


def profile(record: ServerRecord, now: str | None = None) -> dict:
    """The full indicator profile for one server."""
    repo = record.repo
    return {
        "key": record.key,
        "name": record.name,
        "publisher": record.publisher,
        "publisher_kind": record.publisher_kind,
        "surface_digest": record.surface_digest,
        "taxonomy_version": TAXONOMY_VERSION,
        "tool_count": len(record.tools),
        "capabilities": sorted(capability_union(record)),
        "capabilities_by_tool": capabilities_by_tool(record),
        "auth_declared": record.auth_declared,
        "transport": record.transport,
        "install_risk": install_risk(record),
        "injection_markers": injection_markers(record),
        "days_since_push": days_since(repo.pushed_at, now) if repo else None,
        "stars": repo.stars if repo else None,
        "contributors": repo.contributors if repo else None,
        "license": repo.license if repo else "",
        "flags": flags_for(record, now),
    }
