import hashlib
import json
import re
from pathlib import Path


def is_arw(name: str) -> bool:
    return bool(name and name.strip().lower().endswith(".arw"))


def safe_filename(name: str) -> str:
    # Refuse path traversal instead of silently discarding path components.
    if not is_arw(name) or any(c in name for c in '/\\<>:"|?*') or any(ord(c) < 32 for c in name):
        raise ValueError(f"Unsafe ARW filename: {name!r}")
    name = name.strip()
    if re.match(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", name, re.I):
        raise ValueError(f"Reserved Windows filename: {name}")
    return name


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class DownloadStore:
    def __init__(self, folder: Path):
        self.folder = folder
        folder.mkdir(parents=True, exist_ok=True)
        self.manifest = folder / ".downloads.json"
        self.entries = json.loads(self.manifest.read_text(encoding="utf-8")) if self.manifest.exists() else {}

    def complete(self, key: str) -> bool:
        entry = self.entries.get(key)
        if not entry:
            return False
        path = self.folder / safe_filename(entry["path"])
        return (path.is_file() and path.stat().st_size == entry["size"] > 0
                and sha256(path) == entry["sha256"])

    def destination(self, key: str, name: str) -> Path:
        name = safe_filename(name)
        old = self.entries.get(key)
        if old:
            return self.folder / safe_filename(old["path"])
        occupied = {p.name.casefold() for p in self.folder.iterdir()}
        occupied.update(e["path"].casefold() for e in self.entries.values())
        target = self.folder / name
        count = 2
        while target.name.casefold() in occupied:
            target = self.folder / f"{Path(name).stem} ({count}){Path(name).suffix}"
            count += 1
        return target

    def record(self, key: str, path: Path):
        self.entries[key] = {"path": path.name, "size": path.stat().st_size, "sha256": sha256(path)}
        temporary = self.manifest.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(self.entries, indent=2), encoding="utf-8")
        temporary.replace(self.manifest)
