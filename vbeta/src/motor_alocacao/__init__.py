"""Motor combinatório de alocação docente."""

from .audit import AllocationAudit, AuditIssue, audit_allocation
from .domain import (
    MODULE_STAGE_1,
    MODULE_STAGE_2,
    MODULE_STAGES,
    AllocationResult,
    Problem,
    Teacher,
    Transmission,
    module_stages_for_order,
)
from .eligibility import build_eligibility, is_teacher_eligible
from .grasp import GraspHint, build_grasp_hint
from .loader import load_problem
from .reporting import contract_model_for, create_round_directory, write_results
from .solver import solve_allocation

__all__ = [
    "AllocationResult",
    "MODULE_STAGE_1",
    "MODULE_STAGE_2",
    "MODULE_STAGES",
    "AllocationAudit",
    "AuditIssue",
    "Problem",
    "Teacher",
    "Transmission",
    "GraspHint",
    "build_grasp_hint",
    "load_problem",
    "solve_allocation",
    "contract_model_for",
    "create_round_directory",
    "write_results",
    "audit_allocation",
    "build_eligibility",
    "is_teacher_eligible",
    "module_stages_for_order",
]

