"""Canonical serialisation and content digests.

Drift measurement rests on being able to say two observations of the same
server are or are not the same. That requires a canonical form whose hash is
stable under irrelevant variation (key order, list order, whitespace) and
sensitive to the things we actually study (tool names, descriptions, declared
schema keys).

Pure functions. No I/O.
"""

from __future__ import annotations

import hashlib
import json

SEPARATORS = (",", ":")


def canonical_json(payload) -> str:
    """Deterministic JSON: sorted keys, no incidental whitespace."""
    return json.dumps(payload, sort_keys=True, separators=SEPARATORS, ensure_ascii=False)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def digest_payload(payload) -> str:
    return sha256_hex(canonical_json(payload))


def normalise_text(value) -> str:
    """Collapse whitespace so cosmetic reformatting is not counted as drift.

    Deliberately NOT case-folded: a description rewritten in different case is
    still a rewrite, and we would rather over-report than miss a rug-pull.
    """
    return " ".join(str(value or "").split())


def tool_surface(tools) -> list[dict]:
    """The canonical, comparable form of a server's declared tool surface."""
    surface = []
    for tool in tools or []:
        surface.append(
            {
                "name": normalise_text(getattr(tool, "name", None) or tool.get("name", "")),
                "description": normalise_text(
                    getattr(tool, "description", None)
                    if hasattr(tool, "description")
                    else tool.get("description", "")
                ),
                "input_keys": sorted(
                    str(key)
                    for key in (
                        getattr(tool, "input_keys", None)
                        if hasattr(tool, "input_keys")
                        else tool.get("input_keys", [])
                    )
                    or []
                ),
            }
        )
    return sorted(surface, key=lambda item: item["name"])


def surface_digest(tools) -> str:
    """Digest of the declared tool surface -- the anchor for drift detection."""
    return digest_payload(tool_surface(tools))
