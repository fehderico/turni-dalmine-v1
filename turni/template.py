from __future__ import annotations

from io import BytesIO

import pandas as pd
from openpyxl.styles import Font, PatternFill


def create_template_bytes() -> bytes:
    medici = pd.DataFrame(columns=["nome", "cognome", "ats", "minimo_turni", "timestamp_risposta"])
    disponibilita = pd.DataFrame(columns=["nome", "cognome", "data", "tipo_turno", "disponibile", "timestamp_risposta"])
    istruzioni = pd.DataFrame({
        "Campo": ["ats", "minimo_turni", "tipo_turno", "disponibile", "timestamp_risposta"],
        "Regola": [
            "BERGAMO OVEST, BERGAMO EST o altro testo",
            "Informazione facoltativa, non usata dalla V1",
            "SER, NOT, DIU, MAT o POM",
            "Sì/No; se vuoto è considerato Sì",
            "Opzionale; se presente, per invii multipli vale l'ultimo",
        ],
    })
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        medici.to_excel(writer, "Medici", index=False)
        disponibilita.to_excel(writer, "Disponibilita", index=False)
        istruzioni.to_excel(writer, "Istruzioni", index=False)
        for sheet in writer.book.worksheets:
            for cell in sheet[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill("solid", fgColor="17365D")
            sheet.freeze_panes = "A2"
            sheet.sheet_view.showGridLines = False
            for column in sheet.columns:
                sheet.column_dimensions[column[0].column_letter].width = min(max(len(str(c.value or "")) for c in column) + 2, 55)
    return output.getvalue()
