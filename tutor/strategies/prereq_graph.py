"""Prerequisite graph + mastery — suited to maths and science.

Pack shape:
  set           = one skill (e.g. "add fractions with unlike denominators").
  set.links     = the skill's prerequisites (a directed acyclic graph).
  set.activity  = the lesson for that skill.
  units[].sets  = goal skills, in teaching order.

Differences from level descent:
  * Mastery is a probability (Bayesian Knowledge Tracing), not one correct answer.
    A skill is done when P(mastered) >= config.mastery_threshold.
  * On a failure the tutor *diagnoses*: it probes each not-yet-mastered prerequisite
    with one quick question. Prerequisites that pass are skipped; the first one that
    fails becomes the new focus (taught to mastery, diagnosing its own prerequisites
    in turn). Then the student returns to the original skill.
  * Prerequisites already mastered are never re-tested, so strong students move fast.
"""
from ..mastery import bkt_update
from .base import Strategy


class PrereqGraph(Strategy):
    name = "prereq_graph"
    description = "Diagnose failures by probing prerequisite skills; teach the gap; return. Mastery via BKT."

    def init_state(self):
        return {"goal_idx": 0, "stack": [], "mastery": {}, "goals_done": []}

    # --- mastery helpers
    def _p(self, state, sid):
        return state["mastery"].get(sid, float(self.cfg.get("p_init", 0.3)))

    def _mastered(self, state, sid):
        return self._p(state, sid) >= float(self.cfg.get("mastery_threshold", 0.95))

    def _goals(self):
        return [sid for u in self.pack.units for sid in u["sets"]]

    def _learn_frame(self, state, sid, reason):
        state["stack"].append({"set": sid, "mode": "learn", "diagnosed": False, "probe": [], "probe_idx": 0})
        self.queue_activity(state, self.pack.sets[sid].get("activity"), reason)

    def next_step(self, state, ctx):
        goals = self._goals()
        if not state["stack"]:
            while state["goal_idx"] < len(goals) and self._mastered(state, goals[state["goal_idx"]]):
                state["goals_done"].append(goals[state["goal_idx"]])
                state["goal_idx"] += 1
            if state["goal_idx"] >= len(goals):
                return {"type": "done", "text": "You've mastered every skill in this topic!"}
            sid = goals[state["goal_idx"]]
            ctx.log("goal_start", set_id=sid)
            self._learn_frame(state, sid, f"Next skill: {self.set_title(sid)}")
            return None
        return {"type": "item", "set_id": state["stack"][-1]["set"]}

    def on_result(self, state, set_id, item, passed, result, ctx):
        c = self.cfg
        state["mastery"][set_id] = bkt_update(self._p(state, set_id), passed,
                                              c.get("p_learn", 0.15), c.get("p_slip", 0.1), c.get("p_guess", 0.2))
        stack = state["stack"]
        frame = stack[-1]

        if frame["mode"] == "probe":
            stack.pop()
            if passed:
                ctx.log("probe_pass", set_id=set_id)
                self._resume_parent(state, ctx)
            else:
                ctx.log("gap_found", set_id=set_id)
                self._learn_frame(state, set_id, f"Found a gap: “{self.set_title(set_id)}”. Let's fix this first.")
            return

        # learn mode
        if passed:
            frame["diagnosed"] = False
            if self._mastered(state, set_id):
                stack.pop()
                ctx.log("mastered", set_id=set_id)
                self.queue_message(state, f"Mastered: {self.set_title(set_id)} ✓", "success")
                if not stack:
                    state["goals_done"].append(set_id)
                    state["goal_idx"] += 1
                else:
                    self._resume_parent(state, ctx)
            return

        unmastered = [p for p in self.pack.links(set_id) if not self._mastered(state, p)]
        if unmastered and not frame["diagnosed"]:
            frame.update(diagnosed=True, probe=unmastered, probe_idx=0)
            ctx.log("diagnose", set_id=set_id, probing=unmastered)
            self.queue_message(state, "Let's check a couple of building blocks to see where the trouble is.")
            stack.append({"set": unmastered[0], "mode": "probe"})
        else:
            ctx.log("reteach", set_id=set_id)
            self.queue_activity(state, self.pack.sets[set_id].get("activity"),
                                "Here's the lesson again — look closely at the worked example.")

    def _resume_parent(self, state, ctx):
        """A probe or sub-skill finished; continue the parent's diagnosis or return to it."""
        stack = state["stack"]
        if not stack:
            return
        parent = stack[-1]
        if parent["mode"] != "learn" or not parent["probe"]:
            return
        parent["probe_idx"] += 1
        while parent["probe_idx"] < len(parent["probe"]) and self._mastered(state, parent["probe"][parent["probe_idx"]]):
            parent["probe_idx"] += 1
        if parent["probe_idx"] < len(parent["probe"]):
            stack.append({"set": parent["probe"][parent["probe_idx"]], "mode": "probe"})
        else:
            parent["probe"], parent["probe_idx"] = [], 0
            ctx.log("return", set_id=parent["set"])
            self.queue_message(state, f"Now back to: {self.set_title(parent['set'])}.")

    def progress(self, state):
        goals = self._goals()
        cur = state["stack"][-1]["set"] if state["stack"] else None
        return {"skill": self.set_title(cur) if cur else "", "goal_index": min(state["goal_idx"] + 1, len(goals)),
                "goal_count": len(goals), "mastery": round(self._p(state, cur), 2) if cur else None,
                "remediation_depth": max(0, len(state["stack"]) - 1)}

    def summary(self, state):
        return {
            "mastery": {sid: round(self._p(state, sid), 3) for sid in self.pack.sets},
            "threshold": float(self.cfg.get("mastery_threshold", 0.95)),
            "position": [{"set": f["set"], "mode": f["mode"]} for f in state["stack"]],
            "goals_done": state["goals_done"],
        }
