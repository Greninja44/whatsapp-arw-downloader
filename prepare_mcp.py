"""Apply the complete bridge patch to the pinned upstream checkout."""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UPSTREAM_REVISION = "7d6a06dcdce1f01dfb24f60e1030d5efba9f3b88"


def main():
    checkout = ROOT / "integrations/whatsapp-mcp"
    patch = ROOT / "whatsapp-bridge-local.patch"
    if not (checkout / ".git").exists():
        raise SystemExit("Clone the upstream repository first; see MCP_SETUP.md")
    revision = subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()
    if revision != UPSTREAM_REVISION:
        raise SystemExit(f"Expected upstream revision {UPSTREAM_REVISION}; see MCP_SETUP.md")
    command = ["git", "-C", str(checkout), "apply"]
    if subprocess.run(command + ["--reverse", "--check", str(patch)], capture_output=True).returncode == 0:
        print("Complete patch already applied; preserved local checkout.")
        return
    subprocess.run(command + ["--check", str(patch)], check=True)
    subprocess.run(command + [str(patch)], check=True)
    print("Applied complete local bridge patch.")


if __name__ == "__main__":
    main()
