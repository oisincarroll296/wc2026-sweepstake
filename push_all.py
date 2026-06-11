"""Push both sweepstake repos to GitHub.

Run from anywhere:
    python "c:\\World Cup\\push_all.py"
"""
import subprocess
import sys
from pathlib import Path

REPOS = [
    Path(r"c:\World Cup"),
    Path(r"c:\World Cup Work"),
]


def run(cmd: list[str], cwd: Path) -> bool:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip())
    return result.returncode == 0


def push_repo(path: Path) -> bool:
    print(f"\n{'='*50}")
    print(f"  {path}")
    print(f"{'='*50}")

    # Check for uncommitted changes
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=path, capture_output=True, text=True,
    )
    dirty = result.stdout.strip()
    if dirty:
        print("Uncommitted changes — staging data/ and committing...")
        run(["git", "add", "data/"], path)
        run(["git", "commit", "-m", "Auto-push: sync data files"], path)

    # Pull then push
    print("Pulling...")
    if not run(["git", "pull", "--no-rebase", "-X", "ours"], path):
        print("ERROR: pull failed — resolve conflicts manually.")
        return False

    print("Pushing...")
    if not run(["git", "push"], path):
        print("ERROR: push failed.")
        return False

    print("Done.")
    return True


ok = all(push_repo(r) for r in REPOS)
sys.exit(0 if ok else 1)
