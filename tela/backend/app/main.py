from __future__ import annotations

import json
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import Settings
from .database import Database, utc_now
from .services.jobs import (
    JobManager,
    artifact_path,
    build_dashboard,
    load_summary,
    public_job,
    read_json,
)
from .services.insights import build_insights
from .services.resets import reset_primary_rounds, reset_saved_scenarios
from .services.scenarios import (
    ScenarioError,
    ScenarioManager,
    add_scenario_change,
    add_scenario_policy,
    compare_scenario,
    public_scenario,
    source_catalog,
)
from .services.uploads import (
    UploadValidationError,
    save_upload_stream,
    write_validation_workbook,
)


class JobCreate(BaseModel):
    upload_id: str
    confirm_warnings: bool = False
    require_optimal: bool = True
    time_limit_seconds: float | None = Field(default=None, gt=0)


class ScenarioCreate(BaseModel):
    baseline_job_id: str
    name: str = Field(min_length=3, max_length=120)
    description: str = Field(default="", max_length=1000)


class ScenarioChangeCreate(BaseModel):
    change_type: str
    entity_type: str
    row_number: int = Field(ge=2)
    field_name: str
    new_value: str | int | float


class ScenarioPolicyCreate(BaseModel):
    policy_type: str
    target_type: str
    target_value: str
    configuration: dict = Field(default_factory=dict)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    settings.ensure_directories()
    database = Database(settings.db_path)
    database.initialize()
    database.recover_incomplete_jobs()
    manager = JobManager(settings, database)
    scenario_manager = ScenarioManager(settings, database)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        manager.shutdown()
        scenario_manager.shutdown()

    app = FastAPI(
        title="Ferramenta de Alocação Docente",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.database = database
    app.state.job_manager = manager
    app.state.scenario_manager = scenario_manager
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def prevent_stale_frontend_cache(request: Request, call_next):
        response = await call_next(request)
        if not request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

    @app.get("/api/health")
    def health() -> dict:
        return {
            "status": "ok",
            "vbeta_available": settings.vbeta_dir.is_dir(),
            "scenario_engine_available": settings.scenario_engine_dir.is_dir(),
            "data_dir_ready": settings.data_dir.is_dir(),
        }

    @app.post("/api/uploads")
    def upload_and_validate(
        file: Annotated[UploadFile, File(description="Planilha .xlsx")],
        module: Annotated[int, Form(ge=51, le=54)] = 52,
    ) -> dict:
        try:
            return save_upload_stream(
                file.file,
                file.filename,
                module,
                settings,
                database,
            )
        except UploadValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        finally:
            file.file.close()

    @app.get("/api/uploads/{upload_id}/validation.csv", include_in_schema=False)
    @app.get("/api/uploads/{upload_id}/validation.xlsx")
    def download_upload_validation(upload_id: str) -> FileResponse:
        upload = database.get_upload(upload_id)
        if not upload:
            raise HTTPException(status_code=404, detail="Upload não encontrado.")
        path = Path(upload["validation_csv_path"])
        report_path = Path(upload["validation_path"])
        if report_path.is_file():
            path = write_validation_workbook(
                read_json(report_path),
                report_path.parent,
                upload["original_name"],
            )
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Planilha de pendências não disponível.")
        return FileResponse(
            path,
            filename="pendencias_validacao.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    @app.post("/api/jobs", status_code=202)
    def create_job(payload: JobCreate) -> dict:
        upload = database.get_upload(payload.upload_id)
        if not upload:
            raise HTTPException(status_code=404, detail="Upload não encontrado.")
        validation_status = upload["validation_status"]
        if validation_status == "REPROVADO":
            raise HTTPException(
                status_code=409,
                detail="A base foi reprovada e não pode seguir para a otimização.",
            )
        if validation_status == "APROVADO_COM_RESSALVAS" and not payload.confirm_warnings:
            raise HTTPException(
                status_code=409,
                detail="Confirme as ressalvas antes de iniciar a otimização.",
            )
        return manager.create(
            upload,
            require_optimal=payload.require_optimal,
            time_limit_seconds=payload.time_limit_seconds,
        )

    @app.get("/api/jobs")
    def list_jobs(limit: Annotated[int, Query(ge=1, le=250)] = 100) -> list[dict]:
        return [public_job(job) for job in database.list_jobs(limit)]

    @app.get("/api/analysis-jobs")
    def list_analysis_jobs(
        limit: Annotated[int, Query(ge=1, le=250)] = 100,
    ) -> list[dict]:
        jobs = database.list_jobs(limit, kind=None)
        completed = [job for job in jobs if job["status"] == "CONCLUIDA"]
        completed.sort(
            key=lambda job: (bool(job.get("is_official")), job["created_at"]),
            reverse=True,
        )
        return [public_job(job) for job in completed]

    @app.delete("/api/jobs/primary")
    def reset_primary_jobs(
        scope: Annotated[str, Query(pattern="^(latest|all)$")] = "latest",
    ) -> dict:
        try:
            return reset_primary_rounds(settings, database, scope)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/scenarios", status_code=201)
    def create_scenario(payload: ScenarioCreate) -> dict:
        baseline = database.get_job(payload.baseline_job_id)
        if not baseline or baseline["status"] != "CONCLUIDA":
            raise HTTPException(
                status_code=409,
                detail="Selecione uma rodada-base concluída para criar o cenário.",
            )
        if baseline.get("kind", "PRIMARY") != "PRIMARY":
            raise HTTPException(
                status_code=409,
                detail="A baseline deve ser uma execução do motor principal.",
            )
        now = utc_now()
        scenario_id = uuid.uuid4().hex
        database.create_scenario({
            "id": scenario_id,
            "baseline_job_id": payload.baseline_job_id,
            "name": payload.name.strip(),
            "description": payload.description.strip(),
            "status": "RASCUNHO",
            "created_at": now,
            "updated_at": now,
        })
        scenario = database.get_scenario(scenario_id)
        return public_scenario(database, scenario or {})

    @app.get("/api/scenarios")
    def list_scenarios() -> list[dict]:
        return [
            public_scenario(database, scenario)
            for scenario in database.list_scenarios()
        ]

    @app.delete("/api/scenarios")
    def reset_scenarios(
        scope: Annotated[str, Query(pattern="^(latest|all)$")] = "latest",
    ) -> dict:
        try:
            return reset_saved_scenarios(settings, database, scope)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get("/api/scenarios/{scenario_id}")
    def get_scenario(scenario_id: str) -> dict:
        scenario = database.get_scenario(scenario_id)
        if not scenario:
            raise HTTPException(status_code=404, detail="Cenário não encontrado.")
        return public_scenario(database, scenario)

    @app.get("/api/scenarios/{scenario_id}/catalog")
    def get_scenario_catalog(scenario_id: str) -> dict:
        try:
            return source_catalog(database, scenario_id)
        except ScenarioError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/scenarios/{scenario_id}/changes", status_code=201)
    def create_scenario_change(
        scenario_id: str,
        payload: ScenarioChangeCreate,
    ) -> dict:
        try:
            return add_scenario_change(
                database,
                scenario_id,
                change_type=payload.change_type,
                entity_type=payload.entity_type,
                row_number=payload.row_number,
                field_name=payload.field_name,
                new_value=payload.new_value,
            )
        except ScenarioError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.delete("/api/scenarios/{scenario_id}/changes/{change_id}", status_code=204)
    def delete_scenario_change(scenario_id: str, change_id: str) -> None:
        if not database.delete_scenario_change(scenario_id, change_id):
            raise HTTPException(status_code=404, detail="Alteração não encontrada.")

    @app.post("/api/scenarios/{scenario_id}/policies", status_code=201)
    def create_scenario_policy(
        scenario_id: str,
        payload: ScenarioPolicyCreate,
    ) -> dict:
        try:
            return add_scenario_policy(
                database,
                scenario_id,
                policy_type=payload.policy_type,
                target_type=payload.target_type,
                target_value=payload.target_value,
                configuration=payload.configuration,
            )
        except ScenarioError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.delete("/api/scenarios/{scenario_id}/policies/{policy_id}", status_code=204)
    def delete_scenario_policy(scenario_id: str, policy_id: str) -> None:
        if not database.delete_scenario_policy(scenario_id, policy_id):
            raise HTTPException(status_code=404, detail="Política não encontrada.")

    @app.post("/api/scenarios/{scenario_id}/runs", status_code=202)
    def run_scenario(scenario_id: str) -> dict:
        try:
            return scenario_manager.create_run(scenario_id)
        except ScenarioError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get("/api/scenarios/{scenario_id}/comparison")
    def scenario_comparison(scenario_id: str) -> dict:
        try:
            return compare_scenario(database, scenario_id)
        except ScenarioError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/scenarios/{scenario_id}/promote")
    def promote_scenario(scenario_id: str) -> dict:
        try:
            comparison = compare_scenario(database, scenario_id)
        except ScenarioError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        if not comparison["guardrails"]["eligible_for_promotion"]:
            raise HTTPException(
                status_code=409,
                detail="Somente cenários validados, ótimos e auditados podem ser homologados.",
            )
        scenario = database.get_scenario(scenario_id)
        job = database.latest_scenario_job(scenario_id)
        if not scenario or not job:
            raise HTTPException(status_code=404, detail="Cenário não encontrado.")
        database.promote_scenario(scenario_id, job["id"], scenario["module"])
        refreshed = database.get_scenario(scenario_id)
        return public_scenario(database, refreshed or {})

    @app.get("/api/jobs/{job_id}")
    def get_job(job_id: str) -> dict:
        job = database.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Execução não encontrada.")
        return public_job(job)

    @app.get("/api/jobs/{job_id}/validation")
    def get_validation(job_id: str) -> dict:
        job = database.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Execução não encontrada.")
        path = Path(job["validation_path"])
        if job.get("round_dir"):
            round_path = Path(job["round_dir"]) / "validacao" / "relatorio_validacao.json"
            if round_path.exists():
                path = round_path
        payload = read_json(path)
        payload["source"] = job["original_name"]
        return payload

    @app.get("/api/jobs/{job_id}/summary")
    def get_summary(job_id: str) -> dict:
        job = database.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Execução não encontrada.")
        try:
            summary = load_summary(job)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {key: value for key, value in summary.items() if key != "decisions"}

    @app.get("/api/jobs/{job_id}/allocations")
    def get_allocations(
        job_id: str,
        page: Annotated[int, Query(ge=1)] = 1,
        page_size: Annotated[int, Query(ge=10, le=200)] = 25,
        status: str | None = None,
        reason: str | None = None,
        search: str | None = None,
    ) -> dict:
        job = database.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Execução não encontrada.")
        try:
            decisions = load_summary(job).get("decisions", [])
        except FileNotFoundError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        if status:
            decisions = [item for item in decisions if item.get("status") == status]
        if reason:
            decisions = [item for item in decisions if item.get("unassigned_reason") == reason]
        if search:
            needle = search.casefold().strip()
            decisions = [
                item
                for item in decisions
                if needle
                in " ".join(
                    str(item.get(key) or "")
                    for key in (
                        "curriculum",
                        "discipline_code",
                        "discipline_name",
                        "teacher_badge",
                        "teacher_name",
                    )
                ).casefold()
            ]
        total = len(decisions)
        start = (page - 1) * page_size
        return {
            "items": decisions[start : start + page_size],
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": max(1, (total + page_size - 1) // page_size),
        }

    @app.get("/api/jobs/{job_id}/artifacts/{artifact_key}")
    def download_artifact(job_id: str, artifact_key: str) -> FileResponse:
        job = database.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Execução não encontrada.")
        try:
            path = artifact_path(job, artifact_key)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return FileResponse(path, filename=path.name)

    @app.get("/api/dashboard/{job_id}")
    def dashboard(
        job_id: str,
        order: Annotated[list[str] | None, Query()] = None,
        course: Annotated[list[str] | None, Query()] = None,
        cluster: Annotated[list[str] | None, Query()] = None,
        day: Annotated[list[str] | None, Query()] = None,
        schedule_time: Annotated[list[str] | None, Query(alias="time")] = None,
    ) -> dict:
        job = database.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Execução não encontrada.")
        try:
            return build_dashboard(
                job,
                load_summary(job),
                {
                    "order": order or [],
                    "course": course or [],
                    "cluster": cluster or [],
                    "day": day or [],
                    "time": schedule_time or [],
                },
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except (json.JSONDecodeError, KeyError) as exc:
            raise HTTPException(
                status_code=500,
                detail="Os artefatos da rodada não puderam ser interpretados.",
            ) from exc

    @app.get("/api/insights/{job_id}")
    def insights(job_id: str) -> dict:
        job = database.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Execução não encontrada.")
        try:
            return build_insights(job)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            raise HTTPException(
                status_code=500,
                detail="Os artefatos da rodada não puderam ser interpretados para gerar insights.",
            ) from exc

    if settings.frontend_dist.is_dir():
        app.mount("/", StaticFiles(directory=settings.frontend_dist, html=True), name="frontend")

    return app


app = create_app()
