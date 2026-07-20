from __future__ import annotations

import sys
import unittest
from datetime import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from motor_alocacao.audit import audit_allocation  # noqa: E402
from motor_alocacao.domain import (  # noqa: E402
    MODULE_STAGE_1,
    MODULE_STAGE_2,
    AllocationResult,
    Assignment,
    Problem,
    Teacher,
    Transmission,
)


PROFILE = frozenset({"gestão - administração"})
OTHER_PROFILE = frozenset({"engenharia"})


def teacher(
    identifier: int = 0,
    *,
    capacity: int = 4,
    profiles: frozenset[str] = PROFILE,
    status: str = "ATIVO",
    job_function: str = "PROFESSOR REGENTE",
) -> Teacher:
    return Teacher(
        id=identifier,
        name=f"Docente {identifier}",
        badge=f"00000000000{identifier}",
        job_function=job_function,
        contracted_capacity=40,
        teaching_capacity=capacity,
        manager="Gestor",
        status=status,
        profiles=profiles,
        profile_text=", ".join(profiles),
    )


def transmission(
    identifier: int,
    *,
    start: time = time(19, 0),
    profiles: frozenset[str] = PROFILE,
    day: str = "SEGUNDA",
    order: str = "1ª",
) -> Transmission:
    return Transmission(
        id=identifier,
        excel_row=identifier + 2,
        course=f"C{identifier}",
        course_name="Curso",
        curriculum=f"CURR{identifier}",
        discipline_code=f"D{identifier}",
        discipline_name=f"Disciplina {identifier}",
        profiles=profiles,
        profile_text=", ".join(profiles),
        synergy="Curso único",
        day=day,
        start_time=start,
        order=order,
        cluster="GESTÃO",
        coordinator="Coordenador",
    )


def result(
    assignments: list[Assignment],
    teacher_loads: dict[int, int],
    teacher_stage_loads: dict[int, dict[str, int]] | None = None,
) -> AllocationResult:
    unassigned = sum(item.teacher_id is None for item in assignments)
    used_teachers = {item.teacher_id for item in assignments if item.teacher_id is not None}
    return AllocationResult(
        status="COMPLETA" if unassigned == 0 else "PARCIAL",
        solver_status="OPTIMAL",
        assignments=assignments,
        teacher_loads=teacher_loads,
        objective_unassigned=unassigned,
        used_teacher_count=len(used_teachers),
        zero_active_teacher_count=0,
        high_capacity_score=None,
        rescue_scarcity_score=None,
        wall_time_seconds=0.0,
        teacher_stage_loads=teacher_stage_loads or {
            teacher_id: {
                MODULE_STAGE_1: load,
                MODULE_STAGE_2: 0,
            }
            for teacher_id, load in teacher_loads.items()
        },
    )


def assigned(
    transmission_id: int,
    *,
    eligible_teacher_count: int = 1,
    status: str = "ALOCADA",
    reason: str = "",
    allocation_reason: str = "Único docente elegível",
) -> Assignment:
    return Assignment(
        transmission_id=transmission_id,
        teacher_id=0,
        status=status,
        reason=reason,
        eligible_teacher_count=eligible_teacher_count,
        allocation_reason=allocation_reason,
    )


class AllocationAuditTests(unittest.TestCase):
    def assert_rejected_with(self, audit, code: str) -> None:
        self.assertEqual("REPROVADO", audit.status)
        self.assertIn(code, {issue.code for issue in audit.issues})

    def test_approves_consistent_result(self):
        problem = Problem(
            Path("test.xlsx"),
            (teacher(),),
            (transmission(0),),
        )
        audit = audit_allocation(problem, result([assigned(0)], {0: 2}))

        self.assertEqual("APROVADO", audit.status)
        self.assertEqual([], audit.issues)
        self.assertEqual(
            {
                "transmissions": 1,
                "teachers": 1,
                "allocated": 1,
                "unassigned": 0,
                "used_teachers": 1,
                "schedule_slots_checked": 1,
            },
            audit.checks,
        )

    def test_rejects_profile_incompatibility(self):
        problem = Problem(
            Path("test.xlsx"),
            (teacher(),),
            (transmission(0, profiles=OTHER_PROFILE),),
        )

        audit = audit_allocation(
            problem,
            result([assigned(0, eligible_teacher_count=0)], {0: 2}),
        )

        self.assert_rejected_with(audit, "PERFIL_INCOMPATIVEL")

    def test_rejects_capacity_overrun(self):
        problem = Problem(
            Path("test.xlsx"),
            (teacher(capacity=2),),
            (
                transmission(0),
                transmission(1, start=time(20, 40)),
            ),
        )

        audit = audit_allocation(
            problem,
            result([assigned(0), assigned(1)], {0: 4}),
        )

        self.assert_rejected_with(audit, "CAPACIDADE_EXCEDIDA")
        issue = next(item for item in audit.issues if item.code == "CAPACIDADE_EXCEDIDA")
        self.assertEqual(
            {
                "load": 4,
                "capacity": 2,
                "stage_loads": {
                    MODULE_STAGE_1: 4,
                    MODULE_STAGE_2: 0,
                },
                "exceeded_stages": {MODULE_STAGE_1: 4},
            },
            issue.details["teachers"]["000000000000"],
        )

    def test_approves_capacity_and_schedule_reuse_between_stages(self):
        problem = Problem(
            Path("test.xlsx"),
            (teacher(capacity=2),),
            (
                transmission(0, order="1ª"),
                transmission(1, order="2ª"),
            ),
        )
        stage_loads = {
            0: {MODULE_STAGE_1: 2, MODULE_STAGE_2: 2},
        }

        audit = audit_allocation(
            problem,
            result(
                [assigned(0), assigned(1)],
                {0: 4},
                teacher_stage_loads=stage_loads,
            ),
        )

        self.assertEqual("APROVADO", audit.status)
        self.assertEqual([], audit.issues)

    def test_rejects_extended_collision_with_first_stage(self):
        problem = Problem(
            Path("test.xlsx"),
            (teacher(capacity=4),),
            (
                transmission(0, order="ESTENDIDA"),
                transmission(1, order="1ª"),
            ),
        )
        stage_loads = {
            0: {MODULE_STAGE_1: 4, MODULE_STAGE_2: 2},
        }

        audit = audit_allocation(
            problem,
            result(
                [assigned(0), assigned(1)],
                {0: 4},
                teacher_stage_loads=stage_loads,
            ),
        )

        self.assert_rejected_with(audit, "CHOQUE_DE_HORARIO")

    def test_approves_two_stricto_disciplines(self):
        problem = Problem(
            Path("test.xlsx"),
            (
                teacher(
                    capacity=0,
                    job_function="PROFESSOR DE ENSINO SUPERIOR PRESENCIAL",
                ),
            ),
            (
                transmission(0),
                transmission(
                    1,
                    start=time(20, 40),
                ),
            ),
        )

        audit = audit_allocation(
            problem,
            result([assigned(0), assigned(1)], {0: 4}),
        )

        self.assertEqual("APROVADO", audit.status)
        self.assertEqual([], audit.issues)

    def test_rejects_more_than_two_stricto_disciplines(self):
        problem = Problem(
            Path("test.xlsx"),
            (
                teacher(
                    capacity=0,
                    job_function="PROFESSOR DE ENSINO SUPERIOR PRESENCIAL",
                ),
            ),
            (
                transmission(0),
                transmission(
                    1,
                    start=time(20, 40),
                ),
                transmission(2, day="TERÇA"),
            ),
        )

        audit = audit_allocation(
            problem,
            result([assigned(0), assigned(1), assigned(2)], {0: 6}),
        )

        self.assert_rejected_with(audit, "LIMITE_STRICTO_EXCEDIDO")
        issue = next(
            item for item in audit.issues if item.code == "LIMITE_STRICTO_EXCEDIDO"
        )
        self.assertEqual(2, issue.details["max_disciplines_per_module"])
        self.assertEqual(["000000000000"], issue.details["badges"])

    def test_rejects_reported_load_mismatch(self):
        problem = Problem(
            Path("test.xlsx"),
            (teacher(),),
            (transmission(0),),
        )

        audit = audit_allocation(problem, result([assigned(0)], {0: 0}))

        self.assert_rejected_with(audit, "CARGA_REPORTADA_INCONSISTENTE")

    def test_rejects_reported_stage_load_mismatch(self):
        problem = Problem(
            Path("test.xlsx"),
            (teacher(),),
            (transmission(0, order="2ª"),),
        )

        audit = audit_allocation(
            problem,
            result(
                [assigned(0)],
                {0: 2},
                teacher_stage_loads={
                    0: {MODULE_STAGE_1: 2, MODULE_STAGE_2: 0},
                },
            ),
        )

        self.assert_rejected_with(
            audit,
            "CARGA_ETAPA_REPORTADA_INCONSISTENTE",
        )

    def test_rejects_schedule_collision(self):
        problem = Problem(
            Path("test.xlsx"),
            (teacher(capacity=4),),
            (transmission(0), transmission(1)),
        )

        audit = audit_allocation(
            problem,
            result([assigned(0), assigned(1)], {0: 4}),
        )

        self.assert_rejected_with(audit, "CHOQUE_DE_HORARIO")
        issue = next(item for item in audit.issues if item.code == "CHOQUE_DE_HORARIO")
        self.assertEqual((2, 3), issue.rows)

    def test_rejects_allocation_to_inactive_teacher(self):
        problem = Problem(
            Path("test.xlsx"),
            (teacher(status="LICENÇA"),),
            (transmission(0),),
        )

        audit = audit_allocation(
            problem,
            result([assigned(0, eligible_teacher_count=0)], {0: 2}),
        )

        self.assert_rejected_with(audit, "DOCENTE_INATIVO_ALOCADO")

    def test_rejects_inconsistent_assigned_and_unassigned_explanations(self):
        problem = Problem(
            Path("test.xlsx"),
            (teacher(),),
            (
                transmission(0),
                transmission(1, start=time(20, 40)),
            ),
        )
        assignments = [
            assigned(
                0,
                status="NAO_ALOCADA",
                reason="Motivo indevido",
                allocation_reason="",
            ),
            Assignment(
                transmission_id=1,
                teacher_id=None,
                status="ALOCADA",
                reason="",
                eligible_teacher_count=1,
                allocation_reason="Justificativa indevida",
            ),
        ]

        audit = audit_allocation(problem, result(assignments, {0: 2}))

        self.assert_rejected_with(audit, "EXPLICACAO_INCONSISTENTE")
        issue = next(item for item in audit.issues if item.code == "EXPLICACAO_INCONSISTENTE")
        self.assertEqual((2, 3), issue.rows)


if __name__ == "__main__":
    unittest.main()
