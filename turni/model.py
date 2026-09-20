from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import calendar

from .config import ShiftDefinition


@dataclass(frozen=True)
class Doctor:
    key: str
    nome: str
    cognome: str
    ats: str
    email: str = ""
    contract_status: str = ""
    notes: str = ""

    @property
    def display_name(self) -> str:
        return f"{self.nome} {self.cognome}".strip()


@dataclass(frozen=True)
class ShiftInstance:
    id: str
    date: date
    definition: ShiftDefinition
    start: datetime
    end: datetime


def doctor_key(nome: object, cognome: object) -> str:
    def norm(value: object) -> str:
        return " ".join(str(value or "").strip().upper().split())

    return f"{norm(nome)}|{norm(cognome)}"


def generate_shift_instances(
    year: int,
    month: int,
    definitions: tuple[ShiftDefinition, ...],
    active_codes_by_date: dict[date, frozenset[str]] | None = None,
) -> list[ShiftInstance]:
    instances: list[ShiftInstance] = []
    _, last_day = calendar.monthrange(year, month)
    for day_number in range(1, last_day + 1):
        current = date(year, month, day_number)
        for definition in definitions:
            if active_codes_by_date is not None:
                if definition.code not in active_codes_by_date.get(current, frozenset()):
                    continue
            elif current.weekday() not in definition.weekdays:
                continue
            start = datetime.combine(current, definition.start)
            end = datetime.combine(current, definition.end)
            if end <= start:
                end += timedelta(days=1)
            instances.append(
                ShiftInstance(
                    id=f"{current.isoformat()}_{definition.code}",
                    date=current,
                    definition=definition,
                    start=start,
                    end=end,
                )
            )
    return instances
