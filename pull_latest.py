"""pull_latest.py — pull latest changes from GitHub for both WC and WCW."""
import subprocess
import sys
from pathlib import Path

WC  = Path(r"c:\World Cup")
WCW = Path(r"c:\World Cup Work")


def pull(path: Path) -> None:
    print(f"\n{'='*50}")
    print(f"  {path.name}")
    print(f"{'='*50}")
    result = subprocess.run(
        ["git", "pull"],
        cwd=path, capture_output=True, text=True,
    )
    print(result.stdout.strip() or "(no output)")
    if result.stderr.strip():
        print(result.stderr.strip())
    if result.returncode != 0:
        print(f"ERROR: pull failed in {path}")
        sys.exit(1)


pull(WC)
pull(WCW)
print("\nDone — both repos up to date.")
