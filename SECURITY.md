# Security policy

## Reporting a vulnerability in mcpmap itself

Open a private security advisory on this repository, or an issue if the problem
is not sensitive. `mcpmap` reads untrusted published metadata, so parsing and
resource-exhaustion issues are in scope and welcome.

## Reporting something mcpmap found

If you believe a published MCP server is actively malicious rather than merely
loosely scoped, **do not open a public issue naming it.** Contact the
maintainers privately and we will follow the coordinated disclosure process in
[docs/ETHICS.md](docs/ETHICS.md): the server's maintainer and the relevant
registry are contacted before anything is published.

## What this tool does not do

`mcpmap` never installs, launches, connects to or invokes an MCP server. It
reads published metadata over public HTTP and treats it as inert data. There is
no subprocess call, package installer or MCP client anywhere in the package.

A pull request that introduces execution of a studied server will not be
merged: it would change what the project is, turn the instrument into an attack
tool, and put its own researchers at risk. A test enforces this
(`tests/test_no_execution.py`).

## Findings are not vulnerability claims

A flag such as `BRIDGE_FS_NET` describes the shape of a published server, not a
compromise. Whether that shape is acceptable depends on deployment context the
instrument cannot see. Please do not report aggregate findings as
vulnerabilities in the servers they describe.
