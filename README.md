# Multi-strategy tutoring system (prototype)

A tutoring engine that runs **different tutoring algorithms for different subjects**, built on the
tutoring-rules framework from Ramesh (2014), *A Framework for Tutoring Rules* (IIIT Bangalore),
and extended beyond it.

| Subject pack | Strategy | What it does when a student gets something wrong |
|---|---|---|
| **Fractions** (Maths) | `prereq_graph` | Checks each prerequisite skill with one quick question (equivalent fractions, LCM, HCF…), teaches the first one the student lacks until it is mastered, then returns to the original skill. Mastery is a probability (Bayesian Knowledge Tracing). |
| **English vocabulary** | `spaced_repetition` | The word drops back to box 0, its card is shown again, and it returns after 3 other questions. Words the student knows come back days later, and the questions get harder as a word climbs boxes: recognise → fill the gap → type it → use it in a sentence. |
| **Linked lists, UOS1.2** (from the thesis) | `level_descent` | The thesis's Fig. 4.4 rules. A wrong Apply answer leads to the Understand lesson and the pre-selected Understand sets, then the Remember sets, then back up to a *different* Apply item. |

In every subject, after **3 wrong answers in a row on the same set** the teacher is alerted, and the
student is told help is coming. Free-text answers that can't be graded confidently are sent to the
teacher for review.

## Run it

```bash
pip install -r requirements.txt
uvicorn tutor.api:app --reload      # or: python -m tutor.api
```
- Student view: http://localhost:8000/
- Teacher dashboard: http://localhost:8000/teacher (alerts, each student's path, content review and approval)

Optional: `export ANTHROPIC_API_KEY=...` turns on AI grading for free-text answers (otherwise a
keyword check is used and the teacher is asked to confirm) and AI pack authoring.

Tests: `pytest -q`. They run simulated students through every strategy, including the exact sequence
from the thesis's Figure 4.4.

## How it fits together

```
tutor/
  engine.py              shared by every subject: session loop, item picking (never repeats the
                         last item), grading, the "satisfactory" threshold, teacher alerts
  strategies/            one file per tutoring algorithm, all with the same interface
    base.py              next_step(state) -> ask item / done;  on_result(state, ...) -> update
    level_descent.py     the thesis rules
    prereq_graph.py      diagnosis through prerequisites + BKT mastery
    spaced_repetition.py Leitner boxes
  graders.py             mcq, numeric, fraction, text (Unicode-safe), code_python, free_text (AI)
  mastery.py             Bayesian Knowledge Tracing
  validate.py            checks packs: links, cycles, answer keys, runs code solutions against their tests
  authoring.py           AI-assisted pack generation (with self-repair) + validate CLI
  store.py               SQLite: sessions, attempts, path events, alerts
  api.py, static/        FastAPI + student and teacher pages
packs/*.json             content + rules, one file per subject
```

A **pack** is plain JSON: `item_sets` (each with items, a lesson `activity`, and `links`), `activities`
(markdown lessons), `units` (the order of goals/cards), `strategy`, and `config`. What `links` means
depends on the strategy: lower-level sets for `level_descent`, prerequisites for `prereq_graph`, and
unused for `spaced_repetition`.

## Adding a subject

```bash
python -m tutor.authoring generate --strategy prereq_graph --title "Decimals" \
  --subject "Mathematics (Class 6)" --brief "place value, comparing, adding and subtracting decimals" \
  --out packs/math_decimals.json
python -m tutor.authoring validate packs/math_decimals.json
```
The pack is saved as a **draft**. Students can't see it until a teacher approves it under
*Teacher → Content packs → Reload → Review → Approve*. A pack with validation errors can't be approved.

For **Hindi or Kannada**, use `spaced_repetition` with `text` items. The text grader applies Unicode
normalisation, so typed Devanagari and Kannada answers compare correctly.

## Adding a strategy

Subclass `Strategy` in `tutor/strategies/`, implement `init_state`, `next_step`, `on_result` (and
optionally `progress` and `summary` for the dashboards), and register it in
`tutor/strategies/__init__.py`. Grading, logging, alerts and the UI work without changes.

## Prototype limits

- **Code answers** run in a subprocess with CPU and memory limits, but this is **not a real sandbox**.
  Use a container or jail (Judge0, gVisor) before letting untrusted users submit code.
- **No authentication.** Students identify themselves by typing a name, and the teacher page is open.
- **"Skip ahead 1 day"** in the vocabulary subject is a demo helper for testing spaced repetition.
- **AI authoring and AI grading are untested** against the live API: they need `ANTHROPIC_API_KEY`.
  The offline paths are covered by the tests.
