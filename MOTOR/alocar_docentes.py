from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from motor_alocacao import create_round_directory, load_problem, solve_allocation, write_results  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Motor CP-SAT de alocação docente EAD ao vivo.")
    parser.add_argument("planilha", type=Path, help="Planilha validada com MAPA PEDAGÓGICO e DOCENTES")
    parser.add_argument("--saida", type=Path, default=ROOT / "resultado", help="Diretório de saída")
    parser.add_argument(
        "--tempo-limite", type=float, default=None,
        help="Limite total aproximado em segundos; por padrão o CP-SAT processa até concluir",
    )
    parser.add_argument("--workers", type=int, default=8, help="Threads de busca do CP-SAT")
    parser.add_argument(
        "--iteracoes-grasp", type=int, default=0,
        help="Construções multi-start do GRASP; 0 usa CP-SAT puro (padrão)",
    )
    parser.add_argument("--alpha-grasp", type=float, default=0.25, help="Aleatoriedade da lista restrita [0,1]")
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
    print(f"Docentes ativos sem alocação: {result.zero_active_teacher_count}")
    print(f"Rodada: {round_dir.name}")
    print(f"Resultado: {xlsx_path}")
    print(f"Resumo: {json_path}")
    return 0 if result.solver_status in {"OPTIMAL", "FEASIBLE"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
