"""Raspisaniýe solweri: maglumat bazasyna bagly däl, diňe `SolverInput` alýar we `SolverResult` berýär."""
from app.solver.model import Lesson, Room, Slot, SolverInput, SolverResult, Teacher
from app.solver.engine import solve
from app.solver.precheck import precheck

__all__ = ["Lesson", "Room", "Slot", "SolverInput", "SolverResult", "Teacher", "precheck", "solve"]
