"""The interface every tutoring strategy implements.

A strategy is a small state machine. The engine owns the session loop, grading,
storage and teacher alerts; the strategy only decides *what comes next*.

    next_step(state, ctx)  -> {"type": "item", "set_id": ...}   ask an item from this set
                              {"type": "done", "text": ...}      nothing left (for now)
                              None                               "I queued an activity/message, ask me again"
    on_result(state, set_id, item, passed, result, ctx)          update state after a graded answer

Helpers below let strategies queue lessons/messages and pick a fresh item from a set.
"""
from __future__ import annotations


class Strategy:
    name = "base"
    description = ""

    def __init__(self, pack):
        self.pack = pack
        self.cfg = pack.config

    # ---- to implement
    def init_state(self) -> dict:
        return {}

    def next_step(self, state: dict, ctx) -> dict | None:
        raise NotImplementedError

    def on_result(self, state: dict, set_id: str, item: dict, passed: bool, result, ctx) -> None:
        raise NotImplementedError

    def progress(self, state: dict) -> dict:
        """Short student-facing progress info."""
        return {}

    def summary(self, state: dict) -> dict:
        """Teacher-facing snapshot of where the student is (the 'student module')."""
        return {}

    def pick_item_index(self, state: dict, set_id: str) -> int | None:
        """Optionally force which item (by position) to ask. None = random unused item."""
        return None

    # ---- helpers
    @staticmethod
    def queue_activity(state, activity_id, reason=""):
        if activity_id:
            state["pending"].append({"type": "activity", "activity_id": activity_id, "reason": reason})

    @staticmethod
    def queue_message(state, text, tone="info"):
        state["pending"].append({"type": "message", "text": text, "tone": tone})

    def set_title(self, set_id):
        return self.pack.sets[set_id].get("title", set_id)
