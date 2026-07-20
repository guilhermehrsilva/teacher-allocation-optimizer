from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path, PurePosixPath

APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from scripts.integridade_release import ROOT, verify


VERSION_PATTERN = re.compile(r"[0-9A-Za-z][0-9A-Za-z._-]{0,127}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def package_release(
    output_dir: Path,
    *,
    root: Path = ROOT,
    manifest_path: Path | None = None,
) -> tuple[Path, Path, str]:
    root = Path(root).expanduser().resolve()
    manifest = (
        root / "MANIFESTO_RELEASE.json"
        if manifest_path is None
        else Path(manifest_path).expanduser().resolve(strict=False)
    )
    try:
        manifest_relative = manifest.relative_to(root)
    except ValueError as exc:
        raise ValueError("O manifesto deve estar dentro da raiz da release.") from exc
    payload = verify(root=root, manifest_path=manifest)
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    if VERSION_PATTERN.fullmatch(version) is None:
        raise ValueError(f"Versão insegura para nome de arquivo: {version!r}")
    output_dir = output_dir.expanduser().resolve()
    try:
        relative_output = output_dir.relative_to(root)
    except ValueError:
        pass
    else:
        if not relative_output.parts or relative_output.parts[0].casefold() != "release":
            raise ValueError(
                "Dentro da raiz da aplicação, a saída deve ficar sob release/."
            )
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / f"FerramentaAlocacaoDocente-v{version}-windows-x64.zip"
    temporary = archive_path.with_suffix(".zip.tmp")
    temporary.unlink(missing_ok=True)

    members: list[tuple[Path, bytes]] = []
    for entry in payload["arquivos"]:
        portable = str(entry["caminho"])
        relative = Path(*PurePosixPath(portable).parts)
        content = (root / relative).read_bytes()
        if len(content) != entry["bytes"] or hashlib.sha256(content).hexdigest() != entry["sha256"]:
            raise RuntimeError(f"Arquivo mudou durante o empacotamento: {portable}")
        members.append((relative, content))
    manifest_content = manifest.read_bytes()
    try:
        manifest_payload = json.loads(manifest_content)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Manifesto mudou durante o empacotamento: {exc}") from exc
    if manifest_payload != payload:
        raise RuntimeError("Manifesto mudou durante o empacotamento.")
    members.append((manifest_relative, manifest_content))
    members.sort(key=lambda item: item[0].as_posix().casefold())
    portable_names = [relative.as_posix().casefold() for relative, _ in members]
    if len(portable_names) != len(set(portable_names)):
        raise RuntimeError("O pacote produziria entradas duplicadas.")

    try:
        with zipfile.ZipFile(
            temporary,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as archive:
            for relative, content in members:
                info = zipfile.ZipInfo(
                    relative.as_posix(),
                    date_time=(2020, 1, 1, 0, 0, 0),
                )
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, content, compresslevel=9)
        with zipfile.ZipFile(temporary) as archive:
            corrupted = archive.testzip()
        if corrupted is not None:
            raise RuntimeError(f"Arquivo corrompido no pacote gerado: {corrupted}")
        temporary.replace(archive_path)
    finally:
        temporary.unlink(missing_ok=True)
    digest = sha256(archive_path)
    checksum_path = archive_path.with_suffix(archive_path.suffix + ".sha256")
    checksum_temporary = checksum_path.with_name(checksum_path.name + ".tmp")
    checksum_temporary.unlink(missing_ok=True)
    try:
        checksum_temporary.write_text(
            f"{digest}  {archive_path.name}\n",
            encoding="ascii",
        )
        checksum_temporary.replace(checksum_path)
    finally:
        checksum_temporary.unlink(missing_ok=True)
    return archive_path, checksum_path, digest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera o pacote ZIP determinístico e seu checksum SHA-256."
    )
    parser.add_argument("--saida", type=Path, default=ROOT / "release")
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    archive, checksum, digest = package_release(arguments.saida)
    print(f"Release gerada: {archive}")
    print(f"Checksum: {digest}")
    print(f"Arquivo de checksum: {checksum}")
