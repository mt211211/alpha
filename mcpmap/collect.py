"""Turn one or more sources into an immutable snapshot."""

from __future__ import annotations

from datetime import datetime, timezone

from mcpmap.models import ServerRecord, Snapshot


def build_snapshot(
    sources,
    snapshot_id: str | None = None,
    limit: int | None = None,
    notes: str = "",
    captured_at: str | None = None,
) -> Snapshot:
    """Collect from every source and merge into one snapshot.

    Records sharing a key are merged rather than duplicated: later sources fill
    fields the earlier ones left unknown, and provenance from both is kept.
    """
    merged: dict[str, ServerRecord] = {}
    source_ids: list[str] = []

    for source in sources:
        source_ids.append(source.id)
        for record in source.collect(limit=limit):
            existing = merged.get(record.key)
            merged[record.key] = record if existing is None else _merge(existing, record)

    stamp = captured_at or datetime.now(timezone.utc).isoformat()
    return Snapshot(
        snapshot_id=snapshot_id or f"snapshot-{stamp[:10]}",
        captured_at=stamp,
        records=sorted(merged.values(), key=lambda item: item.key),
        sources=source_ids,
        notes=notes,
    )


_UNKNOWN = {"unknown", "", None}


def _merge(base: ServerRecord, extra: ServerRecord) -> ServerRecord:
    """Fill unknowns on `base` from `extra`. Never overwrites a known value."""
    for attribute in ("name", "publisher", "publisher_kind", "description",
                      "transport", "install_method", "auth_declared"):
        if getattr(base, attribute) in _UNKNOWN and getattr(extra, attribute) not in _UNKNOWN:
            setattr(base, attribute, getattr(extra, attribute))
    if base.install_pinned is None:
        base.install_pinned = extra.install_pinned
    if base.manifest_found is None:
        base.manifest_found = extra.manifest_found
    if not base.tools and extra.tools:
        base.tools = extra.tools
    if base.repo is None:
        base.repo = extra.repo
    base.sources = list(base.sources) + list(extra.sources)
    return base
