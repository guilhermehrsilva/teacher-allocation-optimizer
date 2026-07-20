from __future__ import annotations

import argparse
import sys
from pathlib import Path


OPTIMIZE_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = OPTIMIZE_DIR.parent
sys.path.insert(0, str(REPOSITORY_ROOT / "MOTOR" / "src"))

from motor_alocacao import (  # noqa: E402
    create_round_directory,
    load_problem,
    solve_allocation,
    write_results,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Executa a versão otimizada do motor de alocação docente.",
    )
    parser.add_argument(
        "planilha",
        nargs="?",
        type=Path,
        default=OPTIMIZE_DIR / "BASE_SINTETICA_PERFIL_DOCENTE_COMPLETO.xlsx",
    )
    parser.add_argument("--saida", type=Path, default=OPTIMIZE_DIR / "resultado")
    parser.add_argument("--tempo-limite", type=float, default=None)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument(
        "--iteracoes-grasp",
        type=int,
        default=0,
        help="0 executa CP-SAT puro; valores positivos habilitam o GRASP opcional",
    )
    parser.add_argument("--alpha-grasp", type=float, default=0.25)
    args = parser.parse_args()

    problem = load_problem(args.planilha)
    result = solve_allocation(
        problem,
        max_time_seconds=args.tempo_limite,
        workers=args.workers,
        grasp_iterations=args.iteracoes_grasp,
        grasp_alpha=args.alpha_grasp,
    )
    round_dir = create_round_directory(args.saida)
    xlsx_path, json_path = write_results(problem, result, round_dir)

    print(f"Status: {result.status} ({result.solver_status})")
    print(f"Transmissões: {len(problem.transmissions)}")
    print(f"Alocadas: {result.allocated_count}")
    print(f"Não alocadas: {result.unassigned_count}")
    print(f"Docentes com alocação: {result.used_teacher_count}")
    print(f"Tempo total: {result.wall_time_seconds:.3f}s")
    print(f"Tempo GRASP: {result.diagnostics['grasp_wall_time_seconds']:.3f}s")
    print(f"Tempo CP-SAT: {result.diagnostics['cp_sat_wall_time_seconds']:.3f}s")
    print(f"Rodada: {round_dir.name}")
    print(f"Resultado: {xlsx_path}")
    print(f"Resumo: {json_path}")
    return 0 if result.solver_status in {"OPTIMAL", "FEASIBLE"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
