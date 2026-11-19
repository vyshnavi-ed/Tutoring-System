"""Strategy registry. To add a new tutoring algorithm: subclass Strategy and register it here."""
from .level_descent import LevelDescent
from .prereq_graph import PrereqGraph
from .spaced_repetition import SpacedRepetition

STRATEGIES = {cls.name: cls for cls in (LevelDescent, PrereqGraph, SpacedRepetition)}
