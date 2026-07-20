from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Any, Callable

from ..config import Settings
from ..database import Database


def _safe_paths(settings: Settings, plan: dict[str, Any]) -> list[Path]:
    """Return only top-level, existing paths contained by the operational root."""
    candidates: list[Path] = []
    candidates.extend(Path(value) for value in plan.get("round_dirs", []))
    candidates.extend(settings.job_dir / job_id for job_id in plan.get("job_ids", []))
    candidates.extend(
        settings.scenario_job_dir / job_id for job_id in plan.get("job_ids", [])
    )
    candidates.extend(
        settings.result_dir / job_id for job_id in plan.get("primary_job_ids", [])
    )
    candidates.extend(
        settings.scenario_result_dir / scenario_id
        for scenario_id in plan.get("scenario_ids", [])
    )
    candidates.extend(Path(value) for value in plan.get("upload_dirs", []))

    root = settings.data_dir.resolve()
    resolved: list[Path] = []
    for candidate in candidates:
        path = candidate.resolve()
        if path == root or root not in path.parents or not path.exists():
            continue
        resolved.append(path)

    top_level: list[Path] = []
    for path in sorted(set(resolved), key=lambda item: (len(item.parts), str(item))):
        if any(parent == path or parent in path.parents for parent in top_level):
            continue
        top_level.append(path)
    return top_level


def _quarantine(
    settings: Settings,
    plan: dict[str, Any],
) -> tuple[Path | None, list[tuple[Path, Path]]]:
    """Move data before deleting database references, rolling back on any failure."""
    paths = _safe_paths(settings, plan)
    if not paths:
        return None, []
    batch = settings.data_dir / ".lixeira" / uuid.uuid4().hex
    batch.mkdir(parents=True, exist_ok=False)
    moved: list[tuple[Path, Path]] = []
    try:
        for index, source in enumerate(paths, start=1):
            destination = batch / f"{index:03d}-{source.name}"
            source.rename(destination)
            moved.append((source, destination))
    except OSError as exc:
        for source, destination in reversed(moved):
            if destination.exists() and not source.exists():
                destination.rename(source)
        shutil.rmtree(batch, ignore_errors=False)
        raise ValueError(
            "Não foi possível zerar porque um artefato está em uso. "
            "Feche planilhas e tente novamente; nenhum registro foi removido."
        ) from exc
    return batch, moved


def _restore(batch: Path | None, moved: list[tuple[Path, Path]]) -> None:
    if batch is None:
        return
    for source, destination in reversed(moved):
        if destination.exists() and not source.exists():
            source.parent.mkdir(parents=True, exist_ok=True)
            destination.rename(source)
    if batch.exists():
        shutil.rmtree(batch, ignore_errors=False)


def _purge(batch: Path | None) -> bool:
    if batch is None or not batch.exists():
        return False
    try:
        shutil.rmtree(batch, ignore_errors=False)
    except OSError:
        # The directory remains in data/.lixeira and will be retried later.
        return True
    return False


def _retry_pending(settings: Settings) -> int:
    trash = settings.data_dir / ".lixeira"
    if not trash.is_dir():
        return 0
    pending = 0
    for batch in trash.iterdir():
        if batch.is_dir() and _purge(batch):
            pending += 1
    try:
        trash.rmdir()
    except OSError:
        pass
    return pending


def _execute_reset(
    settings: Settings,
    preview: Callable[[], dict[str, Any]],
    commit: Callable[[], dict[str, Any]],
) -> tuple[dict[str, Any], int]:
    _retry_pending(settings)
    plan = preview()
    batch, moved = _quarantine(settings, plan)
    try:
        committed = commit()
        if {
            key: committed.get(key, [])
            for key in ("scenario_ids", "job_ids", "primary_job_ids", "upload_ids")
        } != {
            key: plan.get(key, [])
            for key in ("scenario_ids", "job_ids", "primary_job_ids", "upload_ids")
        }:
            raise RuntimeError("O plano de limpeza mudou durante a operação.")
    except Exception:
        _restore(batch, moved)
        raise
    pending = int(_purge(batch)) + _retry_pending(settings)
    return committed, pending


def reset_saved_scenarios(
    settings: Settings,
    database: Database,
    scope: str,
) -> dict[str, Any]:
    deleted, pending = _execute_reset(
        settings,
        lambda: database.reset_scenarios(scope, dry_run=True),
        lambda: database.reset_scenarios(scope),
    )
    return {
        "scope": scope,
        "deleted_scenarios": len(deleted["scenario_ids"]),
        "deleted_jobs": len(deleted["job_ids"]),
        "cleanup_pending": pending,
    }


def reset_primary_rounds(
    settings: Settings,
    database: Database,
    scope: str,
) -> dict[str, Any]:
    deleted, pending = _execute_reset(
        settings,
        lambda: database.reset_primary_jobs(scope, dry_run=True),
        lambda: database.reset_primary_jobs(scope),
    )
    return {
        "scope": scope,
        "deleted_rounds": len(deleted["primary_job_ids"]),
        "deleted_scenarios": len(deleted["scenario_ids"]),
        "deleted_jobs": len(deleted["job_ids"]),
        "cleanup_pending": pending,
    }
