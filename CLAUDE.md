# CLAUDE.md: project context for Claude Code

This project was started in a Claude chat (November 2026) and handed over to Claude Code. This file records what the
chat decided, so work can continue without it. Keep it up to date when decisions change.

## Who and what

- **Owner:** Vyshnavi (GitHub `vyshnavi-ed`). Works in education (the Agastya inquiry-based science approach). Not a
  full-time developer: explain steps plainly, give exact Terminal commands, and verify things yourself rather than
  asking her to.
- **Goal:** a tutoring system with **different tutoring logic and pedagogy per topic**, built iteratively. It started
  from Ramesh (2014), *A Framework for Tutoring Rules* (PhD thesis, IIIT Bangalore), and has grown into an
  inquiry-driven, constructivist tutor.
- **Learners:** school students (classes 5–8 for most content), mostly **alone on a device**, in India.

## Two kinds of tutor in one app

1. **Topic packs** (`packs/*.json`, engine in `tutor/`). Each pack picks:
   - `strategy`: *what comes next* (`tutor/strategies/`):
     - `level_descent`: the thesis rules (Fig. 4.4). Fail → pre-selected sets one Bloom level lower → back up with a
       different item.
     - `prereq_graph`: diagnose by probing unmastered prerequisites; BKT mastery (default threshold 0.95).
     - `spaced_repetition`: Leitner boxes; items get harder as a card climbs boxes.
   - `pedagogy`: *how each skill is taught* (`tutor/pedagogy.py`):
     - `direct`: lesson, then questions.
     - `inquiry`: 5E / Agastya session-plan episode before any scored question: think back → one prediction (never
       marked) → investigate (explore tool) → probes (observe → why → where else → summarise) → explanation that quotes
       the prediction → connections + key learning.
     - Inquiry wrong answers: misconception probe → Socratic hint → nudge, retrying the *same* item. Only then the
       worked example and strategy remediation. Diagnostic prerequisite probes get **no** hints.
   - Shipped packs:
     - `math_fractions` (prereq_graph + inquiry)
     - `english_vocab` (spaced_repetition + inquiry: guess meaning from context first)
     - `ds_linked_lists` (level_descent + direct, the thesis example UOS1.2; deliberately left as direct)
2. **Science Buddy** (`tutor/buddy/`, page `/buddy`). An open-ended, AI-driven conversational inquiry tutor for
   classes 6–8.
   - **`docs/science-buddy-design.md` is the source of truth** for its behaviour, persona, skill model and assessment,
     including the photo amendment at the end.
   - The NCERT Science books are background only (chapter index in `tutor/buddy/data/chapters.json`), never a script.

## Decisions made in the chat (don't silently undo these)

**Content and authoring**
- Content is **AI-generated, then reviewed by teachers**. Packs are drafts until approved in the teacher dashboard.
  The validator (`tutor/validate.py`) checks links, cycles, answer keys and episodes, and runs code solutions.
- Pack JSON files are the source of truth for content. `tools/content/*.py` are the scripts that originally generated
  the three packs (build, then `inquiry_*` conversion). Re-running them overwrites the packs, so use them only for
  reference or for regenerating from scratch.

**Topic packs**
- A teacher is alerted after **3 consecutive failures** on one set (`alert_after_failures`).
- Explore tools are **built per topic** in `tutor/static/tools.js` (fraction_strips, context_sentences, problem,
  real_materials). Register new ones in `EXPLORE_TOOLS` in `tutor/validate.py`.
- AI dialogue in inquiry episodes is **scripted probes + one optional AI follow-up** (never the answer). Offline, the
  authored follow-ups are used.

**Science Buddy**
- Topic follows the learner's curiosity; the code chooses the session's **focus skill** (basics before integrated
  skills, matched to the inquiry stage).
- A skill's level is set from its **first evidence**, then changes **one level at a time**, always with a reason.
- Guardrails are enforced in code (`tutor/buddy/guards.py`), not only in the prompt:
  - unsafe suggestions are regenerated
  - the Buddy can't claim to be human
  - one question per turn
  - personal details are redacted
  - possible disclosures (hurt, bullied, unsafe, very upset) → wellbeing alert + "tell a trusted adult" reply, and
    excluded from assessment. The keyword list (English + some Hindi) **needs review by educators, and Kannada words
    need adding.**
- **Consent:** nothing is stored before a parent agrees. This is a prototype checkbox, **not verifiable consent**,
  which must change before real use. Photos need a separate consent.
- **Photos (agreed):**
  - The Buddy can see photos, but never describes or identifies them; the child describes first.
  - Only **plants and inanimate objects** are kept (`ALLOWED_CATEGORIES` in `tutor/buddy/photos.py`). People,
    animals, personal info, inappropriate or unclear photos are refused and never stored. A hand holding the item is
    allowed.
  - Photos are resized and EXIF/GPS is stripped before checking.
- **Model:** `TUTOR_BUDDY_MODEL` (default `claude-sonnet-5-5`). That model **rejects forced `tool_choice`**, so
  `AnthropicLLM` falls back to `tool_choice: auto` and parses text replies. Keep that fallback.
- **Without `ANTHROPIC_API_KEY`:** demo mode with canned replies, and photos are always refused.

## State at hand-over

- **Pull requests are stacked and none are merged yet:** #1 prototype → #2 inquiry pedagogy → #3 Science Buddy →
  #4 photos (this file was added on #4's branch, `buddy-photos`). Merge in order. Each later PR targets the previous
  branch, so retarget it to `main` if GitHub doesn't do this automatically.
- **Not yet tested against the real AI:** Science Buddy conversations, the photo check, the "never describe the
  photo" rule, AI follow-ups in episodes, AI pack authoring, AI free-text grading. The owner's API key now
  authenticates; the next step was a real conversation. Use the sample tulsi-plant dialogue in the design doc as the
  benchmark.
- **Known content nit:** in `english_vocab`, the second context sentence in each episode is the same sentence as the
  later cloze item, which makes that item easier. Fix it by using a fresh sentence.

## Ideas discussed for next

- Real-AI role-play testing of the Buddy (several child personas) before any child uses it.
- A Kannada tutor. Needs the owner's answers: L1 or L2 learners, class and syllabus, focus (aksharas / vocabulary /
  grammar / reading), instruction language, input method (letter tiles / Kannada keyboard / transliteration), and a
  native-speaker reviewer. Ideas: an akshara-builder explore tool, guessing vocabulary from context, and grammar
  pattern-spotting.
- A science topic pack using `real_materials`, aligned to the Agastya activity format (a skill for that format exists
  in the owner's workspace).
- Shared prerequisites across topic packs (currently each pack is self-contained, e.g. LCM is duplicated).
- Hosting (e.g. Render or Railway) so students can use a link; real authentication; verifiable parental consent;
  sandboxing for code answers.

## How to run and test

```
python3 -m pip install --user -r requirements.txt
python3 -m uvicorn tutor.api:app          # student http://localhost:8000  teacher /teacher  buddy /buddy
python3 -m pytest -q                      # 54 tests; AI calls are faked
python3 -m tutor.authoring validate packs/*.json
```
Env vars:
- `ANTHROPIC_API_KEY` (real AI)
- `TUTOR_DB` (default `./tutor.db`)
- `TUTOR_PHOTOS` (default `./photos`)
- `TUTOR_BUDDY_MODEL`
- `TUTOR_DEMO_ACCEPT_PHOTOS=1` (dev only: accept photos in demo mode)

The owner also has an un-versioned copy in `~/Desktop/Tutoring App` on her Mac, which is where she has been running
it. Prefer a proper `git clone` going forward.

## Working conventions

- One branch and one PR per change, with a plain-language PR description. Run the tests and check the screens in a
  browser before pushing.
- When the AI's behaviour matters, say clearly what was tested with fakes and what still needs real-AI testing.
- Keep `README.md` and this file current.
