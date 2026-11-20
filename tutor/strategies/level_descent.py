"""Level descent — the tutoring rules from Ramesh (2014), "A Framework for Tutoring Rules", Fig. 4.4.

Pack shape:
  units[]       = Units-of-Study, in order. unit.activity = the top-level instructional
                  activity (IAi.j.TOP); unit.sets = the top-level item sets {Ai.j.TOP.1..k}.
  set.links     = the "pre-selected" sets one cognitive level lower (the tutoring-rule table).
  set.activity  = the instructional activity for that set's level (IAi.j.U, IAi.j.R ...).

Algorithm, for each top-level set p of each Unit-of-Study:
  ask a random item from p
    pass -> next p (after the last p: next Unit-of-Study)
    fail -> deliver the next-lower activity, then work through every pre-selected
            lower set the same way (recursively), then return to p with a *different* item.
  At the lowest level (no links) a failure means: re-study the activity and try again
  (the thesis says "memorise"); the engine alerts a teacher after N failures in a row.
"""
from .base import Strategy


class LevelDescent(Strategy):
    name = "level_descent"
    description = "Thesis rules: on failure, drop one cognitive level via pre-selected sets, then climb back."

    def init_state(self):
        return {"unit_idx": 0, "top_idx": 0, "stack": [], "intro_shown": -1, "completed_units": []}

    def next_step(self, state, ctx):
        units = self.pack.units
        if not state["stack"]:
            if state["unit_idx"] >= len(units):
                return {"type": "done", "text": "You have completed every Unit-of-Study in this module. Well done!"}
            unit = units[state["unit_idx"]]
            if state["intro_shown"] != state["unit_idx"]:
                state["intro_shown"] = state["unit_idx"]
                self.queue_activity(state, unit.get("activity"), f"New unit: {unit.get('title', unit['id'])}")
                ctx.log("unit_start", unit=unit["id"])
                return None
            if state["top_idx"] >= len(unit["sets"]):
                ctx.log("unit_complete", unit=unit["id"])
                state["completed_units"].append(unit["id"])
                state["unit_idx"] += 1
                state["top_idx"] = 0
                if state["unit_idx"] < len(units):
                    self.queue_message(state, f"Unit complete: {unit.get('title', unit['id'])}. On to the next one!", "success")
                return None
            state["stack"].append({"set": unit["sets"][state["top_idx"]], "phase": "ask", "child": 0})
        return {"type": "item", "set_id": state["stack"][-1]["set"]}

    def on_result(self, state, set_id, item, passed, result, ctx):
        stack = state["stack"]
        frame = stack[-1]
        if passed:
            stack.pop()
            self._child_finished(state, ctx)
            return
        links = self.pack.links(set_id)
        if links:
            frame["phase"], frame["child"] = "children", 0
            lower = self.pack.sets[links[0]]
            level = lower.get("level", "an easier level")
            ctx.log("descend", from_set=set_id, to_sets=links, level=level)
            self.queue_activity(state, lower.get("activity"),
                                f"Let's step back to {level.lower()} and build up from there.")
            stack.append({"set": links[0], "phase": "ask", "child": 0})
        else:
            # lowest level: re-study ("memorise") and retry; engine handles the teacher alert
            ctx.log("restudy", set_id=set_id)
            self.queue_activity(state, self.pack.sets[set_id].get("activity"),
                                "Read this carefully once more — try to remember the key facts.")

    def _child_finished(self, state, ctx):
        stack = state["stack"]
        if not stack:
            state["top_idx"] += 1
            return
        parent = stack[-1]
        if parent["phase"] != "children":
            return
        links = self.pack.links(parent["set"])
        parent["child"] += 1
        if parent["child"] < len(links):
            stack.append({"set": links[parent["child"]], "phase": "ask", "child": 0})
        else:
            parent["phase"] = "ask"
            ctx.log("ascend", to_set=parent["set"])
            self.queue_message(state, "Good — now let's go back and try a different question like the one you missed.")

    def progress(self, state):
        units = self.pack.units
        i = min(state["unit_idx"], len(units) - 1) if units else 0
        unit = units[i] if units else {"sets": []}
        depth = max(0, len(state["stack"]) - 1)
        return {"unit": unit.get("title", ""), "unit_index": state["unit_idx"] + 1, "unit_count": len(units),
                "step": min(state["top_idx"] + 1, len(unit["sets"])), "step_count": len(unit["sets"]),
                "remediation_depth": depth}

    def summary(self, state):
        return {
            "position": [{"set": f["set"], "level": self.pack.sets[f["set"]].get("level", ""), "phase": f["phase"]}
                         for f in state["stack"]],
            "unit_index": state["unit_idx"], "top_set_index": state["top_idx"],
            "completed_units": state["completed_units"],
        }
