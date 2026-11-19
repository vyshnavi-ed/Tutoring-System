"""Pack validator — run on every pack, especially AI-generated ones, before a teacher reviews it.

Checks structure (ids, links, cycles), randomisation headroom, and *answer keys*:
fractions must parse, MCQ answers must be among the options, and code items' reference
solutions must actually pass their own tests.
"""
from __future__ import annotations

from .graders import GRADERS, grade_code_python, parse_fraction
from .strategies import STRATEGIES


def validate(data: dict, run_code: bool = True) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    E, W = errors.append, warnings.append

    for key in ("id", "strategy", "item_sets", "units"):
        if key not in data:
            E(f"missing top-level key '{key}'")
    if errors:
        return errors, warnings
    strategy = data["strategy"]
    if strategy not in STRATEGIES:
        E(f"unknown strategy '{strategy}' (known: {', '.join(STRATEGIES)})")

    sets, acts = data["item_sets"], data.get("activities", {})
    if not data["units"]:
        E("pack has no units")
    for u in data["units"]:
        if u.get("activity") and u["activity"] not in acts:
            E(f"unit {u.get('id')}: activity '{u['activity']}' not defined")
        if not u.get("sets"):
            E(f"unit {u.get('id')}: no sets")
        for sid in u.get("sets", []):
            if sid not in sets:
                E(f"unit {u.get('id')}: set '{sid}' not defined")

    for sid, s in sets.items():
        if s.get("activity") and s["activity"] not in acts:
            E(f"{sid}: activity '{s['activity']}' not defined")
        if not s.get("activity"):
            W(f"{sid}: no activity — nothing to teach when a student struggles here")
        for l in s.get("links", []):
            if l not in sets:
                E(f"{sid}: link to unknown set '{l}'")
            if l == sid:
                E(f"{sid}: links to itself")
        items = s.get("items", [])
        if not items:
            E(f"{sid}: no items")
        elif len(items) < 2 and strategy != "spaced_repetition":
            W(f"{sid}: only {len(items)} item — students will see the same question again after remediation")
        ids = [it.get("id") for it in items]
        if len(ids) != len(set(ids)) or None in ids:
            E(f"{sid}: item ids missing or duplicated")
        for it in items:
            _check_item(sid, it, E, W, run_code)

    if strategy in ("level_descent", "prereq_graph"):
        cyc = _find_cycle({sid: s.get("links", []) for sid, s in sets.items()})
        if cyc:
            E("links form a cycle: " + " → ".join(cyc))
    if strategy == "level_descent":
        order = data.get("config", {}).get("levels",
                                           ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"])
        for sid, s in sets.items():
            for l in s.get("links", []):
                if l in sets and s.get("level") in order and sets[l].get("level") in order:
                    if order.index(sets[l]["level"]) >= order.index(s["level"]):
                        W(f"{sid} ({s['level']}) links to {l} ({sets[l]['level']}) which is not a lower level")
        reachable = set()
        stack = [sid for u in data["units"] for sid in u.get("sets", [])]
        while stack:
            x = stack.pop()
            if x in reachable or x not in sets:
                continue
            reachable.add(x)
            stack.extend(sets[x].get("links", []))
        for sid in sets:
            if sid not in reachable:
                W(f"{sid}: never reachable from any unit")
    return errors, warnings


def _check_item(sid, it, E, W, run_code):
    where = f"{sid}/{it.get('id')}"
    t = it.get("type")
    if t not in GRADERS:
        E(f"{where}: unknown item type '{t}'")
        return
    if not it.get("prompt"):
        E(f"{where}: empty prompt")
    if t == "mcq":
        opts = it.get("options", [])
        if len(opts) < 2 or len(set(opts)) != len(opts):
            E(f"{where}: needs ≥2 distinct options")
        if it.get("answer") not in opts:
            E(f"{where}: answer is not one of the options")
    elif t == "fraction":
        if parse_fraction(str(it.get("answer", ""))) is None:
            E(f"{where}: answer '{it.get('answer')}' is not a valid fraction")
    elif t == "numeric":
        try:
            float(it["answer"])
        except (KeyError, ValueError, TypeError):
            E(f"{where}: numeric answer missing/invalid")
    elif t == "text":
        if not (it.get("accepted") or it.get("answer")):
            E(f"{where}: no accepted answers")
    elif t == "free_text":
        if not it.get("rubric"):
            E(f"{where}: free_text item needs a rubric")
    elif t == "code_python":
        if not it.get("tests"):
            E(f"{where}: code item has no tests")
        elif not it.get("solution"):
            W(f"{where}: no reference solution — tests can't be verified")
        elif run_code:
            r = grade_code_python(it, it["solution"])
            if r.score < 1.0:
                E(f"{where}: reference solution fails its own tests — {r.feedback}")
            if it.get("starter"):
                r2 = grade_code_python(it, it["starter"])
                if r2.score >= 1.0:
                    E(f"{where}: the starter code already passes all tests")


def _find_cycle(graph):
    WHITE, GREY, BLACK = 0, 1, 2
    color = {n: WHITE for n in graph}
    path = []

    def dfs(n):
        color[n] = GREY
        path.append(n)
        for m in graph.get(n, []):
            if m not in color:
                continue
            if color[m] == GREY:
                return path[path.index(m):] + [m]
            if color[m] == WHITE:
                c = dfs(m)
                if c:
                    return c
        path.pop()
        color[n] = BLACK
        return None

    for n in graph:
        if color[n] == WHITE:
            c = dfs(n)
            if c:
                return c
    return None
