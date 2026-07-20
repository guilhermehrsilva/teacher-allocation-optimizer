from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .domain import (
    MODULE_STAGES,
    STRICTO_MAX_DISCIPLINES_PER_MODULE,
    AllocationResult,
    Problem,
)
from .eligibility import build_eligibility
from .policies import cluster_policy_eligibility, scenario_policies


@dataclass(frozen=True)
class AuditIssue:
    code: str
    message: str
    rows: tuple[int, ...] = ()
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class AllocationAudit:
    status: str = "APROVADO"
    checks: dict[str, int] = field(default_factory=dict)
    issues: list[AuditIssue] = field(default_factory=list)

    def add(
        self,
        code: str,
        message: str,
        rows: list[int] | tuple[int, ...] = (),
        details: dict[str, Any] | None = None,
    ) -> None:
        self.issues.append(
            AuditIssue(code, message, tuple(sorted(set(rows))), details or {})
        )
        self.status = "REPROVADO"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "checks": self.checks,
            "issue_count": len(self.issues),
            "issues": [asdict(issue) for issue in self.issues],
        }

    def write(self, path: str | Path) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        temporary.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        temporary.replace(destination)
        return destination


def audit_allocation(
    problem: Problem,
    result: AllocationResult,
    scenario_policy: dict[str, Any] | None = None,
) -> AllocationAudit:
    audit = AllocationAudit()
    transmissions = {item.id: item for item in problem.transmissions}
    teachers = {item.id: item for item in problem.teachers}
    policies = scenario_policies(scenario_policy)
    eligibility, scenario_override_pairs, _ = cluster_policy_eligibility(
        problem,
        build_eligibility(problem),
        policies,
    )
    assignments_by_transmission = {
        item.transmission_id: item for item in result.assignments
    }

    expected_ids = set(transmissions)
    actual_ids = [item.transmission_id for item in result.assignments]
    duplicate_ids = [key for key, count in Counter(actual_ids).items() if count > 1]
    if duplicate_ids:
        audit.add(
            "ATRIBUICAO_DUPLICADA",
            "Uma transmissão aparece mais de uma vez no resultado.",
            details={"transmission_ids": duplicate_ids},
        )
    missing_ids = expected_ids - set(actual_ids)
    extra_ids = set(actual_ids) - expected_ids
    if missing_ids or extra_ids:
        audit.add(
            "COBERTURA_RESULTADO_INCONSISTENTE",
            "O conjunto de transmissões do resultado diverge do problema.",
            details={"missing_ids": sorted(missing_ids), "extra_ids": sorted(extra_ids)},
        )

    recomputed_loads = {teacher.id: 0 for teacher in problem.teachers}
    recomputed_stage_loads = {
        teacher.id: {stage: 0 for stage in MODULE_STAGES}
        for teacher in problem.teachers
    }
    occupied: dict[
        tuple[int, str, tuple[str, str]], list[int]
    ] = defaultdict(list)
    assigned_rows: list[int] = []
    unassigned_rows: list[int] = []
    profile_errors: list[int] = []
    inactive_errors: list[int] = []
    ineligible_errors: list[int] = []
    eligibility_count_errors: list[int] = []
    explanation_errors: list[int] = []
    for transmission_id in sorted(expected_ids & set(assignments_by_transmission)):
        assignment = assignments_by_transmission[transmission_id]
        transmission = transmissions[transmission_id]
        eligible = set(eligibility[transmission_id])
        if assignment.eligible_teacher_count != len(eligible):
            eligibility_count_errors.append(transmission.excel_row)

        if assignment.teacher_id is None:
            unassigned_rows.append(transmission.excel_row)
            if assignment.status != "NAO_ALOCADA" or not assignment.reason:
                explanation_errors.append(transmission.excel_row)
            if assignment.allocation_reason:
                explanation_errors.append(transmission.excel_row)
            continue

        assigned_rows.append(transmission.excel_row)
        teacher = teachers.get(assignment.teacher_id)
        if teacher is None:
            audit.add(
                "DOCENTE_INEXISTENTE",
                "Uma alocação referencia docente inexistente.",
                [transmission.excel_row],
                {"teacher_id": assignment.teacher_id},
            )
            continue
        if assignment.status != "ALOCADA" or assignment.reason:
            explanation_errors.append(transmission.excel_row)
        if not assignment.allocation_reason:
            explanation_errors.append(transmission.excel_row)
        if not teacher.is_active:
            inactive_errors.append(transmission.excel_row)
        if teacher.id not in eligible:
            ineligible_errors.append(transmission.excel_row)
        if (
            not transmission.profiles.intersection(teacher.profiles)
            and (transmission.id, teacher.id) not in scenario_override_pairs
        ):
            profile_errors.append(transmission.excel_row)
        recomputed_loads[teacher.id] += problem.hours_per_transmission
        for stage in transmission.module_stages:
            recomputed_stage_loads[teacher.id][stage] += problem.hours_per_transmission
        if transmission.slot is not None:
            for stage in transmission.module_stages:
                occupied[(teacher.id, stage, transmission.slot)].append(
                    transmission.excel_row
                )

    def add_rows(code: str, message: str, rows: list[int]) -> None:
        if rows:
            audit.add(code, message, rows)

    add_rows(
        "DOCENTE_INATIVO_ALOCADO",
        "Há alocação para docente que não está ativo.",
        inactive_errors,
    )
    add_rows(
        "DOCENTE_NAO_ELEGIVEL",
        "Há alocação para docente fora do conjunto de elegibilidade recalculado.",
        ineligible_errors,
    )
    add_rows(
        "PERFIL_INCOMPATIVEL",
        "Há alocação sem interseção de perfil elegível.",
        profile_errors,
    )
    add_rows(
        "CONTAGEM_ELEGIVEIS_INCONSISTENTE",
        "A quantidade registrada de candidatos elegíveis está incorreta.",
        eligibility_count_errors,
    )
    add_rows(
        "EXPLICACAO_INCONSISTENTE",
        "Status, motivo de pendência ou motivo de alocação está inconsistente.",
        explanation_errors,
    )

    collisions = {
        f"{teacher_id}|{stage}|{slot[0]}|{slot[1]}": rows
        for (teacher_id, stage, slot), rows in occupied.items()
        if len(rows) > 1
    }
    if collisions:
        audit.add(
            "CHOQUE_DE_HORARIO",
            "Um docente recebeu mais de uma transmissão na mesma faixa e etapa.",
            [row for rows in collisions.values() for row in rows],
            {"collisions": collisions},
        )

    capacity_errors: dict[str, dict[str, int]] = {}
    stricto_errors: list[str] = []
    for teacher in problem.teachers:
        load = recomputed_loads[teacher.id]
        capacity = teacher.allocation_capacity(problem.hours_per_transmission)
        stage_values = recomputed_stage_loads[teacher.id]
        exceeded_stages = {
            stage: stage_load
            for stage, stage_load in stage_values.items()
            if stage_load > capacity
        }
        if exceeded_stages:
            capacity_errors[teacher.badge] = {
                "load": max(exceeded_stages.values()),
                "capacity": capacity,
                "stage_loads": stage_values,
                "exceeded_stages": exceeded_stages,
            }
        stricto_limit = (
            problem.hours_per_transmission * STRICTO_MAX_DISCIPLINES_PER_MODULE
        )
        if teacher.is_stricto and load > stricto_limit:
            stricto_errors.append(teacher.badge)
    if capacity_errors:
        audit.add(
            "CAPACIDADE_EXCEDIDA",
            "A carga semanal excede a capacidade em uma ou mais etapas do módulo.",
            details={"teachers": capacity_errors},
        )
    if stricto_errors:
        audit.add(
            "LIMITE_STRICTO_EXCEDIDO",
            (
                "Docente Stricto recebeu mais de "
                f"{STRICTO_MAX_DISCIPLINES_PER_MODULE} disciplinas no módulo."
            ),
            details={
                "badges": stricto_errors,
                "max_disciplines_per_module": STRICTO_MAX_DISCIPLINES_PER_MODULE,
            },
        )

    reported_loads = {teacher.id: result.teacher_loads.get(teacher.id, 0) for teacher in problem.teachers}
    extra_load_ids = sorted(set(result.teacher_loads) - set(teachers))
    if reported_loads != recomputed_loads or extra_load_ids:
        differences = {
            teachers[teacher_id].badge: {
                "reported": reported_loads[teacher_id],
                "recomputed": recomputed_loads[teacher_id],
            }
            for teacher_id in reported_loads
            if reported_loads[teacher_id] != recomputed_loads[teacher_id]
        }
        audit.add(
            "CARGA_REPORTADA_INCONSISTENTE",
            "As cargas do resultado divergem das atribuições.",
            details={"teachers": differences, "unknown_teacher_ids": extra_load_ids},
        )

    reported_stage_loads = {
        teacher.id: {
            stage: result.teacher_stage_loads.get(teacher.id, {}).get(stage, 0)
            for stage in MODULE_STAGES
        }
        for teacher in problem.teachers
    }
    extra_stage_load_ids = sorted(set(result.teacher_stage_loads) - set(teachers))
    invalid_stage_keys = {
        teachers[teacher_id].badge: sorted(
            set(result.teacher_stage_loads.get(teacher_id, {})) - set(MODULE_STAGES)
        )
        for teacher_id in teachers
        if set(result.teacher_stage_loads.get(teacher_id, {})) - set(MODULE_STAGES)
    }
    incomplete_stage_load_ids = [
        teacher.id
        for teacher in problem.teachers
        if set(result.teacher_stage_loads.get(teacher.id, {})) != set(MODULE_STAGES)
    ]
    if (
        reported_stage_loads != recomputed_stage_loads
        or extra_stage_load_ids
        or invalid_stage_keys
        or incomplete_stage_load_ids
    ):
        differences = {
            teachers[teacher_id].badge: {
                "reported": reported_stage_loads[teacher_id],
                "recomputed": recomputed_stage_loads[teacher_id],
            }
            for teacher_id in reported_stage_loads
            if reported_stage_loads[teacher_id]
            != recomputed_stage_loads[teacher_id]
        }
        audit.add(
            "CARGA_ETAPA_REPORTADA_INCONSISTENTE",
            "As cargas por etapa reportadas divergem das atribuições.",
            details={
                "teachers": differences,
                "unknown_teacher_ids": extra_stage_load_ids,
                "invalid_stage_keys": invalid_stage_keys,
                "incomplete_teacher_badges": [
                    teachers[teacher_id].badge
                    for teacher_id in incomplete_stage_load_ids
                ],
            },
        )

    audited_used = sum(load > 0 for load in recomputed_loads.values())
    audited_active = sum(teacher.is_active for teacher in problem.teachers)
    expected_result_status = "COMPLETA" if not unassigned_rows else "PARCIAL"
    audited_capacity_score = sum(
        teachers[item.teacher_id].teaching_capacity
        for item in result.assignments
        if item.teacher_id in teachers
    )
    audited_scarcity_score = sum(
        assignment.teacher_id is None
        and transmissions[assignment.transmission_id].slot is not None
        and len(eligibility[assignment.transmission_id]) == 1
        for assignment in result.assignments
        if assignment.transmission_id in transmissions
    )
    aggregate_mismatch = (
        result.status != expected_result_status
        or result.allocated_count != len(assigned_rows)
        or result.unassigned_count != len(unassigned_rows)
        or result.objective_unassigned != len(unassigned_rows)
        or result.used_teacher_count != audited_used
        or result.zero_active_teacher_count != audited_active - audited_used
        or (
            result.high_capacity_score is not None
            and result.high_capacity_score != audited_capacity_score
        )
        or (
            result.rescue_scarcity_score is not None
            and result.rescue_scarcity_score != audited_scarcity_score
        )
    )
    if aggregate_mismatch:
        audit.add(
            "TOTAIS_INCONSISTENTES",
            "Os totais agregados divergem das atribuições auditadas.",
            details={
                "reported_allocated": result.allocated_count,
                "audited_allocated": len(assigned_rows),
                "reported_unassigned": result.unassigned_count,
                "audited_unassigned": len(unassigned_rows),
                "objective_unassigned": result.objective_unassigned,
                "reported_used_teachers": result.used_teacher_count,
                "audited_used_teachers": audited_used,
                "reported_zero_active_teachers": result.zero_active_teacher_count,
                "audited_zero_active_teachers": audited_active - audited_used,
                "reported_status": result.status,
                "expected_status": expected_result_status,
                "reported_high_capacity_score": result.high_capacity_score,
                "audited_high_capacity_score": audited_capacity_score,
                "reported_scarcity_score": result.rescue_scarcity_score,
                "audited_scarcity_score": audited_scarcity_score,
            },
        )

    # Recompute the business meaning of mandatory scenario policies instead
    # of trusting that the solver honored its own constraints.
    transmissions_by_row = {
        transmission.excel_row: transmission for transmission in problem.transmissions
    }
    teachers_by_badge = {teacher.badge: teacher for teacher in problem.teachers}
    priority_errors: list[int] = []
    fixed_errors: list[int] = []
    for policy in policies:
        policy_type = str(policy.get("policy_type") or "").upper()
        target_type = str(policy.get("target_type") or "").upper()
        target_value = str(policy.get("target_value") or "")
        if policy_type == "PRIORIDADE":
            targets = []
            if target_type == "COURSE":
                targets = [
                    item for item in problem.transmissions if item.course == target_value
                ]
            elif target_type == "OFFER" and target_value.isdigit():
                target = transmissions_by_row.get(int(target_value))
                targets = [target] if target else []
            for target in targets:
                assignment = assignments_by_transmission.get(target.id)
                if assignment is None or assignment.teacher_id is None:
                    priority_errors.append(target.excel_row)
        elif policy_type == "FIXAR" and target_value.isdigit():
            target = transmissions_by_row.get(int(target_value))
            badge = str((policy.get("configuration") or {}).get("teacher_badge") or "")
            teacher = teachers_by_badge.get(badge)
            if target is not None:
                assignment = assignments_by_transmission.get(target.id)
                if (
                    teacher is None
                    or assignment is None
                    or assignment.teacher_id != teacher.id
                ):
                    fixed_errors.append(target.excel_row)
    add_rows(
        "PRIORIDADE_NAO_ATENDIDA",
        "Uma oferta priorizada terminou sem docente alocado.",
        priority_errors,
    )
    add_rows(
        "ALOCACAO_FIXADA_NAO_ATENDIDA",
        "Uma oferta não preservou o docente definido na política.",
        fixed_errors,
    )

    audit.checks = {
        "transmissions": len(problem.transmissions),
        "teachers": len(problem.teachers),
        "allocated": len(assigned_rows),
        "unassigned": len(unassigned_rows),
        "used_teachers": audited_used,
        "schedule_slots_checked": len(occupied),
        "scenario_policies_checked": len(policies),
    }
    return audit
