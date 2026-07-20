from __future__ import annotations

from collections import defaultdict
from time import perf_counter

from ortools.sat.python import cp_model

from .domain import (
    MODULE_STAGES,
    STRICTO_MAX_DISCIPLINES_PER_MODULE,
    AllocationResult,
    Assignment,
    Problem,
)
from .eligibility import build_eligibility
from .grasp import build_grasp_hint
from .policies import cluster_policy_eligibility, scenario_policies


def _status_name(status: cp_model.CpSolverStatus) -> str:
    names = {
        cp_model.OPTIMAL: "OPTIMAL",
        cp_model.FEASIBLE: "FEASIBLE",
        cp_model.INFEASIBLE: "INFEASIBLE",
        cp_model.MODEL_INVALID: "MODEL_INVALID",
        cp_model.UNKNOWN: "UNKNOWN",
    }
    return names.get(status, str(status))


def _new_solver(
    max_time_seconds: float | None,
    phase_fraction: float,
    workers: int,
    random_seed: int,
) -> cp_model.CpSolver:
    solver = cp_model.CpSolver()
    if max_time_seconds is not None and max_time_seconds > 0:
        solver.parameters.max_time_in_seconds = max_time_seconds * phase_fraction
    solver.parameters.num_search_workers = workers
    solver.parameters.random_seed = random_seed
    return solver


def _replace_hints(
    model: cp_model.CpModel,
    solver: cp_model.CpSolver,
    variables: tuple[cp_model.IntVar, ...],
) -> None:
    """Usa a melhor solução da fase anterior como warm start da próxima."""
    model.clear_hints()
    for variable in variables:
        model.add_hint(variable, solver.value(variable))


def _assignment_snapshot(
    problem: Problem,
    eligible: dict[int, list[int]],
    assignment_vars: dict[tuple[int, int], cp_model.IntVar],
    solver: cp_model.CpSolver,
) -> dict[int, int | None]:
    return {
        transmission.id: next(
            (
                teacher_id
                for teacher_id in eligible[transmission.id]
                if solver.value(assignment_vars[(transmission.id, teacher_id)])
            ),
            None,
        )
        for transmission in problem.transmissions
    }


def _allocation_reason(
    problem: Problem,
    transmission_id: int,
    teacher_id: int,
    eligible: dict[int, list[int]],
) -> str:
    teacher = problem.teachers[teacher_id]
    candidates = eligible[transmission_id]
    if len(candidates) == 1:
        return "Único docente elegível por perfil, carga e horário"
    if teacher.is_stricto:
        return (
            "Docente Stricto elegível, respeitando o limite de "
            f"{STRICTO_MAX_DISCIPLINES_PER_MODULE} disciplinas no módulo"
        )
    capacities = {
        candidate: problem.teachers[candidate].teaching_capacity
        for candidate in candidates
    }
    if capacities[teacher_id] == max(capacities.values()) and len(set(capacities.values())) > 1:
        return "Docente elegível priorizado pela maior CH letiva"
    # A contagem permanece em CANDIDATOS_ELEGÍVEIS; manter o texto estável
    # evita fragmentar indicadores e integrações por quantidade de candidatos.
    return "Docente elegível selecionado entre alternativas igualmente ótimas"


def solve_allocation(
    problem: Problem,
    max_time_seconds: float | None = None,
    workers: int = 8,
    random_seed: int = 42,
    grasp_iterations: int = 0,
    grasp_alpha: float = 0.25,
    scenario_policy: dict | None = None,
) -> AllocationResult:
    """Resolve a alocação base e três fases SWITCH lexicográficas.

    1. Minimiza transmissões não alocadas.
    2. SWITCH de cobertura: maximiza docentes ativos com alguma alocação.
    3. SWITCH de ocupação: preserva os ótimos anteriores e favorece maior CH.
    4. SWITCH de resgate: protege transmissões com candidato único.
    5. Canonicaliza a solução ótima em busca determinística de um worker.
    """
    optimization_started = perf_counter()
    if grasp_iterations < 0:
        raise ValueError("O número de iterações GRASP não pode ser negativo.")
    model = cp_model.CpModel()
    base_eligibility = build_eligibility(problem)
    assignment_vars: dict[tuple[int, int], cp_model.IntVar] = {}
    unassigned_vars: dict[int, cp_model.IntVar] = {}
    transmission_by_id = {item.id: item for item in problem.transmissions}
    transmission_by_row = {item.excel_row: item for item in problem.transmissions}
    teacher_by_badge = {item.badge: item for item in problem.teachers}
    policies = scenario_policies(scenario_policy)
    eligible, cluster_override_pairs, cluster_targets = cluster_policy_eligibility(
        problem,
        base_eligibility,
        policies,
    )

    for transmission in problem.transmissions:
        unassigned = model.new_bool_var(f"unassigned_t{transmission.id}")
        unassigned_vars[transmission.id] = unassigned
        options = []
        for teacher_id in eligible[transmission.id]:
            variable = model.new_bool_var(f"assign_t{transmission.id}_p{teacher_id}")
            assignment_vars[(transmission.id, teacher_id)] = variable
            options.append(variable)
        model.add_exactly_one(options + [unassigned])

    # Restrições exclusivas do motor de cenários. Elas são aplicadas antes dos
    # objetivos lexicográficos e nunca existem no solver principal de vbeta.
    for policy in policies:
        policy_type = str(policy.get("policy_type") or "").upper()
        target_type = str(policy.get("target_type") or "").upper()
        target_value = str(policy.get("target_value") or "")
        if policy_type == "PRIORIDADE":
            targets = []
            if target_type == "COURSE":
                targets = [item for item in problem.transmissions if item.course == target_value]
            elif target_type == "OFFER" and target_value.isdigit():
                target = transmission_by_row.get(int(target_value))
                targets = [target] if target else []
            if not targets:
                raise ValueError(f"Política de prioridade sem oferta válida: {target_value}")
            for target in targets:
                model.add(unassigned_vars[target.id] == 0)
        elif policy_type == "FIXAR":
            if target_type != "OFFER" or not target_value.isdigit():
                raise ValueError("Política de fixação sem oferta válida.")
            target = transmission_by_row.get(int(target_value))
            badge = str((policy.get("configuration") or {}).get("teacher_badge") or "")
            teacher = teacher_by_badge.get(badge)
            if not target or not teacher or (target.id, teacher.id) not in assignment_vars:
                raise ValueError(
                    f"A alocação fixada da linha {target_value} para a chapa {badge} não é elegível."
                )
            model.add(assignment_vars[(target.id, teacher.id)] == 1)

    load_vars: dict[int, cp_model.IntVar] = {}
    stage_load_vars: dict[tuple[int, str], cp_model.IntVar] = {}
    used_vars: dict[int, cp_model.IntVar] = {}
    for teacher in problem.teachers:
        allocation_capacity = teacher.allocation_capacity(problem.hours_per_transmission)
        teacher_variables = {
            transmission_id: variable
            for (transmission_id, teacher_id), variable in assignment_vars.items()
            if teacher_id == teacher.id
        }
        max_total_load = problem.hours_per_transmission * len(teacher_variables)
        load = model.new_int_var(0, max_total_load, f"load_p{teacher.id}")
        load_vars[teacher.id] = load
        model.add(
            load
            == problem.hours_per_transmission * sum(teacher_variables.values())
        )
        for stage in MODULE_STAGES:
            stage_variables = [
                variable
                for transmission_id, variable in teacher_variables.items()
                if stage in transmission_by_id[transmission_id].module_stages
            ]
            stage_load = model.new_int_var(
                0,
                max(0, allocation_capacity),
                f"load_{stage.lower()}_p{teacher.id}",
            )
            stage_load_vars[(teacher.id, stage)] = stage_load
            model.add(
                stage_load
                == problem.hours_per_transmission * sum(stage_variables)
            )
            model.add(stage_load <= allocation_capacity)
        # A exceção Stricto continua limitada a duas disciplinas distintas no
        # módulo, ainda que elas ocorram em metades diferentes.
        if teacher.is_stricto:
            model.add(load <= allocation_capacity)
        used = model.new_bool_var(f"used_p{teacher.id}")
        used_vars[teacher.id] = used
        if teacher.is_active and teacher_variables:
            model.add(load >= problem.hours_per_transmission * used)
            model.add(load <= max_total_load * used)
        else:
            model.add(used == 0)

    by_teacher_stage_slot: dict[
        tuple[int, str, tuple[str, str]], list[cp_model.IntVar]
    ] = defaultdict(list)
    for (transmission_id, teacher_id), variable in assignment_vars.items():
        transmission = transmission_by_id[transmission_id]
        slot = transmission.slot
        if slot is not None:
            for stage in transmission.module_stages:
                by_teacher_stage_slot[(teacher_id, stage, slot)].append(variable)
    for variables in by_teacher_stage_slot.values():
        if len(variables) > 1:
            model.add_at_most_one(variables)

    grasp_hint = None
    grasp_wall_time = 0.0
    if grasp_iterations:
        grasp_started = perf_counter()
        grasp_hint = build_grasp_hint(
            problem,
            eligible,
            iterations=grasp_iterations,
            alpha=grasp_alpha,
            random_seed=random_seed,
        )
        grasp_wall_time = perf_counter() - grasp_started
        for (transmission_id, teacher_id), variable in assignment_vars.items():
            model.add_hint(variable, int(grasp_hint.assignments[transmission_id] == teacher_id))
        for transmission_id, variable in unassigned_vars.items():
            model.add_hint(variable, int(grasp_hint.assignments[transmission_id] is None))
        hint_loads = {teacher.id: 0 for teacher in problem.teachers}
        hint_stage_loads = {
            teacher.id: {stage: 0 for stage in MODULE_STAGES}
            for teacher in problem.teachers
        }
        for transmission_id, teacher_id in grasp_hint.assignments.items():
            if teacher_id is not None:
                hint_loads[teacher_id] += problem.hours_per_transmission
                for stage in transmission_by_id[transmission_id].module_stages:
                    hint_stage_loads[teacher_id][stage] += problem.hours_per_transmission
        for teacher_id, variable in load_vars.items():
            model.add_hint(variable, hint_loads[teacher_id])
            model.add_hint(used_vars[teacher_id], int(hint_loads[teacher_id] > 0))
            for stage in MODULE_STAGES:
                model.add_hint(
                    stage_load_vars[(teacher_id, stage)],
                    hint_stage_loads[teacher_id][stage],
                )

    all_variables = tuple(assignment_vars.values()) + tuple(unassigned_vars.values()) + (
        tuple(load_vars.values())
        + tuple(stage_load_vars.values())
        + tuple(used_vars.values())
    )

    total_unassigned = sum(unassigned_vars.values())
    model.minimize(total_unassigned)
    first_solver = _new_solver(max_time_seconds, 0.30, workers, random_seed)
    first_status = first_solver.solve(model)
    if first_status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return AllocationResult(
            status="SEM_SOLUCAO",
            solver_status=_status_name(first_status),
            assignments=[],
            teacher_loads={},
            objective_unassigned=len(problem.transmissions),
            used_teacher_count=0,
            zero_active_teacher_count=sum(teacher.is_active for teacher in problem.teachers),
            high_capacity_score=None,
            rescue_scarcity_score=None,
            wall_time_seconds=perf_counter() - optimization_started,
            diagnostics={
                "message": "O CP-SAT não encontrou solução utilizável.",
                "grasp_wall_time_seconds": grasp_wall_time,
                "cp_sat_wall_time_seconds": first_solver.wall_time,
                "stricto_max_disciplines_per_module": (
                    STRICTO_MAX_DISCIPLINES_PER_MODULE
                ),
            },
        )

    best_unassigned = int(round(first_solver.objective_value))
    model.add(total_unassigned == best_unassigned)
    _replace_hints(model, first_solver, all_variables)
    total_used = sum(used_vars.values())
    model.maximize(total_used)

    second_solver = _new_solver(max_time_seconds, 0.25, workers, random_seed)
    second_status = second_solver.solve(model)
    if second_status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        best_used = int(round(second_solver.objective_value))
    else:
        best_used = sum(int(first_solver.value(variable)) for variable in used_vars.values())
    second_incumbent = (
        second_solver
        if second_status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
        else first_solver
    )
    model.add(total_used == best_used)
    _replace_hints(model, second_incumbent, all_variables)

    # Entre soluções com a mesma cobertura, cada atribuição a um docente com
    # maior CH_LETIVA recebe peso maior. Isso reduz a ociosidade dos contratos
    # com maior capacidade sem retirar docentes já cobertos pelo SWITCH anterior.
    high_capacity_score = sum(
        problem.teachers[teacher_id].teaching_capacity * variable
        for (_, teacher_id), variable in assignment_vars.items()
    )
    model.maximize(high_capacity_score)
    third_solver = _new_solver(max_time_seconds, 0.20, workers, random_seed + 1)
    third_status = third_solver.solve(model)

    if third_status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        best_capacity_score = int(round(third_solver.objective_value))
    elif second_status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        best_capacity_score = int(second_solver.value(high_capacity_score))
    else:
        best_capacity_score = int(first_solver.value(high_capacity_score))
    third_incumbent = (
        third_solver
        if third_status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
        else second_incumbent
    )
    model.add(high_capacity_score == best_capacity_score)
    _replace_hints(model, third_incumbent, all_variables)

    # Protege apenas disciplinas com um único docente elegível. A cobertura total,
    # docentes utilizados e score de CH já estão fixados; disciplinas com dois ou
    # mais candidatos não recebem prioridade apenas por sua contagem de candidatos.
    scarcity_penalty = sum(
        unassigned_vars[transmission.id]
        for transmission in problem.transmissions
        if transmission.slot is not None and len(eligible[transmission.id]) == 1
    )
    model.minimize(scarcity_penalty)
    fourth_solver = _new_solver(max_time_seconds, 0.15, workers, random_seed + 2)
    fourth_status = fourth_solver.solve(model)

    if fourth_status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        fourth_incumbent = fourth_solver
        fourth_incumbent_status = fourth_status
        best_scarcity_score = int(round(fourth_solver.objective_value))
    elif third_status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        fourth_incumbent = third_solver
        fourth_incumbent_status = third_status
        best_scarcity_score = int(third_solver.value(scarcity_penalty))
    elif second_status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        fourth_incumbent = second_solver
        fourth_incumbent_status = second_status
        best_scarcity_score = int(second_solver.value(scarcity_penalty))
    else:
        fourth_incumbent = first_solver
        fourth_incumbent_status = first_status
        best_scarcity_score = int(first_solver.value(scarcity_penalty))

    # Os quatro objetivos de negócio já estão fixados. Removemos objetivo e
    # hints paralelos e buscamos uma solução canônica com um único worker. Isso
    # mantém o ganho do paralelismo na prova dos ótimos e evita que empates
    # produzam planilhas diferentes em execuções idênticas.
    model.add(scarcity_penalty == best_scarcity_score)
    model.clear_objective()
    model.clear_hints()
    canonical_solver = _new_solver(max_time_seconds, 0.10, 1, random_seed)
    canonical_status = canonical_solver.solve(model)
    if canonical_status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        solver, final_status = canonical_solver, canonical_status
    else:
        solver, final_status = fourth_incumbent, fourth_incumbent_status

    phase_statuses = [first_status, second_status, third_status, fourth_status]
    overall_solver_status = (
        "OPTIMAL"
        if all(status == cp_model.OPTIMAL for status in phase_statuses)
        else "FEASIBLE"
    )

    loads = {
        teacher.id: int(solver.value(load_vars[teacher.id]))
        for teacher in problem.teachers
    }
    stage_loads = {
        teacher.id: {
            stage: int(solver.value(stage_load_vars[(teacher.id, stage)]))
            for stage in MODULE_STAGES
        }
        for teacher in problem.teachers
    }
    assigned_teacher = _assignment_snapshot(problem, eligible, assignment_vars, solver)
    occupied_stage_slots = {
        (teacher_id, stage, transmission_by_id[transmission_id].slot)
        for transmission_id, teacher_id in assigned_teacher.items()
        if teacher_id is not None
        for stage in transmission_by_id[transmission_id].module_stages
    }

    assignments: list[Assignment] = []
    for transmission in problem.transmissions:
        teacher_id = assigned_teacher[transmission.id]
        if teacher_id is not None:
            status, reason = "ALOCADA", ""
            if (transmission.id, teacher_id) in cluster_override_pairs:
                allocation_reason = (
                    f"Docente do cluster {transmission.cluster} alocado por decisão de cenário; "
                    "perfil exato flexibilizado"
                )
            else:
                allocation_reason = _allocation_reason(
                    problem,
                    transmission.id,
                    teacher_id,
                    eligible,
                )
        elif transmission.slot is None:
            status, reason = "NAO_ALOCADA", "AGENDA_INVALIDA"
            allocation_reason = ""
        elif not eligible[transmission.id]:
            status, reason = "NAO_ALOCADA", "SEM_DOCENTE_COM_PERFIL_E_CARGA"
            allocation_reason = ""
        else:
            capacity_available = {
                candidate
                for candidate in eligible[transmission.id]
                if all(
                    stage_loads[candidate][stage]
                    + problem.hours_per_transmission
                    <= problem.teachers[candidate].allocation_capacity(
                        problem.hours_per_transmission
                    )
                    for stage in transmission.module_stages
                )
                and (
                    not problem.teachers[candidate].is_stricto
                    or loads[candidate] + problem.hours_per_transmission
                    <= problem.teachers[candidate].allocation_capacity(
                        problem.hours_per_transmission
                    )
                )
            }
            schedule_available = {
                candidate
                for candidate in eligible[transmission.id]
                if all(
                    (candidate, stage, transmission.slot)
                    not in occupied_stage_slots
                    for stage in transmission.module_stages
                )
            }
            if not capacity_available and not schedule_available:
                reason = "CAPACIDADE_E_HORARIO_COMBINADOS"
            elif not capacity_available:
                reason = "CAPACIDADE_LETIVA_ESGOTADA"
            elif not schedule_available:
                reason = "CHOQUE_DE_HORARIO"
            else:
                reason = "CAPACIDADE_E_HORARIO_COMBINADOS"
            status = "NAO_ALOCADA"
            allocation_reason = ""
        assignments.append(
            Assignment(
                transmission_id=transmission.id,
                teacher_id=teacher_id,
                status=status,
                reason=reason,
                eligible_teacher_count=len(eligible[transmission.id]),
                allocation_reason=allocation_reason,
            )
        )

    used_count = sum(load > 0 for load in loads.values())
    active_count = sum(teacher.is_active for teacher in problem.teachers)
    capacity_score = int(solver.value(high_capacity_score))
    rescue_score = int(solver.value(scarcity_penalty))
    return AllocationResult(
        status="COMPLETA" if best_unassigned == 0 else "PARCIAL",
        solver_status=overall_solver_status,
        assignments=assignments,
        teacher_loads=loads,
        objective_unassigned=best_unassigned,
        used_teacher_count=used_count,
        zero_active_teacher_count=active_count - used_count,
        high_capacity_score=capacity_score,
        rescue_scarcity_score=rescue_score,
        wall_time_seconds=perf_counter() - optimization_started,
        teacher_stage_loads=stage_loads,
        diagnostics={
            "cp_sat_wall_time_seconds": (
                first_solver.wall_time
                + second_solver.wall_time
                + third_solver.wall_time
                + fourth_solver.wall_time
                + canonical_solver.wall_time
            ),
            "grasp_wall_time_seconds": grasp_wall_time,
            "phase_1_status": _status_name(first_status),
            "switch_1_teacher_coverage_status": _status_name(second_status),
            "scenario_policy_count": len(policies),
            "scenario_cluster_targets": sorted(cluster_targets),
            "scenario_cluster_override_candidates": len(cluster_override_pairs),
            "scenario_cluster_eligibility": {
                str(transmission.id): eligible[transmission.id]
                for transmission in problem.transmissions
                if transmission.cluster in cluster_targets
            },
            "scenario_cluster_override_pairs": [
                [transmission_id, teacher_id]
                for transmission_id, teacher_id in sorted(cluster_override_pairs)
            ],
            "scenario_cluster_override_assignments": sum(
                (item.transmission_id, item.teacher_id) in cluster_override_pairs
                for item in assignments if item.teacher_id is not None
            ),
            "switch_2_high_capacity_status": _status_name(third_status),
            "switch_3_scarcity_rescue_status": _status_name(fourth_status),
            "canonicalization_status": _status_name(canonical_status),
            "canonicalization_workers": 1,
            "selected_solution_phase_status": _status_name(final_status),
            "all_lexicographic_phases_optimal": overall_solver_status == "OPTIMAL",
            "best_used_teachers": best_used,
            "best_high_capacity_score": best_capacity_score,
            "scarcity_rescue_penalty": rescue_score,
            "unique_candidate_unassigned": rescue_score,
            "grasp_iterations": grasp_hint.iterations if grasp_hint else 0,
            "grasp_alpha": grasp_alpha,
            "grasp_hint_unassigned": grasp_hint.score[0] if grasp_hint else None,
            "grasp_hint_zero_active_teachers": grasp_hint.score[1] if grasp_hint else None,
            "grasp_hint_high_capacity_score": -grasp_hint.score[2] if grasp_hint else None,
            "grasp_hint_scarcity_penalty": grasp_hint.score[3] if grasp_hint else None,
            "cp_sat_time_limit_seconds": max_time_seconds,
            "stricto_max_disciplines_per_module": (
                STRICTO_MAX_DISCIPLINES_PER_MODULE
            ),
            "capacity_model": "WEEKLY_BY_MODULE_STAGE",
            "module_stage_order_mapping": {
                "1ª": [MODULE_STAGES[0]],
                "2ª": [MODULE_STAGES[1]],
                "ESTENDIDA": list(MODULE_STAGES),
            },
            "assignment_variables": len(assignment_vars),
            "teacher_slot_constraints": sum(
                len(items) > 1 for items in by_teacher_stage_slot.values()
            ),
            "teacher_stage_slot_constraints": sum(
                len(items) > 1 for items in by_teacher_stage_slot.values()
            ),
            "teacher_stage_capacity_constraints": len(stage_load_vars),
        },
    )
