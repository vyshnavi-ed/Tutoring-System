"""Science Buddy conversation engine: sessions, learner profile, guardrails, assessment records."""
from __future__ import annotations

import json
import time

from . import guards
from .llm import default_llm
from .prompt import CHAPTERS, build_system
from .skills import ALL, LEVELS, STAGES, choose_focus

PACK_ID = "science_buddy"  # used to file alerts alongside the topic packs
CHAPTER_IDS = {c["id"] for c in CHAPTERS}
RESUME_WINDOW = 3 * 3600   # a session left open for less than this is resumed, not restarted

SCHEMA = """
CREATE TABLE IF NOT EXISTS buddy_profiles (student_id TEXT PRIMARY KEY, profile TEXT, updated REAL);
CREATE TABLE IF NOT EXISTS buddy_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT, started REAL, ended REAL,
    focus TEXT, inquiry_id TEXT, closed INTEGER DEFAULT 0, closing INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS buddy_turns (
    id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER, student_id TEXT, role TEXT,
    text TEXT, ts REAL, meta TEXT);
"""

FALLBACK = "Hmm, let's think about that a different way. What did you notice?"
CARE_REPLY = ("I'm really sorry that's happening. Please tell a grown-up you trust — a parent, teacher or school "
              "counsellor — today. You don't have to deal with this alone.")
_TRUSTED = ("parent", "teacher", "counsellor", "counselor", "grown-up", "adult", "mum", "mom", "dad", "trust")
SAFE_FALLBACK = "Let's find a safer way to check that — no heat, sharp things or chemicals. What could you just watch closely instead?"


class ConsentRequired(Exception):
    pass


class Buddy:
    def __init__(self, store, llm=None, clock=time.time):
        self.store, self.llm, self.clock = store, llm or default_llm(), clock
        with store.lock:
            store.conn.executescript(SCHEMA)

    # ------------------------------------------------------------ profiles
    def _new_profile(self, student_id):
        return {"name": student_id, "grade": None, "consent": None,
                "skills": {s: {"level": "emerging", "assessed": False, "evidence": [], "history": []} for s in ALL},
                "inquiries": [], "achievements": []}

    def profile(self, student_id) -> dict:
        rows = self.store._rows("SELECT profile FROM buddy_profiles WHERE student_id=?", (student_id,))
        return json.loads(rows[0]["profile"]) if rows else self._new_profile(student_id)

    def _save(self, student_id, profile):
        self.store._exec("INSERT INTO buddy_profiles VALUES (?,?,?) ON CONFLICT(student_id) DO UPDATE SET "
                         "profile=excluded.profile, updated=excluded.updated",
                         (student_id, json.dumps(profile), self.clock()))

    def give_consent(self, student_id, parent_name, relation, grade=None):
        """Prototype consent record. Production needs *verifiable* parental consent (e.g. OTP to a parent)."""
        if not parent_name.strip() or not relation.strip():
            raise ValueError("parent name and relationship are required")
        p = self.profile(student_id)
        p["consent"] = {"by": parent_name.strip(), "relation": relation.strip(), "ts": self.clock(),
                        "method": "checkbox (prototype — not verifiable)"}
        if grade:
            p["grade"] = int(grade)
        self._save(student_id, p)
        return p

    def has_consent(self, student_id):
        rows = self.store._rows("SELECT profile FROM buddy_profiles WHERE student_id=?", (student_id,))
        return bool(rows and json.loads(rows[0]["profile"]).get("consent"))

    # ------------------------------------------------------------ sessions
    def _open_session(self, student_id):
        rows = self.store._rows("SELECT * FROM buddy_sessions WHERE student_id=? AND closed=0 ORDER BY id DESC LIMIT 1",
                                (student_id,))
        return rows[0] if rows else None

    def _turns(self, session_id):
        rows = self.store._rows("SELECT * FROM buddy_turns WHERE session_id=? ORDER BY id", (session_id,))
        for r in rows:
            r["meta"] = json.loads(r["meta"] or "{}")
        return rows

    def _add_turn(self, session_id, student_id, role, text, meta=None):
        self.store._exec("INSERT INTO buddy_turns (session_id, student_id, role, text, ts, meta) VALUES (?,?,?,?,?,?)",
                         (session_id, student_id, role, text, self.clock(), json.dumps(meta or {})))

    def _close(self, session_id):
        self.store._exec("UPDATE buddy_sessions SET closed=1, ended=? WHERE id=?", (self.clock(), session_id))

    def start(self, student_id) -> dict:
        if not self.has_consent(student_id):
            raise ConsentRequired()
        sess = self._open_session(student_id)
        if sess:
            turns = self._turns(sess["id"])
            last = turns[-1]["ts"] if turns else sess["started"]
            if self.clock() - last < RESUME_WINDOW:
                return self._view(student_id, sess, turns, resumed=True)
            self._close(sess["id"])
        profile = self.profile(student_id)
        open_inq = [i for i in profile["inquiries"] if i.get("status") != "done"]
        stage = open_inq[-1].get("stage") if open_inq else None
        levels = {s: v["level"] for s, v in profile["skills"].items()}
        focus = choose_focus(levels, stage)
        cur = self.store._exec("INSERT INTO buddy_sessions (student_id, started, focus, inquiry_id) VALUES (?,?,?,?)",
                               (student_id, self.clock(), focus, open_inq[-1]["id"] if open_inq else None))
        sess = self._open_session(student_id)
        self._add_turn(sess["id"], student_id, "event", "[session start — greet the learner by name and begin]")
        self._tutor_turn(student_id, sess, profile, learner_text="")
        return self._view(student_id, sess, self._turns(sess["id"]))

    def message(self, student_id, text) -> dict:
        if not self.has_consent(student_id):
            raise ConsentRequired()
        sess = self._open_session(student_id)
        if not sess:
            self.start(student_id)
            sess = self._open_session(student_id)
        text = guards.redact(str(text).strip())[:2000]
        if not text:
            return self._view(student_id, sess, self._turns(sess["id"]))
        concern = guards.wellbeing_concern(text)
        self._add_turn(sess["id"], student_id, "learner", text, {"wellbeing_match": concern} if concern else None)
        if concern:
            self._wellbeing_alert(student_id, sess, f"Possible worrying disclosure (matched “{concern}”).", text)
        profile = self.profile(student_id)
        out = self._tutor_turn(student_id, sess, profile, learner_text=text, concern=concern)
        if out.get("end_session") and sess["closing"]:
            self._close(sess["id"])
        return self._view(student_id, self._session(sess["id"]), self._turns(sess["id"]))

    def stop(self, student_id) -> dict:
        """Learner pressed 'I'm done for today': the buddy closes with a reflection and a next question."""
        sess = self._open_session(student_id)
        if not sess:
            return {"closed": True}
        if sess["closing"]:  # pressed twice: close now
            self._close(sess["id"])
            return self._view(student_id, self._session(sess["id"]), self._turns(sess["id"]))
        self.store._exec("UPDATE buddy_sessions SET closing=1 WHERE id=?", (sess["id"],))
        self._add_turn(sess["id"], student_id, "event",
                       "[learner wants to stop — close with a reflection and a next question; ask easiest/hardest if an inquiry just finished]")
        self._tutor_turn(student_id, self._session(sess["id"]), self.profile(student_id), learner_text="")
        return self._view(student_id, self._session(sess["id"]), self._turns(sess["id"]))

    def _session(self, sid):
        return self.store._rows("SELECT * FROM buddy_sessions WHERE id=?", (sid,))[0]

    # ------------------------------------------------------------ one tutor turn
    def _messages(self, turns):
        msgs = []
        for t in turns:
            role = "assistant" if t["role"] == "tutor" else "user"
            if msgs and msgs[-1]["role"] == role:
                msgs[-1]["content"] += "\n" + t["text"]
            else:
                msgs.append({"role": role, "content": t["text"]})
        if msgs and msgs[0]["role"] == "assistant":
            msgs.insert(0, {"role": "user", "content": "[session start]"})
        return msgs

    def _tutor_turn(self, student_id, sess, profile, learner_text, concern=None):
        prev = self.store._rows("SELECT * FROM buddy_sessions WHERE student_id=? AND closed=1 ORDER BY id DESC LIMIT 1",
                                (student_id,))
        if prev:
            days = (self.clock() - (prev[0]["ended"] or prev[0]["started"])) / 86400
            prev[0]["ended_label"] = "earlier today" if days < 1 else f"{int(days)} day(s) ago"
        system = build_system(profile, sess["focus"], prev, demo=getattr(self.llm, "demo", False))
        msgs = self._messages(self._turns(sess["id"]))
        out = self._call(system, msgs)
        reply = out.get("reply") or FALLBACK
        problem = guards.unsafe_suggestion(reply) and f"suggested something unsafe ({guards.unsafe_suggestion(reply)})" \
            or (guards.claims_human(reply) and "claimed to be a person or to have a family/body")
        regenerated = None
        if problem:
            regenerated = problem
            note = {"role": "user", "content": f"[system check: your draft reply was blocked because it {problem}. "
                                               f"Draft: “{reply}”. Write a different, safe reply.]"}
            out2 = self._call(system, msgs + ([note] if msgs[-1]["role"] == "assistant" else
                                              [{"role": "assistant", "content": reply}, note]))
            reply2 = out2.get("reply") or ""
            if reply2 and not guards.unsafe_suggestion(reply2) and not guards.claims_human(reply2):
                out = {**out, **out2}
                reply = reply2
            else:
                reply = SAFE_FALLBACK
        reply = guards.one_question(reply)
        if concern and not any(w in reply.lower() for w in _TRUSTED):
            # safety net: a possible disclosure must always get kindness + "tell a trusted adult"
            reply, regenerated = CARE_REPLY, regenerated or "missed a possible disclosure"
            out = {**out, "evidence": []}
        if concern:
            out = {**out, "evidence": []}  # don't assess skills from a message about the child's wellbeing
        meta = {"focus": sess["focus"], "ladder_step": out.get("ladder_step"),
                "skill_named": out.get("skill_named") or None, "regenerated": regenerated,
                "demo": getattr(self.llm, "demo", False)}
        self._apply(student_id, sess, profile, out, learner_text)
        self._add_turn(sess["id"], student_id, "tutor", reply, meta)
        if regenerated:
            self.store.add_event(student_id, PACK_ID, "reply_blocked", {"reason": regenerated, "session": sess["id"]})
        return out

    def _call(self, system, msgs):
        try:
            return self.llm.respond(system, msgs) or {}
        except Exception as e:  # network/API problems: keep the child moving, log for the teacher
            self.store.add_event("system", PACK_ID, "llm_error", {"error": str(e)[:300]})
            return {"reply": "Sorry, I lost my train of thought for a second. Can you tell me that again?"}

    # ------------------------------------------------------------ assessment + inquiry records
    def _apply(self, student_id, sess, profile, out, learner_text):
        now = self.clock()
        sk = profile["skills"]
        for ev in out.get("evidence") or []:
            s, sig = ev.get("skill"), ev.get("signal")
            if s not in sk or sig not in LEVELS or not learner_text:
                continue
            rec = sk[s]
            rec["evidence"] = (rec["evidence"] + [{"quote": str(ev.get("quote", ""))[:200], "signal": sig,
                                                   "ts": now, "session": sess["id"]}])[-2:]
            rec["evidence_count"] = rec.get("evidence_count", 0) + 1
            if not rec["assessed"]:  # first evidence places the learner
                rec["history"].append({"from": rec["level"], "to": sig, "reason": "Initial placement from first evidence",
                                       "quote": ev.get("quote", ""), "ts": now, "session": sess["id"]})
                rec["level"], rec["assessed"] = sig, True
        for ch in out.get("level_changes") or []:
            s, to = ch.get("skill"), ch.get("to")
            if s not in sk or to not in LEVELS:
                continue
            rec = sk[s]
            frm = rec["level"]
            if rec["assessed"] and abs(LEVELS.index(to) - LEVELS.index(frm)) > 1:
                to = LEVELS[LEVELS.index(frm) + (1 if LEVELS.index(to) > LEVELS.index(frm) else -1)]
            if to == frm:
                continue
            reason = (ch.get("reason") or "").strip() or "(no reason given)"
            rec["history"].append({"from": frm, "to": to, "reason": reason, "plain_words": ch.get("plain_words", ""),
                                   "quote": (rec["evidence"][-1]["quote"] if rec["evidence"] else ""),
                                   "ts": now, "session": sess["id"]})
            rec["level"], rec["assessed"] = to, True
            if LEVELS.index(to) > LEVELS.index(frm) and ch.get("plain_words"):
                profile["achievements"].append({"text": ch["plain_words"], "skill": s, "ts": now})
        inq = out.get("inquiry")
        if isinstance(inq, dict) and any(inq.get(k) for k in ("title", "question", "stage", "task", "status")):
            current = next((i for i in profile["inquiries"] if i["id"] == sess["inquiry_id"]), None) \
                if sess["inquiry_id"] else None
            if current is None or current.get("status") == "done":
                current = {"id": f"inq{len(profile['inquiries']) + 1}", "title": "", "question": "", "stage": "observe",
                           "task": "", "chapters": [], "status": "open", "started": now, "sessions": []}
                profile["inquiries"].append(current)
                self.store._exec("UPDATE buddy_sessions SET inquiry_id=? WHERE id=?", (current["id"], sess["id"]))
                sess = {**sess, "inquiry_id": current["id"]}
            for k in ("title", "question", "task"):
                if k in inq and isinstance(inq[k], str):
                    current[k] = inq[k][:300]
            if inq.get("stage") in STAGES:
                current["stage"] = inq["stage"]
            if inq.get("status") in ("open", "done"):
                current["status"] = inq["status"]
            if isinstance(inq.get("chapters"), list):
                current["chapters"] = sorted(set(current.get("chapters", [])) | {c for c in inq["chapters"] if c in CHAPTER_IDS})
            if isinstance(inq.get("self_assessment"), dict):
                current["self_assessment"] = {k: str(v)[:200] for k, v in inq["self_assessment"].items() if k in ("easiest", "hardest")}
            if sess["id"] not in current["sessions"]:
                current["sessions"].append(sess["id"])
            current["updated"] = now
        if (out.get("wellbeing_concern") or "").strip():
            self._wellbeing_alert(student_id, sess, "The buddy flagged: " + out["wellbeing_concern"].strip()[:300], learner_text)
        if out.get("skill_named"):
            self.store.add_event(student_id, PACK_ID, "skill_named", {"skill": out["skill_named"], "session": sess["id"]})
        self._save(student_id, profile)

    def _wellbeing_alert(self, student_id, sess, message, excerpt):
        self.store.add_alert(student_id, PACK_ID, "wellbeing", f"session:{sess['id']}", message,
                             {"session": sess["id"], "excerpt": excerpt[:500]})

    # ------------------------------------------------------------ views
    def _view(self, student_id, sess, turns, resumed=False):
        return {"session_id": sess["id"], "closed": bool(sess["closed"]), "closing": bool(sess["closing"]),
                "resumed": resumed, "demo": getattr(self.llm, "demo", False),
                "turns": [{"role": t["role"], "text": t["text"]} for t in turns if t["role"] in ("learner", "tutor")]}

    def progress(self, student_id) -> dict:
        """Learner-facing: specific things they can now do, in plain words — no levels."""
        p = self.profile(student_id)
        return {"name": p["name"], "achievements": p["achievements"][-10:][::-1],
                "inquiries": [{"title": i["title"], "question": i["question"], "task": i["task"], "status": i["status"]}
                              for i in p["inquiries"]][::-1]}

    def teacher_view(self, student_id) -> dict:
        p = self.profile(student_id)
        sessions = self.store._rows("SELECT * FROM buddy_sessions WHERE student_id=? ORDER BY id DESC", (student_id,))
        for s in sessions:
            s["turns"] = self._turns(s["id"])
        return {"profile": p, "sessions": sessions,
                "chapters": {c["id"]: f"Class {c['grade']} · Ch {c['chapter']}: {c['title']}" for c in CHAPTERS}}

    def learners(self):
        rows = self.store._rows("SELECT student_id, profile, updated FROM buddy_profiles ORDER BY updated DESC")
        out = []
        for r in rows:
            p = json.loads(r["profile"])
            out.append({"student": r["student_id"], "grade": p.get("grade"), "updated": r["updated"],
                        "levels": {s: (v["level"] if v["assessed"] else None) for s, v in p["skills"].items()},
                        "inquiries": len(p["inquiries"]), "consent": bool(p.get("consent"))})
        return out
