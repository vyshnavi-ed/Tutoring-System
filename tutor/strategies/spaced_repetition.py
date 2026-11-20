"""Spaced repetition (Leitner boxes) — suited to vocabulary, facts and formulas.

Pack shape:
  set           = one card (e.g. one word). set.activity = its intro card (meaning, example).
  set.items     = ordered from easiest to hardest. The item asked depends on the card's box:
                  box 0 -> items[0] (recognise), box 1 -> items[1] ... (produce, use in a sentence).
  units[].sets  = the order in which new cards are introduced.

config:
  box_intervals_days   e.g. [0, 1, 3, 7, 14, 30] — wait after reaching each box
  new_per_session      new cards introduced per day
  relearn_gap          a missed card comes back after this many other questions

Correct answer -> card moves up a box and is scheduled further out.
Wrong answer   -> card drops to box 0, the intro card is shown again, and it comes back soon.
"""
import time

from .base import Strategy

DAY = 86400.0


class SpacedRepetition(Strategy):
    name = "spaced_repetition"
    description = "Leitner-box spaced repetition; items get harder as a card climbs boxes."

    def init_state(self):
        return {"cards": {}, "step": 0, "relearn": [], "new_today": 0, "day": None}

    def _order(self):
        return [sid for u in self.pack.units for sid in u["sets"]]

    def _intervals(self):
        return list(self.cfg.get("box_intervals_days", [0, 1, 3, 7, 14, 30]))

    def pick_item_index(self, state, set_id):
        return state["cards"].get(set_id, {}).get("box", 0)

    def next_step(self, state, ctx):
        now = ctx.now()
        today = time.strftime("%Y-%m-%d", time.gmtime(now))
        if state["day"] != today:
            state["day"], state["new_today"] = today, 0

        # 1. missed cards whose relearn gap has elapsed
        for r in state["relearn"]:
            if r["due_step"] <= state["step"]:
                return {"type": "item", "set_id": r["set"]}
        # 2. reviews that are due
        due = [(c["due"], sid) for sid, c in state["cards"].items()
               if c.get("seen") and c["due"] <= now and sid not in {r["set"] for r in state["relearn"]}]
        if due:
            return {"type": "item", "set_id": min(due)[1]}
        # 3. a new card
        if state["new_today"] < int(self.cfg.get("new_per_session", 5)):
            for sid in self._order():
                if sid not in state["cards"]:
                    state["cards"][sid] = {"box": 0, "due": now, "seen": True, "lapses": 0, "reviews": 0}
                    state["new_today"] += 1
                    ctx.log("new_card", set_id=sid)
                    self.teach(state, sid, "intro", "")
                    return None
        # 4. missed cards still waiting: bring the earliest forward rather than idling
        if state["relearn"]:
            return {"type": "item", "set_id": min(state["relearn"], key=lambda r: r["due_step"])["set"]}

        upcoming = [c["due"] for c in state["cards"].values() if c.get("seen")]
        if not upcoming and all(sid in state["cards"] for sid in self._order()):
            return {"type": "done", "text": "All cards learned."}
        nxt = min(upcoming) if upcoming else None
        when = f" Next review in {max(1, round((nxt - now) / 3600))} hour(s)." if nxt else ""
        return {"type": "done", "text": "You're done for today — nothing else is due." + when, "resumable": True}

    def on_result(self, state, set_id, item, passed, result, ctx):
        state["step"] += 1
        card = state["cards"][set_id]
        card["reviews"] += 1
        intervals = self._intervals()
        state["relearn"] = [r for r in state["relearn"] if r["set"] != set_id]
        if passed:
            card["box"] = min(card["box"] + 1, len(intervals) - 1)
            card["due"] = ctx.now() + intervals[card["box"]] * DAY
            ctx.log("promote", set_id=set_id, box=card["box"])
        else:
            card["box"] = 0
            card["lapses"] += 1
            card["due"] = ctx.now()
            state["relearn"].append({"set": set_id, "due_step": state["step"] + int(self.cfg.get("relearn_gap", 3))})
            ctx.log("lapse", set_id=set_id, lapses=card["lapses"])
            self.teach(state, set_id, "lapse", "Let's look at this word again.")

    def progress(self, state):
        cards = state["cards"]
        return {"learning": len(cards), "total": len(self._order()),
                "mature": sum(1 for c in cards.values() if c["box"] >= 3),
                "due_again_soon": len(state["relearn"])}

    def summary(self, state):
        return {"cards": {sid: {"box": c["box"], "lapses": c["lapses"], "reviews": c["reviews"]}
                          for sid, c in state["cards"].items()},
                "not_started": [s for s in self._order() if s not in state["cards"]]}
