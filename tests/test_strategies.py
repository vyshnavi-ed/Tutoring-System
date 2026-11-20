from conftest import asked, run

U = ["A1.2.U.1", "A1.2.U.2", "A1.2.U.3", "A1.2.U.4"]
R = ["A1.2.R.1", "A1.2.R.2", "A1.2.R.3", "A1.2.R.4"]


# ------------------------------------------------------------------ level descent (thesis)

def test_level_descent_all_correct(engine):
    trace = run(engine, "s1", "ds_linked_lists", lambda *a: True)
    assert asked(trace) == ["A1.2.Ap.1", "A1.2.Ap.2", "A1.2.Ap.3"]
    assert trace[0][0] == "activity" and trace[-1][0] == "done"


def test_level_descent_matches_thesis_figure_4_4(engine):
    """Fail Ap.1 once -> IA.U -> all pre-selected U sets -> back to Ap.1 with a *different* item."""
    seen = {"ap1": 0}

    def policy(set_id, item, trace):
        if set_id == "A1.2.Ap.1":
            seen["ap1"] += 1
            return seen["ap1"] > 1
        return True

    trace = run(engine, "s2", "ds_linked_lists", policy)
    assert asked(trace) == ["A1.2.Ap.1"] + U + ["A1.2.Ap.1", "A1.2.Ap.2", "A1.2.Ap.3"]
    ap1_items = [t[2] for t in trace if t[0] == "item" and t[1] == "A1.2.Ap.1"]
    assert ap1_items[0] != ap1_items[1], "student must get a different item after remediation"
    lessons = [t[1] for t in trace if t[0] == "activity"]
    assert any("Understand" in l for l in lessons)


def test_level_descent_two_levels(engine):
    """Fail Ap.1 and then U.1 once: U.1 -> R.1..R.4 -> U.1 again -> U.2.. -> Ap.1."""
    fails = {"A1.2.Ap.1": 1, "A1.2.U.1": 1}

    def policy(set_id, item, trace):
        if fails.get(set_id, 0) > 0:
            fails[set_id] -= 1
            return False
        return True

    seq = asked(run(engine, "s3", "ds_linked_lists", policy))
    assert seq[:11] == ["A1.2.Ap.1", "A1.2.U.1"] + R + ["A1.2.U.1", "A1.2.U.2", "A1.2.U.3", "A1.2.U.4", "A1.2.Ap.1"]


def test_level_descent_stuck_at_remember_alerts_teacher_once(engine):
    def policy(set_id, item, trace):
        return set_id != "A1.2.R.1" and set_id != "A1.2.U.1" and set_id != "A1.2.Ap.1"

    trace = run(engine, "s4", "ds_linked_lists", policy, max_steps=60)
    stuck = [a for a in engine.store.alerts() if a["kind"] == "stuck"]
    assert any(a["set_id"] == "A1.2.R.1" and a["details"]["lowest_level"] for a in stuck)
    assert len([a for a in stuck if a["set_id"] == "A1.2.R.1"]) == 1  # deduplicated
    assert any("teacher" in (t[1] or "") for t in trace if t[0] == "message")


# ------------------------------------------------------------------ prerequisite graph (fractions)

def _events(engine, student, pack):
    return [(e["kind"], e["payload"]) for e in engine.store.events(student, pack)]


def test_prereq_strong_student_moves_fast(engine):
    trace = run(engine, "p1", "math_fractions", lambda *a: True)
    assert trace[-1][0] == "done"
    sets_asked = set(asked(trace))
    goals = set(engine.packs["math_fractions"].units[0]["sets"])
    assert sets_asked == goals, "a student who never fails should never be sent to prerequisites"


def test_prereq_diagnoses_gap_and_returns(engine):
    """Student can't simplify fractions; that makes 'add like fractions' fail too."""
    know = {"simplify_right": 0}

    def policy(set_id, item, trace):
        if set_id == "F_SIMPLIFY":
            prior = sum(1 for t in trace if t[0] == "item" and t[1] == "F_SIMPLIFY")
            ok = prior >= 2          # learns after two tries + lesson
            know["simplify_right"] += ok
            return ok
        if set_id == "F_ADD_LIKE":
            return know["simplify_right"] >= 3
        return True

    trace = run(engine, "p2", "math_fractions", policy,
                stop=lambda tr: any(t[0] == "message" and "Mastered: Add & subtract: same" in t[1] for t in tr))
    ev = _events(engine, "p2", "math_fractions")
    kinds = [(k, p.get("set_id")) for k, p in ev]
    assert ("diagnose", "F_ADD_LIKE") in kinds
    assert ("probe_pass", "F_MEANING") in kinds            # known prerequisite is skipped quickly
    assert ("gap_found", "F_SIMPLIFY") in kinds
    assert kinds.index(("mastered", "F_SIMPLIFY")) < kinds.index(("mastered", "F_ADD_LIKE"))
    assert ("return", "F_ADD_LIKE") in kinds
    # simplify's own prerequisites were probed but not taught
    assert ("gap_found", "F_EQUIV") not in kinds


def test_prereq_root_gap_alerts_teacher(engine):
    def policy(set_id, item, trace):
        return set_id not in ("F_ADD_LIKE", "F_SIMPLIFY", "M_FACTORS")

    run(engine, "p3", "math_fractions", policy, max_steps=80)
    stuck = {a["set_id"] for a in engine.store.alerts() if a["kind"] == "stuck"}
    assert "M_FACTORS" in stuck


def test_prereq_free_text_review_alert(engine):
    # F_COMPARE contains a free_text item; offline grader flags passing answers for teacher review
    run(engine, "p4", "math_fractions", lambda *a: True)
    reviews = [a for a in engine.store.alerts() if a["kind"] == "review"]
    attempts = engine.store.attempts("p4", "math_fractions")
    assert len(reviews) == sum(1 for a in attempts if a["item_type"] == "free_text" and a["passed"])


# ------------------------------------------------------------------ spaced repetition (English)

def test_sr_first_session_and_next_day_harder_items(engine):
    trace = run(engine, "e1", "english_vocab", lambda *a: True)
    first = [t for t in trace if t[0] == "item"]
    assert len(first) == 5 and all(t[2].endswith(".recognise") for t in first)
    assert trace[-1][0] == "done"

    engine.clock.t += 86400 + 60
    trace2 = run(engine, "e1", "english_vocab", lambda *a: True)
    items2 = [t[2] for t in trace2 if t[0] == "item"]
    assert sum(i.endswith(".cloze") for i in items2) == 5      # yesterday's words, one box up
    assert sum(i.endswith(".recognise") for i in items2) == 5  # five new words


def test_sr_missed_word_comes_back_and_leech_alerts(engine):
    def policy(set_id, item, trace):
        return set_id != "W_FRAGILE"

    trace = run(engine, "e2", "english_vocab", policy)
    seq = asked(trace)
    idx = [i for i, s in enumerate(seq) if s == "W_FRAGILE"]
    assert len(idx) >= 3
    assert any(a["set_id"] == "W_FRAGILE" for a in engine.store.alerts() if a["kind"] == "stuck")
    # the intro card is re-shown after a miss
    assert sum(1 for t in trace if t[0] == "activity" and t[1] == "fragile") >= 2
