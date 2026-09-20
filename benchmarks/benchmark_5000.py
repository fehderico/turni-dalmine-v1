"""Smoke benchmark for the declared upper bound of 5,000 doctors.

It uses sparse availability (five declared shifts per doctor), which mirrors the
long-form input model and checks construction/solve behavior without pretending
to be a production capacity certification.
"""

from __future__ import annotations

from datetime import date
import random
import time

from turni.config import DEFAULT_SHIFTS
from turni.io import InputData
from turni.model import Doctor, generate_shift_instances
from turni.scheduler import solve_schedule


def main() -> None:
    rng = random.Random(202610)
    shifts = generate_shift_instances(2026, 10, DEFAULT_SHIFTS)
    doctors = {}
    availability = set()
    ats_values = ["BERGAMO OVEST", "BERGAMO EST", "ALTRI"]
    started = time.perf_counter()
    for index in range(5_000):
        key = f"D{index:05d}"
        doctors[key] = Doctor(key, f"Medico{index}", "Test", ats_values[index % 3])
        for shift in rng.sample(shifts, 5):
            availability.add((key, shift.date, shift.definition.code))
    built = time.perf_counter()
    result = solve_schedule(
        InputData(doctors, availability, []),
        2026,
        10,
        max_seconds_per_phase=5,
    )
    finished = time.perf_counter()
    print(f"Medici: {len(doctors):,}")
    print(f"Disponibilità: {len(availability):,}")
    print(f"Preparazione dati: {built - started:.2f}s")
    print(f"Costruzione e solve: {finished - built:.2f}s")
    print(f"Assegnazioni: {len(result.assignments):,}")
    print(f"Fasi: {result.phase_status}")
    if result.warnings:
        print("Avvisi:")
        for warning in result.warnings:
            print(f"- {warning}")


if __name__ == "__main__":
    main()
