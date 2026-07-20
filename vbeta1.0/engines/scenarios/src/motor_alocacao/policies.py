from __future__ import annotations

from collections import defaultdict
from typing import Any

from .domain import CONTRACT_UNKNOWN, Problem


SUPPORTED_SCENARIO_POLICIES = {"ALOCAR_CLUSTER", "PRIORIDADE", "FIXAR"}


def scenario_policies(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    raw = (payload or {}).get("policies", [])
    if not isinstance(raw, list):
        raise ValueError("O snapshot de políticas do cenário é inválido.")
    policies: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("O snapshot de políticas do cenário é inválido.")
        policy_type = str(item.get("policy_type") or "").upper()
        if policy_type not in SUPPORTED_SCENARIO_POLICIES:
            raise ValueError(f"Política de cenário não suportada: {policy_type or 'vazia'}.")
        policies.append(item)
    return policies


def cluster_policy_eligibility(
    problem: Problem,
    base_eligibility: dict[int, list[int]],
    policies: list[dict[str, Any]],
) -> tuple[dict[int, list[int]], set[tuple[int, int]], set[str]]:
    """Recompute the controlled cluster exception from the audited policy.

    Profile relaxation is restricted to rows that were explicitly recorded as
    unassigned in the primary baseline snapshot.
    """
    eligibility = {key: list(values) for key, values in base_eligibility.items()}
    rows_by_cluster: dict[str, set[int]] = defaultdict(set)
    for policy in policies:
        if str(policy.get("policy_type") or "").upper() != "ALOCAR_CLUSTER":
            continue
        if str(policy.get("target_type") or "").upper() != "CLUSTER":
            raise ValueError("Política de cluster sem alvo CLUSTER válido.")
        cluster = str(policy.get("target_value") or "").strip()
        raw_rows = (policy.get("configuration") or {}).get(
            "baseline_unassigned_rows"
        )
        if not cluster or not isinstance(raw_rows, list) or not raw_rows:
            raise ValueError(
                "Política de cluster sem lacunas auditadas da baseline."
            )
        for value in raw_rows:
            if isinstance(value, bool):
                raise ValueError("Linha inválida na política de cluster.")
            try:
                row_number = int(value)
            except (TypeError, ValueError) as exc:
                raise ValueError("Linha inválida na política de cluster.") from exc
            rows_by_cluster[cluster].add(row_number)

    transmissions_by_row = {item.excel_row: item for item in problem.transmissions}
    for cluster, rows in rows_by_cluster.items():
        invalid = sorted(
            row
            for row in rows
            if row not in transmissions_by_row
            or transmissions_by_row[row].cluster != cluster
        )
        if invalid:
            raise ValueError(
                f"A política do cluster {cluster} referencia linhas inválidas: {invalid}."
            )

    cluster_profiles: dict[str, set[str]] = defaultdict(set)
    for transmission in problem.transmissions:
        cluster_profiles[transmission.cluster].update(transmission.profiles)

    override_pairs: set[tuple[int, int]] = set()
    for cluster, rows in rows_by_cluster.items():
        profiles_in_cluster = cluster_profiles[cluster]
        for row_number in rows:
            transmission = transmissions_by_row[row_number]
            if transmission.slot is None:
                continue
            for teacher in problem.teachers:
                if (
                    teacher.id not in eligibility[transmission.id]
                    and teacher.is_active
                    and teacher.contract_family != CONTRACT_UNKNOWN
                    and teacher.allocation_capacity(problem.hours_per_transmission)
                    >= problem.hours_per_transmission
                    and bool(teacher.profiles.intersection(profiles_in_cluster))
                ):
                    eligibility[transmission.id].append(teacher.id)
                    override_pairs.add((transmission.id, teacher.id))
            eligibility[transmission.id].sort()
    return eligibility, override_pairs, set(rows_by_cluster)
