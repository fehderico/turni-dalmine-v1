from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import hashlib

import pandas as pd
from ortools.sat.python import cp_model

from .config import ATS_PRIORITY, DEFAULT_SHIFTS, ShiftDefinition
from .io import InputData
from .model import Doctor, ShiftInstance, generate_shift_instances


@dataclass
class ScheduleResult:
    month: str
    shifts: list[ShiftInstance]
    assignments: list[tuple[str, str]]
    doctors: dict[str, Doctor]
    warnings: list[str] = field(default_factory=list)
    phase_status: dict[str, str] = field(default_factory=dict)
    source_format: str = "normalizzato"
    source_sheet: str = ""
    seed: str = ""
    candidate_counts: dict[str, int] = field(default_factory=dict)

    def assignment_frame(self) -> pd.DataFrame:
        shift_by_id = {s.id: s for s in self.shifts}
        rows = []
        for doctor_key, shift_id in self.assignments:
            doctor = self.doctors[doctor_key]
            shift = shift_by_id[shift_id]
            rows.append({
                "Data": shift.date,
                "Codice": shift.definition.code,
                "Turno": shift.definition.label,
                "Inizio": shift.start,
                "Fine": shift.end,
                "Medico": doctor.display_name,
                "ASST": doctor.ats,
                "Email": doctor.email,
            })
        return pd.DataFrame(rows)


def _stable_cost(seed: str, doctor_key: str, shift_id: str) -> int:
    digest = hashlib.sha256(f"{seed}|{doctor_key}|{shift_id}".encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % 1_000_003


def solve_schedule(
    data: InputData,
    year: int,
    month: int,
    definitions: tuple[ShiftDefinition, ...] = DEFAULT_SHIFTS,
    rest_hours: int = 11,
    max_seconds_per_phase: float = 20.0,
    seed: str | None = None,
) -> ScheduleResult:
    shifts = generate_shift_instances(
        year,
        month,
        definitions,
        data.active_codes_by_date or None,
    )
    valid_shift = {(s.date, s.definition.code): s for s in shifts}
    warnings = list(data.warnings)
    unknown_codes = sorted({code for _, day, code in data.availability if (day, code) not in valid_shift})
    if unknown_codes:
        warnings.append("Disponibilità ignorate per turno non previsto nella data: " + ", ".join(unknown_codes))

    model = cp_model.CpModel()
    x: dict[tuple[str, str], cp_model.IntVar] = {}
    by_doctor: dict[str, list[tuple[ShiftInstance, cp_model.IntVar]]] = {key: [] for key in data.doctors}
    by_shift: dict[str, list[cp_model.IntVar]] = {s.id: [] for s in shifts}

    for doctor_key, day, code in sorted(data.availability, key=lambda v: (v[0], v[1], v[2])):
        shift = valid_shift.get((day, code))
        if shift is None or doctor_key not in data.doctors:
            continue
        var = model.new_bool_var(f"x_{len(x)}")
        x[(doctor_key, shift.id)] = var
        by_doctor[doctor_key].append((shift, var))
        by_shift[shift.id].append(var)

    for shift in shifts:
        model.add(sum(by_shift[shift.id]) <= shift.definition.required)
    candidate_counts = {shift.id: len(by_shift[shift.id]) for shift in shifts}

    epoch = datetime(year, month, 1)
    rest_minutes = rest_hours * 60
    for doctor_key, choices in by_doctor.items():
        intervals = []
        for shift, var in choices:
            start = int((shift.start - epoch).total_seconds() // 60)
            duration = int((shift.end - shift.start).total_seconds() // 60) + rest_minutes
            intervals.append(model.new_optional_fixed_size_interval_var(start, duration, var, f"i_{doctor_key}_{shift.id}"))
        if intervals:
            model.add_no_overlap(intervals)

    coverage = sum(x.values())
    assignments_by_group: dict[int, list[cp_model.IntVar]] = {0: [], 1: [], 2: []}
    for doctor_key, doctor in data.doctors.items():
        group = ATS_PRIORITY.get(doctor.ats, 2)
        assignments_by_group[group].extend(var for _, var in by_doctor[doctor_key])

    phase_status: dict[str, str] = {}
    hint_vars = list(x.values())
    last_hint: dict[cp_model.IntVar, int] = {}

    def optimise(name: str, expression, maximize: bool = True) -> int:
        nonlocal last_hint
        model.clear_hints()
        for var, value in last_hint.items():
            model.add_hint(var, value)
        if maximize:
            model.maximize(expression)
        else:
            model.minimize(expression)
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = max_seconds_per_phase
        solver.parameters.num_search_workers = 8
        status = solver.solve(model)
        phase_status[name] = solver.status_name(status)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            raise RuntimeError(f"Nessuna soluzione nella fase {name}: {solver.status_name(status)}")
        last_hint = {var: solver.value(var) for var in hint_vars}
        value = int(round(solver.objective_value))
        if status != cp_model.OPTIMAL:
            warnings.append(f"Fase {name} terminata con soluzione fattibile ma ottimalità non provata.")
        model.add(expression == value)
        return value

    if not x:
        return ScheduleResult(
            f"{year:04d}-{month:02d}", shifts, [], data.doctors, warnings,
            {"copertura": "NESSUNA DISPONIBILITÀ"}, data.source_format, data.source_sheet, seed or "", candidate_counts,
        )

    optimise("copertura", coverage)
    if assignments_by_group[0]:
        optimise("precedenza_bergamo_ovest", sum(assignments_by_group[0]))
    if assignments_by_group[1]:
        optimise("precedenza_bergamo_est", sum(assignments_by_group[1]))

    tie_seed = seed or f"{year:04d}-{month:02d}"
    tie_cost = sum(_stable_cost(tie_seed, doctor_key, shift_id) * var for (doctor_key, shift_id), var in x.items())
    model.clear_hints()
    for var, value in last_hint.items():
        model.add_hint(var, value)
    model.minimize(tie_cost)
    final_solver = cp_model.CpSolver()
    final_solver.parameters.max_time_in_seconds = max_seconds_per_phase
    final_solver.parameters.num_search_workers = 8
    final_status = final_solver.solve(model)
    phase_status["spareggio"] = final_solver.status_name(final_status)
    if final_status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError("Il modello è diventato infeasible nella fase di spareggio")
    if final_status != cp_model.OPTIMAL:
        warnings.append("La fase di estrazione ha prodotto una soluzione valida, ma l'ottimalità dello spareggio non è stata provata nel tempo disponibile.")

    assignments = sorted(
        [(doctor_key, shift_id) for (doctor_key, shift_id), var in x.items() if final_solver.value(var)],
        key=lambda pair: (pair[1], pair[0]),
    )
    return ScheduleResult(
        f"{year:04d}-{month:02d}", shifts, assignments, data.doctors, warnings, phase_status,
        source_format=data.source_format, source_sheet=data.source_sheet, seed=tie_seed,
        candidate_counts=candidate_counts,
    )
