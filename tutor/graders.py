"""Graders: one per item type. Each returns a GradeResult with a score in [0, 1].

Adding a new answer type = write a function `grade_x(item, response) -> GradeResult`
and register it in GRADERS.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import subprocess
import sys
import tempfile
import unicodedata
from dataclasses import dataclass, field
from fractions import Fraction


@dataclass
class GradeResult:
    score: float
    feedback: str = ""
    needs_review: bool = False      # a teacher should double-check this grade
    detail: dict = field(default_factory=dict)


# ---------------------------------------------------------------- helpers

def normalize_text(s: str) -> str:
    """Unicode-safe normalisation (works for Hindi/Kannada as well as English)."""
    s = unicodedata.normalize("NFC", str(s)).casefold().strip()
    s = re.sub(r"\s+", " ", s)
    return s.strip(" .!?।,;:'\"")


_MIXED = re.compile(r"^\s*(-?)\s*(\d+)\s+(\d+)\s*/\s*(\d+)\s*$")
_FRAC = re.compile(r"^\s*(-?\d+)\s*/\s*(-?\d+)\s*$")


def parse_fraction(s: str) -> tuple[Fraction, str] | None:
    """Parse '3/4', '-3/4', '1 1/2', '2', '0.75'. Returns (value, form)."""
    s = str(s).strip()
    if not s:
        return None
    m = _MIXED.match(s)
    if m:
        sign, whole, num, den = m.groups()
        if int(den) == 0:
            return None
        v = int(whole) + Fraction(int(num), int(den))
        return (-v if sign else v), "mixed"
    m = _FRAC.match(s)
    if m:
        num, den = int(m.group(1)), int(m.group(2))
        if den == 0:
            return None
        return Fraction(num, den), "fraction"
    try:
        if re.fullmatch(r"-?\d+", s):
            return Fraction(int(s)), "integer"
        return Fraction(s), "decimal"
    except (ValueError, ZeroDivisionError):
        return None


def _is_simplest(s: str) -> bool:
    s = s.strip()
    m = _MIXED.match(s)
    if m:
        num, den = int(m.group(3)), int(m.group(4))
        return num < den and Fraction(num, den).denominator == den
    m = _FRAC.match(s)
    if m:
        num, den = int(m.group(1)), int(m.group(2))
        return den > 0 and Fraction(num, den).denominator == den and den != 1
    return bool(re.fullmatch(r"-?\d+", s))


# ---------------------------------------------------------------- graders

def grade_mcq(item, response) -> GradeResult:
    options = item["options"]
    if isinstance(response, int) or (isinstance(response, str) and response.isdigit() and response not in options):
        idx = int(response)
        response = options[idx] if 0 <= idx < len(options) else ""
    ok = normalize_text(response) == normalize_text(item["answer"])
    return GradeResult(1.0 if ok else 0.0, "" if ok else f"The answer was: {item['answer']}")


def grade_numeric(item, response) -> GradeResult:
    try:
        val = float(str(response).replace(",", "").strip())
    except ValueError:
        return GradeResult(0.0, "Please enter a number.")
    tol = float(item.get("tolerance", 1e-6))
    ok = abs(val - float(item["answer"])) <= tol
    return GradeResult(1.0 if ok else 0.0)


def grade_fraction(item, response) -> GradeResult:
    """Exact fraction answers. item: {"answer": "3/4", "form": "simplest"|"any"}."""
    got = parse_fraction(response)
    if got is None:
        return GradeResult(0.0, "Write your answer like 3/4, 1 1/2 or 2.")
    expected, _ = parse_fraction(item["answer"])
    value, form = got
    if value != expected:
        return GradeResult(0.0)
    if item.get("form") == "improper" and form != "fraction":
        return GradeResult(0.5, "Right value — but write it as an improper fraction like 7/3.")
    if item.get("form", "simplest") == "simplest":
        if form == "decimal":
            return GradeResult(0.5, "Right value — but write it as a fraction.")
        if not _is_simplest(str(response)):
            return GradeResult(0.5, "Right value — now simplify it fully.")
    return GradeResult(1.0)


def grade_text(item, response) -> GradeResult:
    """Short typed answer matched against a list of accepted answers."""
    accepted = item.get("accepted") or [item["answer"]]
    ok = normalize_text(response) in {normalize_text(a) for a in accepted}
    return GradeResult(1.0 if ok else 0.0, "" if ok else f"Expected: {accepted[0]}")


_RUNNER = r'''
import json, sys
__tok = sys.argv[1]
__src = open(sys.argv[2], encoding="utf-8").read()
__spec = json.load(open(sys.argv[3], encoding="utf-8"))
__out = {"compile_error": None, "results": []}
__g = {"__name__": "__student__"}
try:
    exec(__spec.get("preamble", ""), __g)
    exec(compile(__src, "<your code>", "exec"), __g)
except Exception as e:
    __out["compile_error"] = f"{type(e).__name__}: {e}"
if __out["compile_error"] is None:
    for t in __spec["tests"]:
        try:
            exec(t, __g)
            __out["results"].append([t, True, ""])
        except AssertionError as e:
            __out["results"].append([t, False, "assertion failed" + (f": {e}" if str(e) else "")])
        except Exception as e:
            __out["results"].append([t, False, f"{type(e).__name__}: {e}"])
print(__tok + json.dumps(__out))
'''


def _limit_resources():  # pragma: no cover - runs in the child process
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_CPU, (4, 4))
        resource.setrlimit(resource.RLIMIT_AS, (1024 * 1024 * 1024, 1024 * 1024 * 1024))
    except Exception:
        pass


def grade_code_python(item, response) -> GradeResult:
    """Run the student's Python against the item's test asserts.

    PROTOTYPE ONLY: this runs code in a subprocess with CPU/memory limits but no
    real sandbox. In production use a container/jail (e.g. Judge0, gVisor, Firecracker).
    """
    tok = "@@" + secrets.token_hex(8) + "@@"
    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, "student.py")
        spec = os.path.join(d, "spec.json")
        runner = os.path.join(d, "runner.py")
        open(src, "w", encoding="utf-8").write(str(response))
        json.dump({"preamble": item.get("preamble", ""), "tests": item["tests"]}, open(spec, "w"))
        open(runner, "w").write(_RUNNER)
        try:
            proc = subprocess.run(
                [sys.executable, "-I", runner, tok, src, spec],
                cwd=d, capture_output=True, text=True, timeout=8,
                preexec_fn=_limit_resources if os.name == "posix" else None,
            )
        except subprocess.TimeoutExpired:
            return GradeResult(0.0, "Your code took too long (infinite loop?).")
    line = next((l for l in reversed(proc.stdout.splitlines()) if l.startswith(tok)), None)
    if line is None:
        if proc.returncode is not None and proc.returncode < 0:  # killed by the CPU/memory limit
            return GradeResult(0.0, "Your code took too long or used too much memory (infinite loop?).")
        return GradeResult(0.0, "Your code crashed: " + (proc.stderr.strip().splitlines() or ["unknown error"])[-1])
    out = json.loads(line[len(tok):])
    if out["compile_error"]:
        return GradeResult(0.0, "Your code has an error: " + out["compile_error"])
    results = out["results"]
    passed = sum(1 for _, ok, _ in results if ok)
    failed = [(t, msg) for t, ok, msg in results if not ok]
    fb = f"{passed}/{len(results)} tests passed."
    if failed:
        fb += f" First failing check: `{failed[0][0]}` ({failed[0][1]})"
    return GradeResult(passed / max(1, len(results)), fb, detail={"tests": results})


# ---- free text (AI-graded, with an offline fallback)

def _llm_available() -> bool:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return False
    try:
        import anthropic  # noqa: F401
        return True
    except ImportError:
        return False


def _llm_grade(item, response) -> GradeResult:
    import anthropic
    client = anthropic.Anthropic()
    model = os.environ.get("TUTOR_LLM_MODEL", "claude-sonnet-5-5")
    prompt = (
        "You are grading a student's short answer for a tutoring system.\n"
        f"Question: {item['prompt']}\n"
        f"Rubric: {item['rubric']}\n"
        f"Student answer: {response}\n\n"
        'Reply with JSON only: {"score": 0..1, "feedback": "one or two kind sentences '
        'addressed to the student", "confidence": 0..1}'
    )
    msg = client.messages.create(model=model, max_tokens=300, messages=[{"role": "user", "content": prompt}])
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    data = json.loads(text[text.find("{"): text.rfind("}") + 1])
    conf = float(data.get("confidence", 0.5))
    return GradeResult(
        max(0.0, min(1.0, float(data["score"]))), data.get("feedback", ""),
        needs_review=conf < 0.7, detail={"grader": "llm", "confidence": conf},
    )


def _heuristic_grade(item, response) -> GradeResult:
    """Offline fallback: checks required keywords + length, and asks a teacher to confirm."""
    text = normalize_text(response)
    words = re.findall(r"\w+", text)
    keywords = [normalize_text(k) for k in item.get("keywords", [])]
    has_kw = (not keywords) or any(k in text for k in keywords)  # substring: catches inflections and symbols like "/"
    long_enough = len(words) >= int(item.get("min_words", 5))
    if has_kw and long_enough:
        return GradeResult(0.75, "Looks good! (Provisional — your teacher will confirm.)",
                           needs_review=True, detail={"grader": "heuristic"})
    reason = "Use the key word in your answer." if not has_kw else "Write a fuller answer."
    return GradeResult(0.3, reason, needs_review=False, detail={"grader": "heuristic"})


def grade_free_text(item, response) -> GradeResult:
    if not str(response).strip():
        return GradeResult(0.0, "Please write an answer.")
    if _llm_available():
        try:
            return _llm_grade(item, response)
        except Exception as e:  # network/API problems fall back, flagged for review
            r = _heuristic_grade(item, response)
            r.detail["llm_error"] = str(e)
            return r
    return _heuristic_grade(item, response)


GRADERS = {
    "mcq": grade_mcq,
    "numeric": grade_numeric,
    "fraction": grade_fraction,
    "text": grade_text,
    "code_python": grade_code_python,
    "free_text": grade_free_text,
}


def grade(item: dict, response) -> GradeResult:
    try:
        fn = GRADERS[item["type"]]
    except KeyError:
        raise ValueError(f"No grader for item type {item['type']!r}")
    return fn(item, response)
