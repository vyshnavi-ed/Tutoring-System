# Multi-strategy tutoring system (prototype)

A tutoring engine that runs **different tutoring algorithms and different pedagogies for different topics**,
built on the tutoring-rules framework from Ramesh (2014), *A Framework for Tutoring Rules* (IIIT Bangalore),
and extended beyond it.

Each topic pack chooses two things:
- a **strategy**: *what comes next* (level descent, prerequisite graph, spaced repetition), and
- a **pedagogy**: *how each skill is taught*. `inquiry` (constructivist, 5E / Agastya session-plan structure)
  or `direct` (lesson, then questions).

### Inquiry pedagogy

Before any scored question, each skill runs an **episode**:

| Phase | What the student does |
|---|---|
| Think back | Recalls their own experience (home, market, cooking, festivals…) |
| Predict | Makes one prediction. It is never marked right or wrong, and is quoted back later |
| Investigate | Explores *before being told*: on-screen fraction strips, sentences to infer a word's meaning from, a problem to try, or real materials at home |
| Think about it | Probing questions: what did you notice → why → where else → say it in your own words. An AI tutor may add one follow-up question (never the answer) |
| Make sense of it | The explanation comes *after* the student's own, and compares it with their prediction |
| Where else? | Everyday connections and the key learning in one sentence |

Wrong answers on scored questions climb a **hint ladder** before the student is "remediated". First comes a
**misconception probe** if the answer matches a known error (e.g. 2/9 + 4/9 = 6/18 → *"is 6/18 bigger than 4/9?"*),
then a Socratic hint, then a nudge, with a retry of the *same* question each time. Only after that is the worked
example shown and the strategy steps in. Quick diagnostic checks (prerequisite probes) get no hints, so gaps aren't hidden.

The teacher dashboard shows each student's **predictions, investigation notes and explanations**, and a
**class-wide list of misconceptions** (which error, which skill, which students).

Explore tools live in `tutor/static/tools.js`. Add a topic-specific tool there (e.g. a circuit builder, a
balance scale) and list its name in `tutor/validate.py`'s `EXPLORE_TOOLS`.

| Subject pack | Strategy | What it does when a student gets something wrong |
|---|---|---|
| **Fractions** (Maths) · inquiry | `prereq_graph` | Checks each prerequisite skill with one quick question (equivalent fractions, LCM, HCF…), teaches the first one the student lacks until it is mastered, then returns to the original skill. Mastery is a probability (Bayesian Knowledge Tracing). |
| **English vocabulary** · inquiry (guess from context first) | `spaced_repetition` | The word drops back to box 0, its card is shown again, and it returns after 3 other questions. Words the student knows come back days later, and the questions get harder as a word climbs boxes: recognise → fill the gap → type it → use it in a sentence. |
| **Linked lists, UOS1.2** (from the thesis) · direct | `level_descent` | The thesis's Fig. 4.4 rules. A wrong Apply answer leads to the Understand lesson and the pre-selected Understand sets, then the Remember sets, then back up to a *different* Apply item. |

In every subject, after **3 wrong answers in a row on the same set** the teacher is alerted, and the
student is told help is coming. Free-text answers that can't be graded confidently are sent to the
teacher for review.

## Science Buddy (open inquiry, classes 6–8)

A separate mode, specified in [`docs/science-buddy-design.md`](docs/science-buddy-design.md), which is the source of truth
for its behaviour. The child tells an AI "curious friend" something they noticed. The Buddy turns it into observations,
an investigable question and a small, safe investigation at home, by asking rather than telling, one short question
per turn, by text or voice (browser speech; best in Chrome).

- **Learner profile per child:** the 12 process skills at Emerging, Developing or Independent, the last two pieces of
  evidence for each, every level change with a one-line reason, the inquiries done (tagged to NCERT chapters after the
  fact), and self-assessments. Each session has a **focus skill** chosen in code: basics before integrated skills,
  matched to the inquiry's stage.
- **Memory:** open inquiries and the task the child went off to do are given to the Buddy next session ("How's the
  tulsi plant doing?"). A session left open for under 3 hours is resumed.
- **Guardrails in code, not just in the prompt:**
  - unsafe suggestions (flames, sharp tools, electricity, chemicals, tasting, disturbing animals, heat without an
    adult) are blocked and regenerated
  - the Buddy can't claim to be a person
  - one question per turn
  - phone numbers, emails and addresses are removed before storing or sending
  - possible disclosures (hurt, bullied, unsafe, very upset) are flagged for a person to review, always get a
    "tell a trusted adult" reply, and are never used for skill assessment
- **Photos:** children can add a photo (📷 button, paste or drag-and-drop). Each photo is resized, stripped of hidden
  data such as GPS location, and checked by the AI *before* it is stored. Only plants and objects are kept; photos of
  people, animals, personal details or anything inappropriate are refused and never saved (inappropriate ones raise a
  wellbeing alert). The Buddy can see kept photos but never describes them: the child describes first, and the Buddy
  only uses the photo to point their attention. Photos need a separate parental consent. To allow insects and other
  creatures later, change `ALLOWED_CATEGORIES` in `tutor/buddy/photos.py`.
- **Consent:** nothing is stored until a parent or guardian agrees on the consent screen. This is a *prototype*
  checkbox; production needs verifiable parental consent.
- **Teacher dashboard → Science Buddy:** a class grid of skill levels, each learner's evidence, level changes with
  reasons, inquiries and full conversations. Wellbeing flags appear under Alerts.
- **Needs `ANTHROPIC_API_KEY`.** Without it, the Buddy runs in *demo mode* with canned replies, so you can try the
  screens but not the tutoring. Model: `TUTOR_BUDDY_MODEL` (default `claude-sonnet-5-5`).
- Code: `tutor/buddy/` (skills and focus choice, prompt built from the design doc, guards, engine, NCERT chapter index,
  noticing starters). The NCERT books are used only to build the chapter index for tagging.

### Science Buddy interface design

The phone-first screens (home, chat with the inquiry journey, and the remaining screens) are described in
[`docs/buddy-ui-design.md`](docs/buddy-ui-design.md). It covers the fonts, colour tokens, motion rules, the six journey
steps, the content rules the Buddy must follow, and the open decisions. The screens are built into the Science Buddy
page (`/buddy`).

## Run it

```bash
pip install -r requirements.txt
uvicorn tutor.api:app --reload      # or: python -m tutor.api
```
- Student view: http://localhost:8000/ (the Science Buddy is the first card; direct link http://localhost:8000/buddy)
- Teacher dashboard: http://localhost:8000/teacher (alerts, each student's path, content review and approval)

Optional: `export ANTHROPIC_API_KEY=...` turns on AI grading for free-text answers (otherwise a
keyword check is used and the teacher is asked to confirm), AI follow-up questions in inquiry episodes
(otherwise authored follow-ups are used for very short answers), and AI pack authoring.

## Hosting (prototype, not ready for children)

The app is one long-running Python server with a SQLite database and kept photos on disk. The included
`Dockerfile` and `render.yaml` are set up for Render's **free tier**. Its limits:
- **Data is erased** on every restart or redeploy (no persistent disk on the free plan). Use it for previews only.
- **Sleeps** after about 15 minutes idle; the first load can take about a minute.

For data that must last, use a paid plan with a disk (add a `disk` block to `render.yaml` and set the plan to
`starter`). Vercel is not a good fit, because its functions don't keep files between requests.

To deploy on Render:
1. Push this repo to GitHub, then in Render choose **New → Blueprint** and pick the repo. Render reads `render.yaml`.
2. In the service's **Environment** tab, add `ANTHROPIC_API_KEY` with your key. Don't put the key in any file.
3. Open the URL Render gives you and add `/buddy` to it.

Before sharing the link with students, these must be done:
- **Authentication:** the app has none. The teacher dashboard and all student data are public to anyone with the link.
- **Verifiable parental consent:** the current consent screen is a prototype checkbox.
- **Wellbeing keyword list:** needs educator review, and Kannada words still need adding.
- **Code sandbox:** code answers are not sandboxed (see Prototype limits).

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
  pedagogy.py            direct vs inquiry: episodes, AI follow-ups, hint ladder, misconception probes
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
python -m tutor.authoring generate --strategy prereq_graph --pedagogy inquiry --title "Decimals" \
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
- **AI authoring, AI grading and AI follow-ups are untested** against the live API: they need `ANTHROPIC_API_KEY`.
  The offline paths are covered by the tests.
