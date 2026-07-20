from __future__ import annotations

import sys
import unittest
from datetime import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from motor_alocacao import (  # noqa: E402
    Problem, Teacher, Transmission, audit_allocation, build_grasp_hint, contract_model_for,
    solve_allocation,
)


PROFILE = frozenset({"gestão - administração"})


def teacher(
    identifier: int, capacity: int = 4, profiles=PROFILE, status="ATIVO",
    job="PROFESSOR REGENTE", contracted: int = 40,
) -> Teacher:
    return Teacher(
        identifier, f"Docente {identifier}", f"00000000000{identifier}", job,
        contracted, capacity, "Gestor", status, profiles, ", ".join(profiles),
    )


def transmission(
    identifier: int, day="SEGUNDA", start=time(19, 0), profiles=PROFILE,
    order="1ª",
) -> Transmission:
    return Transmission(
        identifier, identifier + 2, f"C{identifier}", "Curso", f"CURR{identifier}",
        f"D{identifier}", "Disciplina", profiles, ", ".join(profiles), "Curso único",
        day, start, order, "GESTÃO", "Coordenador",
    )


class SolverTests(unittest.TestCase):
    def solve(self, teachers, transmissions):
        problem = Problem(Path("test.xlsx"), tuple(teachers), tuple(transmissions))
        return solve_allocation(
            problem, max_time_seconds=5, workers=1, grasp_iterations=20,
        )

    def test_assigns_eligible_teacher(self):
        result = self.solve([teacher(0)], [transmission(0)])
        self.assertEqual("COMPLETA", result.status)
        self.assertEqual(0, result.assignments[0].teacher_id)
        self.assertEqual(2, result.teacher_loads[0])
        self.assertEqual(
            "Único docente elegível por perfil, carga e horário",
            result.assignments[0].allocation_reason,
        )

    def test_respects_teaching_capacity(self):
        result = self.solve(
            [teacher(0, capacity=2)],
            [transmission(0), transmission(1, start=time(20, 40))],
        )
        self.assertEqual(1, result.allocated_count)
        self.assertEqual(1, result.unassigned_count)
        self.assertEqual(
            "CAPACIDADE_LETIVA_ESGOTADA",
            next(item.reason for item in result.assignments if item.teacher_id is None),
        )

    def test_reuses_capacity_and_schedule_between_module_stages(self):
        result = self.solve(
            [teacher(0, capacity=2)],
            [
                transmission(0, order="1ª"),
                transmission(1, order="2ª"),
            ],
        )

        self.assertEqual(2, result.allocated_count)
        self.assertEqual(4, result.teacher_loads[0])
        self.assertEqual(
            {"PRIMEIRA_ETAPA": 2, "SEGUNDA_ETAPA": 2},
            result.teacher_stage_loads[0],
        )

    def test_extended_discipline_consumes_capacity_in_both_stages(self):
        result = self.solve(
            [teacher(0, capacity=2)],
            [
                transmission(0, order="ESTENDIDA"),
                transmission(1, start=time(20, 40), order="1ª"),
            ],
        )

        self.assertEqual(1, result.allocated_count)
        self.assertEqual(1, result.unassigned_count)
        self.assertEqual(
            "CAPACIDADE_LETIVA_ESGOTADA",
            next(item.reason for item in result.assignments if item.teacher_id is None),
        )

    def test_extended_schedule_conflicts_with_both_stages(self):
        result = self.solve(
            [teacher(0, capacity=4)],
            [
                transmission(0, order="ESTENDIDA"),
                transmission(1, order="1ª"),
                transmission(2, order="2ª"),
            ],
        )

        self.assertEqual(2, result.allocated_count)
        self.assertIsNone(result.assignments[0].teacher_id)
        self.assertEqual("CHOQUE_DE_HORARIO", result.assignments[0].reason)

    def test_prevents_schedule_collision(self):
        result = self.solve([teacher(0, capacity=4)], [transmission(0), transmission(1)])
        self.assertEqual(1, result.allocated_count)
        self.assertEqual("CHOQUE_DE_HORARIO",
                         next(item.reason for item in result.assignments if item.teacher_id is None))

    def test_reports_missing_profile(self):
        result = self.solve(
            [teacher(0, profiles=frozenset({"outro perfil"}))],
            [transmission(0)],
        )
        self.assertEqual("SEM_DOCENTE_COM_PERFIL_E_CARGA", result.assignments[0].reason)

    def test_reports_invalid_schedule(self):
        result = self.solve([teacher(0)], [transmission(0, start=None)])
        self.assertEqual("AGENDA_INVALIDA", result.assignments[0].reason)

    def test_balances_load_proportionally(self):
        result = self.solve(
            [teacher(0, capacity=4), teacher(1, capacity=4)],
            [transmission(0), transmission(1, start=time(20, 40))],
        )
        self.assertEqual({0: 2, 1: 2}, result.teacher_loads)

    def test_switch_maximizes_teachers_with_allocation(self):
        result = self.solve(
            [teacher(0, capacity=4), teacher(1, capacity=4), teacher(2, capacity=4)],
            [
                transmission(0), transmission(1, start=time(20, 40)),
                transmission(2, day="TERÇA"),
            ],
        )
        self.assertEqual(3, result.used_teacher_count)
        self.assertEqual({0: 2, 1: 2, 2: 2}, result.teacher_loads)

    def test_switch_prioritizes_higher_teaching_capacity(self):
        result = self.solve(
            [teacher(0, capacity=2), teacher(1, capacity=6)],
            [
                transmission(0), transmission(1, start=time(20, 40)),
                transmission(2, day="TERÇA"),
            ],
        )
        self.assertEqual({0: 2, 1: 4}, result.teacher_loads)

    def test_scarcity_switch_preserves_task_with_unique_candidate(self):
        profile_a = frozenset({"perfil a"})
        profile_b = frozenset({"perfil b"})
        flexible = frozenset({"perfil a", "perfil b"})
        result = self.solve(
            [
                teacher(0, capacity=2, profiles=profile_a),
                teacher(1, capacity=2, profiles=profile_b),
            ],
            [
                transmission(0, profiles=profile_a),
                transmission(1, start=time(20, 40), profiles=flexible),
                transmission(2, day="TERÇA", profiles=flexible),
            ],
        )
        self.assertIsNotNone(result.assignments[0].teacher_id)
        self.assertEqual(1, result.unassigned_count)
        self.assertEqual(0, result.rescue_scarcity_score)

    def test_inactive_teacher_is_never_allocated(self):
        result = self.solve([teacher(0, status="LICENÇA")], [transmission(0)])
        self.assertIsNone(result.assignments[0].teacher_id)
        self.assertEqual(0, result.used_teacher_count)

    def test_stricto_teacher_with_zero_base_capacity_gets_up_to_two_disciplines(self):
        stricto = teacher(
            0, capacity=0, contracted=0,
            job="PROFESSOR DE ENSINO SUPERIOR PRESENCIAL",
        )
        result = self.solve(
            [stricto],
            [
                transmission(0),
                transmission(
                    1, start=time(20, 40), order="2ª",
                ),
                transmission(
                    2, day="TERÇA", order="2ª",
                ),
            ],
        )
        self.assertEqual(2, result.allocated_count)
        self.assertEqual(1, result.unassigned_count)
        self.assertEqual(4, result.teacher_loads[0])
        self.assertEqual(
            "CAPACIDADE_LETIVA_ESGOTADA",
            next(item.reason for item in result.assignments if item.teacher_id is None),
        )
        self.assertEqual(2, result.diagnostics["stricto_max_disciplines_per_module"])

    def test_teacher_family_does_not_restrict_profile_eligible_selection(self):
        ead_profile = frozenset({"perfil ead"})
        presencial_profile = frozenset({"perfil presencial"})
        result = self.solve(
            [
                teacher(0, capacity=4, profiles=ead_profile),
                teacher(
                    1, capacity=0, contracted=0,
                    profiles=presencial_profile,
                    job="PROFESSOR DE ENSINO SUPERIOR PRESENCIAL",
                ),
            ],
            [
                transmission(
                    0,
                    profiles=ead_profile,
                ),
                transmission(
                    1,
                    start=time(20, 40),
                    profiles=presencial_profile,
                ),
            ],
        )
        assigned = {item.transmission_id: item.teacher_id for item in result.assignments}
        self.assertEqual({0: 0, 1: 1}, assigned)

    def test_stricto_reason_when_multiple_teachers_are_eligible(self):
        result = self.solve(
            [
                teacher(
                    0, capacity=0, contracted=0,
                    job="PROFESSOR DE ENSINO SUPERIOR PRESENCIAL",
                ),
                teacher(
                    1, capacity=0, contracted=0,
                    job="PROFESSOR DE ENSINO SUPERIOR PRESENCIAL",
                ),
            ],
            [transmission(0)],
        )
        self.assertIn(
            "limite de 2 disciplinas",
            result.assignments[0].allocation_reason,
        )

    def test_contract_model_rules(self):
        self.assertEqual("CLT EAD", contract_model_for("PROFESSOR REGENTE", True))
        self.assertEqual(
            "CLT STRICTO",
            contract_model_for("PROFESSOR DE ENSINO SUPERIOR PRESENCIAL", True),
        )
        self.assertEqual("A DEFINIR", contract_model_for("PROFESSOR REGENTE", False))

    def test_grasp_builds_feasible_warm_start(self):
        teachers = (teacher(0, capacity=2), teacher(1, capacity=4))
        transmissions = (
            transmission(0), transmission(1, start=time(20, 40)),
            transmission(2, day="TERÇA"),
        )
        problem = Problem(Path("test.xlsx"), teachers, transmissions)
        eligible = {item.id: [0, 1] for item in transmissions}
        hint = build_grasp_hint(problem, eligible, iterations=30, alpha=0.3)
        assigned = [value for value in hint.assignments.values() if value is not None]
        self.assertEqual(3, len(assigned))
        self.assertLessEqual(assigned.count(0) * 2, teachers[0].teaching_capacity)
        self.assertLessEqual(assigned.count(1) * 2, teachers[1].teaching_capacity)

    def test_grasp_reuses_capacity_between_module_stages(self):
        only_teacher = teacher(0, capacity=2)
        transmissions = (
            transmission(0, order="1ª"),
            transmission(1, order="2ª"),
        )
        problem = Problem(Path("test.xlsx"), (only_teacher,), transmissions)
        eligible = {item.id: [only_teacher.id] for item in transmissions}

        hint = build_grasp_hint(problem, eligible, iterations=10, alpha=0.3)

        self.assertEqual({0: 0, 1: 0}, hint.assignments)

    def test_grasp_allows_two_stricto_disciplines(self):
        stricto = teacher(
            0, capacity=0, contracted=0,
            job="PROFESSOR DE ENSINO SUPERIOR PRESENCIAL",
        )
        transmissions = (
            transmission(0),
            transmission(1, start=time(20, 40)),
        )
        problem = Problem(Path("test.xlsx"), (stricto,), transmissions)
        eligible = {item.id: [stricto.id] for item in transmissions}

        hint = build_grasp_hint(problem, eligible, iterations=10, alpha=0.3)

        self.assertEqual({0: 0, 1: 0}, hint.assignments)

    def test_grasp_keeps_stricto_limit_across_module_stages(self):
        stricto = teacher(
            0, capacity=0, contracted=0,
            job="PROFESSOR DE ENSINO SUPERIOR PRESENCIAL",
        )
        transmissions = (
            transmission(0, order="1ª"),
            transmission(
                1,
                start=time(20, 40),
                order="2ª",
            ),
            transmission(
                2,
                day="TERÇA",
                order="2ª",
            ),
        )
        problem = Problem(Path("test.xlsx"), (stricto,), transmissions)
        eligible = {item.id: [stricto.id] for item in transmissions}

        hint = build_grasp_hint(problem, eligible, iterations=20, alpha=0.3)

        self.assertEqual(
            2,
            sum(teacher_id is not None for teacher_id in hint.assignments.values()),
        )

    def test_cp_sat_has_no_time_limit_by_default(self):
        problem = Problem(Path("test.xlsx"), (teacher(0),), (transmission(0),))
        result = solve_allocation(problem, workers=1)
        self.assertIsNone(result.diagnostics["cp_sat_time_limit_seconds"])
        self.assertEqual(0, result.diagnostics["grasp_iterations"])
        self.assertEqual(0, result.diagnostics["grasp_wall_time_seconds"])

    def test_parallel_search_is_canonicalized_deterministically(self):
        problem = Problem(
            Path("test.xlsx"),
            tuple(teacher(identifier, capacity=4) for identifier in range(3)),
            (
                transmission(0),
                transmission(1, start=time(20, 40)),
                transmission(2, day="TERÇA"),
            ),
        )
        first = solve_allocation(problem, workers=8, random_seed=42)
        second = solve_allocation(problem, workers=8, random_seed=42)
        first_assignments = {
            item.transmission_id: item.teacher_id for item in first.assignments
        }
        second_assignments = {
            item.transmission_id: item.teacher_id for item in second.assignments
        }

        self.assertEqual(first_assignments, second_assignments)
        self.assertEqual("OPTIMAL", first.diagnostics["canonicalization_status"])
        self.assertEqual(1, first.diagnostics["canonicalization_workers"])

    def test_scenario_priority_protects_selected_offer(self):
        problem = Problem(
            Path("test.xlsx"),
            (teacher(0, capacity=2),),
            (transmission(0), transmission(1, start=time(20, 40))),
        )
        result = solve_allocation(
            problem,
            workers=1,
            scenario_policy={"policies": [{
                "policy_type": "PRIORIDADE", "target_type": "OFFER",
                "target_value": "3", "configuration": {},
            }]},
        )
        assignments = {item.transmission_id: item.teacher_id for item in result.assignments}
        self.assertEqual(0, assignments[1])

    def test_scenario_fix_preserves_teacher_assignment(self):
        problem = Problem(
            Path("test.xlsx"),
            (teacher(0), teacher(1)),
            (transmission(0),),
        )
        result = solve_allocation(
            problem,
            workers=1,
            scenario_policy={"policies": [{
                "policy_type": "FIXAR", "target_type": "OFFER",
                "target_value": "2",
                "configuration": {"teacher_badge": "000000000001"},
            }]},
        )
        self.assertEqual(1, result.assignments[0].teacher_id)

    def test_rejects_removed_internalization_policy(self):
        internal = teacher(0, job="PROFESSOR REGENTE")
        external = teacher(1, job="PROFESSOR TEMPORARIO")
        problem = Problem(Path("test.xlsx"), (internal, external), (transmission(0),))
        with self.assertRaisesRegex(ValueError, "não suportada"):
            solve_allocation(
                problem,
                workers=1,
                scenario_policy={"policies": [{
                    "policy_type": "INTERNALIZACAO", "target_type": "GLOBAL",
                    "target_value": "ALL", "configuration": {},
                }]},
            )

    def test_scenario_cluster_recovers_offer_with_controlled_profile_override(self):
        other_profile = frozenset({"gestão - pessoas"})
        problem = Problem(
            Path("test.xlsx"),
            (teacher(0, capacity=4),),
            (
                transmission(0, profiles=other_profile),
                transmission(1, start=time(20, 40), profiles=PROFILE),
            ),
        )
        policy = {"policies": [{
            "policy_type": "ALOCAR_CLUSTER", "target_type": "CLUSTER",
            "target_value": "GESTÃO",
            "configuration": {"baseline_unassigned_rows": [2]},
        }]}
        result = solve_allocation(
            problem,
            workers=1,
            scenario_policy=policy,
        )
        self.assertEqual(0, result.assignments[0].teacher_id)
        self.assertIn("perfil exato flexibilizado", result.assignments[0].allocation_reason)
        self.assertEqual(1, result.diagnostics["scenario_cluster_override_assignments"])
        # Solver diagnostics cannot authorize their own profile exception.
        self.assertEqual("REPROVADO", audit_allocation(problem, result).status)
        self.assertEqual("APROVADO", audit_allocation(problem, result, policy).status)

    def test_rejects_negative_grasp_iterations(self):
        problem = Problem(Path("test.xlsx"), (teacher(0),), (transmission(0),))
        with self.assertRaisesRegex(ValueError, "não pode ser negativo"):
            solve_allocation(problem, workers=1, grasp_iterations=-1)


if __name__ == "__main__":
    unittest.main()
