import os
import random
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["TUTOR_NO_APP"] = "1"
os.environ.pop("ANTHROPIC_API_KEY", None)  # tests use the offline free-text grader

from tutor.engine import Engine  # noqa: E402
from tutor.pack import load_packs  # noqa: E402
from tutor.store import Store  # noqa: E402

PACKS = ROOT / "packs"


class FakeClock:
    def __init__(self, t=1_800_000_000.0):
        self.t = t

    def __call__(self):
        return self.t


@pytest.fixture
def engine(tmp_path):
    return Engine(load_packs(PACKS), Store(str(tmp_path / "t.db")), rng=random.Random(0), clock=FakeClock())


def correct_answer(item):
    t = item["type"]
    if t in ("mcq", "fraction", "numeric"):
        return str(item["answer"])
    if t == "text":
        return (item.get("accepted") or [item["answer"]])[0]
    if t == "code_python":
        return item["solution"]
    if t == "free_text":
        kw = (item.get("keywords") or ["answer"])[0]
        return f"I think the {kw} is used here because it makes the whole idea clear 1/2 + 1/3 = 5/6 easily"
    raise ValueError(t)


def run(engine, student, pack_id, should_pass, max_steps=400, stop=None):
    """Drive a simulated student. should_pass(set_id, item, history) -> bool.
    Returns the trace: list of ("activity", title) / ("message", text) / ("item", set_id, item_id, passed) / ("done", text)."""
    pack = engine.packs[pack_id]
    trace = []
    a = engine.action(student, pack_id)
    for _ in range(max_steps):
        if stop and stop(trace):
            break
        if a["type"] in ("activity", "message", "explain", "connect"):
            trace.append((a["type"], a.get("title") or a.get("text") or a.get("key_learning")))
            a = engine.acknowledge(student, pack_id)
        elif a["type"] in ("prompt", "explore"):
            trace.append((a["type"], a.get("phase"), a.get("prompt")))
            r = engine.answer(student, pack_id, "I think it is because the pieces are the same size")
            a = r["action"]
        elif a["type"] == "item":
            item = pack.item(a["set_id"], a["item_id"])
            ok = should_pass(a["set_id"], item, trace)
            r = engine.answer(student, pack_id, correct_answer(item) if ok else "definitely wrong 0")
            trace.append(("item", a["set_id"], a["item_id"], r["result"]["passed"], r["result"].get("retry", False)))
            a = r["action"]
        else:
            trace.append(("done", a.get("text")))
            break
    return trace


def asked(trace):
    return [t[1] for t in trace if t[0] == "item"]
