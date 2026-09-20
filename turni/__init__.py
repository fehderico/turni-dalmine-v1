"""Motore di schedulazione della centrale di Dalmine."""

from .config import DEFAULT_SHIFTS
from .io import InputData, load_input_workbook

__all__ = ["DEFAULT_SHIFTS", "InputData", "ScheduleResult", "load_input_workbook", "solve_schedule"]


def __getattr__(name: str):
    if name in {"ScheduleResult", "solve_schedule"}:
        from .scheduler import ScheduleResult, solve_schedule

        return {"ScheduleResult": ScheduleResult, "solve_schedule": solve_schedule}[name]
    raise AttributeError(name)
