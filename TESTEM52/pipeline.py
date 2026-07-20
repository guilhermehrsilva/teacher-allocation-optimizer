from __future__ import annotations

import hashlib
import json
import platform
import shutil
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = ROOT.parent
for source_dir in (
    REPOSITORY_ROOT / "MOTOR" / "src",
    REPOSITORY_ROOT / "VALIDADOR" / "src",
):
    source_text = str(source_dir)
    if source_text not in sys.path:
        sys.path.insert(0, source_text)

from alocacao_docente.validation import (  # noqa: E402
    VALIDATION_CONTRACT_VERSION,
    validate_workbook,
)
from motor_alocacao import (  # noqa: E402
    audit_allocation,
    load_problem,
    solve_allocation,
    write_results,
)


PIPELINE_VERSION = "1.3"
EXPECTED_MODULE = 52
RANDOM_SEED = 42
GRASP_ITERATIONS = 0

EXIT_SUCCESS = 0
EXIT_INPUT_CONFIG = 10
EXIT_VALIDATION = 20
EXIT_SOLVER = 30
EXIT_OPTIMAL_REQUIRED = 31
EXIT_AUDIT = 40
EXIT_INTERNAL = 50

DEFAULT_INPUT_DIR = ROOT / "entrada"
DEFAULT_OUTPUT_DIR = ROOT / "resultado"


class InputConfigurationError(ValueError):
    """Erro previsível de descoberta da entrada ou de configuração."""


class _StageFailure(RuntimeError):
    def __init__(self, exit_code: int, state: str, message: str) -> None:
        super().__init__(message)
        self.exit_code = exit_code
        self.state = state


@dataclass(frozen=True)
class PipelineConfig:
    input_dir: Path = DEFAULT_INPUT_DIR
    output_dir: Path = DEFAULT_OUTPUT_DIR
    base: Path | None = None
    workers: int = 8
    max_time_seconds: float | None = None
    require_optimal: bool = True


@dataclass(frozen=True)
class PipelineRun:
    exit_code: int
    state: str
    message: str
    round_dir: Path | None
    status_path: Path | None
    manifest_path: Path | None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _create_round_directory(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    for _ in range(1000):
        numbers = [
            int(item.name.removeprefix("rodada_"))
            for item in output_dir.glob("rodada_*")
            if item.is_dir() and item.name.removeprefix("rodada_").isdigit()
        ]
        candidate = output_dir / f"rodada_{max(numbers, default=0) + 1:03d}"
        try:
            candidate.mkdir()
        except FileExistsError:
            continue
        return candidate
    raise RuntimeError("Não foi possível reservar uma nova rodada.")


def discover_workbook(input_dir: str | Path) -> Path:
    """Retorna o único XLSX utilizável de ``input_dir``."""

    directory = Path(input_dir)
    if not directory.exists():
        raise InputConfigurationError(f"Diretório de entrada inexistente: {directory}")
    if not directory.is_dir():
        raise InputConfigurationError(f"A entrada não é um diretório: {directory}")
    candidates = sorted(
        (
            item.resolve()
            for item in directory.iterdir()
            if item.is_file()
            and item.suffix.casefold() == ".xlsx"
            and not item.name.startswith("~$")
        ),
        key=lambda item: item.name.casefold(),
    )
    if len(candidates) != 1:
        names = ", ".join(item.name for item in candidates) or "nenhum"
        raise InputConfigurationError(
            "A entrada deve conter exatamente um XLSX utilizável; "
            f"encontrados {len(candidates)}: {names}."
        )
    return candidates[0]


def _select_source(config: PipelineConfig) -> tuple[Path, str]:
    if config.base is None:
        return discover_workbook(config.input_dir), "descoberta"
    source = Path(config.base)
    if not source.exists() or not source.is_file():
        raise InputConfigurationError(f"Base inexistente ou inválida: {source}")
    if source.suffix.casefold() != ".xlsx" or source.name.startswith("~$"):
        raise InputConfigurationError(f"A base deve ser um arquivo XLSX utilizável: {source}")
    return source.resolve(), "explicita"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _code_fingerprints() -> dict[str, dict[str, str]]:
    """Identifica exatamente o código usado, inclusive alterações não commitadas."""

    component_dir = REPOSITORY_ROOT / "MOTOR" / "src" / "motor_alocacao"
    files = {
        "pipeline": Path(__file__).resolve(),
        "validation": REPOSITORY_ROOT
        / "VALIDADOR"
        / "src"
        / "alocacao_docente"
        / "validation.py",
        "domain": component_dir / "domain.py",
        "eligibility": component_dir / "eligibility.py",
        "loader": component_dir / "loader.py",
        "solver": component_dir / "solver.py",
        "grasp": component_dir / "grasp.py",
        "audit": component_dir / "audit.py",
        "reporting": component_dir / "reporting.py",
    }
    return {
        name: {
            "path": str(path.relative_to(REPOSITORY_ROOT)),
            "sha256": _sha256(path),
        }
        for name, path in files.items()
    }


def _copy_source(source: Path, round_dir: Path) -> tuple[Path, str]:
    source_hash_before = _sha256(source)
    destination_dir = round_dir / "fonte"
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / source.name
    temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
    try:
        shutil.copy2(source, temporary)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    copied_hash = _sha256(destination)
    source_hash_after = _sha256(source)
    if source_hash_before != copied_hash or source_hash_before != source_hash_after:
        raise InputConfigurationError("A base foi alterada durante a cópia; execute novamente.")
    return destination, copied_hash


def _package_version(distribution: str) -> str:
    try:
        return metadata.version(distribution)
    except metadata.PackageNotFoundError:
        return "não instalada"


def _versions() -> dict[str, str]:
    return {
        "pipeline": PIPELINE_VERSION,
        "validation_contract": VALIDATION_CONTRACT_VERSION,
        "python": platform.python_version(),
        "openpyxl": _package_version("openpyxl"),
        "ortools": _package_version("ortools"),
    }


def _config_payload(config: PipelineConfig) -> dict[str, Any]:
    return {
        "input_dir": str(Path(config.input_dir).resolve()),
        "output_dir": str(Path(config.output_dir).resolve()),
        "base_argument": str(Path(config.base).resolve()) if config.base else None,
        "expected_module": EXPECTED_MODULE,
        "workers": config.workers,
        "max_time_seconds": config.max_time_seconds,
        "random_seed": RANDOM_SEED,
        "grasp_iterations": GRASP_ITERATIONS,
        "require_optimal": config.require_optimal,
    }


class _StatusRecorder:
    def __init__(self, path: Path, round_name: str) -> None:
        self.path = path
        self.payload: dict[str, Any] = {
            "schema_version": 1,
            "round": round_name,
            "state": "INICIADA",
            "exit_code": None,
            "message": "Rodada criada.",
            "updated_at_utc": _utc_now(),
            "history": [],
        }
        self.update("INICIADA", "Rodada criada.")

    def update(
        self,
        state: str,
        message: str,
        exit_code: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        timestamp = _utc_now()
        event: dict[str, Any] = {
            "state": state,
            "message": message,
            "at_utc": timestamp,
        }
        if exit_code is not None:
            event["exit_code"] = exit_code
        if details:
            event["details"] = details
        self.payload.update(
            {
                "state": state,
                "exit_code": exit_code,
                "message": message,
                "updated_at_utc": timestamp,
            }
        )
        self.payload["history"].append(event)
        _atomic_write_json(self.path, self.payload)


def _validate_config(config: PipelineConfig) -> None:
    if (
        not isinstance(config.workers, int)
        or isinstance(config.workers, bool)
        or config.workers < 1
    ):
        raise InputConfigurationError("workers deve ser um inteiro positivo.")
    if config.max_time_seconds is not None and (
        isinstance(config.max_time_seconds, bool)
        or not isinstance(config.max_time_seconds, (int, float))
        or config.max_time_seconds <= 0
    ):
        raise InputConfigurationError("max_time_seconds deve ser numérico e positivo.")
    if not isinstance(config.require_optimal, bool):
        raise InputConfigurationError("require_optimal deve ser booleano.")


def run_pipeline(config: PipelineConfig | None = None) -> PipelineRun:
    """Executa uma rodada completa e sempre retorna o código operacional."""

    config = config or PipelineConfig()
    try:
        round_dir = _create_round_directory(Path(config.output_dir))
    except Exception as exc:
        return PipelineRun(
            EXIT_INTERNAL,
            "ERRO_INTERNO",
            f"Não foi possível criar a rodada: {exc}",
            None,
            None,
            None,
        )

    status_path = round_dir / "status.json"
    manifest_path = round_dir / "manifesto.json"
    status: _StatusRecorder | None = None
    try:
        status = _StatusRecorder(status_path, round_dir.name)
        manifest: dict[str, Any] = {
            "schema_version": 1,
            "round": round_dir.name,
            "created_at_utc": _utc_now(),
            "config": _config_payload(config),
            "versions": _versions(),
            "code_fingerprints": _code_fingerprints(),
            "source": None,
            "phases": {},
            "artifacts": {},
            "outcome": None,
        }
        _atomic_write_json(manifest_path, manifest)
    except Exception as exc:
        message = f"Não foi possível iniciar os registros da rodada: {exc}"
        if status is not None:
            try:
                status.update("ERRO_INTERNO", message, EXIT_INTERNAL)
            except Exception:
                pass
        return PipelineRun(
            EXIT_INTERNAL,
            "ERRO_INTERNO",
            message,
            round_dir,
            status_path if status_path.exists() else None,
            manifest_path if manifest_path.exists() else None,
        )

    def finish(exit_code: int, state: str, message: str) -> PipelineRun:
        manifest["completed_at_utc"] = _utc_now()
        manifest["outcome"] = {
            "exit_code": exit_code,
            "state": state,
            "message": message,
        }
        _atomic_write_json(manifest_path, manifest)
        status.update(state, message, exit_code)
        return PipelineRun(
            exit_code,
            state,
            message,
            round_dir,
            status_path,
            manifest_path,
        )

    try:
        try:
            _validate_config(config)
            status.update("SELECIONANDO_ENTRADA", "Selecionando a base de entrada.")
            source, selection_mode = _select_source(config)
            status.update("COPIANDO_ENTRADA", f"Copiando {source.name} para a rodada.")
            copied_source, source_hash = _copy_source(source, round_dir)
        except InputConfigurationError as exc:
            raise _StageFailure(EXIT_INPUT_CONFIG, "FALHA_ENTRADA_CONFIG", str(exc)) from exc
        except OSError as exc:
            raise _StageFailure(
                EXIT_INPUT_CONFIG,
                "FALHA_ENTRADA_CONFIG",
                f"Falha ao preparar a entrada: {exc}",
            ) from exc

        manifest["source"] = {
            "selection_mode": selection_mode,
            "original_path": str(source),
            "copied_path": str(copied_source.relative_to(round_dir)),
            "filename": copied_source.name,
            "size_bytes": copied_source.stat().st_size,
            "sha256": source_hash,
        }
        manifest["artifacts"]["source_copy"] = str(copied_source.relative_to(round_dir))
        _atomic_write_json(manifest_path, manifest)

        status.update("VALIDANDO", "Validando a cópia da base para o módulo 52.")
        try:
            validation = validate_workbook(copied_source, expected_module=EXPECTED_MODULE)
            validation_json, validation_csv = validation.write(round_dir / "validacao")
        except Exception as exc:
            raise _StageFailure(
                EXIT_VALIDATION,
                "FALHA_VALIDACAO",
                f"A validação não pôde ser concluída: {exc}",
            ) from exc
        validated_hash = validation.metadata.get("source_sha256")
        if validated_hash != source_hash:
            raise _StageFailure(
                EXIT_VALIDATION,
                "SNAPSHOT_ALTERADO",
                "O SHA da base validada diverge da cópia registrada na rodada.",
            )
        manifest["phases"]["validation"] = {
            "status": validation.status,
            "source_sha256": validated_hash,
            "severity_counts": validation.severity_counts,
            "blocking_issue_groups": sum(issue.blocking for issue in validation.issues),
        }
        manifest["artifacts"].update(
            {
                "validation_report": str(validation_json.relative_to(round_dir)),
                "validation_issues": str(validation_csv.relative_to(round_dir)),
            }
        )
        _atomic_write_json(manifest_path, manifest)
        if validation.status == "REPROVADO":
            raise _StageFailure(
                EXIT_VALIDATION,
                "VALIDACAO_REPROVADA",
                "A base foi reprovada pela validação do módulo 52.",
            )

        status.update("RESOLVENDO", "Executando CP-SAT puro.")
        try:
            if _sha256(copied_source) != source_hash:
                raise _StageFailure(
                    EXIT_VALIDATION,
                    "SNAPSHOT_ALTERADO",
                    "A cópia validada foi alterada antes do carregamento pelo motor.",
                )
            problem = load_problem(copied_source)
            result = solve_allocation(
                problem,
                max_time_seconds=config.max_time_seconds,
                workers=config.workers,
                random_seed=RANDOM_SEED,
                grasp_iterations=GRASP_ITERATIONS,
            )
        except _StageFailure:
            raise
        except Exception as exc:
            raise _StageFailure(
                EXIT_SOLVER,
                "FALHA_SOLVER",
                f"O solver não pôde ser concluído: {exc}",
            ) from exc

        manifest["phases"]["solver"] = {
            "status": result.status,
            "solver_status": result.solver_status,
            "transmissions": len(problem.transmissions),
            "allocated": result.allocated_count,
            "unassigned": result.unassigned_count,
            "used_teachers": result.used_teacher_count,
            "wall_time_seconds": result.wall_time_seconds,
            "diagnostics": result.diagnostics,
        }
        _atomic_write_json(manifest_path, manifest)
        if result.solver_status not in {"OPTIMAL", "FEASIBLE"}:
            raise _StageFailure(
                EXIT_SOLVER,
                "FALHA_SOLVER",
                f"O CP-SAT terminou sem solução utilizável: {result.solver_status}.",
            )

        status.update("AUDITANDO", "Auditando a solução produzida.")
        try:
            audit = audit_allocation(problem, result)
            audit_path = audit.write(round_dir / "auditoria" / "auditoria_alocacao.json")
        except Exception as exc:
            raise _StageFailure(
                EXIT_AUDIT,
                "FALHA_AUDITORIA",
                f"A auditoria não pôde ser concluída: {exc}",
            ) from exc
        manifest["phases"]["audit"] = {
            "status": audit.status,
            "checks": audit.checks,
            "issue_count": len(audit.issues),
        }
        manifest["artifacts"]["audit_report"] = str(audit_path.relative_to(round_dir))
        _atomic_write_json(manifest_path, manifest)
        if audit.status != "APROVADO":
            raise _StageFailure(
                EXIT_AUDIT,
                "AUDITORIA_REPROVADA",
                "A auditoria reprovou a solução produzida.",
            )
        if config.require_optimal and result.solver_status != "OPTIMAL":
            raise _StageFailure(
                EXIT_OPTIMAL_REQUIRED,
                "OTIMO_NAO_COMPROVADO",
                "A solução foi auditada, mas o status OPTIMAL era obrigatório.",
            )

        status.update("GRAVANDO_ALOCACAO", "Publicando os resultados auditados.")
        try:
            allocation_xlsx, allocation_json = write_results(
                problem,
                result,
                round_dir / "alocacao",
            )
        except Exception as exc:
            raise _StageFailure(
                EXIT_SOLVER,
                "FALHA_SOLVER",
                f"Os resultados auditados não puderam ser gravados: {exc}",
            ) from exc
        manifest["artifacts"].update(
            {
                "allocation_workbook": str(allocation_xlsx.relative_to(round_dir)),
                "allocation_summary": str(allocation_json.relative_to(round_dir)),
            }
        )
        _atomic_write_json(manifest_path, manifest)

        return finish(EXIT_SUCCESS, "CONCLUIDA", "Rodada concluída e auditada com sucesso.")
    except _StageFailure as exc:
        return finish(exc.exit_code, exc.state, str(exc))
    except Exception as exc:
        return finish(
            EXIT_INTERNAL,
            "ERRO_INTERNO",
            f"Erro interno inesperado ({type(exc).__name__}): {exc}",
        )
