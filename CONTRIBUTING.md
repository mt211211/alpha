# Contributing

## One hard rule

**Nothing in `mcpmap` may execute, install, launch, connect to or invoke an MCP
server.** A source returns metadata records; nothing downstream may do anything
else with them. `tests/test_no_execution.py` enforces this structurally and a
pull request that breaks it will not be merged. The reasoning is in
[SECURITY.md](SECURITY.md).

## Disputing a capability label

The most useful contribution is often an argument that we labelled something
wrong. The label set in `mcpmap/data/capability_labels.json` decides the
measured accuracy of the capability inference, which in turn decides how much
weight the published figures can carry.

Open an issue with the tool declaration and the capability set you think is
correct, and why. Label changes are reviewed on the reasoning, not on whether
they improve the score — a label edited to make the heuristic look better is
the one thing that would invalidate the whole instrument.

## Adding a collection source

Implement the `Source` protocol in `mcpmap/sources/base.py`. A source must:

- read only published metadata, and only what the publisher made public
- identify itself in a `User-Agent`
- throttle, and respect a request budget
- cache responses on disk so re-analysis costs the upstream API nothing
- stay within the source's documented terms — if a source's terms prohibit
  automated collection, it does not get added

New sources change the sampling frame, so a source PR should also update the
population and coverage discussion in [docs/METHODOLOGY.md](docs/METHODOLOGY.md).

## Changing the taxonomy

`mcpmap/taxonomy.py` is versioned data. Any change to the signals **must** bump
`TAXONOMY_VERSION`, because figures are only comparable within a version. Run
`mcpmap validate` before and after and put both scores in the PR description.

Beware of overfitting: tuning signals until the shipped 45 labels score
perfectly would mean the labels had been fitted to the model rather than the
other way round. Expanding the label set is the legitimate way to improve
recall.

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

pytest -q
mcpmap validate --min-f1 0.85
python fixtures/build_fixtures.py --check
```

If you change the fixture generator, regenerate the corpus
(`python fixtures/build_fixtures.py`) and commit the result — CI checks that the
committed snapshots still match their generator.

## Style

Standard library first; the runtime dependency list is one package and should
stay short. The analysis path (`digest`, `taxonomy`, `indicators`, `drift`,
`report`, `validate`) is pure: no clock, no network, no hidden state. Keep it
that way — pass `now` explicitly rather than reading the system clock.
