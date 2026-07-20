from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath, PureWindowsPath


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "MANIFESTO_RELEASE.json"

EXCLUDED_PARTS = {
    ".git",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "node_modules",
    "release",
}
EXCLUDED_PART_PREFIXES = (".release-scripts-",)
EXCLUDED_FILES = {
    "MANIFESTO_RELEASE.json",
    "MANIFESTO_RELEASE.json.tmp",
}
RUNTIME_PREFIXES = (
    "data/",
    "backend/data/",
    "engines/primary/entrada/",
    "engines/primary/resultados/",
    "engines/scenarios/resultados/",
)
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}


def _manifest_path(root: Path, manifest_path: Path | None) -> Path:
    candidate = (
        root / "MANIFESTO_RELEASE.json"
        if manifest_path is None
        else Path(manifest_path).expanduser()
    )
    if candidate.is_symlink():
        raise SystemExit("Falha de integridade: o manifesto não pode ser um link simbólico.")
    manifest = candidate.resolve(strict=False)
    try:
        manifest.relative_to(root)
    except ValueError as exc:
        raise SystemExit("Falha de integridade: o manifesto deve estar dentro da release.") from exc
    return manifest


def _portable_manifest_path(value: object) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise ValueError
    path = PurePosixPath(value)
    windows_path = PureWindowsPath(value)
    if (
        path.is_absolute()
        or windows_path.is_absolute()
        or bool(windows_path.drive)
        or path.as_posix() != value
        or any(part in {"", ".", ".."} for part in path.parts)
        or any(
            ":" in part
            or part.endswith((" ", "."))
            or part.split(".", 1)[0].upper() in WINDOWS_RESERVED_NAMES
            for part in path.parts
        )
    ):
        raise ValueError
    return path


def relative_files(root: Path = ROOT) -> list[Path]:
    root = Path(root).expanduser().resolve()
    files: list[Path] = []
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        portable = relative.as_posix()
        if any(
            part in EXCLUDED_PARTS or part.startswith(EXCLUDED_PART_PREFIXES)
            for part in relative.parts
        ):
            continue
        if relative.name in EXCLUDED_FILES:
            continue
        if path.is_symlink():
            raise SystemExit(
                f"Falha de integridade: link simbólico não permitido: {portable}"
            )
        if portable == "data/README.md" or portable == "data/.gitkeep":
            files.append(relative)
            continue
        if portable.startswith(RUNTIME_PREFIXES):
            continue
        if not path.is_file():
            continue
        if path.suffix.lower() in {".pyc", ".sqlite3", ".sqlite3-shm", ".sqlite3-wal"}:
            continue
        files.append(relative)
    return sorted(files, key=lambda item: item.as_posix().casefold())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def current_entries(root: Path = ROOT) -> list[dict[str, object]]:
    root = Path(root).expanduser().resolve()
    return [
        {
            "caminho": relative.as_posix(),
            "bytes": (root / relative).stat().st_size,
            "sha256": sha256(root / relative),
        }
        for relative in relative_files(root)
    ]


def generate(
    root: Path = ROOT,
    manifest_path: Path | None = None,
) -> dict[str, object]:
    root = Path(root).expanduser().resolve()
    manifest = _manifest_path(root, manifest_path)
    entries = current_entries(root)
    payload = {
        "schema_version": 1,
        "produto": "Ferramenta de Alocacao Docente",
        "versao": (root / "VERSION").read_text(encoding="utf-8").strip(),
        "algoritmo": "SHA-256",
        "observacao": "Dados operacionais e o proprio manifesto nao integram a soma.",
        "total_arquivos": len(entries),
        "total_bytes": sum(int(entry["bytes"]) for entry in entries),
        "arquivos": entries,
    }
    temporary = manifest.with_name(manifest.name + ".tmp")
    temporary.unlink(missing_ok=True)
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(manifest)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"Manifesto gerado: {len(payload['arquivos'])} arquivos.")
    return payload


def verify(
    root: Path = ROOT,
    manifest_path: Path | None = None,
) -> dict[str, object]:
    root = Path(root).expanduser().resolve()
    manifest = _manifest_path(root, manifest_path)
    if not manifest.is_file():
        raise SystemExit("Manifesto ausente. Execute com --gerar.")
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Falha de integridade: manifesto ilegível ({exc}).") from exc
    if not isinstance(payload, dict):
        raise SystemExit("Falha de integridade: estrutura raiz do manifesto inválida.")
    if payload.get("schema_version") != 1:
        raise SystemExit("Falha de integridade: schema_version do manifesto inválida.")
    current_version = (root / "VERSION").read_text(encoding="utf-8").strip()
    if payload.get("versao") != current_version:
        raise SystemExit("Falha de integridade: versão do manifesto divergente.")
    entries = payload.get("arquivos", [])
    if not isinstance(entries, list):
        raise SystemExit("Falha de integridade: lista de arquivos inválida.")
    validated_entries: list[dict[str, object]] = []
    portable_keys: set[str] = set()
    try:
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError
            path = _portable_manifest_path(entry.get("caminho"))
            portable = path.as_posix()
            key = portable.casefold()
            size = entry.get("bytes")
            digest = entry.get("sha256")
            if (
                key in portable_keys
                or not isinstance(size, int)
                or isinstance(size, bool)
                or size < 0
                or not isinstance(digest, str)
                or SHA256_PATTERN.fullmatch(digest) is None
            ):
                raise ValueError
            portable_keys.add(key)
            validated_entries.append(entry)
    except ValueError as exc:
        raise SystemExit("Falha de integridade: caminhos inválidos ou duplicados no manifesto.")
    expected = {str(entry["caminho"]): entry for entry in validated_entries}
    current = {str(entry["caminho"]): entry for entry in current_entries(root)}
    missing = sorted(set(expected) - set(current))
    unexpected = sorted(set(current) - set(expected))
    changed = sorted(
        path
        for path in set(expected) & set(current)
        if expected[path]["bytes"] != current[path]["bytes"]
        or expected[path]["sha256"] != current[path]["sha256"]
    )
    if missing or unexpected or changed:
        details = []
        if missing:
            details.append(f"ausentes={missing}")
        if unexpected:
            details.append(f"nao registrados={unexpected}")
        if changed:
            details.append(f"alterados={changed}")
        raise SystemExit("Falha de integridade: " + "; ".join(details))
    total_files = payload.get("total_arquivos")
    if (
        not isinstance(total_files, int)
        or isinstance(total_files, bool)
        or total_files != len(current)
    ):
        raise SystemExit("Falha de integridade: total de arquivos divergente.")
    total_bytes = sum(int(entry["bytes"]) for entry in current.values())
    recorded_total_bytes = payload.get("total_bytes")
    if (
        not isinstance(recorded_total_bytes, int)
        or isinstance(recorded_total_bytes, bool)
        or recorded_total_bytes != total_bytes
    ):
        raise SystemExit("Falha de integridade: total de bytes divergente.")
    print(f"Integridade confirmada: {len(current)} arquivos com SHA-256 válido.")
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gera ou verifica o manifesto da vBeta 1.0.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--gerar", action="store_true")
    mode.add_argument("--verificar", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    if arguments.gerar:
        generate()
    else:
        verify()
