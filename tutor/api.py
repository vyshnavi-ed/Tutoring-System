"""HTTP API + static pages.

    uvicorn tutor.api:app --reload        (or: python -m tutor.api)
    student UI:  http://localhost:8000/
    teacher UI:  http://localhost:8000/teacher
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .engine import Engine
from .pack import load_packs
from .store import Store
from .validate import validate

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"


def _sid(student: str) -> str:
    s = re.sub(r"\s+", " ", student.strip())
    if not s or len(s) > 60:
        raise HTTPException(400, "invalid student name")
    return s


def create_app(packs_dir: str | Path | None = None, db_path: str | None = None, engine: Engine | None = None) -> FastAPI:
    packs_dir = Path(packs_dir or os.environ.get("TUTOR_PACKS", ROOT.parent / "packs"))
    store = Store(db_path or os.environ.get("TUTOR_DB", str(ROOT.parent / "tutor.db")))
    eng = engine or Engine(load_packs(packs_dir), store)
    app = FastAPI(title="Multi-strategy tutor")
    app.state.engine = eng

    def pack_or_404(pack_id, student_facing=False):
        pack = eng.packs.get(pack_id)
        if pack is None or (student_facing and pack.status != "approved"):
            raise HTTPException(404, "unknown pack")
        return pack

    # ---------------- pages
    @app.get("/", include_in_schema=False)
    def student_page():
        return FileResponse(STATIC / "index.html")

    @app.get("/teacher", include_in_schema=False)
    def teacher_page():
        return FileResponse(STATIC / "teacher.html")

    app.mount("/static", StaticFiles(directory=STATIC), name="static")

    # ---------------- packs
    @app.get("/api/packs")
    def list_packs():
        return [{"id": p.id, "title": p.title, "subject": p.subject, "strategy": p.strategy, "pedagogy": p.pedagogy,
                 "status": p.status,
                 "description": p.data.get("description", ""), "sets": len(p.sets),
                 "items": sum(len(s.get("items", [])) for s in p.sets.values())}
                for p in eng.packs.values()]

    @app.get("/api/packs/{pack_id}")
    def get_pack(pack_id: str):
        return pack_or_404(pack_id).data

    @app.get("/api/packs/{pack_id}/validate")
    def validate_pack(pack_id: str):
        errors, warnings = validate(pack_or_404(pack_id).data)
        return {"errors": errors, "warnings": warnings}

    @app.post("/api/packs/{pack_id}/approve")
    def approve_pack(pack_id: str, approved: bool = Body(True, embed=True)):
        pack = pack_or_404(pack_id)
        if approved:
            errors, _ = validate(pack.data)
            if errors:
                raise HTTPException(400, {"message": "fix validation errors first", "errors": errors})
        pack.status = "approved" if approved else "draft"
        if pack.path:
            pack.save()
        return {"id": pack.id, "status": pack.status}

    @app.post("/api/packs/reload")
    def reload_packs():
        eng.packs = load_packs(packs_dir)
        return {"packs": list(eng.packs)}

    # ---------------- student session
    @app.get("/api/session/{student}/{pack_id}")
    def session_action(student: str, pack_id: str):
        pack_or_404(pack_id, True)
        return eng.action(_sid(student), pack_id)

    @app.post("/api/session/{student}/{pack_id}/continue")
    def session_continue(student: str, pack_id: str):
        pack_or_404(pack_id, True)
        return eng.acknowledge(_sid(student), pack_id)

    @app.post("/api/session/{student}/{pack_id}/answer")
    def session_answer(student: str, pack_id: str, response: str = Body(..., embed=True)):
        pack_or_404(pack_id, True)
        if len(response) > 20000:
            raise HTTPException(400, "answer too long")
        return eng.answer(_sid(student), pack_id, response)

    @app.post("/api/session/{student}/{pack_id}/advance")
    def session_advance(student: str, pack_id: str, days: float = Body(1, embed=True)):
        pack_or_404(pack_id, True)
        return eng.advance_clock(_sid(student), pack_id, days)

    @app.post("/api/session/{student}/{pack_id}/reset")
    def session_reset(student: str, pack_id: str):
        pack_or_404(pack_id)
        eng.reset(_sid(student), pack_id)
        return {"ok": True}

    # ---------------- teacher
    @app.get("/api/teacher/alerts")
    def alerts(all: bool = False):
        return eng.store.alerts(include_resolved=all)

    @app.post("/api/teacher/alerts/{alert_id}/resolve")
    def resolve(alert_id: int, note: str = Body("", embed=True)):
        eng.store.resolve_alert(alert_id, note)
        return {"ok": True}

    @app.get("/api/teacher/sessions")
    def sessions():
        open_alerts = eng.store.alerts()
        out = []
        for s in eng.store.sessions():
            if s["pack_id"] not in eng.packs:
                continue
            att = eng.store.attempts(s["student_id"], s["pack_id"])
            out.append({
                "student": s["student_id"], "pack": s["pack_id"], "updated": s["updated"],
                "attempts": len(att), "correct": sum(a["passed"] for a in att),
                "open_alerts": sum(1 for a in open_alerts
                                   if a["student_id"] == s["student_id"] and a["pack_id"] == s["pack_id"]),
                "progress": eng.strategy_for(eng.packs[s["pack_id"]]).progress(
                    eng.store.load_state(s["student_id"], s["pack_id"])),
            })
        return out

    @app.get("/api/teacher/sessions/{student}/{pack_id}")
    def session_detail(student: str, pack_id: str):
        pack_or_404(pack_id)
        return {"summary": eng.summary(student, pack_id),
                "attempts": eng.store.attempts(student, pack_id),
                "responses": eng.store.responses(student, pack_id),
                "events": eng.store.events(student, pack_id)}

    @app.get("/api/teacher/misconceptions/{pack_id}")
    def misconceptions(pack_id: str):
        pack = pack_or_404(pack_id)
        out = []
        for m in eng.store.misconception_counts(pack_id):
            s = pack.sets.get(m["set_id"], {})
            label = next((mc.get("label", mc["id"]) for it in s.get("items", [])
                          for mc in it.get("misconceptions", []) if mc["id"] == m["misconception"]), m["misconception"])
            out.append({**m, "label": label, "set_title": s.get("title", m["set_id"])})
        return sorted(out, key=lambda x: -len(x["students"]))

    return app


app = create_app() if os.environ.get("TUTOR_NO_APP") != "1" else None

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("tutor.api:app", host="127.0.0.1", port=int(os.environ.get("PORT", 8000)))
