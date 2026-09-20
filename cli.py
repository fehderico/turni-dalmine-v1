from __future__ import annotations

import argparse
from pathlib import Path

from turni.exporters import export_excel, export_pdf
from turni.io import load_input_workbook
from turni.scheduler import solve_schedule


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera il calendario dei turni della centrale di Dalmine")
    parser.add_argument("--input", required=True, type=Path, help="Export XLSX Google Forms o file con Medici e Disponibilita")
    parser.add_argument("--month", required=True, help="Mese nel formato YYYY-MM")
    parser.add_argument("--output-dir", type=Path, default=Path("output"))
    parser.add_argument("--seconds", type=float, default=20.0, help="Tempo massimo per fase di ottimizzazione")
    args = parser.parse_args()
    year, month = (int(part) for part in args.month.split("-"))
    data = load_input_workbook(args.input, year, month)
    result = solve_schedule(data, year, month, max_seconds_per_phase=args.seconds)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    excel_path = args.output_dir / f"calendario_turni_{args.month}.xlsx"
    pdf_path = args.output_dir / f"calendario_turni_{args.month}.pdf"
    excel_path.write_bytes(export_excel(result))
    pdf_path.write_bytes(export_pdf(result))
    print(f"Copertura: {len(result.assignments)} assegnazioni")
    print(excel_path.resolve())
    print(pdf_path.resolve())


if __name__ == "__main__":
    main()
