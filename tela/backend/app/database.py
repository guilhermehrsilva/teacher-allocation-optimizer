from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    @contextmanager
    def session(self):
        connection = self.connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.session() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS uploads (
                    id TEXT PRIMARY KEY,
                    original_name TEXT NOT NULL,
                    stored_path TEXT NOT NULL,
                    module INTEGER NOT NULL,
                    validation_status TEXT NOT NULL,
                    validation_path TEXT NOT NULL,
                    validation_csv_path TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    upload_id TEXT NOT NULL REFERENCES uploads(id),
                    status TEXT NOT NULL,
                    message TEXT NOT NULL,
                    module INTEGER NOT NULL,
                    require_optimal INTEGER NOT NULL,
                    time_limit_seconds REAL,
                    round_name TEXT,
                    round_dir TEXT,
                    process_id INTEGER,
                    exit_code INTEGER,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_jobs_created_at
                    ON jobs(created_at DESC);

                CREATE TABLE IF NOT EXISTS scenarios (
                    id TEXT PRIMARY KEY,
                    baseline_job_id TEXT NOT NULL REFERENCES jobs(id),
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    promoted_at TEXT
                );

                CREATE TABLE IF NOT EXISTS scenario_changes (
                    id TEXT PRIMARY KEY,
                    scenario_id TEXT NOT NULL REFERENCES scenarios(id) ON DELETE CASCADE,
                    change_type TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    row_number INTEGER NOT NULL,
                    field_name TEXT NOT NULL,
                    old_value_json TEXT NOT NULL,
                    new_value_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(scenario_id, entity_type, row_number, field_name)
                );

                CREATE TABLE IF NOT EXISTS scenario_runs (
                    scenario_id TEXT NOT NULL REFERENCES scenarios(id),
                    job_id TEXT NOT NULL REFERENCES jobs(id),
                    input_path TEXT NOT NULL,
                    changes_path TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (scenario_id, job_id)
                );

                CREATE TABLE IF NOT EXISTS scenario_policies (
                    id TEXT PRIMARY KEY,
                    scenario_id TEXT NOT NULL REFERENCES scenarios(id) ON DELETE CASCADE,
                    policy_type TEXT NOT NULL,
                    target_type TEXT NOT NULL,
                    target_value TEXT NOT NULL,
                    configuration_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(scenario_id, policy_type, target_type, target_value)
                );

                CREATE TABLE IF NOT EXISTS official_results (
                    module INTEGER PRIMARY KEY,
                    job_id TEXT NOT NULL REFERENCES jobs(id),
                    scenario_id TEXT REFERENCES scenarios(id),
                    selected_at TEXT NOT NULL
                );
                """
            )
            job_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(jobs)")
            }
            if "kind" not in job_columns:
                connection.execute(
                    "ALTER TABLE jobs ADD COLUMN kind TEXT NOT NULL DEFAULT 'PRIMARY'"
                )
            if "scenario_id" not in job_columns:
                connection.execute("ALTER TABLE jobs ADD COLUMN scenario_id TEXT")

    def recover_incomplete_jobs(self) -> None:
        now = utc_now()
        with self.session() as connection:
            connection.execute(
                """
                UPDATE jobs
                   SET status = 'INTERROMPIDA',
                       message = 'O servidor foi reiniciado durante esta execução.',
                       updated_at = ?
                 WHERE status IN ('QUEUED', 'RUNNING')
                """,
                (now,),
            )
            connection.execute(
                """
                UPDATE scenarios
                   SET status = 'FALHA', updated_at = ?
                 WHERE status = 'EXECUTANDO'
                """,
                (now,),
            )

    def create_upload(self, payload: dict[str, Any]) -> None:
        with self.session() as connection:
            connection.execute(
                """
                INSERT INTO uploads (
                    id, original_name, stored_path, module, validation_status,
                    validation_path, validation_csv_path, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["id"],
                    payload["original_name"],
                    payload["stored_path"],
                    payload["module"],
                    payload["validation_status"],
                    payload["validation_path"],
                    payload["validation_csv_path"],
                    payload["created_at"],
                ),
            )

    def get_upload(self, upload_id: str) -> dict[str, Any] | None:
        with self.session() as connection:
            row = connection.execute(
                "SELECT * FROM uploads WHERE id = ?", (upload_id,)
            ).fetchone()
        return dict(row) if row else None

    def create_job(self, payload: dict[str, Any]) -> None:
        with self.session() as connection:
            connection.execute(
                """
                INSERT INTO jobs (
                    id, upload_id, status, message, module, require_optimal,
                    time_limit_seconds, kind, scenario_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["id"],
                    payload["upload_id"],
                    payload["status"],
                    payload["message"],
                    payload["module"],
                    int(payload["require_optimal"]),
                    payload.get("time_limit_seconds"),
                    payload.get("kind", "PRIMARY"),
                    payload.get("scenario_id"),
                    payload["created_at"],
                    payload["updated_at"],
                ),
            )

    def update_job(self, job_id: str, **changes: Any) -> None:
        if not changes:
            return
        changes["updated_at"] = utc_now()
        columns = ", ".join(f"{key} = ?" for key in changes)
        values = list(changes.values()) + [job_id]
        with self.session() as connection:
            connection.execute(
                f"UPDATE jobs SET {columns} WHERE id = ?",  # noqa: S608
                values,
            )

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self.session() as connection:
            row = connection.execute(
                """
                SELECT jobs.*, uploads.original_name, uploads.stored_path,
                       uploads.validation_status, uploads.validation_path,
                       uploads.validation_csv_path,
                       EXISTS(
                           SELECT 1 FROM official_results
                            WHERE official_results.job_id = jobs.id
                       ) AS is_official
                  FROM jobs
                  JOIN uploads ON uploads.id = jobs.upload_id
                 WHERE jobs.id = ?
                """,
                (job_id,),
            ).fetchone()
        return dict(row) if row else None

    def list_jobs(
        self,
        limit: int = 100,
        kind: str | None = "PRIMARY",
    ) -> list[dict[str, Any]]:
        with self.session() as connection:
            where = "WHERE jobs.kind = ?" if kind else ""
            parameters: tuple[Any, ...] = (kind, limit) if kind else (limit,)
            rows = connection.execute(
                f"""
                SELECT jobs.*, uploads.original_name, uploads.validation_status,
                       EXISTS(
                           SELECT 1 FROM official_results
                            WHERE official_results.job_id = jobs.id
                       ) AS is_official
                  FROM jobs
                  JOIN uploads ON uploads.id = jobs.upload_id
                 {where}
                 ORDER BY jobs.created_at DESC
                 LIMIT ?
                """,  # noqa: S608 - fragmento SQL interno e controlado
                parameters,
            ).fetchall()
        return [dict(row) for row in rows]

    def create_scenario(self, payload: dict[str, Any]) -> None:
        with self.session() as connection:
            connection.execute(
                """
                INSERT INTO scenarios (
                    id, baseline_job_id, name, description, status,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["id"],
                    payload["baseline_job_id"],
                    payload["name"],
                    payload.get("description", ""),
                    payload["status"],
                    payload["created_at"],
                    payload["updated_at"],
                ),
            )

    def update_scenario(self, scenario_id: str, **changes: Any) -> None:
        if not changes:
            return
        changes["updated_at"] = utc_now()
        columns = ", ".join(f"{key} = ?" for key in changes)
        values = list(changes.values()) + [scenario_id]
        with self.session() as connection:
            connection.execute(
                f"UPDATE scenarios SET {columns} WHERE id = ?",  # noqa: S608
                values,
            )

    def get_scenario(self, scenario_id: str) -> dict[str, Any] | None:
        with self.session() as connection:
            row = connection.execute(
                """
                SELECT scenarios.*,
                       jobs.module,
                       jobs.upload_id,
                       jobs.round_name AS baseline_round,
                       uploads.original_name AS baseline_filename,
                       official_results.job_id AS official_job_id
                  FROM scenarios
                  JOIN jobs ON jobs.id = scenarios.baseline_job_id
                  JOIN uploads ON uploads.id = jobs.upload_id
             LEFT JOIN official_results
                    ON official_results.scenario_id = scenarios.id
                 WHERE scenarios.id = ?
                """,
                (scenario_id,),
            ).fetchone()
        return dict(row) if row else None

    def list_scenarios(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.session() as connection:
            rows = connection.execute(
                """
                SELECT scenarios.*,
                       jobs.module,
                       jobs.round_name AS baseline_round,
                       uploads.original_name AS baseline_filename,
                       official_results.job_id AS official_job_id,
                       (
                           SELECT scenario_runs.job_id
                             FROM scenario_runs
                            WHERE scenario_runs.scenario_id = scenarios.id
                            ORDER BY scenario_runs.created_at DESC
                            LIMIT 1
                       ) AS latest_job_id
                  FROM scenarios
                  JOIN jobs ON jobs.id = scenarios.baseline_job_id
                  JOIN uploads ON uploads.id = jobs.upload_id
             LEFT JOIN official_results
                    ON official_results.scenario_id = scenarios.id
              ORDER BY scenarios.created_at DESC
                 LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def upsert_scenario_change(self, payload: dict[str, Any]) -> None:
        with self.session() as connection:
            connection.execute(
                """
                INSERT INTO scenario_changes (
                    id, scenario_id, change_type, entity_type, row_number,
                    field_name, old_value_json, new_value_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(scenario_id, entity_type, row_number, field_name)
                DO UPDATE SET
                    change_type = excluded.change_type,
                    new_value_json = excluded.new_value_json,
                    created_at = excluded.created_at
                """,
                (
                    payload["id"],
                    payload["scenario_id"],
                    payload["change_type"],
                    payload["entity_type"],
                    payload["row_number"],
                    payload["field_name"],
                    payload["old_value_json"],
                    payload["new_value_json"],
                    payload["created_at"],
                ),
            )

    def list_scenario_changes(self, scenario_id: str) -> list[dict[str, Any]]:
        with self.session() as connection:
            rows = connection.execute(
                """
                SELECT * FROM scenario_changes
                 WHERE scenario_id = ?
              ORDER BY created_at, row_number, field_name
                """,
                (scenario_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def delete_scenario_change(self, scenario_id: str, change_id: str) -> bool:
        with self.session() as connection:
            cursor = connection.execute(
                "DELETE FROM scenario_changes WHERE scenario_id = ? AND id = ?",
                (scenario_id, change_id),
            )
        return cursor.rowcount > 0

    def upsert_scenario_policy(self, payload: dict[str, Any]) -> None:
        with self.session() as connection:
            connection.execute(
                """
                INSERT INTO scenario_policies (
                    id, scenario_id, policy_type, target_type, target_value,
                    configuration_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(scenario_id, policy_type, target_type, target_value)
                DO UPDATE SET
                    configuration_json = excluded.configuration_json,
                    created_at = excluded.created_at
                """,
                (
                    payload["id"], payload["scenario_id"], payload["policy_type"],
                    payload["target_type"], payload["target_value"],
                    payload["configuration_json"], payload["created_at"],
                ),
            )

    def list_scenario_policies(self, scenario_id: str) -> list[dict[str, Any]]:
        with self.session() as connection:
            rows = connection.execute(
                """
                SELECT * FROM scenario_policies
                 WHERE scenario_id = ?
              ORDER BY created_at, policy_type, target_value
                """,
                (scenario_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def delete_scenario_policy(self, scenario_id: str, policy_id: str) -> bool:
        with self.session() as connection:
            cursor = connection.execute(
                "DELETE FROM scenario_policies WHERE scenario_id = ? AND id = ?",
                (scenario_id, policy_id),
            )
        return cursor.rowcount > 0

    def create_scenario_run(self, payload: dict[str, Any]) -> None:
        with self.session() as connection:
            connection.execute(
                """
                INSERT INTO scenario_runs (
                    scenario_id, job_id, input_path, changes_path, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    payload["scenario_id"],
                    payload["job_id"],
                    payload["input_path"],
                    payload["changes_path"],
                    payload["created_at"],
                ),
            )

    def latest_scenario_job(self, scenario_id: str) -> dict[str, Any] | None:
        with self.session() as connection:
            row = connection.execute(
                """
                SELECT jobs.*, uploads.original_name, uploads.stored_path,
                       uploads.validation_status, uploads.validation_path,
                       uploads.validation_csv_path,
                       EXISTS(
                           SELECT 1 FROM official_results
                            WHERE official_results.job_id = jobs.id
                       ) AS is_official
                  FROM scenario_runs
                  JOIN jobs ON jobs.id = scenario_runs.job_id
                  JOIN uploads ON uploads.id = jobs.upload_id
                 WHERE scenario_runs.scenario_id = ?
              ORDER BY scenario_runs.created_at DESC
                 LIMIT 1
                """,
                (scenario_id,),
            ).fetchone()
        return dict(row) if row else None

    def promote_scenario(self, scenario_id: str, job_id: str, module: int) -> None:
        selected_at = utc_now()
        with self.session() as connection:
            previous = connection.execute(
                "SELECT scenario_id FROM official_results WHERE module = ?",
                (module,),
            ).fetchone()
            if previous and previous["scenario_id"] != scenario_id:
                connection.execute(
                    """
                    UPDATE scenarios
                       SET status = 'ARQUIVADO', updated_at = ?
                     WHERE id = ?
                    """,
                    (selected_at, previous["scenario_id"]),
                )
            connection.execute(
                """
                INSERT INTO official_results (module, job_id, scenario_id, selected_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(module) DO UPDATE SET
                    job_id = excluded.job_id,
                    scenario_id = excluded.scenario_id,
                    selected_at = excluded.selected_at
                """,
                (module, job_id, scenario_id, selected_at),
            )
            connection.execute(
                """
                UPDATE scenarios
                   SET status = 'HOMOLOGADO', promoted_at = ?, updated_at = ?
                 WHERE id = ?
                """,
                (selected_at, selected_at, scenario_id),
            )

    def official_job(self, module: int) -> dict[str, Any] | None:
        with self.session() as connection:
            row = connection.execute(
                """
                SELECT jobs.*, uploads.original_name, uploads.stored_path,
                       uploads.validation_status, uploads.validation_path,
                       uploads.validation_csv_path, 1 AS is_official
                  FROM official_results
                  JOIN jobs ON jobs.id = official_results.job_id
                  JOIN uploads ON uploads.id = jobs.upload_id
                 WHERE official_results.module = ?
                """,
                (module,),
            ).fetchone()
        return dict(row) if row else None

    def reset_scenarios(self, scope: str) -> dict[str, Any]:
        if scope not in {"latest", "all"}:
            raise ValueError("Escopo de limpeza inválido.")
        with self.session() as connection:
            query = "SELECT id FROM scenarios ORDER BY created_at DESC"
            if scope == "latest":
                query += " LIMIT 1"
            scenario_ids = [row["id"] for row in connection.execute(query).fetchall()]
            if not scenario_ids:
                return {"scenario_ids": [], "job_ids": [], "primary_job_ids": [], "round_dirs": [], "upload_dirs": []}
            placeholders = ",".join("?" for _ in scenario_ids)
            running = connection.execute(
                f"SELECT COUNT(*) AS total FROM jobs WHERE scenario_id IN ({placeholders}) AND status IN ('QUEUED', 'RUNNING')",  # noqa: S608
                scenario_ids,
            ).fetchone()["total"]
            if running:
                raise ValueError("Não é possível zerar cenários enquanto houver simulação em andamento.")
            jobs = connection.execute(
                f"SELECT id, round_dir FROM jobs WHERE scenario_id IN ({placeholders})",  # noqa: S608
                scenario_ids,
            ).fetchall()
            job_ids = [row["id"] for row in jobs]
            connection.execute(
                f"DELETE FROM official_results WHERE scenario_id IN ({placeholders})",  # noqa: S608
                scenario_ids,
            )
            connection.execute(
                f"DELETE FROM scenario_runs WHERE scenario_id IN ({placeholders})",  # noqa: S608
                scenario_ids,
            )
            if job_ids:
                job_placeholders = ",".join("?" for _ in job_ids)
                connection.execute(
                    f"DELETE FROM jobs WHERE id IN ({job_placeholders})",  # noqa: S608
                    job_ids,
                )
            connection.execute(
                f"DELETE FROM scenarios WHERE id IN ({placeholders})",  # noqa: S608
                scenario_ids,
            )
        return {
            "scenario_ids": scenario_ids,
            "job_ids": job_ids,
            "round_dirs": [row["round_dir"] for row in jobs if row["round_dir"]],
            "upload_dirs": [],
        }

    def reset_primary_jobs(self, scope: str) -> dict[str, Any]:
        if scope not in {"latest", "all"}:
            raise ValueError("Escopo de limpeza inválido.")
        with self.session() as connection:
            query = "SELECT id, upload_id, round_dir FROM jobs WHERE kind = 'PRIMARY' ORDER BY created_at DESC"
            if scope == "latest":
                query += " LIMIT 1"
            primary_jobs = connection.execute(query).fetchall()
            primary_ids = [row["id"] for row in primary_jobs]
            if not primary_ids:
                return {"scenario_ids": [], "job_ids": [], "primary_job_ids": [], "round_dirs": [], "upload_dirs": []}
            primary_placeholders = ",".join("?" for _ in primary_ids)
            scenarios = connection.execute(
                f"SELECT id FROM scenarios WHERE baseline_job_id IN ({primary_placeholders})",  # noqa: S608
                primary_ids,
            ).fetchall()
            scenario_ids = [row["id"] for row in scenarios]
            scenario_jobs = []
            if scenario_ids:
                scenario_placeholders = ",".join("?" for _ in scenario_ids)
                scenario_jobs = connection.execute(
                    f"SELECT id, round_dir FROM jobs WHERE scenario_id IN ({scenario_placeholders})",  # noqa: S608
                    scenario_ids,
                ).fetchall()
            all_job_ids = primary_ids + [row["id"] for row in scenario_jobs]
            all_job_placeholders = ",".join("?" for _ in all_job_ids)
            running = connection.execute(
                f"SELECT COUNT(*) AS total FROM jobs WHERE id IN ({all_job_placeholders}) AND status IN ('QUEUED', 'RUNNING')",  # noqa: S608
                all_job_ids,
            ).fetchone()["total"]
            if running:
                raise ValueError("Não é possível zerar rodadas enquanto houver execução vinculada em andamento.")
            connection.execute(
                f"DELETE FROM official_results WHERE job_id IN ({all_job_placeholders})",  # noqa: S608
                all_job_ids,
            )
            if scenario_ids:
                scenario_placeholders = ",".join("?" for _ in scenario_ids)
                connection.execute(
                    f"DELETE FROM official_results WHERE scenario_id IN ({scenario_placeholders})",  # noqa: S608
                    scenario_ids,
                )
                connection.execute(
                    f"DELETE FROM scenario_runs WHERE scenario_id IN ({scenario_placeholders})",  # noqa: S608
                    scenario_ids,
                )
                connection.execute(
                    f"DELETE FROM scenarios WHERE id IN ({scenario_placeholders})",  # noqa: S608
                    scenario_ids,
                )
            connection.execute(
                f"DELETE FROM jobs WHERE id IN ({all_job_placeholders})",  # noqa: S608
                all_job_ids,
            )
            upload_ids = list(dict.fromkeys(row["upload_id"] for row in primary_jobs))
            upload_dirs: list[str] = []
            deleted_upload_ids: list[str] = []
            for upload_id in upload_ids:
                remaining = connection.execute(
                    "SELECT COUNT(*) AS total FROM jobs WHERE upload_id = ?",
                    (upload_id,),
                ).fetchone()["total"]
                if remaining:
                    continue
                upload = connection.execute(
                    "SELECT stored_path FROM uploads WHERE id = ?", (upload_id,),
                ).fetchone()
                if upload:
                    upload_dirs.append(str(Path(upload["stored_path"]).parent))
                connection.execute("DELETE FROM uploads WHERE id = ?", (upload_id,))
                deleted_upload_ids.append(upload_id)
        return {
            "scenario_ids": scenario_ids,
            "job_ids": all_job_ids,
            "primary_job_ids": primary_ids,
            "round_dirs": [
                row["round_dir"] for row in [*primary_jobs, *scenario_jobs] if row["round_dir"]
            ],
            "upload_dirs": upload_dirs,
            "upload_ids": deleted_upload_ids,
        }
