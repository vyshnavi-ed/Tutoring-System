"""Code-level guardrails that do not depend on the AI behaving well.

- wellbeing_concern(): spots worrying disclosures in what the child writes -> flag for human review
- unsafe_suggestion(): spots unsafe investigation suggestions in the tutor's reply -> regenerate
- claims_human():     the tutor must never claim to be a person
- one_question():     at most one question per turn (keeps voice turns short)
- redact():           strips phone numbers / emails / street addresses before storing or sending
"""
from __future__ import annotations

import re

_WELLBEING = [
    r"\b(hit|hits|hitting|beat|beats|beating|slap\w*|kick\w*|punch\w*)\s+(me|us)\b",
    r"\b(hurt\w*|harm\w*)\s+(me|myself)\b", r"\bkill\w*\s+(me|myself)\b", r"\bsuicid\w*", r"\bwants? to die\b", r"\bwish I (was|were) dead\b",
    r"\bbull(y|ies|ied|ying)\b", r"\b(scared|afraid|frightened)\s+(of (my|him|her|them|going|home|school|someone)|to go)\b", r"\bnot safe\b|\bunsafe at\b",
    r"\b(touch\w*)\s+me\b", r"\babus\w*", r"\bno one (loves|cares)\b", r"\b(very|so|really) (sad|upset|lonely)\b",
    r"\b(run|ran) away\b", r"\bcutting myself\b",
    # Hindi (romanised and Devanagari) — a starting list for review with local educators
    r"\bmaar(ta|ti|te)\b", r"\bdar lag\w*", r"मारत[ाीे]", r"डर लग",
]
_WELLBEING_RE = re.compile("|".join(_WELLBEING), re.I)


def wellbeing_concern(text: str) -> str | None:
    m = _WELLBEING_RE.search(text or "")
    return m.group(0) if m else None


_UNSAFE = {
    "flame": r"\b(candle|matchstick|matches|lighter|flame|bonfire|set (it )?on fire|burn (it|the))\b",
    "sharp": r"\b(knife|knives|blade|razor|cutter)\b",
    "electricity": r"\b(socket|mains|plug (it )?in|electric(al)? (wire|current)|battery|batteries)\b",
    "chemicals": r"\b(bleach|acid|phenyl|kerosene|petrol|toilet cleaner|insecticide|pesticide|medicine)\b",
    "tasting": r"\b(taste|lick|swallow|drink)\b(?!\s+(water|it\?)\b)",
    "animals": r"\b(catch|trap|poke|squash|pick up|disturb)\b[^.?!]{0,25}\b(ants?|bees?|birds?|insects?|lizards?|frogs?|snakes?|animals?|worms?|spiders?)\b",
}
_HEAT = re.compile(r"\b(boil\w*|stove|gas burner|hot water|heat (it|the|some))\b", re.I)
_ADULT = re.compile(r"\b(adult|grown-?up|parent|mum|mom|dad|amma|appa|papa|mummy|teacher)\b", re.I)
_NEGATED = re.compile(r"\b(don'?t|do not|never|no|not|avoid|without)\b", re.I)


def unsafe_suggestion(reply: str) -> str | None:
    """Return the kind of unsafe content suggested, or None. Mentions inside a warning
    ("don't taste it") are allowed."""
    for sentence in re.split(r"(?<=[.!?])\s+", reply or ""):
        for kind, pat in _UNSAFE.items():
            m = re.search(pat, sentence, re.I)
            if m and not _NEGATED.search(sentence[: m.start()]):
                return kind
        if _HEAT.search(sentence) and not _ADULT.search(reply) and not _NEGATED.search(sentence):
            return "heat without an adult"
    return None


_HUMAN = re.compile(r"\bI(?:'m| am)\s+(?:a\s+)?(?:real\s+)?(person|human|kid|child|girl|boy|student|teacher)\b"
                    r"|\bmy (mum|mom|dad|family|body|brother|sister)\b", re.I)


def claims_human(reply: str) -> bool:
    return bool(_HUMAN.search(reply or ""))


def one_question(reply: str) -> str:
    """Keep everything up to and including the first question mark."""
    reply = (reply or "").strip()
    if reply.count("?") <= 1:
        return reply
    return reply[: reply.index("?") + 1]


_PHONE = re.compile(r"(?<!\d)(?:\+?\d[\d\s-]{8,}\d)(?!\d)")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")
_ADDRESS = re.compile(r"\b(house|flat|door)\s*(no\.?|number|#)\s*\S+", re.I)


def redact(text: str) -> str:
    text = _PHONE.sub("[number removed]", text or "")
    text = _EMAIL.sub("[email removed]", text)
    return _ADDRESS.sub("[address removed]", text)
