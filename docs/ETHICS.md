# Collection ethics and publication policy

## The property that matters

**This software never executes what it studies.** It does not install, launch,
connect to, invoke, or clone an MCP server. It reads published metadata over
public HTTP and treats it as inert data.

This is enforced by construction rather than by policy: there is no subprocess
call, no package installer, and no MCP client anywhere in the package. A source
returns metadata records (`mcpmap/sources/base.py`) and nothing downstream can
do anything else with them. Any change that introduces execution would be a
change to the project's purpose, not an implementation detail.

The reason is straightforward. A study of potentially malicious tool servers
that ran them would be a study that compromised its own researchers, and a tool
that others could point at arbitrary servers would be an attack instrument.

## What is collected

Only what a publisher has already made public:

- repository metadata — name, owner, description, stars, licence, timestamps,
  archived status, topics
- machine-readable server manifests where published — tool names, descriptions,
  input schema keys, declared auth, install command

## What is deliberately not collected

- Repository contents beyond named manifest paths. No cloning, no code corpus.
- Contributor identities, email addresses, or commit authorship.
- Anything behind authentication, a paywall, or an access control.
- Any private, internal or non-published server.

## Collection conduct

- **Identified.** Requests carry a `User-Agent` naming the project and its
  repository, so an operator seeing our traffic can find out who we are.
- **Throttled.** A minimum interval between requests, defaulting to one second.
- **Budgeted.** A hard request cap per run (default 300), so a mistake cannot
  become a crawl.
- **Cached.** Responses are cached on disk; re-analysis costs the upstream API
  nothing.
- **Authenticated where possible.** Running with a `GITHUB_TOKEN` uses the
  higher documented rate limit rather than competing for the anonymous pool.

Collection stays within documented public API terms. Where a source's terms
prohibit automated collection, that source is not added.

## Personal data

Publisher handles are personal data under UK GDPR when they identify an
individual. They are collected because provenance is load-bearing for a supply
chain study — "who published this" is a risk signal, not decoration.

Handling: handles are retained in snapshots because reproducibility requires it;
published outputs report aggregate distributions (for example the share of
servers published by individuals rather than organisations) and do not single
out individuals. Contributor identities are not collected at all.

## Dual use, and how findings are published

A map of which published servers carry risky properties is useful to a defender
choosing what to adopt, and useful to an attacker choosing what to target. This
is a real tension and it cannot be resolved by pretending otherwise.

The publication policy that follows from it:

1. **Aggregate first.** Population-level distributions and drift rates are the
   research output. They inform defenders without functioning as a target list.
2. **No public naming of individual servers as risky** in study outputs. The
   report names event types and counts; per-server detail stays in the local
   snapshot for the researcher who collected it.
3. **Coordinated disclosure.** Where analysis suggests a specific server is
   actively malicious rather than merely loosely scoped — for example injection
   markers in a tool description that appear designed to hijack an agent — the
   maintainer and the relevant registry are contacted before anything is
   published, on a standard disclosure timeline.
4. **Structural properties are not vulnerability claims.** A flag such as
   `BRIDGE_FS_NET` describes shape, not compromise. Outputs say so, and the
   distinction is kept in the tool itself: `mcpmap` measures, it does not judge.

## Reporting a concern

If you maintain a server that appears in a snapshot and want its metadata
excluded, or you believe collection has behaved improperly, open an issue on
this repository.
