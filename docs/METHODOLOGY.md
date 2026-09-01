# Methodology

## Research questions

**RQ1 — Distribution.** What is the risk distribution of publicly published MCP
servers, measured from their published metadata?

**RQ2 — Drift.** How does that distribution change over time? Specifically: how
often does a published tool surface change under its users after publication,
in what direction, and how often does a change expand capability, weaken
authentication, or transfer ownership?

RQ2 is the part that does not exist elsewhere and the reason the study is
longitudinal rather than a one-off scan. It is also the question with an answer
that could come out either way: if published tool surfaces turn out to be
stable, the rug-pull threat is largely theoretical and defensive effort belongs
elsewhere. That is a finding, and the instrument is built so it can produce it.

## Population and sampling frame

The target population is *MCP servers whose existence and metadata are
published*. That is not the same as "MCP servers in use", and the gap matters:

- Servers published only inside organisations are invisible to us.
- Servers distributed as packages without a public repository are under-covered.
- Discovery depends on how a server is labelled, so servers that do not use
  conventional topics or naming are under-sampled.

The sampling frame is therefore *published, discoverable* servers, and every
figure should be read against that frame. Coverage is reported in each snapshot
rather than assumed.

## Identity across snapshots

Longitudinal measurement lives or dies on stable identity. A record's `key` is
`<source>:<namespace>/<name>` — for the GitHub source, the repository full name.

This choice has known failure modes, and they bias in a specific direction:

- A repository **rename or transfer** breaks the key, and the server is recorded
  as one disappearance plus one appearance rather than as continuity. This
  *understates* drift, and `PUBLISHER_CHANGED` only catches transfers that keep
  the repository path.
- A **fork** presents as a distinct server, which is usually correct for risk
  purposes (a fork is a different supply chain) but inflates population counts.

Where drift rates are reported, they are therefore lower bounds.

## What is declared versus what is inferred

Two very different kinds of evidence, kept separate throughout:

| Kind | Examples | Confidence |
| --- | --- | --- |
| **Declared** | tool names, tool descriptions, input schema keys, declared auth type, install command, licence, push dates | high — read directly from published metadata |
| **Inferred** | capabilities (`filesystem_read`, `network`, …), bridges, install exposure class | measured — see below |

Field names preserve the distinction: `auth_declared`, not `auth`.

## Capability inference and its accuracy

Published MCP metadata almost never declares capabilities. It declares tool
names, prose descriptions and schema keys. Capability is inferred from those by
a keyword-and-verb model held as versioned data in `mcpmap/taxonomy.py`, so that
it is inspectable and citable rather than buried in code.

The inference is scored against a hand-labelled set of 45 tool declarations that
ships in `mcpmap/data/capability_labels.json`. At taxonomy `2026.09.1`:

| Measure | Value |
| --- | --- |
| Micro precision | 0.97 |
| Micro recall | 0.79 |
| Micro F1 | 0.87 |
| Exact capability-set match | 78% |

Reproduce with `python -m mcpmap validate`.

**The asymmetry is deliberate and it matters for reading the results.** Precision
is high, recall is lower, and the residual errors are concentrated in `network`
(recall 0.62). The misses are semantic rather than lexical: a tool called
`get_weather` described as "return the current weather forecast for a city" must
make a network call, but says nothing a keyword model can see. No amount of
keyword tuning fixes that class of miss, and tuning against our own 45 labels
until it did would be overfitting to the label set rather than improving the
instrument.

The consequence, stated plainly: **capability prevalence figures are lower
bounds, and `network` prevalence is the loosest of them.** Bridge counts, which
require `network`, are lower bounds for the same reason. Reducing this bound is
the main methodological work a funded phase would take on — most plausibly by
replacing keyword matching with a classifier scored against a much larger
labelled set.

## Denominators

Two denominators are reported and never conflated:

- **population** — every server observed.
- **analysable** — servers that publish a machine-readable tool manifest.

Capability and flag prevalence can only be computed over the analysable subset.
Reporting them against the population would count "did not declare" as "does not
have", which is the single most likely way a study of this kind misleads. That
most servers publish no manifest at all is itself a headline finding, reported
as manifest coverage in every snapshot.

## Drift measurement

Drift is computed between two snapshots over the **panel** — servers present in
both. A server first observed in the later snapshot cannot have been observed to
drift, and including it in the denominator would dilute every rate.

Event types are listed in `mcpmap/drift.py`. Rates are reported three ways:
raw counts, share of panel, and an annualised share (linearly scaled by the
observation window and capped at 1.0). The annualisation assumes a constant
hazard rate, which is a simplification; with more than two snapshots it should
be replaced by survival analysis, and the instrument stores snapshots in a form
that supports that.

A server that changes twice between snapshots counts once. Sub-window changes
that revert before the later snapshot are invisible. Both understate drift.

## Threats to validity

**Construct validity.** "Risk" here is a set of structural properties of a
published server, not observed harm. A server with `BRIDGE_FS_NET` is not
compromised; it is shaped such that a compromise has somewhere to go. The
instrument deliberately measures and does not judge: whether a property is
acceptable depends on deployment context, which a population study cannot see.

**Internal validity.** Capability inference is imperfect and measured (above).
Injection-marker detection is a fixed pattern list and will miss novel phrasings.
Install-exposure classification depends on manifests that most servers do not
publish.

**External validity.** Findings generalise to published, discoverable servers.
They should not be extended to servers deployed inside organisations, which are
plausibly a different population — likely better maintained and more narrowly
scoped, so ecosystem figures are probably an upper bound on in-house risk.

**Reactivity.** Publishing this study may change the thing it measures, by
prompting maintainers to add manifests or tighten descriptions. That is a
desirable outcome and a measurement hazard at the same time; later snapshots
should be read with the publication date in mind.

## Reproducibility

- Snapshots are immutable JSON, refuse to overwrite, and carry a content digest
  checked on load.
- Every figure is reproducible from a snapshot file plus a taxonomy version,
  with no network access.
- The analysis path (`analyse`, `drift`, `report`, `validate`) is pure: no
  clock, no network, no hidden state. Ages take an explicit `--now`.
- Collection is cached on disk, so a re-run neither re-fetches nor re-bills the
  upstream API.
