"""Pedagogy: *how* a skill is taught and how wrong answers are handled.

Strategies (tutor/strategies) decide *what comes next*. A pedagogy decides how each
learning episode unfolds. A pack picks one of each:

    "strategy": "prereq_graph",
    "pedagogy": "inquiry",          # or "direct" (default: show lesson, then questions)

Inquiry (constructivist, aligned with the Agastya session-plan structure / 5E cycle)
----------------------------------------------------------------------------------
When a skill is introduced, the set's "episode" runs before any scored question:

    "episode": {
      "elicit":  [{"prompt": ...}],                          Engage: draw out prior knowledge
      "predict": {"prompt": ..., "options": [...]},          Engage: one prediction, never marked
      "explore": {"tool": "fraction_strips" | "context_sentences" | "problem" | "real_materials",
                  "prompt": ..., ...tool config..., "record": "What did you find?"},
      "probe":   [{"kind": "observe" | "why" | "where_else" | "summarise", "prompt": ...}],
      "explain": {"activity": "ACT_ID", "revisit": "You predicted {prediction}. ..."},
      "connect": ["everyday example", ...],                  Elaborate
      "key_learning": "one sentence"
    }

Student responses in an episode are recorded, not graded. An AI tutor may add one
follow-up question per response (never giving the answer away); offline, the authored
"followup" text is used when an answer is very short.

Wrong answers on scored items climb a hint ladder before they count as a failure:
  1. a misconception probe, if the answer matches one the author anticipated
     (e.g. 2/9 + 4/9 = 6/18 -> "is 6/18 bigger than 4/9?"),
  2. the item's "hints" in order (Socratic question -> nudge),
  3. the worked example (item "explanation") — only then does the strategy remediate.
The student retries the *same* item between rungs.
"""
from __future__ import annotations

import json
import os
import re

from .graders import normalize_text, parse_fraction


class Direct:
    """Teach-then-test: the original behaviour."""
    name = "direct"

    def __init__(self, pack):
        self.pack, self.cfg = pack, pack.config

    def teach(self, state, set_id, mode="intro", reason="", activity_id=None):
        aid = activity_id or self.pack.sets[set_id].get("activity")
        if aid:
            state["pending"].append({"type": "activity", "activity_id": aid, "reason": reason})

    def on_wrong(self, state, item, response, result, ctx):
        return None  # no retries: the strategy remediates immediately

    def respond(self, state, entry, response, ctx):
        return {}


class Inquiry(Direct):
    name = "inquiry"

    # ------------------------------------------------------------ episodes
    def teach(self, state, set_id, mode="intro", reason="", activity_id=None):
        ep = self.pack.sets[set_id].get("episode")
        if not ep:
            return super().teach(state, set_id, mode, reason, activity_id)
        q = state["pending"]
        full = mode in ("intro", "gap", "descend")
        title = self.pack.sets[set_id].get("title", set_id)
        if reason:
            q.append({"type": "message", "text": reason, "tone": "info"})
        if full:
            for e in ep.get("elicit", []):
                q.append({"type": "prompt", "phase": "elicit", "set_id": set_id, "prompt": e["prompt"],
                          "followup": e.get("followup", "")})
            if ep.get("predict"):
                p = ep["predict"]
                q.append({"type": "prompt", "phase": "predict", "set_id": set_id, "prompt": p["prompt"],
                          "options": p.get("options"), "followup": p.get("followup", "")})
        if ep.get("explore"):
            q.append({"type": "explore", "phase": "explore", "set_id": set_id, "title": title,
                      "again": not full})
        probes = ep.get("probe", [])
        if not full:  # re-investigation: one "what do you notice now?" probe
            probes = [{"kind": "observe",
                       "prompt": ep.get("reprobe", "Look again carefully. What do you notice now that you missed before?")}]
        for pr in probes:
            q.append({"type": "prompt", "phase": "probe", "kind": pr.get("kind", ""), "set_id": set_id,
                      "prompt": pr["prompt"], "followup": pr.get("followup", "")})
        expl = ep.get("explain", {})
        q.append({"type": "explain", "set_id": set_id,
                  "activity_id": expl.get("activity") or self.pack.sets[set_id].get("activity"),
                  "revisit": expl.get("revisit", "") if full else ""})
        if full and (ep.get("connect") or ep.get("key_learning")):
            q.append({"type": "connect", "set_id": set_id, "items": ep.get("connect", []),
                      "key_learning": ep.get("key_learning", "")})

    # ------------------------------------------------------------ open responses
    def respond(self, state, entry, response, ctx):
        """Record an ungraded episode response; maybe ask one follow-up question."""
        sid = entry.get("set_id")
        if entry.get("phase") == "predict" or (entry.get("phase") == "explore" and not entry.get("again")
                                                and sid not in state.setdefault("predictions", {})):
            state.setdefault("predictions", {})[sid] = response
        if entry.get("is_followup"):
            return {"ack": "Thanks — keep that thought in mind."}
        follow = None
        if entry.get("phase") in ("probe", "explore", "elicit") and self.cfg.get("ai_followups", True):
            follow = ai_followup(self.pack, sid, entry, response)
        if follow is None:  # offline / AI unavailable: authored follow-up for very short answers
            if entry.get("followup") and len(re.findall(r"\w+", str(response))) < 4:
                follow = entry["followup"]
        if follow:
            state["pending"].insert(0, {"type": "prompt", "phase": entry.get("phase"), "set_id": sid,
                                        "prompt": follow, "is_followup": True})
            ctx.log("followup", set_id=sid, question=follow)
        acks = {"predict": "Noted! Let's investigate and find out.", "elicit": "Thanks for sharing that.",
                "explore": "Interesting — hold on to that.", "probe": "Good thinking."}
        return {"ack": acks.get(entry.get("phase"), "Thanks.")}

    # ------------------------------------------------------------ hint ladder
    def ladder(self, item):
        hints = list(item.get("hints") or ([item["hint"]] if item.get("hint") else []))
        return hints[: int(self.cfg.get("max_hints", 3))]

    def on_wrong(self, state, item, response, result, ctx):
        """Return a rung to show (student retries the same item) or None (count as a failure)."""
        cur = state["current"]
        key = f"{cur['set_id']}::{item['id']}"
        tries = state.setdefault("tries", {})
        used = state.setdefault("misc_used", {}).setdefault(key, [])
        n = tries.get(key, 0)
        ladder = self.ladder(item)
        mc = match_misconception(item, response)
        if mc and mc["id"] not in used and n <= len(ladder):
            used.append(mc["id"])
            tries[key] = n + 1
            ctx.log("misconception", set_id=cur["set_id"], item_id=item["id"], misconception=mc["id"],
                    response=str(response))
            return {"kind": "misconception", "text": mc["probe"].replace("{response}", str(response).strip())}
        if n < len(ladder):
            tries[key] = n + 1
            return {"kind": "hint", "text": ladder[n], "rung": n + 1, "of": len(ladder)}
        tries.pop(key, None)
        return None

    def clear_tries(self, state, set_id, item_id):
        state.get("tries", {}).pop(f"{set_id}::{item_id}", None)
        state.get("misc_used", {}).pop(f"{set_id}::{item_id}", None)


PEDAGOGIES = {"direct": Direct, "inquiry": Inquiry}


# ---------------------------------------------------------------- misconceptions

def match_misconception(item, response):
    for mc in item.get("misconceptions", []):
        for r in mc.get("responses", []):
            if normalize_text(response) == normalize_text(r):
                return mc
        for v in mc.get("values", []):
            got, want = parse_fraction(str(response)), parse_fraction(str(v))
            if got and want and got[0] == want[0]:
                return mc
        if mc.get("pattern") and re.search(mc["pattern"], str(response), re.I):
            return mc
    return None


# ---------------------------------------------------------------- AI follow-up

def _llm_available():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return False
    try:
        import anthropic  # noqa: F401
        return True
    except ImportError:
        return False


def ai_followup(pack, set_id, entry, response):
    """One short Socratic follow-up question, or "" if none is needed. None if AI unavailable."""
    if not _llm_available():
        return None
    s = pack.sets.get(set_id, {})
    ep = s.get("episode", {})
    try:
        import anthropic
        client = anthropic.Anthropic()
        prompt = f"""You are a patient, inquiry-based tutor for a {pack.subject or 'school'} student, working alone on a device.
Topic: {s.get('title', set_id)}. The big idea they should construct: {ep.get('key_learning', '')}
Phase: {entry.get('phase')} ({entry.get('kind', '')}). Question asked: {entry['prompt']}
Student's answer: {response}

Decide if ONE short follow-up question would help the student think further (e.g. to justify,
notice something they missed, or confront a misconception). Rules: never give the answer or
explain the concept; be warm; use simple words a 10-12 year old understands; reply in the
student's language. If the answer is already thoughtful, or this is a prediction, reply with nothing.
Reply as JSON only: {{"followup": "question or empty string"}}"""
        model = os.environ.get("TUTOR_LLM_MODEL", "claude-sonnet-5-5")
        msg = client.messages.create(model=model, max_tokens=200, messages=[{"role": "user", "content": prompt}])
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        return (json.loads(text[text.find("{"): text.rfind("}") + 1]).get("followup") or "").strip()
    except Exception:
        return None
