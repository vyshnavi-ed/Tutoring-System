"""LLM clients for the Science Buddy. The engine only needs `respond(system, messages) -> dict`.

AnthropicLLM forces a structured tool call so every turn returns the reply *and* the
assessment data (evidence, level changes, inquiry state, wellbeing flag) in one go.
DemoLLM gives canned replies so the screens can be tried without an API key.
"""
from __future__ import annotations

import base64
import os

from .photos import SCREEN_PROMPT, parse_screen
from .skills import ALL, LEVELS, STAGES

SKILL_ENUM = {"type": "string", "enum": ALL}

RESPOND_TOOL = {
    "name": "respond",
    "description": "Send your next turn to the learner and record what you observed about their skills.",
    "input_schema": {
        "type": "object",
        "properties": {
            "reply": {"type": "string", "description": "What you say to the learner: one or two short sentences, at most ONE question."},
            "ladder_step": {"type": "integer", "minimum": 0, "maximum": 5,
                            "description": "Scaffolding-ladder step used for the FOCUS skill this turn (0 = none, 1 open ... 5 explain)."},
            "evidence": {"type": "array", "description": "Skills the learner showed in their LAST message.",
                         "items": {"type": "object", "properties": {
                             "skill": SKILL_ENUM,
                             "quote": {"type": "string", "description": "Short quote of the learner's words."},
                             "signal": {"type": "string", "enum": LEVELS}},
                             "required": ["skill", "quote", "signal"]}},
            "level_changes": {"type": "array", "description": "Only when the evidence clearly justifies a new level.",
                              "items": {"type": "object", "properties": {
                                  "skill": SKILL_ENUM, "to": {"type": "string", "enum": LEVELS},
                                  "reason": {"type": "string", "description": "One line, for the teacher."},
                                  "plain_words": {"type": "string", "description": "For the learner, e.g. 'You planned a fair test on your own.'"}},
                                  "required": ["skill", "to", "reason"]}},
            "skill_named": {"type": "string", "description": "Skill you named for the learner this turn, or empty."},
            "inquiry": {"type": "object", "description": "Current state of the inquiry (omit fields that haven't changed).",
                        "properties": {
                            "title": {"type": "string", "description": "Short title, e.g. 'Drooping tulsi plant'."},
                            "question": {"type": "string", "description": "The investigable question, once there is one."},
                            "stage": {"type": "string", "enum": STAGES},
                            "task": {"type": "string", "description": "What the learner will go and do before next time, or empty."},
                            "chapters": {"type": "array", "items": {"type": "string"}, "description": "Matching chapter ids, e.g. g6c8."},
                            "status": {"type": "string", "enum": ["open", "done"]},
                            "self_assessment": {"type": "object", "properties": {
                                "easiest": {"type": "string"}, "hardest": {"type": "string"}}}}},
            "wellbeing_concern": {"type": "string", "description": "If the child mentioned being hurt, bullied, unsafe or very upset: a short neutral summary. Otherwise empty."},
            "end_session": {"type": "boolean", "description": "True once the session has closed with a reflection and a next question."},
        },
        "required": ["reply"],
    },
}


class AnthropicLLM:
    demo = False

    def __init__(self, model: str | None = None):
        import anthropic
        self.client = anthropic.Anthropic()
        self.model = model or os.environ.get("TUTOR_BUDDY_MODEL", "claude-sonnet-5-5")
        self.force_tool = True  # some models don't allow forcing a tool; we fall back to "auto"

    def _create(self, system, messages):
        kw = dict(model=self.model, max_tokens=1200, system=system, messages=messages, tools=[RESPOND_TOOL])
        kw["tool_choice"] = {"type": "tool", "name": "respond"} if self.force_tool else {"type": "auto"}
        return self.client.messages.create(**kw)

    def respond(self, system: str, messages: list[dict]) -> dict:
        try:
            msg = self._create(system, messages)
        except Exception as e:
            if self.force_tool and "tool_choice" in str(e):
                self.force_tool = False
                msg = self._create(system, messages)
            else:
                raise
        for block in msg.content:
            if getattr(block, "type", "") == "tool_use":
                return dict(block.input)
        return parse_text_reply("".join(getattr(b, "text", "") for b in msg.content))

    def screen_image(self, jpeg: bytes) -> dict:
        """Check a photo before it is stored. Returns {"category", "reason"}."""
        msg = self.client.messages.create(
            model=self.model, max_tokens=200,
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                             "data": base64.b64encode(jpeg).decode()}},
                {"type": "text", "text": SCREEN_PROMPT}]}])
        return parse_screen("".join(getattr(b, "text", "") for b in msg.content))


def parse_text_reply(text: str) -> dict:
    """The model answered in plain text instead of calling the tool: use JSON if present, else the text."""
    import json
    text = (text or "").strip()
    if "{" in text and '"reply"' in text:
        try:
            data = json.loads(text[text.find("{"): text.rfind("}") + 1])
            if isinstance(data, dict) and data.get("reply"):
                return data
        except ValueError:
            pass
    return {"reply": text}


class DemoLLM:
    """Canned curious-friend replies. NOT a tutor — just lets you click through the screens."""
    demo = True
    LINES = [
        "Ooh, interesting! What exactly did you see?",
        "Good detail. What else did you notice?",
        "Hmm, could be! What did you see that made you think that?",
        "How could you find out if that's right?",
        "If you try that, what would be different and what would stay the same?",
        "Great plan. Go and check, then come back and tell me what you find!",
    ]

    def screen_image(self, jpeg: bytes) -> dict:
        # Demo mode can't check photos, so it refuses them (nothing unchecked is ever stored).
        # TUTOR_DEMO_ACCEPT_PHOTOS=1 is for developers testing the screens only.
        if os.environ.get("TUTOR_DEMO_ACCEPT_PHOTOS") == "1":
            return {"category": "object", "reason": "demo: not really checked"}
        return {"category": "unchecked", "reason": "demo mode has no AI to check photos"}

    def respond(self, system: str, messages: list[dict]) -> dict:
        n = sum(1 for m in messages if m["role"] == "user")
        last = messages[-1]["content"] if messages else ""
        if isinstance(last, list):
            last = " ".join(b.get("text", "") for b in last if b.get("type") == "text")
        if "[session start]" in last:
            return {"reply": "Hi! Seen anything interesting today? (Demo mode: replies are canned until an AI key is added.)"}
        if "learner wants to stop" in last:
            return {"reply": "What did we find out today? And what are you wondering now?"}
        out = {"reply": self.LINES[(n - 1) % len(self.LINES)]}
        words = last.split()
        if len(words) >= 3:
            out["evidence"] = [{"skill": "observing", "quote": " ".join(words[:12]),
                                "signal": "developing" if len(words) > 8 else "emerging"}]
        if n == 2:
            out["inquiry"] = {"title": "Something I noticed", "stage": "observe", "status": "open"}
        return out


def default_llm():
    if os.environ.get("ANTHROPIC_API_KEY") and os.environ.get("TUTOR_BUDDY_DEMO") != "1":
        try:
            return AnthropicLLM()
        except Exception:
            pass
    return DemoLLM()
