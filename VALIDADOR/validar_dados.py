from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from alocacao_docente.validation import validate_workbook  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida as bases de alocação docente.")
    parser.add_argument("planilha", type=Path, help="Arquivo .xlsx com as abas do piloto")
    parser.add_argument(
        "--saida", type=Path, default=Path("resultado_validacao"),
        help="Diretório dos relatórios JSON e CSV",
    )
    parser.add_argument(
        "--modulo-esperado", type=int, default=None,
        help="Reprova a base quando MÓD contém outro módulo",
    )
    args = parser.parse_args()
    report = validate_workbook(args.planilha, expected_module=args.modulo_esperado)
    json_path, csv_path = report.write(args.saida)
    counts = report.severity_counts
    print(f"Status: {report.status}")
    print(f"Abas: {report.sheets}")
    print("Ocorrências: " + ", ".join(f"{key}={value}" for key, value in counts.items()))
    print(f"Relatório JSON: {json_path}")
    print(f"Inconsistências CSV: {csv_path}")
    return 0 if report.status != "REPROVADO" else 2


if __name__ == "__main__":
    raise SystemExit(main())
