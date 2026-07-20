from __future__ import annotations

from .domain import CONTRACT_UNKNOWN, Problem, Teacher, Transmission


def is_teacher_eligible(
    problem: Problem,
    transmission: Transmission,
    teacher: Teacher,
) -> bool:
    return (
        transmission.slot is not None
        and teacher.is_active
        and teacher.contract_family != CONTRACT_UNKNOWN
        and teacher.allocation_capacity(problem.hours_per_transmission)
        >= problem.hours_per_transmission
        and bool(transmission.profiles.intersection(teacher.profiles))
    )


def build_eligibility(problem: Problem) -> dict[int, list[int]]:
    return {
        transmission.id: [
            teacher.id
            for teacher in problem.teachers
            if is_teacher_eligible(problem, transmission, teacher)
        ]
        for transmission in problem.transmissions
    }
