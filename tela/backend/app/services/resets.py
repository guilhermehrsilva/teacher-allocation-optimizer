from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from ..config import Settings
from ..database import Database


def _remove_tree(path_value: str | Path, root: Path) -> None:
    path = Path(path_value).resolve()
    allowed_root = root.resolve()
    if path == allowed_root or allowed_root not in path.parents:
        return
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)


def _cleanup(settings: Settings, deleted: dict[str, Any]) -> None:
    for round_dir in deleted.get("round_dirs", []):
        _remove_tree(round_dir, settings.data_dir)
    for job_id in deleted.get("job_ids", []):
        _remove_tree(settings.job_dir / job_id, settings.job_dir)
        _remove_tree(settings.scenario_job_dir / job_id, settings.scenario_job_dir)
    for scenario_id in deleted.get("scenario_ids", []):
        _remove_tree(settings.scenario_result_dir / scenario_id, settings.scenario_result_dir)
    for upload_dir in deleted.get("upload_dirs", []):
        _remove_tree(upload_dir, settings.upload_dir)


def reset_saved_scenarios(
    settings: Settings,
    database: Database,
    scope: str,
) -> dict[str, Any]:
    deleted = database.reset_scenarios(scope)
    _cleanup(settings, deleted)
    return {
        "scope": scope,
        "deleted_scenarios": len(deleted["scenario_ids"]),
        "deleted_jobs": len(deleted["job_ids"]),
    }


def reset_primary_rounds(
    settings: Settings,
    database: Database,
    scope: str,
) -> dict[str, Any]:
    deleted = database.reset_primary_jobs(scope)
    _cleanup(settings, deleted)
    return {
        "scope": scope,
        "deleted_rounds": len(deleted["primary_job_ids"]),
        "deleted_scenarios": len(deleted["scenario_ids"]),
        "deleted_jobs": len(deleted["job_ids"]),
    }
