import json

from fastapi.testclient import TestClient

from conftest import PACKS, correct_answer
from tutor.api import create_app
from tutor.graders import grade, parse_fraction
from tutor.validate import validate


def test_fraction_grader_forms():
    it = {"type": "fraction", "answer": "3/4", "form": "simplest"}
    assert grade(it, "3/4").score == 1
    assert grade(it, " 3 / 4 ").score == 1
    assert grade(it, "6/8").score == 0.5
    assert grade(it, "0.75").score == 0.5
    assert grade(it, "2/3").score == 0
    assert grade(it, "abc").score == 0
    imp = {"type": "fraction", "answer": "13/5", "form": "improper"}
    assert grade(imp, "13/5").score == 1 and grade(imp, "2 3/5").score == 0.5
    assert parse_fraction("1 1/2")[0] == parse_fraction("3/2")[0]
    assert grade({"type": "fraction", "answer": "12"}, "12").score == 1


def test_text_grader_unicode():
    it = {"type": "text", "accepted": ["नाज़ुक"]}
    assert grade(it, " नाज़ुक। ").score == 1
    assert grade({"type": "text", "accepted": ["Abundant"]}, "abundant.").score == 1


def test_code_grader():
    it = {"type": "code_python", "preamble": "", "tests": ["assert add(1, 2) == 3", "assert add(-1, 1) == 0"]}
    assert grade(it, "def add(a, b):\n    return a + b").score == 1
    r = grade(it, "def add(a, b):\n    return a + b if a > 0 else 99")   # passes only add(1, 2)
    assert r.score == 0.5 and "1/2 tests passed" in r.feedback
    r = grade(it, "def add(a, b) return")
    assert r.score == 0 and "SyntaxError" in r.feedback
    r = grade(it, "while True:\n    pass")
    assert r.score == 0 and "too long" in r.feedback


def test_free_text_offline():
    it = {"type": "free_text", "prompt": "Use 'vivid'", "rubric": "uses vivid", "keywords": ["vivid"], "min_words": 5}
    r = grade(it, "The painting had vivid colours everywhere")
    assert r.score >= 0.7 and r.needs_review
    assert grade(it, "I like pizza a lot today").score < 0.7


def test_shipped_packs_valid():
    for p in PACKS.glob("*.json"):
        errors, _ = validate(json.loads(p.read_text()))
        assert not errors, (p.name, errors)


def test_validator_catches_problems():
    data = json.loads((PACKS / "ds_linked_lists.json").read_text())
    data["item_sets"]["A1.2.R.1"]["links"] = ["A1.2.Ap.1"]       # cycle
    data["item_sets"]["A1.2.U.1"]["items"][0]["answer"] = "nope"  # bad key
    data["item_sets"]["A1.2.Ap.1"]["items"][0]["solution"] = "def insert_at_end(h, d):\n    return h"
    errors, _ = validate(data)
    msg = "\n".join(errors)
    assert "cycle" in msg and "not one of the options" in msg and "fails its own tests" in msg


def test_api_flow(tmp_path):
    app = create_app(PACKS, str(tmp_path / "api.db"))
    c = TestClient(app)
    packs = c.get("/api/packs").json()
    assert {p["id"] for p in packs} == {"ds_linked_lists", "english_vocab", "math_fractions"}
    a = c.get("/api/session/Asha/math_fractions").json()
    assert a["type"] == "activity"
    a = c.post("/api/session/Asha/math_fractions/continue").json()
    assert a["type"] == "item" and "answer" not in a
    eng = app.state.engine
    item = eng.packs["math_fractions"].item(a["set_id"], a["item_id"])
    r = c.post("/api/session/Asha/math_fractions/answer", json={"response": correct_answer(item)}).json()
    assert r["result"]["passed"] is True
    r = c.post("/api/session/Asha/math_fractions/answer", json={"response": "999/1"}).json()
    assert r["result"]["passed"] is False and "answer" in r["result"]
    sessions = c.get("/api/teacher/sessions").json()
    assert sessions[0]["student"] == "Asha" and sessions[0]["attempts"] == 2
    d = c.get("/api/teacher/sessions/Asha/math_fractions").json()
    assert d["summary"]["strategy"] == "prereq_graph" and len(d["attempts"]) == 2
    assert c.get("/api/packs/nope").status_code == 404
    assert c.get("/").status_code == 200 and c.get("/teacher").status_code == 200


def test_draft_pack_hidden_and_approval_requires_valid(tmp_path):
    packs_dir = tmp_path / "packs"
    packs_dir.mkdir()
    data = json.loads((PACKS / "english_vocab.json").read_text())
    data.update(id="draft_vocab", status="draft")
    data["item_sets"]["W_BRIEF"]["items"][0]["answer"] = "not an option"
    (packs_dir / "draft_vocab.json").write_text(json.dumps(data))
    c = TestClient(create_app(packs_dir, str(tmp_path / "d.db")))
    assert c.get("/api/session/x/draft_vocab").status_code == 404
    assert c.post("/api/packs/draft_vocab/approve", json={"approved": True}).status_code == 400
    data["item_sets"]["W_BRIEF"]["items"][0]["answer"] = data["item_sets"]["W_BRIEF"]["items"][0]["options"][0]
    (packs_dir / "draft_vocab.json").write_text(json.dumps(data))
    c.post("/api/packs/reload")
    assert c.post("/api/packs/draft_vocab/approve", json={"approved": True}).json()["status"] == "approved"
    assert c.get("/api/session/x/draft_vocab").status_code == 200
    assert json.loads((packs_dir / "draft_vocab.json").read_text())["status"] == "approved"
