from __future__ import annotations

import argparse
import os
import socket
import struct
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = PACKAGE_ROOT / "backend"
VERSION = (PACKAGE_ROOT / "VERSION").read_text(encoding="utf-8").strip()


class DataDirectoryLock:
    """Impede duas instâncias de escreverem no mesmo diretório operacional."""

    def __init__(self, data_dir: Path) -> None:
        self.path = data_dir / ".aplicacao.lock"
        self.file_descriptor: int | None = None

    @staticmethod
    def _process_is_running(pid: int) -> bool:
        if pid <= 0:
            return False
        try:
            os.kill(pid, 0)
        except PermissionError:
            return True
        except OSError:
            return False
        return True

    def __enter__(self) -> "DataDirectoryLock":
        for _ in range(2):
            try:
                self.file_descriptor = os.open(
                    self.path,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                )
            except FileExistsError:
                try:
                    owner = int(self.path.read_text(encoding="ascii").strip())
                except (OSError, ValueError):
                    owner = -1
                if self._process_is_running(owner):
                    raise SystemExit(
                        "Já existe uma instância usando este diretório de dados "
                        f"(PID {owner})."
                    )
                try:
                    self.path.unlink()
                except OSError as exc:
                    raise SystemExit(
                        "Não foi possível recuperar o bloqueio do diretório de dados."
                    ) from exc
                continue
            os.write(self.file_descriptor, str(os.getpid()).encode("ascii"))
            os.fsync(self.file_descriptor)
            return self
        raise SystemExit("Não foi possível reservar o diretório de dados.")

    def __exit__(self, *_: object) -> None:
        if self.file_descriptor is not None:
            os.close(self.file_descriptor)
            self.file_descriptor = None
        try:
            if self.path.read_text(encoding="ascii").strip() == str(os.getpid()):
                self.path.unlink()
        except OSError:
            pass


def default_data_dir() -> Path:
    configured = os.environ.get("ALOCACAO_DATA_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    local_app_data = os.environ.get("LOCALAPPDATA")
    if os.name == "nt" and local_app_data:
        return Path(local_app_data) / "UniCesumar" / "AlocacaoDocente" / "vbeta1.0"
    return PACKAGE_ROOT / "data"


def check_package() -> None:
    required = (
        PACKAGE_ROOT / "frontend" / "dist" / "index.html",
        PACKAGE_ROOT / "engines" / "primary" / "executar_pipeline.py",
        PACKAGE_ROOT / "engines" / "scenarios" / "executar_cenario.py",
        PACKAGE_ROOT / "requirements.lock",
        PACKAGE_ROOT / "SBOM-python.cdx.json",
        PACKAGE_ROOT / "SBOM-frontend.cdx.json",
        PACKAGE_ROOT / "THIRD_PARTY_LICENSES.md",
        PACKAGE_ROOT / "THIRD_PARTY_LICENSES.json",
        PACKAGE_ROOT / "THIRD_PARTY_NOTICES.md",
        PACKAGE_ROOT / "MANIFESTO_RELEASE.json",
    )
    missing = [path.relative_to(PACKAGE_ROOT) for path in required if not path.is_file()]
    if missing:
        rendered = ", ".join(str(path) for path in missing)
        raise SystemExit(f"Pacote incompleto. Arquivos ausentes: {rendered}")
    supported_python = (
        sys.version_info.releaselevel == "final"
        and sys.version_info[:2] in {(3, 12), (3, 13)}
        and struct.calcsize("P") * 8 == 64
    )
    if not supported_python:
        raise SystemExit(
            "A versão 1.0 requer Python 64 bits estável 3.12 ou 3.13."
        )

    from scripts.integridade_release import verify

    verify()


def port_is_available(host: str, port: int) -> bool:
    bind_host = "127.0.0.1" if host in {"localhost", "0.0.0.0"} else host
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind((bind_host, port))
        except OSError:
            return False
    return True


def open_when_ready(url: str) -> None:
    health_url = f"{url}/api/health"
    for _ in range(100):
        try:
            with urllib.request.urlopen(health_url, timeout=1) as response:
                if response.status == 200:
                    webbrowser.open(url)
                    return
        except OSError:
            time.sleep(0.2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inicia a versão 1.0 da Ferramenta de Alocação Docente.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--porta", type=int, default=8000)
    parser.add_argument("--dados", type=Path, default=default_data_dir())
    parser.add_argument("--sem-navegador", action="store_true")
    parser.add_argument("--verificar", action="store_true", help="Valida o pacote sem iniciar o servidor.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    check_package()
    if args.host not in {"127.0.0.1", "localhost"}:
        raise SystemExit(
            "Por segurança, esta aplicação aceita somente --host 127.0.0.1 ou localhost."
        )
    data_dir = args.dados.expanduser().resolve()
    if args.verificar:
        print(f"Versão {VERSION}: pacote íntegro; dados operacionais em {data_dir}")
        return 0
    data_dir.mkdir(parents=True, exist_ok=True)
    os.environ["ALOCACAO_DATA_DIR"] = str(data_dir)
    if not port_is_available(args.host, args.porta):
        raise SystemExit(
            f"A porta {args.porta} já está em uso. Encerre a instância existente ou use --porta."
        )

    sys.path.insert(0, str(BACKEND_DIR))
    import uvicorn
    from app.main import create_app

    browser_host = "127.0.0.1" if args.host == "localhost" else args.host
    url = f"http://{browser_host}:{args.porta}"
    with DataDirectoryLock(data_dir):
        app = create_app()
        if not args.sem_navegador:
            threading.Thread(target=open_when_ready, args=(url,), daemon=True).start()

        print(f"Versão {VERSION} disponível em {url}")
        print(f"Dados operacionais: {data_dir}")
        uvicorn.run(app, host=args.host, port=args.porta, reload=False, workers=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
