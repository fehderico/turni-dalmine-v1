from __future__ import annotations

from dataclasses import dataclass
from datetime import time


@dataclass(frozen=True)
class ShiftDefinition:
    code: str
    label: str
    start: time
    end: time
    weekdays: frozenset[int]
    required: int
    credit_units: int


ALL_DAYS = frozenset(range(7))
WEEKEND = frozenset({5, 6})

# Unità di credito: 1 = mezzo turno; 2 = un turno intero.
# I valori di DIU e NOT sono assunzioni v1 configurabili.
DEFAULT_SHIFTS = (
    ShiftDefinition("SER", "Serale", time(19, 0), time(0, 0), ALL_DAYS, 7, 1),
    ShiftDefinition("NOT", "Notturno", time(20, 0), time(8, 0), ALL_DAYS, 5, 2),
    ShiftDefinition("DIU", "Diurno", time(8, 0), time(20, 0), WEEKEND, 7, 2),
    ShiftDefinition("MAT", "Mattina", time(8, 0), time(14, 0), WEEKEND, 8, 1),
    ShiftDefinition("POM", "Pomeriggio", time(14, 0), time(20, 0), WEEKEND, 8, 1),
)

ATS_PRIORITY = {
    "BERGAMO OVEST": 0,
    "BERGAMO EST": 1,
}

FORM_ASST_MAP = {
    "OVEST": "BERGAMO OVEST",
    "BGEST": "BERGAMO EST",
    "PG23": "ALTRI",
    "SPEDALI": "ALTRI",
    "GARDA": "ALTRI",
    "FRANCIA": "ALTRI",
}

FORM_SHIFT_MAP = {
    "8-14": "MAT",
    "14-20": "POM",
    "8-20": "DIU",
    "19-00": "SER",
    "20-8": "NOT",
}

def normalize_ats(value: object) -> str:
    text = " ".join(str(value or "").strip().upper().split())
    if text in FORM_ASST_MAP:
        return FORM_ASST_MAP[text]
    if text in ATS_PRIORITY:
        return text
    return "ALTRI"
