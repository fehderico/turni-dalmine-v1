from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from io import BytesIO
from pathlib import Path
import re
from typing import BinaryIO
import unicodedata

import pandas as pd

from .config import FORM_SHIFT_MAP, normalize_ats
from .model import Doctor, doctor_key


@dataclass
class InputData:
    doctors: dict[str, Doctor]
    availability: set[tuple[str, date, str]]
    warnings: list[str]
    source_format: str = "normalizzato"
    source_sheet: str = ""
    active_codes_by_date: dict[date, frozenset[str]] = field(default_factory=dict)


REQUIRED_DOCTOR_COLUMNS = {"nome", "cognome", "ats"}
REQUIRED_AVAILABILITY_COLUMNS = {"nome", "cognome", "data", "tipo_turno"}


def _normalise_columns(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame.columns = [str(c).strip().lower() for c in frame.columns]
    return frame


def _canonical(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.lower().replace("’", "'")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


def _email_key(value: object) -> str:
    email = str(value or "").strip().lower()
    return f"EMAIL:{email}" if email else ""


def _find_column(columns: list[object], predicate) -> object | None:
    return next((column for column in columns if predicate(_canonical(column))), None)


def _normalise_contract_status(value: object) -> str:
    text = _canonical(value)
    if text == "si":
        return "SI"
    if text == "no":
        return "NO"
    if "solo unica" in text:
        return "SOLO UNICA"
    return str(value or "").strip()


def _parse_form_selections(value: object) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        values = value
    elif pd.isna(value):
        return []
    else:
        values = re.split(r"[,;\n]+", str(value))
    return [re.sub(r"\s+", "", str(item)).replace("–", "-").strip() for item in values if str(item).strip()]


WEEKDAY_BY_NAME = {
    "lunedi": 0,
    "martedi": 1,
    "mercoledi": 2,
    "giovedi": 3,
    "venerdi": 4,
    "sabato": 5,
    "domenica": 6,
}

FULL_DAY_CODES = frozenset({"MAT", "POM", "DIU", "SER", "NOT"})
WEEKDAY_CODES = frozenset({"SER", "NOT"})


def _day_from_grid_header(
    header: object,
    year: int,
    month: int,
    after: date | None = None,
) -> tuple[date | None, bool]:
    text = str(header)
    matches = re.findall(r"\[([^\]]+)\]", text)
    label = matches[-1] if matches else text
    canonical = _canonical(label)
    match = re.search(r"(lunedi|martedi|mercoledi|giovedi|venerdi|sabato|domenica)\s+(\d{1,2})", canonical)
    if not match:
        return None, False
    weekday = WEEKDAY_BY_NAME[match.group(1)]
    try:
        candidate = date(year, month, int(match.group(2)))
    except ValueError:
        return None, False
    if candidate.weekday() == weekday and (after is None or candidate > after):
        return candidate, False

    # Le colonne delle singole griglie sono cronologiche. Questo recupera un
    # refuso nel numero del giorno (es. martedi 20 dopo lunedi 28 -> 29), senza
    # correggere in silenzio l'intero file quando mese/anno sono sbagliati.
    if after is not None:
        probe = after + timedelta(days=1)
        while probe.month == month:
            if probe.weekday() == weekday:
                return probe, True
            probe += timedelta(days=1)
    return candidate, candidate.weekday() != weekday


def _parse_bool(value: object) -> bool:
    if pd.isna(value):
        return True
    return str(value).strip().lower() not in {"0", "false", "no", "n", "non disponibile"}


def _open_excel(source: str | Path | bytes | BinaryIO) -> pd.ExcelFile:
    if isinstance(source, bytes):
        source = BytesIO(source)
    return pd.ExcelFile(source)


def _load_normalized(workbook: pd.ExcelFile, year: int, month: int) -> InputData:
    doctors_df = _normalise_columns(pd.read_excel(workbook, "Medici"))
    availability_df = _normalise_columns(pd.read_excel(workbook, "Disponibilita"))
    missing = REQUIRED_DOCTOR_COLUMNS - set(doctors_df.columns)
    if missing:
        raise ValueError(f"Colonne mancanti in Medici: {', '.join(sorted(missing))}")
    missing = REQUIRED_AVAILABILITY_COLUMNS - set(availability_df.columns)
    if missing:
        raise ValueError(f"Colonne mancanti in Disponibilita: {', '.join(sorted(missing))}")

    warnings: list[str] = []
    doctors_df["_key"] = [doctor_key(n, c) for n, c in zip(doctors_df["nome"], doctors_df["cognome"])]
    if "timestamp_risposta" in doctors_df.columns:
        doctors_df["_ts"] = pd.to_datetime(doctors_df["timestamp_risposta"], errors="coerce")
        doctors_df = doctors_df.sort_values("_ts", kind="stable").drop_duplicates("_key", keep="last")
    else:
        duplicates = doctors_df["_key"].duplicated(keep=False)
        if duplicates.any():
            warnings.append("Invii duplicati in Medici senza timestamp: è stata usata l'ultima riga.")
        doctors_df = doctors_df.drop_duplicates("_key", keep="last")

    doctors: dict[str, Doctor] = {}
    latest_ts: dict[str, pd.Timestamp] = {}
    for _, row in doctors_df.iterrows():
        key = row["_key"]
        if key == "|":
            warnings.append("Riga Medici senza nome e cognome ignorata.")
            continue
        doctors[key] = Doctor(
            key=key,
            nome=str(row["nome"]).strip(),
            cognome=str(row["cognome"]).strip(),
            ats=normalize_ats(row["ats"]),
        )
        if "_ts" in row and pd.notna(row["_ts"]):
            latest_ts[key] = row["_ts"]

    availability_df["_key"] = [doctor_key(n, c) for n, c in zip(availability_df["nome"], availability_df["cognome"])]
    availability_df["_date"] = pd.to_datetime(availability_df["data"], errors="coerce").dt.date
    if "timestamp_risposta" in availability_df.columns and latest_ts:
        availability_df["_ts"] = pd.to_datetime(availability_df["timestamp_risposta"], errors="coerce")
        keep = [pd.isna(ts) or key not in latest_ts or ts == latest_ts[key] for key, ts in zip(availability_df["_key"], availability_df["_ts"])]
        availability_df = availability_df.loc[keep]

    availability: set[tuple[str, date, str]] = set()
    for _, row in availability_df.iterrows():
        key = row["_key"]
        day = row["_date"]
        code = str(row["tipo_turno"]).strip().upper()
        if key not in doctors:
            warnings.append(f"Disponibilità ignorata per medico non presente: {key.replace('|', ' ')}")
            continue
        if pd.isna(day) or day.year != year or day.month != month:
            warnings.append(f"Disponibilità fuori mese o data non valida ignorata: {key.replace('|', ' ')}")
            continue
        if "disponibile" in availability_df.columns and not _parse_bool(row.get("disponibile")):
            continue
        availability.add((key, day, code))

    return InputData(
        doctors=doctors,
        availability=availability,
        warnings=warnings,
        source_format="normalizzato",
        source_sheet="Medici + Disponibilita",
    )


def _load_google_forms(workbook: pd.ExcelFile, year: int, month: int) -> InputData:
    candidates: list[tuple[str, pd.DataFrame]] = []
    for sheet_name in workbook.sheet_names:
        frame = pd.read_excel(workbook, sheet_name)
        canonical = {_canonical(column) for column in frame.columns}
        if "cognome" in canonical and "nome" in canonical and any("asst di appartenenza" in value for value in canonical):
            candidates.append((sheet_name, frame))
    if not candidates:
        raise ValueError(
            "Formato non riconosciuto: servono i fogli Medici/Disponibilita oppure un foglio risposte Google Forms con NOME, COGNOME e ASST DI APPARTENENZA."
        )

    sheet_name, frame = candidates[0]
    columns = list(frame.columns)
    nome_col = _find_column(columns, lambda value: value == "nome")
    cognome_col = _find_column(columns, lambda value: value == "cognome")
    email_col = _find_column(columns, lambda value: value in {"email", "indirizzo email", "indirizzo di posta elettronica"})
    asst_col = _find_column(columns, lambda value: "asst di appartenenza" in value)
    timestamp_col = _find_column(columns, lambda value: value in {"timestamp", "indicazione oraria", "data e ora"})
    contract_col = _find_column(columns, lambda value: "raggiungi gia i turni da contratto in periferica" in value)
    notes_col = _find_column(columns, lambda value: "note da comunicare" in value or "altro da comunicare" in value)
    if email_col is None:
        raise ValueError("Nel foglio Google Forms manca il campo Email, necessario per identificare le risposte duplicate.")

    frame = frame.copy()
    frame["_row_order"] = range(len(frame))
    frame["_identity"] = [
        _email_key(email) or doctor_key(nome, cognome)
        for email, nome, cognome in zip(frame[email_col], frame[nome_col], frame[cognome_col])
    ]
    if timestamp_col is not None:
        frame["_timestamp"] = pd.to_datetime(frame[timestamp_col], errors="coerce", dayfirst=True)
        frame = frame.sort_values(["_timestamp", "_row_order"], na_position="first", kind="stable")
    frame = frame.drop_duplicates("_identity", keep="last")

    warnings = [
        "Il riposo di 11 ore è verificato tra i turni presenti nel file; eventuali turni periferici non inclusi non possono essere controllati.",
        "Le informazioni contrattuali sono importate a scopo informativo ma non influenzano le assegnazioni nella V1.",
    ]
    doctors: dict[str, Doctor] = {}
    availability: set[tuple[str, date, str]] = set()
    grid_columns: list[tuple[object, date, frozenset[str]]] = []
    last_date_by_section: dict[str, date] = {}
    corrected_headers: list[str] = []
    weekday_mismatches = 0
    for column in columns:
        canonical = _canonical(column)
        if canonical.startswith("feriali"):
            section = "feriali"
            codes = WEEKDAY_CODES
        elif any(token in canonical for token in ("festiv", "prefestiv", "sabato", "sabati", "domenica", "domeniche")):
            section = "festivi"
            codes = FULL_DAY_CODES
        else:
            continue
        day, corrected = _day_from_grid_header(column, year, month, last_date_by_section.get(section))
        if day is not None:
            grid_columns.append((column, day, codes))
            last_date_by_section[section] = day
            if corrected:
                corrected_headers.append(f"{column} -> {day:%d/%m/%Y}")
                weekday_mismatches += 1

    if not grid_columns:
        raise ValueError("Nessuna colonna della griglia disponibilità riconosciuta nel foglio Google Forms.")
    if weekday_mismatches > max(2, len(grid_columns) // 4):
        raise ValueError(
            "Il mese o l'anno selezionato non corrisponde alle intestazioni dei giorni del modulo. "
            "Controlla i valori nella barra laterale."
        )
    if corrected_headers:
        warnings.append("Intestazioni con possibile refuso interpretate in ordine cronologico: " + "; ".join(corrected_headers))

    active_codes_by_date: dict[date, set[str]] = {}
    for _, day, codes in grid_columns:
        active_codes_by_date.setdefault(day, set()).update(codes)

    unknown_options: set[str] = set()
    for _, row in frame.iterrows():
        key = row["_identity"]
        nome = str(row[nome_col] if pd.notna(row[nome_col]) else "").strip()
        cognome = str(row[cognome_col] if pd.notna(row[cognome_col]) else "").strip()
        email = str(row[email_col] if pd.notna(row[email_col]) else "").strip().lower()
        if not nome or not cognome or not email or key in {"", "|"}:
            warnings.append(f"Riga {int(row['_row_order']) + 2} ignorata: email, nome o cognome mancante.")
            continue
        status = _normalise_contract_status(row[contract_col]) if contract_col is not None else ""
        notes = str(row[notes_col]).strip() if notes_col is not None and pd.notna(row[notes_col]) else ""
        doctors[key] = Doctor(
            key=key,
            nome=nome,
            cognome=cognome,
            ats=normalize_ats(row[asst_col]),
            email=email,
            contract_status=status,
            notes=notes,
        )
        for column, day, _ in grid_columns:
            for option in _parse_form_selections(row[column]):
                code = FORM_SHIFT_MAP.get(option)
                if code is None:
                    unknown_options.add(option)
                    continue
                availability.add((key, day, code))

    if unknown_options:
        warnings.append("Opzioni turno non riconosciute e ignorate: " + ", ".join(sorted(unknown_options)))
    return InputData(
        doctors=doctors,
        availability=availability,
        warnings=warnings,
        source_format="google_forms",
        source_sheet=sheet_name,
        active_codes_by_date={day: frozenset(codes) for day, codes in active_codes_by_date.items()},
    )


def load_input_workbook(source: str | Path | bytes | BinaryIO, year: int, month: int) -> InputData:
    workbook = _open_excel(source)
    if {"Medici", "Disponibilita"}.issubset(workbook.sheet_names):
        return _load_normalized(workbook, year, month)
    return _load_google_forms(workbook, year, month)
