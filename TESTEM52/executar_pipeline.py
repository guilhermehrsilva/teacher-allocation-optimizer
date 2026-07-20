from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pipeline import (
    DEFAULT_INPUT_DIR,
    DEFAULT_OUTPUT_DIR,
    EXIT_INPUT_CONFIG,
    PipelineConfig,
    run_pipeline,
)


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(EXIT_INPUT_CONFIG, f"{self.prog}: erro: {message}\n")


def build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(
        description="Valida, resolve e audita a alocação docente do módulo 52.",
    )
    parser.add_argument(
        "--base",
        type=Path,
        help="XLSX explícito; se omitido, descobre exatamente um arquivo em entrada/.",
    )
    parser.add_argument("--entrada", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--resultado", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="Workers das fases de otimização; a canonicalização final usa 1.",
    )
    parser.add_argument("--tempo-limite", type=float, default=None)
    parser.add_argument(
        "--permitir-nao-otimo",
        action="store_true",
        help="Aceita FEASIBLE auditado; por padrão exige OPTIMAL.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    run = run_pipeline(
        PipelineConfig(
            input_dir=args.entrada,
            output_dir=args.resultado,
            base=args.base,
            workers=args.workers,
            max_time_seconds=args.tempo_limite,
            require_optimal=not args.permitir_nao_otimo,
        )
    )
    print(f"Status: {run.state}")
    print(f"Código: {run.exit_code}")
    print(f"Mensagem: {run.message}")
    if run.round_dir:
        print(f"Rodada: {run.round_dir}")
        print(f"Status JSON: {run.status_path}")
        print(f"Manifesto: {run.manifest_path}")
    return run.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
