"""The tutoring engine: runs any strategy over any pack.

Responsibilities that are the same for every subject live here:
item selection (never repeat the last item), grading, logging every attempt,
the "satisfactory" threshold, and alerting a teacher when a student is stuck.
"""
from __future__ import annotations

import random
import time

from .graders import grade
from .strategies import STRATEGIES

DAY = 86400.0


class Ctx:
    """What a strategy is allowed to touch while making decisions."""

    def __init__(self, engine, student_id, pack, state):
        self.engine, self.student_id, self.pack, self.state = engine, student_id, pack, state
        self.rng = engine.rng

    def now(self) -> float:
        return self.engine.clock() + self.state.get("clock_offset", 0.0)

    def log(self, kind, **payload):
        self.engine.store.add_event(self.student_id, self.pack.id, kind, payload)

    def alert(self, kind, set_id, message, dedupe=True, **details):
        store = self.engine.store
        if dedupe and store.has_open_alert(self.student_id, self.pack.id, kind, set_id):
            return False
        store.add_alert(self.student_id, self.pack.id, kind, set_id, message, details)
        self.log("teacher_alert", alert_kind=kind, set_id=set_id, message=message)
        return True


class Engine:
    def __init__(self, packs: dict, store, rng: random.Random | None = None, clock=time.time):
        self.packs, self.store = packs, store
        self.rng = rng or random.Random()
        self.clock = clock

    # ------------------------------------------------------------ plumbing
    def strategy_for(self, pack):
        return STRATEGIES[pack.strategy](pack)

    def _load(self, student_id, pack_id):
        pack = self.packs[pack_id]
        strat = self.strategy_for(pack)
        state = self.store.load_state(student_id, pack_id)
        if state is None:
            state = {"pending": [], "current": None, "used": {}, "fails": {}, "clock_offset": 0.0,
                     **strat.init_state()}
            self.store.add_event(student_id, pack_id, "session_start", {"strategy": pack.strategy})
        return pack, strat, state, Ctx(self, student_id, pack, state)

    def _pick_item(self, pack, strat, state, set_id):
        items = pack.sets[set_id]["items"]
        forced = strat.pick_item_index(state, set_id)
        if forced is not None:
            return items[min(forced, len(items) - 1)]["id"]
        used = state["used"].setdefault(set_id, [])
        fresh = [it["id"] for it in items if it["id"] not in used]
        if not fresh:  # all seen: start over, but never repeat the immediately previous item
            last = used[-1] if used else None
            used.clear()
            fresh = [it["id"] for it in items if it["id"] != last] or [items[0]["id"]]
        choice = self.rng.choice(fresh)
        used.append(choice)
        return choice

    def _render(self, pack, strat, state, act):
        base = {"progress": strat.progress(state)}
        if act["type"] == "activity":
            a = pack.activity(act["activity_id"]) or {"title": act["activity_id"], "body": ""}
            return {**base, "type": "activity", "title": a.get("title", ""), "body": a.get("body", ""),
                    "reason": act.get("reason", "")}
        if act["type"] == "message":
            return {**base, "type": "message", "text": act["text"], "tone": act.get("tone", "info")}
        if act["type"] == "item":
            item = pack.item(act["set_id"], act["item_id"])
            out = {**base, "type": "item", "set_id": act["set_id"], "item_id": item["id"],
                   "item_type": item["type"], "prompt": item["prompt"]}
            for k in ("options", "starter", "placeholder"):
                if k in item:
                    out[k] = item[k]
            return out
        return {**base, **act}

    def _next(self, pack, strat, state, ctx):
        for _ in range(100):
            if state["pending"]:
                return self._render(pack, strat, state, state["pending"][0])
            if state["current"]:
                return self._render(pack, strat, state, {"type": "item", **state["current"]})
            step = strat.next_step(state, ctx)
            if step is None:
                continue
            if step["type"] == "item":
                item_id = self._pick_item(pack, strat, state, step["set_id"])
                state["current"] = {"set_id": step["set_id"], "item_id": item_id}
                ctx.log("ask", set_id=step["set_id"], item_id=item_id)
                continue
            return self._render(pack, strat, state, step)
        raise RuntimeError("strategy did not converge on an action")

    # ------------------------------------------------------------ public API
    def action(self, student_id, pack_id) -> dict:
        pack, strat, state, ctx = self._load(student_id, pack_id)
        out = self._next(pack, strat, state, ctx)
        self.store.save_state(student_id, pack_id, state)
        return out

    def acknowledge(self, student_id, pack_id) -> dict:
        """Student clicked 'Continue' on an activity or message."""
        pack, strat, state, ctx = self._load(student_id, pack_id)
        if state["pending"]:
            shown = state["pending"].pop(0)
            if shown["type"] == "activity":
                ctx.log("activity", activity_id=shown["activity_id"], reason=shown.get("reason", ""))
        out = self._next(pack, strat, state, ctx)
        self.store.save_state(student_id, pack_id, state)
        return out

    def answer(self, student_id, pack_id, response) -> dict:
        pack, strat, state, ctx = self._load(student_id, pack_id)
        if state["pending"] or not state["current"]:
            return {"error": "no question is waiting for an answer", "action": self._next(pack, strat, state, ctx)}
        cur = state["current"]
        set_id, item = cur["set_id"], pack.item(cur["set_id"], cur["item_id"])
        result = grade(item, response)
        default_pass = 1.0 if item["type"] == "code_python" else pack.config["pass_score"]
        passed = result.score >= float(item.get("pass_score", default_pass))

        self.store.add_attempt(student_id, pack_id, set_id, item, response, result, passed)
        state["current"] = None

        if result.needs_review:
            ctx.alert("review", set_id, f"Please check a free-text answer on “{strat.set_title(set_id)}”.",
                      dedupe=False, item_id=item["id"], prompt=item["prompt"], response=str(response),
                      provisional_score=result.score)

        # consecutive-failure tracking → teacher alert (same rule for every strategy)
        fails = state["fails"]
        if passed:
            fails.pop(set_id, None)
        else:
            fails[set_id] = fails.get(set_id, 0) + 1
            limit = int(pack.config["alert_after_failures"])
            if fails[set_id] >= limit:
                level = pack.sets[set_id].get("level", "")
                bottom = not pack.links(set_id)
                msg = (f"Stuck on “{strat.set_title(set_id)}”" + (f" ({level})" if level else "") +
                       f": {fails[set_id]} failed attempts in a row" +
                       (" at the lowest level — no further remediation available." if bottom else "."))
                if ctx.alert("stuck", set_id, msg, attempts=fails[set_id], lowest_level=bottom):
                    state["pending"].append({"type": "message", "tone": "notice",
                                             "text": "This one is tricky. I've let your teacher know so they "
                                                     "can help you — keep going in the meantime."})

        strat.on_result(state, set_id, item, passed, result, ctx)

        reveal = pack.config.get("reveal_answer_on_fail", False)
        res = {"score": round(result.score, 3), "passed": passed, "feedback": result.feedback,
               "needs_review": result.needs_review}
        if not passed:
            if item.get("hint"):
                res["hint"] = item["hint"]
            if reveal and "answer" in item:
                res["answer"] = item["answer"]
            if item.get("explanation"):
                res["explanation"] = item["explanation"]
        elif item.get("explanation") and pack.config.get("explain_on_pass", True):
            res["explanation"] = item["explanation"]

        out = self._next(pack, strat, state, ctx)
        self.store.save_state(student_id, pack_id, state)
        return {"result": res, "action": out}

    def advance_clock(self, student_id, pack_id, days: float) -> dict:
        """Demo helper for spaced repetition: pretend time has passed."""
        pack, strat, state, ctx = self._load(student_id, pack_id)
        state["clock_offset"] = state.get("clock_offset", 0.0) + days * DAY
        ctx.log("clock_advanced", days=days)
        out = self._next(pack, strat, state, ctx)
        self.store.save_state(student_id, pack_id, state)
        return out

    def summary(self, student_id, pack_id) -> dict:
        pack = self.packs[pack_id]
        strat = self.strategy_for(pack)
        state = self.store.load_state(student_id, pack_id)
        if state is None:
            return {}
        return {"strategy": pack.strategy, **strat.summary(state), "consecutive_failures": state.get("fails", {})}

    def reset(self, student_id, pack_id):
        self.store.delete_session(student_id, pack_id)
