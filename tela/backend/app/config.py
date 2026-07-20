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

    @classmethod
    def from_env(cls) -> "Settings":
        repo_root = Path(__file__).resolve().parents[3]
        tela_dir = repo_root / "tela"
        data_dir = Path(
            os.environ.get("ALOCACAO_DATA_DIR", tela_dir / "data")
        ).resolve()
        return cls(
            repo_root=repo_root,
            tela_dir=tela_dir,
            vbeta_dir=repo_root / "vbeta",
            data_dir=data_dir,
        )

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
        return self.repo_root / "scenario_engine"

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
