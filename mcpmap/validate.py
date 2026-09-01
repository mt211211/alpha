"""Measure the accuracy of the capability inference against hand labels.

This is what separates a measurement study from a script. The inference in
taxonomy.py is a heuristic over prose; if it is wrong, every capability figure
in the report is wrong by the same amount. So the heuristic is scored against a
hand-labelled set, the score is published with the results, and the label set
ships in the repository so anyone can re-score it or dispute a label.

Pure functions apart from reading the label file.
"""

from __future__ import annotations

import json
from pathlib import Path

from mcpmap.taxonomy import CAPABILITY_SIGNALS, TAXONOMY_VERSION, capabilities_of

LABELS_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "labels" / "capability_labels.json"


def load_labels(path=None) -> list[dict]:
    payload = json.loads(Path(path or LABELS_PATH).read_text(encoding="utf-8"))
    return payload["labels"] if isinstance(payload, dict) else payload


def _scores(true_positive: int, false_positive: int, false_negative: int) -> dict:
    precision = true_positive / (true_positive + false_positive) if (true_positive + false_positive) else None
    recall = true_positive / (true_positive + false_negative) if (true_positive + false_negative) else None
    if precision and recall:
        f1 = 2 * precision * recall / (precision + recall)
    else:
        f1 = 0.0 if (precision is not None and recall is not None) else None
    return {
        "tp": true_positive,
        "fp": false_positive,
        "fn": false_negative,
        "precision": round(precision, 4) if precision is not None else None,
        "recall": round(recall, 4) if recall is not None else None,
        "f1": round(f1, 4) if f1 is not None else None,
    }


def evaluate(labels=None) -> dict:
    """Score the capability inference. Returns per-capability and micro totals."""
    labels = labels if labels is not None else load_labels()
    per_capability = {
        capability: {"tp": 0, "fp": 0, "fn": 0} for capability in CAPABILITY_SIGNALS
    }
    disagreements: list[dict] = []

    for item in labels:
        expected = set(item.get("capabilities") or [])
        predicted = capabilities_of(
            item.get("name", ""), item.get("description", ""), item.get("input_keys") or []
        )
        for capability in CAPABILITY_SIGNALS:
            in_expected = capability in expected
            in_predicted = capability in predicted
            if in_expected and in_predicted:
                per_capability[capability]["tp"] += 1
            elif in_predicted and not in_expected:
                per_capability[capability]["fp"] += 1
            elif in_expected and not in_predicted:
                per_capability[capability]["fn"] += 1
        if expected != predicted:
            disagreements.append(
                {
                    "name": item.get("name", ""),
                    "expected": sorted(expected),
                    "predicted": sorted(predicted),
                    "missed": sorted(expected - predicted),
                    "spurious": sorted(predicted - expected),
                }
            )

    scored = {
        capability: _scores(counts["tp"], counts["fp"], counts["fn"])
        for capability, counts in per_capability.items()
    }
    micro = _scores(
        sum(counts["tp"] for counts in per_capability.values()),
        sum(counts["fp"] for counts in per_capability.values()),
        sum(counts["fn"] for counts in per_capability.values()),
    )
    exact = sum(1 for item in labels if set(item.get("capabilities") or []) ==
                capabilities_of(item.get("name", ""), item.get("description", ""),
                                item.get("input_keys") or []))

    return {
        "taxonomy_version": TAXONOMY_VERSION,
        "labelled_tools": len(labels),
        "exact_match": exact,
        "exact_match_share": round(exact / len(labels), 4) if labels else 0.0,
        "micro": micro,
        "per_capability": scored,
        "disagreements": disagreements,
    }


def to_markdown(result: dict) -> str:
    lines = [
        "# Capability inference accuracy",
        "",
        f"- Taxonomy version: `{result['taxonomy_version']}`",
        f"- Hand-labelled tool declarations: {result['labelled_tools']}",
        f"- Exact set match: {result['exact_match']}/{result['labelled_tools']} "
        f"({result['exact_match_share'] * 100:.1f}%)",
        "",
        "## Micro-averaged",
        "",
        f"Precision {result['micro']['precision']} · recall {result['micro']['recall']} "
        f"· F1 {result['micro']['f1']}",
        "",
        "## Per capability",
        "",
        "| Capability | TP | FP | FN | Precision | Recall | F1 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for capability, scores in sorted(result["per_capability"].items()):
        lines.append(
            f"| `{capability}` | {scores['tp']} | {scores['fp']} | {scores['fn']} | "
            f"{scores['precision']} | {scores['recall']} | {scores['f1']} |"
        )
    lines.append("")
    if result["disagreements"]:
        lines += ["## Disagreements", "", "| Tool | Missed | Spurious |", "| --- | --- | --- |"]
        for item in result["disagreements"]:
            lines.append(
                f"| `{item['name']}` | {', '.join(item['missed']) or '—'} | "
                f"{', '.join(item['spurious']) or '—'} |"
            )
        lines.append("")
    return "\n".join(lines)
