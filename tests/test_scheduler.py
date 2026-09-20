from datetime import date, time
from io import BytesIO

import pandas as pd

from turni.config import ALL_DAYS, ShiftDefinition
from turni.io import InputData, load_input_workbook
from turni.model import Doctor
from turni.scheduler import solve_schedule


def doctor(name: str, ats: str = "ALTRI") -> Doctor:
    return Doctor(name, name, "Test", ats)


def test_never_assigns_outside_availability():
    definition = (ShiftDefinition("X", "Test", time(8), time(12), ALL_DAYS, 2, 2),)
    doctors = {"A": doctor("A"), "B": doctor("B")}
    data = InputData(doctors, {("A", date(2026, 10, 1), "X")}, [])
    result = solve_schedule(data, 2026, 10, definition, max_seconds_per_phase=2)
    assert result.assignments == [("A", "2026-10-01_X")]


def test_shortage_keeps_every_compatible_available_doctor():
    definition = (ShiftDefinition("X", "Test", time(8), time(12), frozenset({3}), 5, 2),)
    doctors = {str(i): doctor(str(i)) for i in range(3)}
    data = InputData(doctors, {(str(i), date(2026, 10, 1), "X") for i in range(3)}, [])
    result = solve_schedule(data, 2026, 10, definition, max_seconds_per_phase=2)
    assert len(result.assignments) == 3


def test_eleven_hour_rest_blocks_following_shift():
    definitions = (
        ShiftDefinition("N", "Notte", time(20), time(8), ALL_DAYS, 1, 2),
        ShiftDefinition("M", "Mattina", time(8), time(14), ALL_DAYS, 1, 1),
    )
    doctors = {"A": doctor("A")}
    data = InputData(doctors, {("A", date(2026, 10, 1), "N"), ("A", date(2026, 10, 2), "M")}, [])
    result = solve_schedule(data, 2026, 10, definitions, max_seconds_per_phase=2)
    assert len(result.assignments) == 1


def test_overlapping_shifts_are_incompatible():
    definitions = (
        ShiftDefinition("D", "Diurno", time(8), time(20), ALL_DAYS, 1, 2),
        ShiftDefinition("M", "Mattina", time(8), time(14), ALL_DAYS, 1, 1),
    )
    doctors = {"A": doctor("A")}
    data = InputData(doctors, {("A", date(2026, 10, 1), "D"), ("A", date(2026, 10, 1), "M")}, [])
    result = solve_schedule(data, 2026, 10, definitions, max_seconds_per_phase=2)
    assert len(result.assignments) == 1


def test_ats_priority_prefers_west_then_east():
    definition = (ShiftDefinition("X", "Test", time(8), time(12), frozenset({3}), 1, 2),)
    doctors = {
        "W": doctor("W", "BERGAMO OVEST"),
        "E": doctor("E", "BERGAMO EST"),
        "A": doctor("A", "ALTRI"),
    }
    data = InputData(doctors, {(key, date(2026, 10, 1), "X") for key in doctors}, [])
    result = solve_schedule(data, 2026, 10, definition, max_seconds_per_phase=2)
    assert result.assignments == [("W", "2026-10-01_X")]


def test_same_seed_reproduces_same_extraction():
    definition = (ShiftDefinition("X", "Test", time(8), time(12), frozenset({3}), 2, 2),)
    doctors = {str(i): doctor(str(i)) for i in range(5)}
    data = InputData(doctors, {(key, date(2026, 10, 1), "X") for key in doctors}, [])
    first = solve_schedule(data, 2026, 10, definition, max_seconds_per_phase=2, seed="abc")
    second = solve_schedule(data, 2026, 10, definition, max_seconds_per_phase=2, seed="abc")
    assert first.assignments == second.assignments


def google_forms_bytes(rows: list[dict]) -> bytes:
    payload = BytesIO()
    with pd.ExcelWriter(payload, engine="openpyxl") as writer:
        pd.DataFrame(rows).to_excel(writer, sheet_name="Risposte del modulo 1", index=False)
    return payload.getvalue()


def test_google_forms_import_uses_latest_response():
    rows = [
        {
            "Timestamp": "01/09/2026 10:00:00",
            "Email": "anna@example.test",
            "COGNOME": "Rossi",
            "NOME": "Anna",
            "ASST DI APPARTENENZA": "OVEST",
            "feriali [giovedì 1]": "19-00",
            "RAGGIUNGI GIA' I TURNI DA CONTRATTO IN PERIFERICA?": "SI",
            "Altro da comunicare": "prima risposta",
        },
        {
            "Timestamp": "02/09/2026 10:00:00",
            "Email": "anna@example.test",
            "COGNOME": "Rossi",
            "NOME": "Anna",
            "ASST DI APPARTENENZA": "BGEST",
            "feriali [giovedì 1]": "20-8",
            "RAGGIUNGI GIA' I TURNI DA CONTRATTO IN PERIFERICA?": "NO",
            "Altro da comunicare": "seconda risposta",
        },
    ]
    data = load_input_workbook(google_forms_bytes(rows), 2026, 10)
    key = "EMAIL:anna@example.test"
    assert data.doctors[key].ats == "BERGAMO EST"
    assert data.doctors[key].notes == "seconda risposta"
    assert data.availability == {(key, date(2026, 10, 1), "NOT")}


def test_infrasettimanale_festivo_creates_all_five_shift_types():
    rows = [{
        "Timestamp": "01/09/2026 10:00:00",
        "Email": "anna@example.test",
        "COGNOME": "Rossi",
        "NOME": "Anna",
        "ASST DI APPARTENENZA": "OVEST",
        "SABATO, DOMENICA, FESTIVI, PREFESTIVI [giovedì 1]": "8-14",
        "RAGGIUNGI GIA' I TURNI DA CONTRATTO IN PERIFERICA?": "SI",
    }]
    data = load_input_workbook(google_forms_bytes(rows), 2026, 10)
    assert data.active_codes_by_date[date(2026, 10, 1)] == frozenset({"MAT", "POM", "DIU", "SER", "NOT"})


def test_typo_in_day_number_is_recovered_from_column_order():
    rows = [{
        "Timestamp": "01/09/2026 10:00:00",
        "Email": "anna@example.test",
        "COGNOME": "Rossi",
        "NOME": "Anna",
        "ASST DI APPARTENENZA": "OVEST",
        "feriali [lunedì 26]": "19-00",
        "feriali [martedì 20]": "20-8",
        "feriali [mercoledì 28]": "19-00",
        "RAGGIUNGI GIA' I TURNI DA CONTRATTO IN PERIFERICA?": "SI",
    }]
    data = load_input_workbook(google_forms_bytes(rows), 2026, 10)
    assert date(2026, 10, 27) in data.active_codes_by_date
    assert any("possibile refuso" in warning for warning in data.warnings)
