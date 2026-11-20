"""Inquiry pedagogy: episodes run before scoring, predictions are revisited, wrong answers
get misconception probes / hints and a retry of the same item before the strategy remediates."""
import json

from conftest import PACKS, correct_answer
from tutor.validate import validate

S, P = "kid", "math_fractions"


def walk_episode(engine, answers=None):
    """Go through episode steps until a scored item appears. Returns (item_action, steps)."""
    answers = answers or {}
    steps = []
    a = engine.action(S, P)
    while a["type"] != "item":
        steps.append(a)
        if a["type"] in ("prompt", "explore"):
            a = engine.answer(S, P, answers.get(a.get("phase"), "I think the pieces stay the same size"))["action"]
        else:
            a = engine.acknowledge(S, P)
    return a, steps


def test_episode_runs_before_any_scored_question(engine):
    item, steps = walk_episode(engine, {"predict": "5/16 — because 8 + 8"})
    kinds = [(s["type"], s.get("phase")) for s in steps]
    assert kinds[:6] == [("message", None), ("prompt", "elicit"), ("prompt", "predict"), ("explore", "explore"),
                         ("prompt", "probe"), ("prompt", "probe")]
    explore = next(s for s in steps if s["type"] == "explore")
    assert explore["tool"] == "fraction_strips" and explore["record"]
    explain = next(s for s in steps if s["type"] == "explain")
    assert "5/16 — because 8 + 8" in explain["revisit"]          # the student's own prediction is revisited
    assert [s["type"] for s in steps].index("explain") > [s.get("phase") for s in steps].index("probe")
    assert steps[-1]["type"] == "connect" and steps[-1]["key_learning"]
    assert item["set_id"] == "F_ADD_LIKE"
    rows = engine.store.responses(S, P)
    assert {r["phase"] for r in rows} >= {"elicit", "predict", "explore", "probe"}


def test_misconception_probe_then_retry_same_item(engine):
    item_a, _ = walk_episode(engine)
    item = engine.packs[P].item(item_a["set_id"], item_a["item_id"])
    mc = item["misconceptions"][0]
    wrong = (mc.get("values") or mc.get("responses"))[0]
    r = engine.answer(S, P, wrong)
    assert r["result"]["retry"] and r["result"]["probe"]["kind"] == "misconception"
    assert "{response}" not in r["result"]["probe"]["text"]
    assert r["action"]["type"] == "item" and r["action"]["item_id"] == item_a["item_id"]   # same item again
    # the strategy has not remediated yet
    kinds = [e["kind"] for e in engine.store.events(S, P)]
    assert "misconception" in kinds and "diagnose" not in kinds
    counts = engine.store.misconception_counts(P)
    assert counts[0]["misconception"] == mc["id"] and counts[0]["students"] == [S]
    # then the correct answer is accepted as an assisted success
    r = engine.answer(S, P, correct_answer(item))
    assert r["result"]["passed"] and r["result"]["assisted"]


def test_hint_ladder_exhausted_then_strategy_remediates(engine):
    item_a, _ = walk_episode(engine)
    item = engine.packs[P].item(item_a["set_id"], item_a["item_id"])
    rungs = []
    for _ in range(5):
        r = engine.answer(S, P, "999/1")
        if not r["result"].get("retry"):
            break
        rungs.append(r["result"]["probe"])
    assert [x["kind"] for x in rungs] == ["hint"] * len(item["hints"])
    assert r["result"]["passed"] is False and r["result"].get("explanation")      # worked example last
    kinds = [e["kind"] for e in engine.store.events(S, P)]
    assert "diagnose" in kinds                                                      # now the strategy steps in


def test_diagnostic_probes_get_no_hints(engine):
    item_a, _ = walk_episode(engine)
    for _ in range(3):
        r = engine.answer(S, P, "999/1")
    # walk to the first prerequisite probe question
    a = r["action"]
    while a["type"] != "item":
        a = engine.acknowledge(S, P) if a["type"] not in ("prompt", "explore") else engine.answer(S, P, "x")["action"]
    assert a["set_id"] in ("F_MEANING", "F_SIMPLIFY")
    r = engine.answer(S, P, "999/1")
    assert not r["result"].get("retry")                  # a wrong check = a gap, not a hint


def test_short_answer_gets_authored_followup_offline(engine):
    a = engine.action(S, P)
    while not (a["type"] == "prompt" and a.get("phase") == "probe" and "bottom number stay" in a["prompt"]):
        a = engine.answer(S, P, "some thoughts here about it")["action"] if a["type"] in ("prompt", "explore") \
            else engine.acknowledge(S, P)
    r = engine.answer(S, P, "dunno")
    assert r["action"]["type"] == "prompt" and r["action"]["is_followup"]
    assert "size of each piece" in r["action"]["prompt"]


def test_vocab_guess_from_context_then_revisit(engine):
    a = engine.action("v", "english_vocab")
    assert a["type"] == "explore" and a["tool"] == "context_sentences" and len(a["sentences"]) == 3
    r = engine.answer("v", "english_vocab", "something there is a lot of")
    a = r["action"]
    assert a["type"] == "prompt" and a["phase"] == "probe"
    a = engine.answer("v", "english_vocab", "the word 'so much' and the rains filled the well")["action"]
    assert a["type"] == "explain" and "something there is a lot of" in a["revisit"]


def test_validator_checks_episodes():
    data = json.loads((PACKS / "math_fractions.json").read_text())
    ep = data["item_sets"]["F_ADD_LIKE"]["episode"]
    ep["explore"]["tool"] = "hologram"
    ep["explain"]["activity"] = "NOPE"
    data["item_sets"]["F_ADD_LIKE"]["items"][0]["misconceptions"][0]["values"] = ["banana"]
    errors, _ = validate(data)
    msg = "\n".join(errors)
    assert "unknown explore tool" in msg and "explain activity" in msg and "not a number" in msg
