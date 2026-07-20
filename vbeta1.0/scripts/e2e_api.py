from __future__ import annotations

import argparse
import hashlib
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx


TERMINAL_STATES = {
    "CONCLUIDA",
    "INTERROMPIDA",
    "VALIDACAO_REPROVADA",
    "FALHA_VALIDACAO",
    "FALHA_SOLVER",
    "FALHA_AUDITORIA",
    "OTIMO_NAO_COMPROVADO",
    "ERRO_INTERNO",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class E2EFailure(RuntimeError):
    pass


class Api:
    def __init__(self, base_url: str, timeout_seconds: float) -> None:
        self.client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=httpx.Timeout(timeout_seconds, connect=10),
            follow_redirects=False,
        )

    def close(self) -> None:
        self.client.close()

    def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        response = self.client.request(method, path, **kwargs)
        if not response.is_success:
            try:
                detail = response.json().get("detail")
            except (ValueError, AttributeError):
                detail = response.text[:500]
            raise E2EFailure(f"{method} {path}: HTTP {response.status_code}: {detail}")
        return response

    def json(self, method: str, path: str, **kwargs: Any) -> Any:
        return self.request(method, path, **kwargs).json()

    def wait_job(self, job_id: str, timeout_seconds: float) -> dict[str, Any]:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            job = self.json("GET", f"/api/jobs/{job_id}")
            if job.get("terminal") or job.get("status") in TERMINAL_STATES:
                return job
            time.sleep(0.5)
        raise E2EFailure(f"Execução {job_id} não terminou em {timeout_seconds:.0f}s.")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise E2EFailure(message)


def verify_artifacts(api: Api, job_id: str) -> dict[str, int]:
    sizes: dict[str, int] = {}
    json_artifacts = {
        "manifest",
        "status",
        "validation_report",
        "audit_report",
        "allocation_summary",
    }
    for key in (
        "manifest",
        "status",
        "source_copy",
        "validation_report",
        "validation_issues",
        "audit_report",
        "allocation_workbook",
        "allocation_summary",
    ):
        response = api.request("GET", f"/api/jobs/{job_id}/artifacts/{key}")
        require(response.content, f"Artefato vazio: {key}.")
        if key in json_artifacts:
            try:
                response.json()
            except ValueError as exc:
                raise E2EFailure(f"Artefato JSON inválido: {key}.") from exc
        if key in {"source_copy", "allocation_workbook"}:
            require(response.content.startswith(b"PK"), f"XLSX inválido: {key}.")
        sizes[key] = len(response.content)
    return sizes


def verify_published_job(api: Api, job_id: str) -> dict[str, Any]:
    job = api.json("GET", f"/api/jobs/{job_id}")
    require(job["status"] == "CONCLUIDA", f"Estado final inesperado: {job['status']}.")
    summary = api.json("GET", f"/api/jobs/{job_id}/summary")
    require(summary["solver_status"] == "OPTIMAL", "O solver não comprovou ótimo.")
    require(summary["transmissions"] == 402, "A base de demonstração não produziu 402 ofertas.")
    require(summary["allocated"] == 377, "A base de demonstração não produziu 377 alocações.")
    require(summary["unassigned"] == 25, "A base de demonstração não produziu 25 lacunas.")
    dashboard = api.json("GET", f"/api/dashboard/{job_id}")
    require(dashboard["guardrails"]["solver"] == "OPTIMAL", "Dashboard diverge do solver.")
    require(dashboard["guardrails"]["audit"] == "APROVADO", "Dashboard diverge da auditoria.")
    insights = api.json("GET", f"/api/insights/{job_id}")
    require(
        insights["kpis"]["disciplines_uncovered"] == 24,
        "Insights divergem das 24 disciplinas totalmente descobertas.",
    )
    allocation_page = api.json(
        "GET", f"/api/jobs/{job_id}/allocations", params={"page": 1, "page_size": 25}
    )
    require(allocation_page["total"] == 402, "Paginação de alocações não reconcilia.")
    return {
        "job": job,
        "summary": summary,
        "dashboard_guardrails": dashboard["guardrails"],
        "insights_uncovered": insights["kpis"]["disciplines_uncovered"],
        "artifact_sizes": verify_artifacts(api, job_id),
    }


def run_flow(api: Api, workbook: Path, timeout_seconds: float) -> dict[str, Any]:
    health = api.json("GET", "/api/health")
    require(health.get("status") == "ok", "Health check não retornou ok.")
    with workbook.open("rb") as stream:
        upload = api.json(
            "POST",
            "/api/uploads",
            data={"module": "52"},
            files={
                "file": (
                    workbook.name,
                    stream,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )
    require(
        upload["validation"]["status"] in {"APROVADO", "APROVADO_COM_RESSALVAS"},
        f"Validação não liberou a base: {upload['validation']['status']}.",
    )
    pending = api.request("GET", f"/api/uploads/{upload['id']}/validation.xlsx")
    require(pending.content.startswith(b"PK"), "Planilha de pendências inválida.")
    created_job = api.json(
        "POST",
        "/api/jobs",
        json={
            "upload_id": upload["id"],
            "confirm_warnings": True,
            "require_optimal": True,
            "time_limit_seconds": None,
        },
    )
    primary = api.wait_job(created_job["id"], timeout_seconds)
    require(primary["status"] == "CONCLUIDA", f"Motor principal terminou em {primary['status']}.")
    primary_evidence = verify_published_job(api, primary["id"])

    scenario = api.json(
        "POST",
        "/api/scenarios",
        json={
            "baseline_job_id": primary["id"],
            "name": "E2E produção 1.0",
            "description": "Cenário de homologação automatizada com uma alocação fixada.",
        },
    )
    catalog = api.json("GET", f"/api/scenarios/{scenario['id']}/catalog")
    fixed_offer = next(
        (
            offer
            for offer in catalog["offers"]
            if offer["baseline_status"] == "ALOCADA" and offer["baseline_teacher_badge"]
        ),
        None,
    )
    require(fixed_offer is not None, "Nenhuma oferta alocada disponível para a política FIXAR.")
    policy = api.json(
        "POST",
        f"/api/scenarios/{scenario['id']}/policies",
        json={
            "policy_type": "FIXAR",
            "target_type": "OFFER",
            "target_value": str(fixed_offer["row_number"]),
            "configuration": {"teacher_badge": fixed_offer["baseline_teacher_badge"]},
        },
    )
    scenario_created_job = api.json("POST", f"/api/scenarios/{scenario['id']}/runs")
    scenario_job = api.wait_job(scenario_created_job["id"], timeout_seconds)
    require(
        scenario_job["status"] == "CONCLUIDA",
        f"Motor de cenários terminou em {scenario_job['status']}.",
    )
    scenario_evidence = verify_published_job(api, scenario_job["id"])
    comparison = api.json("GET", f"/api/scenarios/{scenario['id']}/comparison")
    require(
        comparison["guardrails"]["eligible_for_promotion"] is True,
        f"Guardrails bloquearam a promoção: {comparison['guardrails']}.",
    )
    promoted = api.json("POST", f"/api/scenarios/{scenario['id']}/promote")
    require(promoted["status"] == "HOMOLOGADO", "Cenário não foi homologado.")
    analysis_jobs = api.json("GET", "/api/analysis-jobs")
    require(
        any(job["id"] == scenario_job["id"] and job["is_official"] for job in analysis_jobs),
        "Cenário homologado não aparece como resultado oficial.",
    )
    return {
        "schema_version": 1,
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "workbook": str(workbook.resolve()),
        "workbook_sha256": sha256(workbook),
        "upload_id": upload["id"],
        "validation_status": upload["validation"]["status"],
        "primary_job_id": primary["id"],
        "primary": primary_evidence,
        "scenario_id": scenario["id"],
        "scenario_job_id": scenario_job["id"],
        "scenario_policy_id": policy["id"],
        "scenario": scenario_evidence,
        "comparison_guardrails": comparison["guardrails"],
        "promoted_status": promoted["status"],
    }


def verify_restored(api: Api, receipt: dict[str, Any], reset_at_end: bool) -> dict[str, Any]:
    health = api.json("GET", "/api/health")
    require(health.get("status") == "ok", "Health check da restauração falhou.")
    primary = verify_published_job(api, str(receipt["primary_job_id"]))
    scenario = api.json("GET", f"/api/scenarios/{receipt['scenario_id']}")
    require(scenario["status"] == "HOMOLOGADO", "Cenário restaurado não está homologado.")
    comparison = api.json("GET", f"/api/scenarios/{receipt['scenario_id']}/comparison")
    require(comparison["guardrails"]["eligible_for_promotion"], "Guardrails restaurados divergiram.")
    reset_result: dict[str, Any] | None = None
    if reset_at_end:
        scenario_reset = api.json("DELETE", "/api/scenarios", params={"scope": "latest"})
        primary_reset = api.json("DELETE", "/api/jobs/primary", params={"scope": "latest"})
        require(scenario_reset["deleted_scenarios"] == 1, "Reset do cenário não removeu um item.")
        require(primary_reset["deleted_rounds"] == 1, "Reset da rodada não removeu um item.")
        reset_result = {"scenario": scenario_reset, "primary": primary_reset}
    return {
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "primary": primary,
        "scenario_status": scenario["status"],
        "comparison_guardrails": comparison["guardrails"],
        "reset": reset_result,
    }


def write_receipt(path: Path | None, payload: dict[str, Any]) -> None:
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if path is None:
        print(rendered, end="")
        return
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(rendered, encoding="utf-8")
    temporary.replace(path)
    print(f"Recibo E2E gravado em {path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Executa a homologação E2E da API local.")
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--timeout", type=float, default=900)
    parser.add_argument("--saida", type=Path)
    modes = parser.add_subparsers(dest="mode", required=True)
    run = modes.add_parser("executar", help="Executa upload, dois motores e promoção.")
    run.add_argument("--base", type=Path, required=True)
    restore = modes.add_parser("verificar-restauracao", help="Valida dados restaurados.")
    restore.add_argument("--recibo", type=Path, required=True)
    restore.add_argument("--resetar-no-final", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    api = Api(args.url, args.timeout)
    try:
        if args.mode == "executar":
            workbook = args.base.expanduser().resolve()
            if not workbook.is_file():
                raise FileNotFoundError(f"Base de demonstração ausente: {workbook}")
            payload = run_flow(api, workbook, args.timeout)
        else:
            receipt = json.loads(args.recibo.read_text(encoding="utf-8"))
            payload = verify_restored(api, receipt, args.resetar_no_final)
    finally:
        api.close()
    write_receipt(args.saida, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
