"""The capability inference model, expressed as versioned data.

Published MCP metadata rarely declares capabilities directly. What it gives us
is tool names, prose descriptions and input schema keys. We infer capability
from those, which means the inference can be *wrong*, so it is kept here as
inspectable, versioned data rather than buried in code -- and its accuracy is
measured against a hand-labelled set (see mcpmap/validate.py).

Any figure produced by this package is only meaningful when cited alongside
TAXONOMY_VERSION.
"""

from __future__ import annotations

TAXONOMY_VERSION = "2026.09.1"

# Capability -> substrings matched case-insensitively against tool name,
# description and input schema keys. Deliberately high-recall: a false positive
# is visible in the validation report, a false negative silently understates
# ecosystem risk.
CAPABILITY_SIGNALS: dict[str, dict[str, list[str]]] = {
    "filesystem_read": {
        "name": ["read_file", "readfile", "get_file", "cat_", "list_dir", "list_files",
                 "read_dir", "glob", "search_files", "grep", "load_file", "open_file"],
        "text": ["read a file", "read files", "reads the file", "contents of a file",
                 "list files", "directory listing", "local filesystem", "file system",
                 "from disk", "read from the local"],
        "keys": ["path", "filepath", "file_path", "filename", "directory", "dirpath"],
    },
    "filesystem_write": {
        "name": ["write_file", "writefile", "put_file", "save_file", "create_file",
                 "delete_file", "remove_file", "move_file", "edit_file", "patch_file",
                 "mkdir", "rmdir"],
        "text": ["write a file", "writes the file", "write to disk", "create a file",
                 "delete a file", "modify the file", "overwrite", "save the file",
                 "save it locally", "saves the file", "store the file", "to a local"],
        "keys": ["content", "contents", "destination", "outpath", "out_path"],
    },
    "network": {
        "name": ["fetch", "http", "request", "curl", "download", "upload", "webhook",
                 "api_call", "post_", "get_url", "browse", "crawl", "scrape", "send_"],
        "text": ["http request", "https request", "makes a request", "call an api",
                 "calls the api", "outbound", "remote server", "fetch a url",
                 "download from", "upload to", "send to"],
        "keys": ["url", "uri", "endpoint", "host", "webhook_url"],
    },
    "shell": {
        "name": ["exec", "shell", "run_command", "runcommand", "bash", "sh_", "spawn",
                 "subprocess", "terminal", "cmd", "powershell", "eval_"],
        "text": ["shell command", "execute a command", "run a command", "arbitrary command",
                 "runs commands", "command line", "subprocess", "execute code",
                 "runs the code", "evaluate code"],
        "keys": ["command", "cmd", "script", "args", "argv"],
    },
    "credentials": {
        "name": ["access_token", "auth_token", "api_token", "get_token", "rotate_token",
                 "secret", "credential", "apikey", "api_key", "password",
                 "keychain", "vault", "login", "signin"],
        "text": ["api key", "access token", "credentials", "secret", "password",
                 "private key", "authentication token", "environment variable"],
        "keys": ["token", "api_key", "apikey", "secret", "password", "credential"],
    },
    "database": {
        "name": ["query", "sql", "select_", "insert_", "update_row", "delete_row",
                 "mongo", "postgres", "mysql", "sqlite", "redis", "collection"],
        "text": ["sql query", "database", "execute a query", "queries the", "table",
                 "records from the", "datastore"],
        "keys": ["query", "sql", "table", "collection", "database", "db"],
    },
}

# Schema keys are weak evidence on their own -- almost every tool has a "path"
# or a "query" argument. They only count when the declaration also uses a verb
# appropriate to THAT capability, so a writing tool is not read as a reader.
KEY_VERBS: dict[str, list[str]] = {
    "filesystem_read": ["read", "list", "open", "load", "search", "find", "index",
                        "walk", "browse the", "inspect"],
    "filesystem_write": ["write", "save", "create", "delete", "remove", "modify",
                         "overwrite", "export", "mkdir", "rename", "move"],
    "network": ["fetch", "send", "post", "download", "upload", "request", "call",
                "publish", "sync"],
    "shell": ["run", "execute", "spawn", "eval", "invoke"],
    "credentials": ["read", "return", "get", "store", "rotate", "retrieve"],
    "database": ["query the", "queries", "execute a query", "run a query", "select",
                 "insert", "update", "delete from", "find documents", "return the tables"],
}

# Capability pairs that constitute an exfiltration path when held by one server.
BRIDGE_PAIRS: list[tuple[str, str]] = [
    ("filesystem_read", "network"),
    ("credentials", "network"),
    ("database", "network"),
]

# Imperative patterns inside a tool DESCRIPTION. Descriptions are fed verbatim
# into the model's context, so a description is an injection surface, not
# documentation. Matched case-insensitively.
INJECTION_MARKERS: list[str] = [
    "ignore previous", "ignore all previous", "disregard the above",
    "do not tell the user", "without telling the user", "do not mention",
    "you must always", "you should always call", "always call this tool first",
    "before answering", "before using any other tool", "before calling any",
    "system prompt", "your instructions are", "new instructions",
    "important: you", "note to the assistant", "note to ai", "<instructions>",
]

# Install strings that fetch and execute code from a remote registry at run time.
REMOTE_EXEC_INSTALLERS = ("npx", "uvx", "pipx", "bunx")

# A version pin makes that fetch reproducible; its absence does not.
PIN_MARKERS = ("@", "==", "~=", ":")


def capabilities_of(name: str, description: str, input_keys) -> set[str]:
    """Infer capabilities for one tool declaration. Heuristic by construction."""
    lowered_name = (name or "").lower()
    lowered_text = (description or "").lower()
    lowered_keys = {str(key).lower() for key in input_keys or []}

    found: set[str] = set()
    for capability, signals in CAPABILITY_SIGNALS.items():
        if any(marker in lowered_name for marker in signals["name"]):
            found.add(capability)
            continue
        if any(marker in lowered_text for marker in signals["text"]):
            found.add(capability)
            continue
        # Schema keys alone are weak evidence: they count only alongside a verb
        # appropriate to this capability, in either the name or the description.
        if lowered_keys & set(signals["keys"]) and _has_verb(capability, lowered_name, lowered_text):
            found.add(capability)
    return found


def _has_verb(capability: str, name: str, text: str) -> bool:
    verbs = KEY_VERBS.get(capability, [])
    return any(verb in name or verb in text for verb in verbs)


def injection_markers_in(description: str) -> list[str]:
    lowered = (description or "").lower()
    return sorted(marker for marker in INJECTION_MARKERS if marker in lowered)
