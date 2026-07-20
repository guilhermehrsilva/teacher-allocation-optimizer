from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time
from pathlib import Path


CONTRACT_EAD_POOL = "EAD_POOL"
CONTRACT_STRICTO = "STRICTO"
CONTRACT_UNKNOWN = "UNKNOWN"
STRICTO_MAX_DISCIPLINES_PER_MODULE = 2
MODULE_STAGE_1 = "PRIMEIRA_ETAPA"
MODULE_STAGE_2 = "SEGUNDA_ETAPA"
MODULE_STAGES = (MODULE_STAGE_1, MODULE_STAGE_2)


def module_stages_for_order(order: str) -> tuple[str, ...]:
    """Retorna as metades do módulo em que a disciplina consome carga."""
    normalized = " ".join(order.strip().upper().split())
    mapping = {
        "1ª": (MODULE_STAGE_1,),
        "2ª": (MODULE_STAGE_2,),
        "ESTENDIDA": MODULE_STAGES,
    }
    try:
        return mapping[normalized]
    except KeyError as exc:
        raise ValueError(
            f"ORDEM não suportada: {order!r}; esperado 1ª, 2ª ou ESTENDIDA."
        ) from exc


@dataclass(frozen=True)
class Teacher:
    id: int
    name: str
    badge: str
    job_function: str
    contracted_capacity: int
    teaching_capacity: int
    manager: str
    status: str
    profiles: frozenset[str]
    profile_text: str

    @property
    def is_active(self) -> bool:
        return self.status.strip().upper() == "ATIVO"

    @property
    def is_stricto(self) -> bool:
        return self.contract_family == CONTRACT_STRICTO

    @property
    def contract_family(self) -> str:
        normalized = " ".join(self.job_function.strip().upper().split())
        if normalized == "PROFESSOR DE ENSINO SUPERIOR PRESENCIAL":
            return CONTRACT_STRICTO
        if normalized in {
            "PROFESSOR DE ENSINO SUPERIOR EAD",
            "PROFESSOR REGENTE",
        }:
            return CONTRACT_EAD_POOL
        return CONTRACT_UNKNOWN

    def allocation_capacity(self, hours_per_transmission: int) -> int:
        """Capacidade usada pelo solver sem alterar as cargas originais da base."""
        if self.is_stricto:
            return hours_per_transmission * STRICTO_MAX_DISCIPLINES_PER_MODULE
        return self.teaching_capacity


@dataclass(frozen=True)
class Transmission:
    id: int
    excel_row: int
    course: str
    course_name: str
    curriculum: str
    discipline_code: str
    discipline_name: str
    profiles: frozenset[str]
    profile_text: str
    synergy: str
    day: str
    start_time: time | None
    order: str
    cluster: str
    coordinator: str

    @property
    def slot(self) -> tuple[str, str] | None:
        if not self.day or self.day == "NSA" or self.start_time is None:
            return None
        return self.day, self.start_time.strftime("%H:%M")

    @property
    def module_stages(self) -> tuple[str, ...]:
        return module_stages_for_order(self.order)

@dataclass(frozen=True)
class Problem:
    source: Path
    teachers: tuple[Teacher, ...]
    transmissions: tuple[Transmission, ...]
    hours_per_transmission: int = 2


@dataclass(frozen=True)
class Assignment:
    transmission_id: int
    teacher_id: int | None
    status: str
    reason: str
    eligible_teacher_count: int
    allocation_reason: str = ""


@dataclass
class AllocationResult:
    status: str
    solver_status: str
    assignments: list[Assignment]
    teacher_loads: dict[int, int]
    objective_unassigned: int
    used_teacher_count: int
    zero_active_teacher_count: int
    high_capacity_score: int | None
    rescue_scarcity_score: int | None
    wall_time_seconds: float
    diagnostics: dict[str, object] = field(default_factory=dict)
    teacher_stage_loads: dict[int, dict[str, int]] = field(default_factory=dict)

    @property
    def allocated_count(self) -> int:
        return sum(item.teacher_id is not None for item in self.assignments)

    @property
    def unassigned_count(self) -> int:
        return len(self.assignments) - self.allocated_count
