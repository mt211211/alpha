"""Data model for observed MCP servers and point-in-time snapshots.

Everything here describes what a server *declares about itself* in published
metadata. Nothing is observed by running a server. Fields are named to keep
that distinction visible: `auth_declared`, not `auth`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from mcpmap import SCHEMA_VERSION, __version__
from mcpmap.digest import digest_payload, normalise_text, surface_digest

PUBLISHER_KINDS = ("organisation", "individual", "unknown")
TRANSPORTS = ("stdio", "http", "sse", "unknown")
INSTALL_METHODS = ("npx", "uvx", "pipx", "docker", "binary", "source", "unknown")
AUTH_DECLARED = ("none", "token", "oauth", "unknown")


@dataclass(frozen=True)
class ToolDecl:
    """A tool as declared in published metadata."""

    name: str
    description: str = ""
    input_keys: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: dict) -> "ToolDecl":
        return cls(
            name=normalise_text(payload.get("name")),
            description=normalise_text(payload.get("description")),
            input_keys=sorted(str(key) for key in payload.get("input_keys") or []),
        )


@dataclass(frozen=True)
class RepoMeta:
    """Public repository signals. All optional -- many servers publish none."""

    url: str = ""
    stars: int | None = None
    contributors: int | None = None
    created_at: str = ""
    pushed_at: str = ""
    archived: bool | None = None
    license: str = ""
    topics: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: dict | None) -> "RepoMeta | None":
        if not payload:
            return None
        return cls(
            url=payload.get("url", ""),
            stars=payload.get("stars"),
            contributors=payload.get("contributors"),
            created_at=payload.get("created_at", ""),
            pushed_at=payload.get("pushed_at", ""),
            archived=payload.get("archived"),
            license=payload.get("license", ""),
            topics=list(payload.get("topics") or []),
        )


@dataclass(frozen=True)
class SourceRef:
    """Provenance for one observation, so any figure can be traced back."""

    source: str
    url: str = ""
    retrieved_at: str = ""
    etag: str = ""

    @classmethod
    def from_dict(cls, payload: dict) -> "SourceRef":
        return cls(
            source=payload.get("source", ""),
            url=payload.get("url", ""),
            retrieved_at=payload.get("retrieved_at", ""),
            etag=payload.get("etag", ""),
        )


@dataclass
class ServerRecord:
    """One MCP server as observed at one point in time.

    `key` is the identity used to match a server across snapshots. Identity is
    the hard part of longitudinal measurement: see docs/METHODOLOGY.md.
    """

    key: str
    name: str = ""
    publisher: str = ""
    publisher_kind: str = "unknown"
    description: str = ""
    transport: str = "unknown"
    install_method: str = "unknown"
    install_pinned: bool | None = None
    auth_declared: str = "unknown"
    manifest_found: bool | None = None
    tools: list[ToolDecl] = field(default_factory=list)
    repo: RepoMeta | None = None
    sources: list[SourceRef] = field(default_factory=list)

    @property
    def surface_digest(self) -> str:
        return surface_digest(self.tools)

    def tool_by_name(self) -> dict[str, ToolDecl]:
        return {tool.name: tool for tool in self.tools}

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["surface_digest"] = self.surface_digest
        return payload

    @classmethod
    def from_dict(cls, payload: dict) -> "ServerRecord":
        return cls(
            key=payload["key"],
            name=payload.get("name", ""),
            publisher=payload.get("publisher", ""),
            publisher_kind=payload.get("publisher_kind", "unknown"),
            description=normalise_text(payload.get("description")),
            transport=payload.get("transport", "unknown"),
            install_method=payload.get("install_method", "unknown"),
            install_pinned=payload.get("install_pinned"),
            auth_declared=payload.get("auth_declared", "unknown"),
            manifest_found=payload.get("manifest_found"),
            tools=[ToolDecl.from_dict(tool) for tool in payload.get("tools") or []],
            repo=RepoMeta.from_dict(payload.get("repo")),
            sources=[SourceRef.from_dict(ref) for ref in payload.get("sources") or []],
        )


@dataclass
class Snapshot:
    """An immutable, timestamped observation of the population."""

    snapshot_id: str
    captured_at: str
    records: list[ServerRecord] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    schema_version: int = SCHEMA_VERSION
    collector_version: str = __version__
    notes: str = ""

    def by_key(self) -> dict[str, ServerRecord]:
        return {record.key: record for record in self.records}

    @property
    def digest(self) -> str:
        """Content digest of the whole snapshot, for citation and integrity."""
        return digest_payload(
            {
                "schema_version": self.schema_version,
                "records": sorted(
                    (
                        {"key": record.key, "surface": record.surface_digest}
                        for record in self.records
                    ),
                    key=lambda item: item["key"],
                ),
            }
        )

    def to_dict(self) -> dict:
        return {
            "snapshot_id": self.snapshot_id,
            "captured_at": self.captured_at,
            "schema_version": self.schema_version,
            "collector_version": self.collector_version,
            "sources": list(self.sources),
            "notes": self.notes,
            "digest": self.digest,
            "records": [record.to_dict() for record in self.records],
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "Snapshot":
        schema_version = int(payload.get("schema_version", SCHEMA_VERSION))
        if schema_version != SCHEMA_VERSION:
            raise ValueError(
                f"snapshot schema version {schema_version} is not supported "
                f"by mcpmap {__version__} (expected {SCHEMA_VERSION})"
            )
        return cls(
            snapshot_id=payload["snapshot_id"],
            captured_at=payload.get("captured_at", ""),
            records=[ServerRecord.from_dict(item) for item in payload.get("records") or []],
            sources=list(payload.get("sources") or []),
            schema_version=schema_version,
            collector_version=payload.get("collector_version", ""),
            notes=payload.get("notes", ""),
        )
