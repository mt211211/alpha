from mcpmap.validate import evaluate, load_labels


def test_shipped_labels_load():
    labels = load_labels()
    assert len(labels) >= 40
    assert all("name" in item and "capabilities" in item for item in labels)


def test_perfect_prediction_scores_one():
    labels = [{"name": "run_command", "description": "Execute a shell command", "input_keys": ["command"],
               "capabilities": ["shell"]}]
    result = evaluate(labels)
    assert result["micro"]["precision"] == 1.0
    assert result["micro"]["recall"] == 1.0
    assert result["disagreements"] == []


def test_a_missed_capability_is_counted_as_a_false_negative():
    labels = [{"name": "healthcheck", "description": "Return ok", "input_keys": [],
               "capabilities": ["network"]}]
    result = evaluate(labels)
    assert result["micro"]["fn"] == 1
    assert result["disagreements"][0]["missed"] == ["network"]


def test_shipped_label_set_is_scored_and_imperfect():
    result = evaluate()
    # An inference over prose that scored perfectly on its own labels would mean
    # the labels were written to fit it.
    assert 0.5 < result["micro"]["f1"] < 1.0
    assert result["disagreements"]


def test_every_capability_is_covered_by_the_label_set():
    from mcpmap.taxonomy import CAPABILITY_SIGNALS

    labelled = {cap for item in load_labels() for cap in item["capabilities"]}
    assert labelled == set(CAPABILITY_SIGNALS)
