"""Collection from public GitHub repositories that publish MCP servers.

Reads published metadata over the public API. It clones nothing, installs
nothing, and runs nothing it finds. See docs/ETHICS.md for the collection
posture (rate limiting, caching, identification, and what we deliberately do
not collect).

Known limitation, and itself a finding: most MCP servers declare their tools in
code rather than in a machine-readable manifest. Where no manifest is found the
record carries `manifest_found=False` and an empty tool surface, so that
"undeclared" is never silently counted as "no capabilities".
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

from mcpmap import __version__
from mcpmap.models import RepoMeta, ServerRecord, SourceRef, ToolDecl
from mcpmap.sources.base import SourceError

API = "https://api.github.com"
RAW = "https://raw.githubusercontent.com"

USER_AGENT = f"mcpmap/{__version__} (+https://github.com/mt211211/alpha; research collector)"

# Manifest paths tried, in order, on the repository default branch.
MANIFEST_PATHS = (
    "server.json",
    "mcp.json",
    ".well-known/mcp.json",
    ".mcp/server.json",
    "mcp-server.json",
)

DEFAULT_QUERY = "topic:mcp-server"

# Politeness: a floor on the gap between requests, plus a hard request budget
# so an accidental run cannot turn into a crawl.
MIN_INTERVAL_SECONDS = 1.0
DEFAULT_REQUEST_BUDGET = 300


class GitHubSource:
    id = "github"

    def __init__(
        self,
        query: str = DEFAULT_QUERY,
        token: str | None = None,
        cache_dir="./.cache/github",
        request_budget: int = DEFAULT_REQUEST_BUDGET,
        with_manifests: bool = True,
        min_interval: float = MIN_INTERVAL_SECONDS,
    ):
        self.query = query
        self.token = token or os.environ.get("GITHUB_TOKEN") or ""
        self.cache_dir = Path(cache_dir)
        self.request_budget = request_budget
        self.with_manifests = with_manifests
        self.min_interval = min_interval
        self._spent = 0
        self._last_request = 0.0

    # -- plumbing ----------------------------------------------------------

    def _headers(self) -> dict:
        headers = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_request = time.monotonic()

    def _cache_path(self, url: str) -> Path:
        from mcpmap.digest import sha256_hex

        return self.cache_dir / f"{sha256_hex(url)}.json"

    def _get(self, url: str, params: dict | None = None, raw: bool = False):
        """One budgeted, throttled, disk-cached GET. Returns None on 404."""
        cache_key = url if not params else url + "?" + json.dumps(params, sort_keys=True)
        cached = self._cache_path(cache_key)
        if cached.exists():
            payload = json.loads(cached.read_text(encoding="utf-8"))
            return payload["body"]

        if self._spent >= self.request_budget:
            raise SourceError(
                f"request budget of {self.request_budget} exhausted; "
                "raise --request-budget or narrow the query"
            )

        self._throttle()
        self._spent += 1
        try:
            response = httpx.get(
                url, params=params, headers=self._headers(), timeout=30.0,
                follow_redirects=True,
            )
        except httpx.HTTPError as exc:
            raise SourceError(f"GET {url} failed: {exc}") from exc

        if response.status_code == 404:
            body = None
        elif response.status_code == 403 and "rate limit" in response.text.lower():
            raise SourceError(
                "GitHub rate limit reached. Set GITHUB_TOKEN for a higher limit, "
                "or resume later -- responses already fetched are cached."
            )
        elif response.status_code >= 400:
            raise SourceError(f"GET {url} returned {response.status_code}: {response.text[:200]}")
        else:
            body = response.text if raw else response.json()

        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_text(json.dumps({"url": cache_key, "body": body}), encoding="utf-8")
        return body

    # -- collection --------------------------------------------------------

    def collect(self, limit: int | None = None) -> list[ServerRecord]:
        records: list[ServerRecord] = []
        per_page = 50
        page = 1
        while limit is None or len(records) < limit:
            body = self._get(
                f"{API}/search/repositories",
                params={"q": self.query, "per_page": per_page, "page": page,
                        "sort": "updated", "order": "desc"},
            )
            items = (body or {}).get("items") or []
            if not items:
                break
            for item in items:
                records.append(self._to_record(item))
                if limit is not None and len(records) >= limit:
                    break
            if len(items) < per_page:
                break
            page += 1
        return records

    def _to_record(self, item: dict) -> ServerRecord:
        full_name = item.get("full_name", "")
        owner = item.get("owner") or {}
        retrieved_at = datetime.now(timezone.utc).isoformat()

        tools: list[ToolDecl] = []
        manifest_found: bool | None = None
        auth_declared = "unknown"
        transport = "unknown"
        install_method = "unknown"
        install_pinned = None

        if self.with_manifests:
            manifest = self._fetch_manifest(full_name, item.get("default_branch") or "main")
            manifest_found = manifest is not None
            if manifest:
                tools = _tools_from_manifest(manifest)
                auth_declared = _auth_from_manifest(manifest)
                transport = _transport_from_manifest(manifest)
                install_method, install_pinned = _install_from_manifest(manifest)

        return ServerRecord(
            key=f"github:{full_name}",
            name=item.get("name", ""),
            publisher=owner.get("login", ""),
            publisher_kind="organisation" if owner.get("type") == "Organization" else "individual",
            description=item.get("description") or "",
            transport=transport,
            install_method=install_method,
            install_pinned=install_pinned,
            auth_declared=auth_declared,
            manifest_found=manifest_found,
            tools=tools,
            repo=RepoMeta(
                url=item.get("html_url", ""),
                stars=item.get("stargazers_count"),
                contributors=None,  # a separate paginated call; not worth the budget
                created_at=item.get("created_at", ""),
                pushed_at=item.get("pushed_at", ""),
                archived=item.get("archived"),
                license=((item.get("license") or {}).get("spdx_id") or ""),
                topics=list(item.get("topics") or []),
            ),
            sources=[SourceRef(source=self.id, url=item.get("html_url", ""),
                               retrieved_at=retrieved_at)],
        )

    def _fetch_manifest(self, full_name: str, branch: str) -> dict | None:
        for candidate in MANIFEST_PATHS:
            body = self._get(f"{RAW}/{full_name}/{branch}/{candidate}", raw=True)
            if not body:
                continue
            try:
                parsed = json.loads(body)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed
        return None


# -- manifest parsing (tolerant: published manifests vary) -------------------


def _tools_from_manifest(manifest: dict) -> list[ToolDecl]:
    raw_tools = manifest.get("tools")
    if isinstance(raw_tools, dict):
        raw_tools = [dict(value, name=key) for key, value in raw_tools.items()]
    if not isinstance(raw_tools, list):
        return []
    tools = []
    for entry in raw_tools:
        if not isinstance(entry, dict):
            continue
        schema = entry.get("inputSchema") or entry.get("input_schema") or {}
        properties = schema.get("properties") if isinstance(schema, dict) else {}
        tools.append(
            ToolDecl.from_dict(
                {
                    "name": entry.get("name", ""),
                    "description": entry.get("description", ""),
                    "input_keys": sorted(properties) if isinstance(properties, dict) else [],
                }
            )
        )
    return [tool for tool in tools if tool.name]


def _auth_from_manifest(manifest: dict) -> str:
    auth = manifest.get("auth") or manifest.get("authentication") or {}
    if isinstance(auth, str):
        value = auth.lower()
    elif isinstance(auth, dict):
        value = str(auth.get("type") or auth.get("scheme") or "").lower()
    else:
        return "unknown"
    if not value:
        return "unknown"
    if "oauth" in value:
        return "oauth"
    if any(marker in value for marker in ("token", "bearer", "apikey", "api_key", "key")):
        return "token"
    if value in ("none", "no", "false", "anonymous"):
        return "none"
    return "unknown"


def _transport_from_manifest(manifest: dict) -> str:
    value = str(manifest.get("transport") or "").lower()
    for candidate in ("stdio", "sse", "http"):
        if candidate in value:
            return candidate
    return "unknown"


def _install_from_manifest(manifest: dict) -> tuple[str, bool | None]:
    from mcpmap.taxonomy import PIN_MARKERS, REMOTE_EXEC_INSTALLERS

    runtime = manifest.get("runtime") or manifest.get("install") or {}
    command = ""
    args: list = []
    if isinstance(runtime, dict):
        command = str(runtime.get("command") or "")
        args = list(runtime.get("args") or [])
    elif isinstance(runtime, str):
        command = runtime

    base = Path(command).name.lower() if command else ""
    if base in REMOTE_EXEC_INSTALLERS:
        package = next((str(arg) for arg in args if not str(arg).startswith("-")), "")
        pinned = any(marker in package for marker in PIN_MARKERS) if package else None
        return base, pinned
    if base in ("docker", "podman"):
        return "docker", None
    if base in ("python", "python3", "node", "deno", "bun"):
        return "source", None
    if base:
        return "binary", None
    return "unknown", None
