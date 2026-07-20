from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    repo_root: Path
    tela_dir: Path
    vbeta_dir: Path
    data_dir: Path
    max_upload_bytes: int = 50 * 1024 * 1024
    max_upload_storage_bytes: int = 500 * 1024 * 1024
    multipart_overhead_bytes: int = 512 * 1024
    orphan_upload_retention_seconds: int = 7 * 24 * 60 * 60
    max_primary_inflight_jobs: int = 2
    max_scenario_inflight_jobs: int = 2
    shutdown_grace_seconds: float = 5.0
    allowed_hosts: tuple[str, ...] = ("localhost", "127.0.0.1", "::1")
    allowed_origins: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        positive = {
            "max_upload_bytes": self.max_upload_bytes,
            "max_upload_storage_bytes": self.max_upload_storage_bytes,
            "max_primary_inflight_jobs": self.max_primary_inflight_jobs,
            "max_scenario_inflight_jobs": self.max_scenario_inflight_jobs,
        }
        invalid = [name for name, value in positive.items() if value <= 0]
        if invalid:
            raise ValueError(
                f"Configurações devem ser positivas: {', '.join(sorted(invalid))}."
            )
        if self.multipart_overhead_bytes < 0:
            raise ValueError("multipart_overhead_bytes não pode ser negativo.")
        if self.orphan_upload_retention_seconds < 0:
            raise ValueError("orphan_upload_retention_seconds não pode ser negativo.")
        if self.shutdown_grace_seconds < 0:
            raise ValueError("shutdown_grace_seconds não pode ser negativo.")
        if not self.allowed_hosts:
            raise ValueError("Ao menos um host local deve ser permitido.")

    @classmethod
    def from_env(cls) -> "Settings":
        # `config.py` lives in vbeta1.0/backend/app. Keeping the application
        # root relative to this file makes the package portable.
        repo_root = Path(__file__).resolve().parents[2]
        tela_dir = repo_root
        data_dir = Path(
            os.environ.get("ALOCACAO_DATA_DIR", tela_dir / "data")
        ).resolve()
        # In production the frontend is served same-origin by the API, so no
        # cross-origin requests occur and this tuple stays empty.  During
        # development with the Vite dev server on a different port, set
        # ALOCACAO_DEV_CORS_ORIGINS to a comma-separated list of origins
        # (e.g. "http://localhost:5173,http://127.0.0.1:5173").
        dev_cors = os.environ.get("ALOCACAO_DEV_CORS_ORIGINS", "")
        allowed_origins = tuple(
            origin.strip()
            for origin in dev_cors.split(",")
            if origin.strip()
        )
        return cls(
            repo_root=repo_root,
            tela_dir=tela_dir,
            vbeta_dir=repo_root / "engines" / "primary",
            data_dir=data_dir,
            allowed_origins=allowed_origins,
            max_upload_bytes=int(
                os.environ.get("ALOCACAO_MAX_UPLOAD_BYTES", 50 * 1024 * 1024)
            ),
            max_upload_storage_bytes=int(
                os.environ.get(
                    "ALOCACAO_UPLOAD_QUOTA_BYTES", 500 * 1024 * 1024
                )
            ),
            orphan_upload_retention_seconds=int(
                os.environ.get(
                    "ALOCACAO_UPLOAD_RETENTION_SECONDS", 7 * 24 * 60 * 60
                )
            ),
            max_primary_inflight_jobs=int(
                os.environ.get("ALOCACAO_MAX_PRIMARY_INFLIGHT", 2)
            ),
            max_scenario_inflight_jobs=int(
                os.environ.get("ALOCACAO_MAX_SCENARIO_INFLIGHT", 2)
            ),
        )

    @property
    def max_request_body_bytes(self) -> int:
        """Multipart framing allowance on top of the actual workbook limit."""
        return self.max_upload_bytes + self.multipart_overhead_bytes

    @property
    def upload_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def result_dir(self) -> Path:
        return self.data_dir / "resultados"

    @property
    def job_dir(self) -> Path:
        return self.data_dir / "jobs"

    @property
    def scenario_engine_dir(self) -> Path:
        return self.repo_root / "engines" / "scenarios"

    @property
    def scenario_dir(self) -> Path:
        return self.data_dir / "cenarios"

    @property
    def scenario_job_dir(self) -> Path:
        return self.scenario_dir / "jobs"

    @property
    def scenario_result_dir(self) -> Path:
        return self.scenario_dir / "resultados"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "app.sqlite3"

    @property
    def frontend_dist(self) -> Path:
        return self.tela_dir / "frontend" / "dist"

    def ensure_directories(self) -> None:
        for path in (
            self.data_dir,
            self.upload_dir,
            self.result_dir,
            self.job_dir,
            self.scenario_dir,
            self.scenario_job_dir,
            self.scenario_result_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)
