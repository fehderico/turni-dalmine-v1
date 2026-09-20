from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd


def main() -> None:
    doctors = [
        ("Anna", "Rossi", "BERGAMO OVEST", 1.0),
        ("Luca", "Bianchi", "BERGAMO OVEST", 1.0),
        ("Sara", "Verdi", "BERGAMO OVEST", 0.5),
        ("Marco", "Neri", "BERGAMO EST", 1.0),
        ("Elena", "Galli", "BERGAMO EST", 1.0),
        ("Paolo", "Conti", "BERGAMO EST", 0.5),
        ("Giulia", "Sala", "BRESCIA", 1.0),
        ("Andrea", "Villa", "BRESCIA", 1.0),
        ("Chiara", "Fontana", "BRESCIA", 0.5),
        ("Matteo", "Riva", "ALTRO", 1.0),
        ("Irene", "Ferri", "ALTRO", 0.5),
        ("Davide", "Marini", "ALTRO", 1.0),
    ]
    timestamp = datetime(2026, 9, 10, 12, 0)
    medici = pd.DataFrame(doctors, columns=["nome", "cognome", "ats", "minimo_turni"])
    medici["timestamp_risposta"] = timestamp

    rows = []
    for index, (nome, cognome, _, _) in enumerate(doctors):
        for day in range(1, 8):
            for code in ("SER", "NOT"):
                if (index + day + (code == "NOT")) % 3:
                    rows.append((nome, cognome, datetime(2026, 10, day), code, True, timestamp))
            if datetime(2026, 10, day).weekday() >= 5:
                for code in ("DIU", "MAT", "POM"):
                    if (index + day + len(code)) % 2:
                        rows.append((nome, cognome, datetime(2026, 10, day), code, True, timestamp))
    disponibilita = pd.DataFrame(rows, columns=["nome", "cognome", "data", "tipo_turno", "disponibile", "timestamp_risposta"])
    path = Path(__file__).parent / "sample_data" / "input_esempio_ottobre_2026.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        medici.to_excel(writer, sheet_name="Medici", index=False)
        disponibilita.to_excel(writer, sheet_name="Disponibilita", index=False)
    print(path)


if __name__ == "__main__":
    main()
