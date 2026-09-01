"""The property the whole project rests on: mcpmap never runs what it studies.

This is asserted structurally rather than trusted. A study of potentially
malicious tool servers that executed them would compromise its own researchers,
and a tool others could point at arbitrary servers would be an attack
instrument. So the absence of any execution path is a test, not a promise in a
document -- and a pull request that adds one fails CI.
"""

from __future__ import annotations

import ast
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1] / "mcpmap"

# Modules that can start a process, install code, or open a shell.
FORBIDDEN_MODULES = {
    "subprocess", "multiprocessing", "pty", "pexpect", "shlex",
    "pip", "setuptools", "venv", "importlib.util", "runpy", "ctypes",
    "docker", "mcp", "asyncio.subprocess",
}

# Builtins that execute or dynamically load code.
FORBIDDEN_CALLS = {"eval", "exec", "compile", "__import__"}

# os functions that spawn.
FORBIDDEN_OS_ATTRS = {
    "system", "popen", "execv", "execve", "execvp", "execl", "execlp",
    "spawnv", "spawnve", "spawnl", "fork", "forkpty", "posix_spawn",
}


def source_files():
    return sorted(PACKAGE.rglob("*.py"))


def test_the_package_has_source_to_check():
    assert len(source_files()) >= 10


def test_no_process_spawning_or_code_loading_imports():
    offenders = []
    for path in source_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in FORBIDDEN_MODULES or alias.name in FORBIDDEN_MODULES:
                        offenders.append(f"{path.name}:{node.lineno} import {alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                root = node.module.split(".")[0]
                if root in FORBIDDEN_MODULES or node.module in FORBIDDEN_MODULES:
                    offenders.append(f"{path.name}:{node.lineno} from {node.module}")
    assert not offenders, "mcpmap must never gain an execution path: " + "; ".join(offenders)


def test_no_dynamic_code_execution_calls():
    offenders = []
    for path in source_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Name) and func.id in FORBIDDEN_CALLS:
                offenders.append(f"{path.name}:{node.lineno} {func.id}()")
            elif isinstance(func, ast.Attribute) and func.attr in FORBIDDEN_OS_ATTRS:
                offenders.append(f"{path.name}:{node.lineno} .{func.attr}()")
    assert not offenders, "dynamic execution is not permitted in mcpmap: " + "; ".join(offenders)


def test_the_only_outbound_http_lives_in_a_source_module():
    """Network access is confined to sources/, so the analysis path stays pure."""
    offenders = []
    for path in source_files():
        if path.parent.name == "sources":
            continue
        text = path.read_text(encoding="utf-8")
        for marker in ("httpx", "urllib.request", "requests.", "socket."):
            if marker in text:
                offenders.append(f"{path.relative_to(PACKAGE)} mentions {marker}")
    assert not offenders, (
        "the analysis path must run offline; network access belongs in mcpmap/sources/: "
        + "; ".join(offenders)
    )


def test_sources_declare_no_install_or_launch_helpers():
    """A source returns metadata records. It must not fetch-and-run anything."""
    banned = ("npm install", "npx ", "pip install", "docker run", "uvx ")
    offenders = []
    for path in (PACKAGE / "sources").rglob("*.py"):
        text = path.read_text(encoding="utf-8").lower()
        for phrase in banned:
            # The taxonomy names these installers as data to classify; a source
            # module has no business containing them at all.
            if phrase in text:
                offenders.append(f"{path.name} contains {phrase!r}")
    assert not offenders, "; ".join(offenders)
