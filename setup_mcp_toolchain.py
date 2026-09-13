"""Download portable official Go and Zig distributions with SHA-256 verification."""
import hashlib
import json
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "toolchain"
ROOT.mkdir(exist_ok=True)


def fetch_json(url):
    with urllib.request.urlopen(url, timeout=60) as response:
        return json.load(response)


def install(url, expected):
    target = ROOT / url.rsplit("/", 1)[-1]
    if not target.exists():
        print(f"Downloading {target.name}", flush=True)
        with urllib.request.urlopen(url, timeout=120) as response, target.open("wb") as out:
            while block := response.read(1024 * 1024):
                out.write(block)
    if hashlib.file_digest(target.open("rb"), "sha256").hexdigest() != expected:
        raise RuntimeError(f"Checksum mismatch: {target}")
    print(f"Verified {target.name}; extracting", flush=True)
    with zipfile.ZipFile(target) as archive:
        archive.extractall(ROOT)


go = next(v for v in fetch_json("https://go.dev/dl/?mode=json") if v["stable"])
asset = next(f for f in go["files"] if f["os"] == "windows" and f["arch"] == "amd64" and f["kind"] == "archive")
if not (ROOT / "go/bin/go.exe").exists():
    install("https://go.dev/dl/" + asset["filename"], asset["sha256"])
zig = fetch_json("https://ziglang.org/download/index.json")["0.14.1"]["x86_64-windows"]
if not (ROOT / "zig-x86_64-windows-0.14.1/zig.exe").exists():
    install(zig["tarball"], zig["shasum"])
print("Portable Go and Zig ready", flush=True)
