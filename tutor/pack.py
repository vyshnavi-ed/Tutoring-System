"""Subject packs: the content + rules for one subject, stored as JSON.

A pack is strategy-agnostic in shape:

    {
      "id": "math_fractions",
      "title": "Fractions",
      "subject": "Mathematics",
      "strategy": "prereq_graph",          # which tutoring algorithm runs it (what comes next)
      "pedagogy": "inquiry",               # how each skill is taught (see tutor/pedagogy.py)
      "status": "approved",                # "draft" packs are hidden from students
      "config": {...},                     # strategy / grading parameters
      "activities": {"ACT_ID": {"title": ..., "body": "markdown"}},
      "item_sets": {
        "SET_ID": {
          "title": ..., "level": "Apply",  # level/knowledge type: teacher-facing only
          "activity": "ACT_ID",            # what to teach when this set is a problem
          "links": ["SET_ID", ...],        # remediation targets (lower level / prerequisite)
          "items": [{"id": ..., "type": "mcq|numeric|fraction|text|code_python|free_text", ...}]
        }
      },
      "units": [{"id": ..., "title": ..., "activity": "ACT_ID", "sets": ["SET_ID", ...]}]
    }

What "links" and "units" mean is up to the strategy (see tutor/strategies).
"""
from __future__ import annotations

import json
from pathlib import Path

DEFAULT_CONFIG = {
    "pass_score": 0.7,          # item score needed to count as "satisfactory"
    "alert_after_failures": 3,  # consecutive failures on one set before a teacher is alerted
}


class Pack:
    def __init__(self, data: dict, path: Path | None = None):
        self.data = data
        self.path = path
        self.id: str = data["id"]
        self.title: str = data.get("title", self.id)
        self.subject: str = data.get("subject", "")
        self.strategy: str = data["strategy"]
        self.pedagogy: str = data.get("pedagogy", "direct")
        self.status: str = data.get("status", "draft")
        self.config: dict = {**DEFAULT_CONFIG, **data.get("config", {})}
        self.activities: dict = data.get("activities", {})
        self.sets: dict = data.get("item_sets", {})
        self.units: list = data.get("units", [])
        self._items = {
            (sid, it["id"]): it for sid, s in self.sets.items() for it in s.get("items", [])
        }

    def item(self, set_id: str, item_id: str) -> dict:
        return self._items[(set_id, item_id)]

    def activity(self, activity_id: str | None) -> dict | None:
        if not activity_id:
            return None
        return self.activities.get(activity_id)

    def links(self, set_id: str) -> list[str]:
        return list(self.sets[set_id].get("links", []))

    def save(self) -> None:
        if self.path is None:
            raise ValueError("pack has no file path")
        self.data["status"] = self.status
        self.path.write_text(json.dumps(self.data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_pack(path: str | Path) -> Pack:
    path = Path(path)
    return Pack(json.loads(path.read_text(encoding="utf-8")), path)


def load_packs(directory: str | Path) -> dict[str, Pack]:
    packs = {}
    for p in sorted(Path(directory).glob("*.json")):
        pack = load_pack(p)
        packs[pack.id] = pack
    return packs
