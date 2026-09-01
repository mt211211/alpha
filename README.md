# The map — an empirical risk study of the public MCP ecosystem

`mcpmap` measures the risk distribution of publicly published Model Context
Protocol servers, and how that distribution **drifts over time**.

Everyone currently reasons about agent tool-server risk by assertion. Ask how
common it is for a published server to be able to both read local files and call
out to the network, or how often a tool's description silently changes after
people have adopted it, and the honest answer today is that nobody has measured
it. This is an instrument for producing those numbers.

**It never runs what it studies.** No MCP server is installed, launched,
connected to or invoked. Published metadata is read over public HTTP and treated
as inert data. See [docs/ETHICS.md](docs/ETHICS.md).

## The two questions

**What does the ecosystem look like?** Capability prevalence, exfiltration
bridges, declared authentication, install exposure, maintenance, injection
markers in tool descriptions.

**How does it move?** Between two snapshots, over the servers present in both:
tool surfaces changed, capabilities expanded, authentication weakened, ownership
transferred, install exposure increased. This is the part that does not exist
elsewhere, and it is the question that could come out either way — if published
surfaces are stable, the rug-pull threat is largely theoretical, and that is a
finding worth having.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# score the capability inference against hand labels
python -m mcpmap validate

# analyse a snapshot, and compare two
python -m mcpmap analyse fixtures/snapshots/2026-09-01-synthetic.json
python -m mcpmap drift  fixtures/snapshots/2026-06-01-synthetic.json \
                        fixtures/snapshots/2026-09-01-synthetic.json

# the full study report
python -m mcpmap report fixtures/snapshots/2026-09-01-synthetic.json \
       --drift-from fixtures/snapshots/2026-06-01-synthetic.json -o report.md

pytest -q
```

Everything above runs offline against the synthetic fixture corpus, so a
reviewer can reproduce every number with only this repository.

### Collecting real data

```bash
export GITHUB_TOKEN=...          # optional, but uses the higher rate limit
python -m mcpmap collect --source github --limit 200 --out snapshots/
python -m mcpmap report snapshots/<new>.json --drift-from snapshots/<older>.json
```

Collection is throttled, request-budgeted and cached on disk. Re-running an
analysis costs the upstream API nothing.

## What it measures

**Risk flags**, computed per server from declared metadata:

| Flag | Meaning |
| --- | --- |
| `BRIDGE_FS_NET` | one server can both read local files and call out |
| `BRIDGE_CRED_NET` | can read credentials and call out |
| `BRIDGE_DB_NET` | can query a database and call out |
| `SHELL_CAPABLE` | declares a tool that executes shell commands |
| `UNAUTH_NETWORK` | declares no authentication and can reach the network |
| `UNPINNED_REMOTE_EXEC` | fetches and runs code from a registry with no version pin |
| `DESCRIPTION_INJECTION_MARKERS` | imperative instructions inside a tool description |
| `UNMAINTAINED` | archived, or no push in a year |
| `NO_LICENSE` | no licence declared |
| `SINGLE_MAINTAINER` | one contributor |

Tool descriptions are fed verbatim into a model's context, which makes a
description an injection surface rather than documentation. That is why
`DESCRIPTION_INJECTION_MARKERS` is measured at population scale.

**Drift events**, computed between snapshots: `SERVER_APPEARED`,
`SERVER_DISAPPEARED`, `TOOL_ADDED`, `TOOL_REMOVED`, `DESCRIPTION_CHANGED`,
`SCHEMA_CHANGED`, `CAPABILITY_EXPANDED`, `CAPABILITY_REDUCED`, `AUTH_WEAKENED`,
`AUTH_STRENGTHENED`, `PUBLISHER_CHANGED`, `INSTALL_RISK_INCREASED`.

## How to read the numbers

Three things are true of every figure this tool produces, and the report says so
on its face:

**Capability figures are lower bounds.** Capabilities are inferred from names,
descriptions and schema keys. The inference is scored against a hand-labelled
set that ships in the repo — precision 0.97, recall 0.79, F1 0.87 at taxonomy
`2026.09.1`. Recall is the weak side, concentrated in `network`, because a tool
called `get_weather` must make a network call but says nothing a keyword model
can see. Run `python -m mcpmap validate` to reproduce the score, including the
list of declarations it gets wrong.

**Two denominators, never conflated.** *Population* is every server observed;
*analysable* is those publishing a machine-readable tool manifest. Capability
and flag shares are reported over the analysable subset only, because counting
"did not declare" as "does not have" is the most likely way a study like this
misleads.

**Drift rates are over the panel.** Only servers present in both snapshots can
be observed to drift. Servers that appear later are excluded from the
denominator rather than diluting it.

Full research design, including threats to validity:
[docs/METHODOLOGY.md](docs/METHODOLOGY.md).

## It measures; it does not judge

A flag is an observation about a published server, not a verdict. Whether
`SHELL_CAPABLE` is acceptable depends on where the server runs, over what data,
under whose supervision — deployment context a population study cannot see.
Keeping measurement separate from judgement is deliberate: it is what makes the
output usable as evidence by people who disagree about policy.

## Layout

```
mcpmap/
  models.py      observed servers and immutable snapshots
  digest.py      canonical form and content digests (drift anchor)
  taxonomy.py    the capability inference model, as versioned data
  indicators.py  per-server risk indicators and flags
  drift.py       snapshot-to-snapshot comparison and panel rates
  validate.py    scores the inference against hand labels
  report.py      aggregation into study output
  corpus.py      immutable snapshot storage with integrity checks
  collect.py     source orchestration
  sources/       fixtures (offline) and github (live, throttled)
  cli.py         command line
fixtures/
  snapshots/     two synthetic snapshots exercising every drift type
  labels/        hand-labelled capability validation set
docs/            methodology and ethics
```

The analysis path is pure — no clock, no network, no hidden state — so the risk
logic can be reviewed and tested without a network or a database.

## Status

Early. The instrument works end to end on synthetic data and against the live
GitHub API; the published findings do not exist yet, because they require
snapshots separated by real time. The next milestones are a baseline collection,
a larger labelled set to lift capability recall, and a second snapshot far
enough out to make the drift rates meaningful.

Contributions, and disputes about individual capability labels, are welcome as
issues.

## Licence

MIT. See [LICENSE](LICENSE).
