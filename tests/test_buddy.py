"""Science Buddy: tested with a scripted fake LLM (no API calls). These check the code around the AI —
consent, guardrails, assessment records, focus-skill choice, memory across sessions — not the AI's teaching."""
import pytest
from fastapi.testclient import TestClient

from conftest import PACKS, FakeClock
from tutor.api import create_app
from tutor.buddy.engine import Buddy, ConsentRequired
from tutor.buddy.prompt import build_system
from tutor.buddy.skills import choose_focus
from tutor.store import Store


class FakeLLM:
    demo = False

    def __init__(self, outputs=None):
        self.outputs = list(outputs or [])
        self.calls = []

    def respond(self, system, messages):
        self.calls.append((system, messages))
        return self.outputs.pop(0) if self.outputs else {"reply": "What exactly did you see?"}


@pytest.fixture
def mk(tmp_path):
    def make(outputs=None, clock=None):
        llm = FakeLLM(outputs)
        b = Buddy(Store(str(tmp_path / "b.db")), llm=llm, clock=clock or FakeClock())
        return b, llm
    return make


def consented(b, name="Asha", grade=7):
    b.give_consent(name, "Lakshmi", "Mother", grade)


def test_consent_required_before_anything_is_stored(mk):
    b, llm = mk()
    with pytest.raises(ConsentRequired):
        b.start("Asha")
    with pytest.raises(ConsentRequired):
        b.message("Asha", "hello")
    assert llm.calls == [] and b.learners() == []
    with pytest.raises(ValueError):
        b.give_consent("Asha", "", "Mother")


def test_turn_records_evidence_and_initial_placement(mk):
    b, llm = mk([{"reply": "Hi Asha! Seen anything interesting today?"},
                 {"reply": "Ooh. What exactly does the drooping look like?",
                  "evidence": [{"skill": "observing", "quote": "tulsi on the balcony is drooping", "signal": "developing"}],
                  "inquiry": {"title": "Drooping tulsi", "stage": "observe", "chapters": ["g7c10", "bogus"]}}])
    consented(b)
    v = b.start("Asha")
    assert v["turns"][0]["text"].startswith("Hi Asha")
    b.message("Asha", "My mum's tulsi on the balcony is drooping but the one inside isn't")
    p = b.profile("Asha")
    obs = p["skills"]["observing"]
    assert obs["assessed"] and obs["level"] == "developing" and obs["history"][0]["reason"].startswith("Initial")
    assert p["inquiries"][0]["title"] == "Drooping tulsi" and p["inquiries"][0]["chapters"] == ["g7c10"]


def test_level_changes_one_step_with_reason_and_plain_words(mk):
    b, _ = mk([{"reply": "Hi!"},
               {"reply": "Nice.", "evidence": [{"skill": "controlling_variables", "quote": "change only the sun", "signal": "emerging"}]},
               {"reply": "Great plan.", "level_changes": [{"skill": "controlling_variables", "to": "independent",
                                                           "reason": "Said what stays the same before being asked",
                                                           "plain_words": "You planned a fair test on your own."}]}])
    consented(b)
    b.start("Asha"); b.message("Asha", "I could change only the sun"); b.message("Asha", "the pot stays the same and the water")
    cv = b.profile("Asha")["skills"]["controlling_variables"]
    assert cv["level"] == "developing"                       # clamped: one level at a time
    assert cv["history"][-1]["reason"] == "Said what stays the same before being asked"
    assert b.progress("Asha")["achievements"][0]["text"] == "You planned a fair test on your own."


def test_evidence_keeps_last_two(mk):
    outs = [{"reply": "Hi"}] + [{"reply": "Mm?", "evidence": [{"skill": "observing", "quote": f"q{i}", "signal": "emerging"}]}
                                for i in range(4)]
    b, _ = mk(outs)
    consented(b)
    b.start("Asha")
    for i in range(4):
        b.message("Asha", f"report {i}")
    ev = b.profile("Asha")["skills"]["observing"]["evidence"]
    assert [e["quote"] for e in ev] == ["q2", "q3"]


def test_unsafe_reply_is_regenerated_then_falls_back(mk):
    b, llm = mk([{"reply": "Hi"}, {"reply": "Light a candle and watch the shadow move."},
                 {"reply": "Use a torch instead. What happens to the shadow?"}])
    consented(b)
    b.start("Asha")
    v = b.message("Asha", "I want to make shadows")
    assert v["turns"][-1]["text"] == "Use a torch instead. What happens to the shadow?"
    assert "blocked" in llm.calls[-1][1][-1]["content"]
    b2, _ = mk([{"reply": "Hi"}, {"reply": "Taste the salt water!"}, {"reply": "Then lick the spoon."}])
    consented(b2, "Ravi")
    b2.start("Ravi")
    assert "safer way" in b2.message("Ravi", "what now")["turns"][-1]["text"]


def test_claiming_to_be_human_is_blocked(mk):
    b, _ = mk([{"reply": "Hi"}, {"reply": "Yes, I'm a real person!"}, {"reply": "No, I'm an AI science buddy. But I love your questions!"}])
    consented(b)
    b.start("Asha")
    assert "AI science buddy" in b.message("Asha", "are you a real person?")["turns"][-1]["text"]


def test_one_question_per_turn(mk):
    b, _ = mk([{"reply": "Hi"}, {"reply": "Ooh! What colour was it? And how big?"}])
    consented(b)
    b.start("Asha")
    assert b.message("Asha", "I saw a bug")["turns"][-1]["text"] == "Ooh! What colour was it?"


def test_wellbeing_disclosure_flagged_by_code_and_by_ai(mk):
    b, _ = mk([{"reply": "Hi"}, {"reply": "I'm sorry that happened. Please tell your teacher or a parent today."},
               {"reply": "Thanks for telling me.", "wellbeing_concern": "Child says they feel unsafe at home"}])
    consented(b)
    b.start("Asha")
    b.message("Asha", "the big boys bully me at school")
    b.message("Asha", "something happened at home")
    al = [a for a in b.store.alerts() if a["kind"] == "wellbeing"]
    turns = b.teacher_view("Asha")["sessions"][0]["turns"]
    assert "teacher or a parent" in [t for t in turns if t["role"] == "tutor"][1]["text"]
    assert len(al) == 2 and any("bully" in a["details"]["excerpt"] for a in al)
    assert any("unsafe at home" in a["message"] for a in al)


def test_missed_disclosure_gets_care_reply_and_no_assessment(mk):
    b, _ = mk([{"reply": "Hi"}, {"reply": "Interesting! What did you notice?",
                                 "evidence": [{"skill": "observing", "quote": "x", "signal": "developing"}]}])
    consented(b)
    b.start("Asha")
    v = b.message("Asha", "my uncle hits me")
    assert "grown-up you trust" in v["turns"][-1]["text"]
    assert not b.profile("Asha")["skills"]["observing"]["assessed"]


def test_personal_details_redacted(mk):
    b, llm = mk()
    consented(b)
    b.start("Asha")
    b.message("Asha", "my number is 98450 12345")
    turns = b.teacher_view("Asha")["sessions"][0]["turns"]
    assert all("98450" not in t["text"] for t in turns)
    assert "98450" not in str(llm.calls[-1][1])


def test_focus_skill_choice():
    base = {s: "emerging" for s in ["observing"]}
    assert choose_focus(base) == "observing"                           # foundation first
    lv = {"observing": "developing", "classifying": "developing", "measuring": "developing", "communicating": "developing",
          "inferring": "developing", "predicting": "developing"}
    assert choose_focus(lv, "plan") == "controlling_variables"         # integrated, matched to the inquiry stage
    lv2 = dict(lv, measuring="emerging")
    assert choose_focus(lv2, "plan") == "measuring"                    # don't push integrated while basics are weak
    assert choose_focus({**{s: "independent" for s in lv}, "observing": "independent"}, "interpret") == "interpreting_data"


def test_memory_across_sessions_and_resume(mk):
    clock = FakeClock()
    b, llm = mk([{"reply": "Hi"}, {"reply": "Great plan. Check tomorrow and tell me!",
                                   "inquiry": {"title": "Drooping tulsi", "stage": "plan",
                                               "task": "Count drooping leaves morning and evening"}}], clock=clock)
    consented(b)
    b.start("Asha"); b.message("Asha", "I'll move it inside")
    clock.t += 600
    assert b.start("Asha")["resumed"]                                   # same session within a few hours
    b.stop("Asha"); b.stop("Asha")                                      # reflection, then close
    clock.t += 86400
    b.start("Asha")
    system = llm.calls[-1][0]
    assert "Count drooping leaves morning and evening" in system and "Drooping tulsi" in system
    assert "FOCUS SKILL" in system


def test_system_prompt_carries_the_design_rules():
    s = build_system({"name": "Asha", "grade": 6, "skills": {}, "inquiries": []}, "observing", [])
    for rule in ["ONE question", "Never", "Correct a wrong prediction", "I'm an AI science buddy",
                 "flames", "school name", "g6c8", "noticing"]:
        assert rule.lower() in s.lower(), rule
    assert "g8c13" not in s           # only chapters near the learner's grade


def test_buddy_api_demo_mode(tmp_path):
    c = TestClient(create_app(PACKS, str(tmp_path / "a.db")))
    assert c.post("/api/buddy/Asha/start").status_code == 403
    assert c.get("/api/buddy/Asha/status").json()["consent"] is False
    assert c.post("/api/buddy/Asha/consent", json={"parent_name": "L", "relation": "Mother", "agree": False}).status_code == 400
    c.post("/api/buddy/Asha/consent", json={"parent_name": "L", "relation": "Mother", "agree": True, "grade": 6})
    v = c.post("/api/buddy/Asha/start").json()
    assert v["demo"] and v["turns"][0]["role"] == "tutor"
    v = c.post("/api/buddy/Asha/message", json={"text": "I saw ants carrying a crumb of bread"}).json()
    assert v["turns"][-1]["role"] == "tutor"
    rows = c.get("/api/teacher/buddy").json()
    assert rows[0]["student"] == "Asha" and rows[0]["levels"]["observing"]
    assert c.get("/buddy").status_code == 200
