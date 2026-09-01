"""The contract every collection source obeys.

The safety property that matters is enforced by construction: a source returns
metadata records. There is no code path anywhere in this package that installs,
launches, connects to or invokes an MCP server.
"""

from __future__ import annotations

from typing import Protocol

from mcpmap.models import ServerRecord


class SourceError(RuntimeError):
    """Raised when a source cannot collect (network, auth, rate limit)."""


class Source(Protocol):
    id: str

    def collect(self, limit: int | None = None) -> list[ServerRecord]:
        """Return observed servers. Must not execute anything it observes."""
        ...
