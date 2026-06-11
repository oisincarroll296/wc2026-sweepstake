"""Check both sweepstake repos for live-app updates and pull if anything is new.

Run from anywhere:
    python "c:\\World Cup\\check_and_pull.py"
"""
import subprocess
import sys
from pathlib import Path

REPOS = [
    Path(r"c:\World Cup"),
    Path(r"c:\World Cup Work"),
]


def run(cmd: list[str], cwd: Path) -> str:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return result.stdout.strip()


def check_and_pull(path: Path) -> None:
    print(f"\n{'='*50}")
    print(f"  {path.name}")
    print(f"{'='*50}")

    # Fetch silently
    subprocess.run(["git", "fetch"], cwd=path, capture_output=True)

    # New commits on remote not yet local
    new = run(["git", "log", "HEAD..origin/master", "--oneline", "--no-decorate"], path)

    if not new:
        print("  Up to date.")
        return

    print(f"  {len(new.splitlines())} new commit(s) from live app:")
    for line in new.splitlines():
        # Strip the hash, just show the message
        msg = line.split(" ", 1)[1] if " " in line else line
        print(f"    • {msg}")

    print("\n  Pulling...")
    result = subprocess.run(
        ["git", "pull", "--no-rebase", "-X", "ours"],
        cwd=path, capture_output=True, text=True,
    )
    output = (result.stdout + result.stderr).strip()
    for line in output.splitlines():
        if line.strip():
            print(f"  {line}")
    print("  Done." if result.returncode == 0 else "  Pull failed — check for conflicts.")


for repo in REPOS:
    check_and_pull(repo)

print()
