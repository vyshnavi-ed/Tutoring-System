"""SQLite persistence: sessions (strategy state), attempts, path events, teacher alerts."""
from __future__ import annotations

import json
import sqlite3
import threading
import time

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    student_id TEXT NOT NULL, pack_id TEXT NOT NULL, state TEXT NOT NULL,
    created REAL NOT NULL, updated REAL NOT NULL,
    PRIMARY KEY (student_id, pack_id)
);
CREATE TABLE IF NOT EXISTS attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT, pack_id TEXT, set_id TEXT, item_id TEXT, item_type TEXT,
    response TEXT, score REAL, passed INTEGER, feedback TEXT, needs_review INTEGER, ts REAL
);
CREATE TABLE IF NOT EXISTS responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT, pack_id TEXT, set_id TEXT, phase TEXT, kind TEXT, prompt TEXT, response TEXT,
    is_followup INTEGER, ts REAL
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT, pack_id TEXT, kind TEXT, payload TEXT, ts REAL
);
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT, pack_id TEXT, kind TEXT, set_id TEXT, message TEXT, details TEXT,
    ts REAL, resolved INTEGER DEFAULT 0, resolved_note TEXT
);
"""


class Store:
    def __init__(self, path: str = "tutor.db"):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        with self.lock:
            self.conn.executescript(SCHEMA)

    def _exec(self, sql, args=()):
        with self.lock:
            cur = self.conn.execute(sql, args)
            self.conn.commit()
            return cur

    def _rows(self, sql, args=()):
        with self.lock:
            return [dict(r) for r in self.conn.execute(sql, args).fetchall()]

    # sessions
    def load_state(self, student_id, pack_id):
        rows = self._rows("SELECT state FROM sessions WHERE student_id=? AND pack_id=?", (student_id, pack_id))
        return json.loads(rows[0]["state"]) if rows else None

    def save_state(self, student_id, pack_id, state):
        now = time.time()
        self._exec(
            "INSERT INTO sessions VALUES (?,?,?,?,?) ON CONFLICT(student_id, pack_id) "
            "DO UPDATE SET state=excluded.state, updated=excluded.updated",
            (student_id, pack_id, json.dumps(state), now, now),
        )

    def delete_session(self, student_id, pack_id):
        for t in ("sessions", "attempts", "events", "alerts", "responses"):
            self._exec(f"DELETE FROM {t} WHERE student_id=? AND pack_id=?", (student_id, pack_id))

    def sessions(self):
        return self._rows("SELECT student_id, pack_id, state, created, updated FROM sessions ORDER BY updated DESC")

    # attempts & events
    def add_attempt(self, student_id, pack_id, set_id, item, response, result, passed):
        self._exec(
            "INSERT INTO attempts (student_id, pack_id, set_id, item_id, item_type, response, score, passed,"
            " feedback, needs_review, ts) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (student_id, pack_id, set_id, item["id"], item["type"], str(response), result.score,
             int(passed), result.feedback, int(result.needs_review), time.time()),
        )

    def attempts(self, student_id, pack_id):
        return self._rows("SELECT * FROM attempts WHERE student_id=? AND pack_id=? ORDER BY id", (student_id, pack_id))

    def add_event(self, student_id, pack_id, kind, payload):
        self._exec("INSERT INTO events (student_id, pack_id, kind, payload, ts) VALUES (?,?,?,?,?)",
                   (student_id, pack_id, kind, json.dumps(payload), time.time()))

    def events(self, student_id, pack_id):
        rows = self._rows("SELECT * FROM events WHERE student_id=? AND pack_id=? ORDER BY id", (student_id, pack_id))
        for r in rows:
            r["payload"] = json.loads(r["payload"])
        return rows

    # ungraded episode responses (predictions, observations, explanations)
    def add_response(self, student_id, pack_id, set_id, phase, kind, prompt, response, is_followup):
        self._exec("INSERT INTO responses (student_id, pack_id, set_id, phase, kind, prompt, response, is_followup, ts)"
                   " VALUES (?,?,?,?,?,?,?,?,?)",
                   (student_id, pack_id, set_id, phase, kind, prompt, response, int(is_followup), time.time()))

    def responses(self, student_id=None, pack_id=None):
        sql, args = "SELECT * FROM responses WHERE 1=1", []
        if student_id:
            sql += " AND student_id=?"; args.append(student_id)
        if pack_id:
            sql += " AND pack_id=?"; args.append(pack_id)
        return self._rows(sql + " ORDER BY id", tuple(args))

    def misconception_counts(self, pack_id):
        rows = self._rows("SELECT student_id, payload FROM events WHERE pack_id=? AND kind='misconception'", (pack_id,))
        out = {}
        for r in rows:
            p = json.loads(r["payload"])
            k = (p["set_id"], p["misconception"])
            out.setdefault(k, set()).add(r["student_id"])
        return [{"set_id": k[0], "misconception": k[1], "students": sorted(v)} for k, v in out.items()]

    # alerts
    def has_open_alert(self, student_id, pack_id, kind, set_id):
        return bool(self._rows(
            "SELECT 1 FROM alerts WHERE student_id=? AND pack_id=? AND kind=? AND set_id IS ? AND resolved=0",
            (student_id, pack_id, kind, set_id)))

    def add_alert(self, student_id, pack_id, kind, set_id, message, details):
        self._exec(
            "INSERT INTO alerts (student_id, pack_id, kind, set_id, message, details, ts) VALUES (?,?,?,?,?,?,?)",
            (student_id, pack_id, kind, set_id, message, json.dumps(details), time.time()))

    def alerts(self, include_resolved=False):
        sql = "SELECT * FROM alerts" + ("" if include_resolved else " WHERE resolved=0") + " ORDER BY id DESC"
        rows = self._rows(sql)
        for r in rows:
            r["details"] = json.loads(r["details"] or "{}")
        return rows

    def resolve_alert(self, alert_id, note=""):
        self._exec("UPDATE alerts SET resolved=1, resolved_note=? WHERE id=?", (note, alert_id))
