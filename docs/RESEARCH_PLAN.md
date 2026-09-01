# Research plan

The instrument in this repository is the starting point, not the study. This
document states what the study would measure, what would count as success, and
what result would falsify the premise.

## The premise, and what would falsify it

**Premise.** Published MCP tool surfaces change under their users after
adoption, often enough and in risky enough directions that pre-adoption review
alone is an inadequate control.

**What would falsify it.** If a year of monthly snapshots shows that published
surfaces are largely static — capability expansion in low single-digit
percentages annually, description changes rare and benign — then the rug-pull
threat is substantially theoretical, continuous monitoring is poor value for
defenders, and effort belongs at initial review instead.

That is a real possible outcome and it is worth publishing. An instrument that
can only confirm its premise is not a measurement instrument.

## Work packages

### WP1 — Coverage and baseline (months 1–3)

Extend collection beyond a single source, establish the sampling frame, and
capture the baseline snapshot.

- Additional sources beyond the GitHub collector, each with its terms position
  documented before it is added
- Written coverage analysis: what the frame includes, what it provably misses
- Baseline snapshot published with its digest

*Acceptance:* a baseline snapshot exists, its coverage is characterised rather
than assumed, and every figure in it is reproducible from the snapshot file.

### WP2 — Capability inference accuracy (months 2–5)

The dependency the whole study rests on. Current measured accuracy at taxonomy
`2026.09.1`: micro precision 0.97, recall 0.79, F1 0.87, over 45 labels.

- Expand the labelled set from 45 to ≥500 declarations
- Two independent labellers with inter-rater agreement reported (Cohen's κ);
  a heuristic scored against labels one person wrote alone is weakly evidenced
- Evaluate whether a trained classifier beats the keyword-and-verb model,
  particularly on `network`, where the residual errors are semantic rather
  than lexical
- Held-out test split, so the reported score is not the tuning score

*Acceptance:* micro F1 ≥ 0.92 and `network` recall ≥ 0.85 on a held-out split,
**or** a documented account of the ceiling and why it was not reached. The
second outcome is a legitimate result: it bounds what metadata-only inference
can do, which is itself worth knowing.

### WP3 — Longitudinal drift (months 3–11)

The novel contribution, and the reason the study is longitudinal.

- Monthly snapshots throughout
- Panel-based rates with confidence intervals
- Replace linear annualisation with survival analysis once ≥3 snapshots exist;
  the current constant-hazard assumption is a two-point simplification
- Characterise *direction*: expansion versus reduction, and whether risky
  changes cluster in identifiable subpopulations (single-maintainer projects,
  unlicensed projects, recently transferred ownership)

*Acceptance:* capability-expansion and description-change rates reported with
intervals, over a panel large enough for the intervals to be informative, and a
stated answer to the premise above.

### WP4 — Publication and adoption (months 9–12)

- Findings report
- Dataset release under the publication policy in [ETHICS.md](ETHICS.md):
  aggregate first, no public naming of individual servers as risky
- Instrument packaged so a third party can reproduce the figures and run their
  own collection

*Acceptance:* an independent party can reproduce the headline figures from the
released snapshots and the pinned taxonomy version.

### WP5 — Ethics, disclosure and governance (continuous)

- Coordinated disclosure for anything that looks actively malicious rather than
  loosely scoped
- Personal-data position reviewed as sources are added
- Dual-use review before each publication: does this release function as a
  target list?

## Threats to the plan

**The panel may be too small or too churny.** If most published servers appear
and disappear within the observation window, the panel shrinks and drift rates
lose power. Mitigation: report panel size prominently; if it is inadequate,
that is a finding about ecosystem volatility, which is itself a risk signal.

**Identity breaks on repository rename or transfer.** Currently recorded as a
disappearance plus an appearance, which understates drift. Mitigation: add
redirect-following to the collector so renames are tracked as continuity.

**Manifest coverage may be too low to analyse.** If very few servers publish
machine-readable tool declarations, the analysable subset may be too small to
support capability figures. Mitigation: report coverage as a headline finding;
if it is low, that *is* the story — an ecosystem that cannot be assessed before
adoption is a governance problem regardless of what the servers do.

**Publication changes the population.** Maintainers may tighten descriptions in
response to the study. Desirable, and a measurement hazard; later snapshots must
be read with the publication date in mind.

## What this study does not attempt

- Observed harm. The instrument measures structural properties of published
  servers, not incidents. A server with `BRIDGE_FS_NET` is not compromised; it
  is shaped so that a compromise has somewhere to go.
- Private or in-house servers. Findings generalise to the published,
  discoverable population only.
- Policy. Whether a property is acceptable depends on deployment context the
  study cannot see. The instrument measures; it does not judge.
