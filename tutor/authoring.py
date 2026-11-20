"""AI-assisted authoring: generate a draft subject pack from a short brief, validate it,
and let the model repair its own validation errors. Drafts are hidden from students
until a teacher approves them in the dashboard.

    # needs ANTHROPIC_API_KEY
    python -m tutor.authoring generate --strategy prereq_graph \
        --title "Decimals" --subject "Mathematics (Class 6)" \
        --brief "Place value of decimals, comparing, adding and subtracting decimals, converting fractions to decimals" \
        --out packs/math_decimals.json

    python -m tutor.authoring validate packs/*.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .strategies import STRATEGIES
from .validate import validate

PACKS_DIR = Path(__file__).resolve().parent.parent / "packs"
EXAMPLE_FOR = {"level_descent": "ds_linked_lists.json", "prereq_graph": "math_fractions.json",
               "spaced_repetition": "english_vocab.json"}

GUIDE = {
    "level_descent": """Design it with the Anderson-Bloom taxonomy (Ramesh 2014 tutoring rules):
- units = Units-of-Study (2-6 per competency), each with an "activity" (top-level instructional activity) and "sets" = the top-level item sets (one per item TYPE at the unit's highest cognitive level).
- Every set has "level" (Remember/Understand/Apply/Analyze/Evaluate/Create), an "activity" for that level, and "links" = the sets ONE cognitive level lower that test the prerequisite knowledge for it (the tutoring rule table). Remember-level sets have no links.
- Provide at least 2 items per set (students get a *different* item after remediation).""",
    "prereq_graph": """Design it as a skill graph:
- Each set is one skill with a lesson ("activity"), and "links" = its direct prerequisite skills (must be acyclic). Include the foundational skills students commonly lack, so failures can be diagnosed.
- units[0].sets = the goal skills, in teaching order.
- 5-6 items per skill, varied numbers; each item has a "hint" and a worked "explanation".""",
    "spaced_repetition": """Design it as flashcards:
- Each set is one card (word/fact) with an intro "activity" (meaning, example; add a translation line if useful).
- items ordered easiest → hardest: recognise (mcq) → recall in context (mcq cloze) → produce (text) → use (free_text with rubric and keywords). No links.
- units[0].sets = the order new cards are introduced.""",
}

ITEM_TYPES = """Item types (field "type"):
- mcq: options[], answer (must exactly equal one option)
- numeric: answer (number), optional tolerance
- fraction: answer like "3/4" or "2", form "simplest"|"improper"|"any"
- text: accepted[] (exact typed answers; unicode OK, e.g. Hindi/Kannada)
- code_python: preamble, starter, tests[] (python assert statements), solution (must pass the tests)
- free_text: rubric, keywords[], min_words
Every item has a unique "id" within its set and a "prompt" (markdown allowed). Optional: hint, explanation."""


def _example(strategy: str, max_sets: int = 3) -> dict:
    data = json.loads((PACKS_DIR / EXAMPLE_FOR[strategy]).read_text(encoding="utf-8"))
    keep = list(data["item_sets"])[:max_sets]
    data["item_sets"] = {k: data["item_sets"][k] for k in keep}
    used = {s.get("activity") for s in data["item_sets"].values()} | {u.get("activity") for u in data["units"]}
    data["activities"] = {k: v for k, v in data["activities"].items() if k in used}
    for u in data["units"]:
        u["sets"] = [s for s in u["sets"] if s in keep]
    for s in data["item_sets"].values():
        s["links"] = [l for l in s.get("links", []) if l in keep]
    return data


def _call_model(messages, model):
    import anthropic
    client = anthropic.Anthropic()
    with client.messages.stream(model=model, max_tokens=32000, messages=messages) as stream:
        msg = stream.get_final_message()
    return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")


def _extract_json(text: str) -> dict:
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start:end + 1])


def generate(strategy, title, subject, brief, pack_id, model, max_repairs=2, log=print) -> dict:
    prompt = f"""You are an instructional designer building content for an intelligent tutoring system.
Create a complete subject pack as JSON.

Title: {title}
Subject / level: {subject}
Brief: {brief}
Strategy: {strategy} — {STRATEGIES[strategy].description}

{GUIDE[strategy]}

{ITEM_TYPES}

Use exactly this JSON shape (a trimmed example from another pack follows). Set "id": "{pack_id}",
"strategy": "{strategy}", "status": "draft". Answers must be correct — they will be checked automatically.

EXAMPLE:
{json.dumps(_example(strategy), ensure_ascii=False, indent=1)}

Reply with the JSON object only."""
    messages = [{"role": "user", "content": prompt}]
    for attempt in range(max_repairs + 1):
        log(f"[authoring] calling {model} (attempt {attempt + 1})…")
        text = _call_model(messages, model)
        try:
            data = _extract_json(text)
        except json.JSONDecodeError as e:
            errors, warnings, data = [f"output was not valid JSON: {e}"], [], None
        else:
            data.update(id=pack_id, strategy=strategy, status="draft")
            errors, warnings = validate(data)
        if not errors:
            for w in warnings:
                log("  warning:", w)
            return data
        log(f"  {len(errors)} validation error(s); asking the model to fix them")
        messages += [{"role": "assistant", "content": text},
                     {"role": "user", "content": "The pack failed validation:\n- " + "\n- ".join(errors[:40]) +
                      "\nReturn the corrected full JSON object only."}]
    raise RuntimeError("could not produce a valid pack:\n" + "\n".join(errors))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m tutor.authoring")
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate", help="draft a new pack with an LLM")
    g.add_argument("--strategy", required=True, choices=list(STRATEGIES))
    g.add_argument("--title", required=True)
    g.add_argument("--subject", default="")
    g.add_argument("--brief", required=True)
    g.add_argument("--id")
    g.add_argument("--out", required=True)
    g.add_argument("--model", default=os.environ.get("TUTOR_LLM_MODEL", "claude-sonnet-5-5"))
    v = sub.add_parser("validate", help="validate pack files")
    v.add_argument("files", nargs="+")
    v.add_argument("--no-code", action="store_true", help="skip running code solutions")
    args = ap.parse_args(argv)

    if args.cmd == "validate":
        bad = 0
        for f in args.files:
            data = json.loads(Path(f).read_text(encoding="utf-8"))
            errors, warnings = validate(data, run_code=not args.no_code)
            print(f"{f}: {'OK' if not errors else 'FAILED'} ({len(errors)} errors, {len(warnings)} warnings)")
            for e in errors:
                print("  error:", e)
            for w in warnings:
                print("  warning:", w)
            bad += bool(errors)
        return 1 if bad else 0

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Set ANTHROPIC_API_KEY to generate packs.", file=sys.stderr)
        return 2
    pack_id = args.id or Path(args.out).stem
    data = generate(args.strategy, args.title, args.subject, args.brief, pack_id, args.model)
    Path(args.out).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote draft pack {args.out} — review and approve it in the teacher dashboard")
    return 0


if __name__ == "__main__":
    sys.exit(main())
