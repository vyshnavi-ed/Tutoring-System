"""Bayesian Knowledge Tracing: a probability that the student has mastered a skill.

Replaces the thesis's undefined "satisfactory performance" with an explicit,
tunable rule: a skill is mastered once P(mastered) >= threshold.
"""


def bkt_update(p: float, correct: bool, p_learn: float = 0.15, p_slip: float = 0.1, p_guess: float = 0.2) -> float:
    if correct:
        num = p * (1 - p_slip)
        posterior = num / (num + (1 - p) * p_guess)
    else:
        num = p * p_slip
        posterior = num / (num + (1 - p) * (1 - p_guess))
    return posterior + (1 - posterior) * p_learn
