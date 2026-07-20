from __future__ import annotations

import math
import random
from dataclasses import dataclass

from .domain import MODULE_STAGES, Problem, Transmission


@dataclass(frozen=True)
class GraspHint:
    assignments: dict[int, int | None]
    score: tuple[int, int, int, int]
    iterations: int


def _state(
    problem: Problem, assignments: dict[int, int | None]
) -> tuple[
    dict[tuple[int, str], int],
    dict[int, int],
    set[tuple[int, str, tuple[str, str]]],
]:
    transmissions = {item.id: item for item in problem.transmissions}
    stage_loads = {
        (teacher.id, stage): 0
        for teacher in problem.teachers
        for stage in MODULE_STAGES
    }
    assignment_counts = {teacher.id: 0 for teacher in problem.teachers}
    occupied: set[tuple[int, str, tuple[str, str]]] = set()
    for transmission_id, teacher_id in assignments.items():
        if teacher_id is None:
            continue
        transmission = transmissions[transmission_id]
        assignment_counts[teacher_id] += 1
        slot = transmission.slot
        for stage in transmission.module_stages:
            stage_loads[(teacher_id, stage)] += problem.hours_per_transmission
            if slot is not None:
                occupied.add((teacher_id, stage, slot))
    return stage_loads, assignment_counts, occupied


def _can_assign_with_state(
    problem: Problem,
    transmissions: dict[int, Transmission],
    stage_loads: dict[tuple[int, str], int],
    assignment_counts: dict[int, int],
    occupied: set[tuple[int, str, tuple[str, str]]],
    transmission_id: int,
    teacher_id: int,
) -> bool:
    transmission = transmissions[transmission_id]
    teacher = problem.teachers[teacher_id]
    capacity = teacher.allocation_capacity(problem.hours_per_transmission)
    return (
        transmission.slot is not None
        and all(
            stage_loads[(teacher_id, stage)] + problem.hours_per_transmission
            <= capacity
            for stage in transmission.module_stages
        )
        and (not teacher.is_stricto or assignment_counts[teacher_id] < 2)
        and all(
            (teacher_id, stage, transmission.slot) not in occupied
            for stage in transmission.module_stages
        )
    )


def _construct(
    problem: Problem,
    eligible: dict[int, list[int]],
    alpha: float,
    rng: random.Random,
) -> dict[int, int | None]:
    transmissions = {item.id: item for item in problem.transmissions}
    teachers = {item.id: item for item in problem.teachers}
    assignments = {item.id: None for item in problem.transmissions}
    stage_loads = {
        (teacher.id, stage): 0
        for teacher in problem.teachers
        for stage in MODULE_STAGES
    }
    assignment_counts = {teacher.id: 0 for teacher in problem.teachers}
    occupied: set[tuple[int, str, tuple[str, str]]] = set()
    remaining = {
        item.id
        for item in problem.transmissions
        if item.slot is not None and eligible[item.id]
    }

    while remaining:
        feasible: dict[int, list[int]] = {}
        for transmission_id in remaining:
            transmission = transmissions[transmission_id]
            options = [
                teacher_id
                for teacher_id in eligible[transmission_id]
                if _can_assign_with_state(
                    problem,
                    transmissions,
                    stage_loads,
                    assignment_counts,
                    occupied,
                    transmission_id,
                    teacher_id,
                )
            ]
            if options:
                feasible[transmission_id] = options
        if not feasible:
            break

        counts = [len(options) for options in feasible.values()]
        minimum, maximum = min(counts), max(counts)
        threshold = minimum + alpha * (maximum - minimum)
        task_rcl = [
            transmission_id
            for transmission_id, options in feasible.items()
            if len(options) <= threshold
        ]
        transmission_id = rng.choice(task_rcl)

        def candidate_score(teacher_id: int) -> tuple[int, int, int]:
            # Primeiro abre espaço para docentes ainda ociosos; depois favorece
            # maior CH e, por fim, a menor ocupação semanal de pico.
            return (
                0 if assignment_counts[teacher_id] == 0 else 1,
                -teachers[teacher_id].teaching_capacity,
                max(
                    stage_loads[(teacher_id, stage)]
                    for stage in MODULE_STAGES
                ),
            )

        ranked = sorted(feasible[transmission_id], key=candidate_score)
        rcl_size = max(1, math.ceil(len(ranked) * max(alpha, 0.05)))
        teacher_id = rng.choice(ranked[:rcl_size])
        assignments[transmission_id] = teacher_id
        assignment_counts[teacher_id] += 1
        for stage in transmissions[transmission_id].module_stages:
            stage_loads[(teacher_id, stage)] += problem.hours_per_transmission
            occupied.add(
                (teacher_id, stage, transmissions[transmission_id].slot)
            )
        remaining.remove(transmission_id)
    return assignments


def _local_search(
    problem: Problem,
    eligible: dict[int, list[int]],
    assignments: dict[int, int | None],
    rng: random.Random,
) -> dict[int, int | None]:
    """Tenta inserções diretas e movimentos 1-for-1 até estabilizar."""
    transmissions = {item.id: item for item in problem.transmissions}
    stage_loads, assignment_counts, occupied = _state(problem, assignments)
    teacher_tasks = {teacher.id: set() for teacher in problem.teachers}
    for transmission_id, teacher_id in assignments.items():
        if teacher_id is not None:
            teacher_tasks[teacher_id].add(transmission_id)

    def assign(transmission_id: int, teacher_id: int) -> None:
        assignments[transmission_id] = teacher_id
        assignment_counts[teacher_id] += 1
        teacher_tasks[teacher_id].add(transmission_id)
        transmission = transmissions[transmission_id]
        slot = transmission.slot
        for stage in transmission.module_stages:
            stage_loads[(teacher_id, stage)] += problem.hours_per_transmission
            if slot is not None:
                occupied.add((teacher_id, stage, slot))

    def unassign(transmission_id: int, teacher_id: int) -> None:
        assignments[transmission_id] = None
        assignment_counts[teacher_id] -= 1
        teacher_tasks[teacher_id].remove(transmission_id)
        transmission = transmissions[transmission_id]
        slot = transmission.slot
        for stage in transmission.module_stages:
            stage_loads[(teacher_id, stage)] -= problem.hours_per_transmission
            if slot is not None:
                occupied.remove((teacher_id, stage, slot))

    improved = True
    while improved:
        improved = False
        pending = [
            item.id
            for item in problem.transmissions
            if assignments[item.id] is None and item.slot is not None and eligible[item.id]
        ]
        rng.shuffle(pending)
        for target_id in pending:
            candidates = list(eligible[target_id])
            rng.shuffle(candidates)
            direct = next(
                (
                    teacher_id
                    for teacher_id in candidates
                    if _can_assign_with_state(
                        problem,
                        transmissions,
                        stage_loads,
                        assignment_counts,
                        occupied,
                        target_id,
                        teacher_id,
                    )
                ),
                None,
            )
            if direct is not None:
                assign(target_id, direct)
                improved = True
                continue

            for teacher_id in candidates:
                current_tasks = list(teacher_tasks[teacher_id])
                rng.shuffle(current_tasks)
                moved = False
                for blocker_id in current_tasks:
                    unassign(blocker_id, teacher_id)
                    if not _can_assign_with_state(
                        problem,
                        transmissions,
                        stage_loads,
                        assignment_counts,
                        occupied,
                        target_id,
                        teacher_id,
                    ):
                        assign(blocker_id, teacher_id)
                        continue
                    alternatives = [
                        other
                        for other in eligible[blocker_id]
                        if other != teacher_id
                        and _can_assign_with_state(
                            problem,
                            transmissions,
                            stage_loads,
                            assignment_counts,
                            occupied,
                            blocker_id,
                            other,
                        )
                    ]
                    if alternatives:
                        assign(blocker_id, rng.choice(alternatives))
                        assign(target_id, teacher_id)
                        improved = moved = True
                        break
                    assign(blocker_id, teacher_id)
                if moved:
                    break
    return assignments


def _score(
    problem: Problem,
    eligible: dict[int, list[int]],
    assignments: dict[int, int | None],
) -> tuple[int, int, int, int]:
    teachers = {item.id: item for item in problem.teachers}
    unassigned = sum(value is None for value in assignments.values())
    used = {value for value in assignments.values() if value is not None}
    active_count = sum(teacher.is_active for teacher in problem.teachers)
    high_capacity = sum(teachers[value].teaching_capacity for value in assignments.values() if value is not None)
    scarcity = sum(
        1
        for transmission_id, teacher_id in assignments.items()
        if teacher_id is None and len(eligible[transmission_id]) == 1
    )
    return unassigned, active_count - len(used), -high_capacity, scarcity


def build_grasp_hint(
    problem: Problem,
    eligible: dict[int, list[int]],
    iterations: int = 200,
    alpha: float = 0.25,
    random_seed: int = 42,
) -> GraspHint:
    if iterations < 1:
        raise ValueError("GRASP requer ao menos uma iteração.")
    if not 0 <= alpha <= 1:
        raise ValueError("alpha do GRASP deve estar entre 0 e 1.")
    rng = random.Random(random_seed)
    best_assignments: dict[int, int | None] | None = None
    best_score: tuple[int, int, int, int] | None = None
    for _ in range(iterations):
        assignments = _construct(problem, eligible, alpha, rng)
        assignments = _local_search(problem, eligible, assignments, rng)
        score = _score(problem, eligible, assignments)
        if best_score is None or score < best_score:
            best_score = score
            best_assignments = assignments.copy()
    assert best_assignments is not None and best_score is not None
    return GraspHint(best_assignments, best_score, iterations)

