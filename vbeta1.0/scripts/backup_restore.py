from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
import sqlite3
import time
import zipfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Iterator


ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
BACKUP_SCHEMA_VERSION = 1
MAX_BACKUP_FILES = 100_000
IGNORED_NAMES = {".aplicacao.lock", "app.sqlite3-shm", "app.sqlite3-wal"}
PATH_COLUMNS = {
    "uploads": ("stored_path", "validation_path", "validation_csv_path"),
    "jobs": ("round_dir",),
    "scenario_runs": ("input_path", "changes_path"),
}
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
REPLACE_ATTEMPTS = 8
WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _replace_with_retry(source: Path, destination: Path) -> None:
    """Publica um arquivo/diretório apesar de bloqueios transitórios do Windows."""

    for attempt in range(REPLACE_ATTEMPTS):
        try:
            source.replace(destination)
            return
        except PermissionError:
            if attempt == REPLACE_ATTEMPTS - 1:
                raise
            time.sleep(0.05 * (attempt + 1))


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


def _lock_owner(lock: Path) -> int:
    try:
        return int(lock.read_text(encoding="ascii").strip())
    except (OSError, ValueError):
        return -1


def ensure_application_stopped(data_dir: Path) -> None:
    lock = data_dir / ".aplicacao.lock"
    if not lock.is_file():
        return
    pid = _lock_owner(lock)
    if _process_is_running(pid):
        raise RuntimeError(
            f"A aplicação ainda está usando este diretório de dados (PID {pid})."
        )


@contextmanager
def _reserve_application_stopped(data_dir: Path) -> Iterator[None]:
    """Reserva o mesmo lock exclusivo usado por ``DataDirectoryLock``."""

    lock = data_dir / ".aplicacao.lock"
    descriptor: int | None = None
    owner = str(os.getpid())
    for _ in range(2):
        try:
            descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            pid = _lock_owner(lock)
            if _process_is_running(pid):
                raise RuntimeError(
                    f"A aplicação ainda está usando este diretório de dados (PID {pid})."
                )
            try:
                lock.unlink()
            except OSError as exc:
                raise RuntimeError(
                    "Não foi possível recuperar o bloqueio do diretório de dados."
                ) from exc
            continue
        encoded_owner = owner.encode("ascii")
        try:
            if os.write(descriptor, encoded_owner) != len(encoded_owner):
                raise OSError("Gravação incompleta do lock da aplicação.")
            os.fsync(descriptor)
        except Exception:
            os.close(descriptor)
            descriptor = None
            lock.unlink(missing_ok=True)
            raise
        break
    if descriptor is None:
        raise RuntimeError("Não foi possível reservar o diretório de dados.")
    try:
        yield
    finally:
        os.close(descriptor)
        if _lock_owner(lock) == os.getpid():
            lock.unlink(missing_ok=True)


@contextmanager
def _temporary_directory(parent: Path, prefix: str) -> Iterator[Path]:
    """Cria staging exclusivo sem a regressão de ACL do Python 3.14 RC no Windows."""

    parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    for _ in range(100):
        candidate = parent / f"{prefix}{secrets.token_hex(16)}"
        try:
            if os.name == "nt":
                # No Windows, herdar a ACL do pai é mais seguro do que aplicar
                # mode=0o700, que no Python 3.14 RC pode negar acesso ao criador.
                candidate.mkdir()
            else:
                candidate.mkdir(mode=0o700)
        except FileExistsError:
            continue
        temporary = candidate
        break
    if temporary is None:
        raise FileExistsError("Não foi possível reservar um diretório temporário exclusivo.")
    try:
        yield temporary
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def _portable_files(root: Path, *, include_manifest: bool = False) -> list[Path]:
    files = []
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if path.is_symlink():
            raise ValueError(
                f"Link simbólico não permitido nos dados: {relative.as_posix()}"
            )
        if not path.is_file():
            continue
        if not include_manifest and relative.as_posix() == "backup_manifest.json":
            continue
        files.append(relative)
    return sorted(files, key=lambda item: item.as_posix().casefold())


def _write_deterministic_zip(
    source: Path,
    destination: Path,
    *,
    reservation: tuple[int, int] | None = None,
) -> None:
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    try:
        with zipfile.ZipFile(
            temporary,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as archive:
            for relative in _portable_files(source, include_manifest=True):
                info = zipfile.ZipInfo(
                    relative.as_posix(),
                    date_time=(2020, 1, 1, 0, 0, 0),
                )
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(
                    info,
                    (source / relative).read_bytes(),
                    compresslevel=9,
                )
        if reservation is not None:
            try:
                current = destination.stat()
            except OSError as exc:
                raise FileExistsError(
                    "A reserva do caminho de saída foi removida durante o backup."
                ) from exc
            if (current.st_dev, current.st_ino) != reservation or current.st_size != 0:
                raise FileExistsError(
                    "O caminho de saída foi alterado durante a criação do backup."
                )
        _replace_with_retry(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def create_backup(
    data_dir: Path,
    destination: Path,
    *,
    overwrite: bool = False,
) -> dict[str, object]:
    data_dir = data_dir.expanduser().resolve()
    destination = destination.expanduser().resolve()
    database_path = data_dir / "app.sqlite3"
    if not database_path.is_file():
        raise FileNotFoundError(f"Banco operacional ausente: {database_path}")
    if database_path.is_symlink():
        raise ValueError("O banco operacional não pode ser um link simbólico.")
    try:
        destination.relative_to(data_dir)
    except ValueError:
        pass
    else:
        raise ValueError("O backup deve ser gravado fora do diretório de dados.")

    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not destination.is_file():
        raise FileExistsError(f"A saída do backup não é um arquivo: {destination}")
    reservation: tuple[int, int] | None = None
    if not overwrite:
        try:
            descriptor = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise FileExistsError(
                f"O backup de destino já existe; use --sobrescrever: {destination}"
            ) from exc
        try:
            reserved = os.fstat(descriptor)
            reservation = (reserved.st_dev, reserved.st_ino)
        finally:
            os.close(descriptor)

    try:
        with _reserve_application_stopped(data_dir):
            with _temporary_directory(destination.parent, "vbeta-backup-") as temporary:
                staging = temporary / "payload"
                staging.mkdir()
                source_connection = sqlite3.connect(
                    f"{database_path.as_uri()}?mode=ro",
                    uri=True,
                    timeout=30,
                )
                destination_connection = sqlite3.connect(staging / "app.sqlite3")
                try:
                    source_connection.backup(destination_connection)
                finally:
                    destination_connection.close()
                    source_connection.close()

                for source in data_dir.rglob("*"):
                    if source.name in IGNORED_NAMES or source == database_path:
                        continue
                    relative = source.relative_to(data_dir)
                    if source.is_symlink():
                        raise ValueError(
                            "Link simbólico não permitido nos dados: "
                            f"{relative.as_posix()}"
                        )
                    if not source.is_file():
                        continue
                    target = staging / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)

                entries = [
                    {
                        "caminho": relative.as_posix(),
                        "bytes": (staging / relative).stat().st_size,
                        "sha256": sha256(staging / relative),
                    }
                    for relative in _portable_files(staging)
                ]
                manifest = {
                    "schema_version": BACKUP_SCHEMA_VERSION,
                    "app_version": VERSION,
                    "created_at_utc": datetime.now(timezone.utc).isoformat(),
                    "source_data_dir": str(data_dir),
                    "files": entries,
                }
                (staging / "backup_manifest.json").write_text(
                    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                _write_deterministic_zip(
                    staging,
                    destination,
                    reservation=reservation,
                )
        return manifest
    finally:
        if reservation is not None:
            try:
                current = destination.stat()
            except OSError:
                pass
            else:
                if (current.st_dev, current.st_ino) == reservation:
                    destination.unlink(missing_ok=True)


def _safe_archive_name(name: str) -> PurePosixPath:
    if not isinstance(name, str) or not name or "\\" in name or "\x00" in name:
        raise ValueError(f"Caminho inseguro no backup: {name!r}")
    path = PurePosixPath(name)
    windows_path = PureWindowsPath(name)
    if (
        path.is_absolute()
        or windows_path.is_absolute()
        or bool(windows_path.drive)
        or not path.parts
        or path.as_posix() != name
        or any(part in {"", ".", ".."} for part in path.parts)
        or any(
            ":" in part
            or part.endswith((" ", "."))
            or part.split(".", 1)[0].upper() in WINDOWS_RESERVED_NAMES
            for part in path.parts
        )
    ):
        raise ValueError(f"Caminho inseguro no backup: {name!r}")
    return path


def _extract_and_verify(archive_path: Path, staging: Path) -> dict[str, object]:
    seen: set[str] = set()
    with zipfile.ZipFile(archive_path) as archive:
        archive_items = archive.infolist()
        if len(archive_items) > MAX_BACKUP_FILES:
            raise ValueError("O backup excede o limite de quantidade de arquivos.")
        declared_size = sum(item.file_size for item in archive_items)
        if declared_size > shutil.disk_usage(staging).free:
            raise ValueError("Espaço insuficiente para extrair o backup com segurança.")
        members: list[tuple[zipfile.ZipInfo, PurePosixPath]] = []
        for item in archive_items:
            if item.is_dir():
                raise ValueError(f"Diretório explícito não permitido no backup: {item.filename}")
            relative = _safe_archive_name(item.filename)
            portable = relative.as_posix()
            key = portable.casefold()
            if key in seen:
                raise ValueError(f"Entrada duplicada no backup: {portable}")
            seen.add(key)
            mode = (item.external_attr >> 16) & 0o170000
            if mode == 0o120000:
                raise ValueError(f"Link simbólico não permitido no backup: {portable}")
            if mode not in {0, 0o100000}:
                raise ValueError(f"Tipo de arquivo não permitido no backup: {portable}")
            if item.flag_bits & 0x1:
                raise ValueError(f"Arquivo criptografado não permitido no backup: {portable}")
            members.append((item, relative))

        names = {relative.as_posix().casefold() for _, relative in members}
        for _, relative in members:
            if any(
                parent.as_posix().casefold() in names
                for parent in relative.parents
                if parent.as_posix() != "."
            ):
                raise ValueError(
                    f"Conflito entre arquivo e diretório no backup: {relative.as_posix()}"
                )

        staging_root = staging.resolve()
        for item, relative in members:
            target = staging.joinpath(*relative.parts)
            try:
                target.resolve(strict=False).relative_to(staging_root)
            except ValueError as exc:
                raise ValueError(
                    f"Caminho inseguro no backup: {item.filename!r}"
                ) from exc
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(item) as source, target.open("wb") as destination:
                shutil.copyfileobj(source, destination)

    manifest_path = staging / "backup_manifest.json"
    if not manifest_path.is_file():
        raise ValueError("Manifesto ausente no backup.")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Manifesto ilegível no backup: {exc}") from exc
    if not isinstance(manifest, dict):
        raise ValueError("Estrutura raiz inválida no manifesto do backup.")
    if manifest.get("schema_version") != BACKUP_SCHEMA_VERSION:
        raise ValueError("Versão do formato de backup não suportada.")
    if manifest.get("app_version") != VERSION:
        raise ValueError(
            f"Backup da versão {manifest.get('app_version')!r}; aplicação atual {VERSION!r}."
        )
    source_data_dir = manifest.get("source_data_dir")
    if (
        not isinstance(source_data_dir, str)
        or not source_data_dir
        or not Path(source_data_dir).is_absolute()
    ):
        raise ValueError("Diretório de origem inválido no manifesto do backup.")
    entries = manifest.get("files")
    if not isinstance(entries, list):
        raise ValueError("Lista de arquivos inválida no manifesto do backup.")
    expected: dict[str, dict[str, object]] = {}
    expected_keys: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Entrada de arquivo inválida no manifesto do backup.")
        try:
            relative = _safe_archive_name(entry.get("caminho"))
        except (TypeError, ValueError) as exc:
            raise ValueError("Caminho inválido no manifesto do backup.") from exc
        portable = relative.as_posix()
        key = portable.casefold()
        size = entry.get("bytes")
        digest = entry.get("sha256")
        if (
            key in expected_keys
            or not isinstance(size, int)
            or isinstance(size, bool)
            or size < 0
            or not isinstance(digest, str)
            or SHA256_PATTERN.fullmatch(digest) is None
        ):
            raise ValueError("Entrada duplicada ou inválida no manifesto do backup.")
        expected_keys.add(key)
        expected[portable] = entry
    if "app.sqlite3" not in expected:
        raise ValueError("Banco app.sqlite3 ausente no manifesto do backup.")
    current = {
        relative.as_posix(): {
            "bytes": (staging / relative).stat().st_size,
            "sha256": sha256(staging / relative),
        }
        for relative in _portable_files(staging)
    }
    if set(expected) != set(current):
        raise ValueError("O conjunto de arquivos do backup diverge do manifesto.")
    for name, entry in current.items():
        if expected[name].get("bytes") != entry["bytes"] or expected[name].get("sha256") != entry["sha256"]:
            raise ValueError(f"Integridade inválida no arquivo de backup: {name}")
    return manifest


def _rebase_database(database_path: Path, old_root: Path, new_root: Path) -> int:
    if not database_path.is_file():
        raise ValueError("Banco app.sqlite3 ausente na restauração.")
    old_root = old_root.resolve(strict=False)
    new_root = new_root.resolve(strict=False)
    updated = 0
    try:
        connection = sqlite3.connect(
            f"{database_path.resolve().as_uri()}?mode=rw",
            uri=True,
            timeout=30,
        )
    except sqlite3.DatabaseError as exc:
        raise ValueError(f"Banco SQLite inválido no backup: {exc}") from exc
    try:
        with connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            for table, columns in PATH_COLUMNS.items():
                if table not in tables:
                    continue
                available = {
                    row[1] for row in connection.execute(f"PRAGMA table_info({table})")
                }
                for column in columns:
                    if column not in available:
                        continue
                    rows = connection.execute(
                        f"SELECT rowid, {column} FROM {table} WHERE {column} IS NOT NULL"
                    ).fetchall()
                    for rowid, raw_value in rows:
                        if not isinstance(raw_value, str):
                            continue
                        try:
                            stored_path = Path(raw_value)
                            if not stored_path.is_absolute():
                                continue
                            relative = stored_path.resolve(strict=False).relative_to(old_root)
                        except (OSError, ValueError):
                            continue
                        connection.execute(
                            f"UPDATE {table} SET {column} = ? WHERE rowid = ?",
                            (str(new_root / relative), rowid),
                        )
                        updated += 1
            foreign_key_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
            if foreign_key_errors:
                raise ValueError(f"Backup restaurado viola chaves estrangeiras: {foreign_key_errors}")
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                raise ValueError(f"Falha de integridade SQLite: {integrity}")
    except sqlite3.DatabaseError as exc:
        raise ValueError(f"Banco SQLite inválido no backup: {exc}") from exc
    finally:
        connection.close()
    return updated


def restore_backup(archive_path: Path, data_dir: Path) -> dict[str, object]:
    archive_path = archive_path.expanduser().resolve()
    data_dir = data_dir.expanduser().resolve()
    if not archive_path.is_file():
        raise FileNotFoundError(f"Backup inexistente: {archive_path}")
    ensure_application_stopped(data_dir)
    destination_existed = data_dir.exists()
    if destination_existed:
        if not data_dir.is_dir() or any(data_dir.iterdir()):
            raise FileExistsError(
                "O destino da restauração deve estar vazio para evitar perda de dados."
            )
    data_dir.parent.mkdir(parents=True, exist_ok=True)
    with _temporary_directory(data_dir.parent, "vbeta-restore-") as temporary:
        staging = temporary / "payload"
        staging.mkdir()
        manifest = _extract_and_verify(archive_path, staging)
        source_root = Path(str(manifest["source_data_dir"])).resolve(strict=False)
        updated = _rebase_database(staging / "app.sqlite3", source_root, data_dir)
        (staging / "backup_manifest.json").unlink()

        # Só publica o diretório depois de validar e ajustar todo o payload.
        # O staging fica no mesmo volume do destino para permitir rename atômico.
        if data_dir.exists():
            if any(data_dir.iterdir()):
                raise FileExistsError(
                    "O destino da restauração deixou de estar vazio durante a operação."
                )
            data_dir.rmdir()
        try:
            _replace_with_retry(staging, data_dir)
        except Exception:
            if destination_existed and not data_dir.exists():
                data_dir.mkdir()
            raise
    return {
        "app_version": manifest["app_version"],
        "restored_files": len(manifest["files"]),
        "rebased_paths": updated,
        "data_dir": str(data_dir),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Cria e restaura backups íntegros da vBeta 1.0 com a aplicação encerrada."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    backup = subparsers.add_parser("backup", help="Cria um backup ZIP verificado.")
    backup.add_argument("--dados", type=Path, required=True)
    backup.add_argument("--saida", type=Path, required=True)
    backup.add_argument(
        "--sobrescrever",
        action="store_true",
        help="Substitui explicitamente um ZIP de destino existente.",
    )
    restore = subparsers.add_parser("restore", help="Restaura em um diretório vazio.")
    restore.add_argument("--arquivo", type=Path, required=True)
    restore.add_argument("--dados", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "backup":
        manifest = create_backup(
            args.dados,
            args.saida,
            overwrite=args.sobrescrever,
        )
        print(
            f"Backup criado: {args.saida.resolve()} "
            f"({len(manifest['files'])} arquivos, versão {manifest['app_version']})."
        )
    else:
        result = restore_backup(args.arquivo, args.dados)
        print(
            f"Backup restaurado em {result['data_dir']}: "
            f"{result['restored_files']} arquivos, {result['rebased_paths']} caminhos atualizados."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
