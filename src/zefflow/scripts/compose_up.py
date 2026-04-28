"""Entry point that delegates to the compose_up.sh shell script."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# Repo root is three levels up from this file: src/zefflow/scripts/compose_up.py
REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "compose_up.sh"


def main() -> int:
    if not SCRIPT_PATH.is_file():
        sys.stderr.write(f"compose_up.sh not found at {SCRIPT_PATH}\n")
        return 1

    # Ensure the script is executable; bash invocation also works regardless.
    os.chmod(SCRIPT_PATH, 0o755)

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH), *sys.argv[1:]],
        cwd=REPO_ROOT,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
