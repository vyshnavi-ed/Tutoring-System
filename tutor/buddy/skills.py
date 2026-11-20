"""Science process skills, levels and evidence cues — from docs/science-buddy-design.md."""

LEVELS = ["emerging", "developing", "independent"]

BASIC = ["observing", "classifying", "measuring", "communicating", "inferring", "predicting"]
INTEGRATED = ["questioning", "controlling_variables", "hypothesising", "defining_operationally",
              "experimenting", "interpreting_data"]
ALL = BASIC + INTEGRATED

SKILLS = {
    "observing": ("Observing",
                  "Names objects; reports one feature (\"it's green\")",
                  "Reports several features using more than one sense; notices change over time",
                  "Observes systematically, separates observation from interpretation, uses simple tools (ruler, timer)"),
    "classifying": ("Classifying",
                    "Sorts by one obvious property",
                    "Sorts by a chosen property and states the rule",
                    "Builds multi-level groupings and re-sorts by a different property on purpose"),
    "measuring": ("Measuring and using numbers",
                  "Compares by eye (\"bigger\")",
                  "Uses non-standard or standard units with some consistency",
                  "Picks the right unit and tool, repeats measurements, notices error"),
    "communicating": ("Communicating",
                      "Describes vaguely in speech",
                      "Describes clearly enough for someone else to picture it; makes a simple list or table",
                      "Chooses a fitting form (table, sketch, graph) and records as they go"),
    "inferring": ("Inferring",
                  "Gives an explanation as fact",
                  "Offers an explanation linked to an observation",
                  "Offers several possible explanations and says which observation supports each"),
    "predicting": ("Predicting",
                   "Guesses with no reason",
                   "Predicts from a pattern seen once",
                   "Predicts from a pattern and says how confident they are and why"),
    "questioning": ("Questioning",
                    "Asks broad \"why\" questions",
                    "Turns a \"why\" into a \"what happens if\" with help",
                    "Asks investigable questions that name what to change and what to watch"),
    "controlling_variables": ("Identifying and controlling variables",
                              "Changes several things at once",
                              "Names the one thing to change; controls some others when prompted",
                              "Lists what to change, what to measure and what to keep the same, unprompted"),
    "hypothesising": ("Hypothesising",
                      "States a prediction only",
                      "Links a prediction to a reason (\"because...\")",
                      "States a testable if/then/because and knows what result would prove it wrong"),
    "defining_operationally": ("Defining operationally",
                               "Uses loose terms (\"grows better\")",
                               "Says how they will measure one term",
                               "Defines every key term as a measurement before starting"),
    "experimenting": ("Experimenting",
                      "Tries something to see what happens",
                      "Runs a planned test with a comparison",
                      "Plans a fair test with repeats, carries it out, and adjusts the plan when problems appear"),
    "interpreting_data": ("Interpreting data",
                          "Reads off a single result",
                          "Describes a pattern in results",
                          "Draws a conclusion, states its limits and suggests the next question"),
}

# which skills each stage of an inquiry naturally exercises (observe -> question -> predict -> plan -> ...)
STAGES = ["observe", "question", "predict", "plan", "experiment", "interpret", "reflect"]
STAGE_SKILLS = {
    "observe": ["observing", "communicating", "classifying"],
    "question": ["questioning", "inferring"],
    "predict": ["predicting", "hypothesising"],
    "plan": ["controlling_variables", "defining_operationally", "measuring"],
    "experiment": ["experimenting", "measuring", "observing"],
    "interpret": ["interpreting_data", "inferring", "communicating"],
    "reflect": ["communicating", "questioning"],
}

LADDER = ["open question", "narrower question", "choice between two options", "worked hint", "brief explanation, then apply it"]


def label(skill):
    return SKILLS[skill][0]


def describe(skill, level):
    return SKILLS[skill][1 + LEVELS.index(level)]


def skill_map_text():
    lines = []
    for group, names in (("Basic process skills", BASIC), ("Integrated process skills", INTEGRATED)):
        lines.append(f"{group}:")
        for s in names:
            name, e, d, i = SKILLS[s]
            lines.append(f"- {s} ({name}): Emerging = {e}. Developing = {d}. Independent = {i}.")
    return "\n".join(lines)


def choose_focus(levels: dict, stage: str | None = None) -> str:
    """Pick the session's focus skill: one just above the learner's current level.

    Rules from the design: basic skills are the foundation, and experimenting is not pushed
    on a learner who cannot yet observe in detail. Within that, prefer a skill the current
    inquiry stage naturally exercises, at the lowest level.
    """
    lvl = lambda s: LEVELS.index(levels.get(s, "emerging"))
    if lvl("observing") == 0:
        return "observing"
    pool = [s for s in ALL if lvl(s) < 2]
    if not pool:
        return "interpreting_data"
    basics_weak = [s for s in BASIC if lvl(s) == 0]
    if basics_weak and lvl("observing") < 2:  # still building the foundation: no integrated focus yet
        pool = [s for s in pool if s in BASIC]
    order = {s: i for i, s in enumerate(ALL)}
    if stage in STAGE_SKILLS:
        staged = [s for s in STAGE_SKILLS[stage] if s in pool]
        if staged:
            return min(staged, key=lambda s: (lvl(s), order[s]))
    return min(pool, key=lambda s: (lvl(s), order[s]))
