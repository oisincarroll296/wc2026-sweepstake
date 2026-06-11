"""sync_results.py — copy match data from World Cup to World Cup Work, push both.

Match data files are identical for both sweepstakes (same tournament).
Player/allocation/payment files are app-specific and are NOT touched.

Usage:
    python "c:\\World Cup\\sync_results.py"
"""
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

WC  = Path(r"c:\World Cup")
WCW = Path(r"c:\World Cup Work")

# Files that are match-data — same for both apps
SYNC_FILES = [
    "data/match_results.csv",
    "data/match_stats.csv",
    "data/score_history.csv",
    "data/fixtures.csv",
    "data/tournament_results.json",
    "data/teams.csv",
]


def run(cmd: list[str], cwd: Path) -> bool:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip())
    return result.returncode == 0


def push_repo(path: Path, msg: str) -> bool:
    print(f"\n{'='*50}")
    print(f"  {path.name}")
    print(f"{'='*50}")
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=path, capture_output=True, text=True,
    )
    if not result.stdout.strip():
        print("Nothing to commit — already up to date.")
        return True
    run(["git", "add", "data/"], path)
    run(["git", "commit", "-m", msg], path)
    print("Pulling...")
    if not run(["git", "pull", "--rebase"], path):
        print("ERROR: pull/rebase failed — resolve conflicts manually.")
        return False
    print("Pushing...")
    if not run(["git", "push"], path):
        print("ERROR: push failed.")
        return False
    print("Done.")
    return True


# ── Step 1: sync match data files WC → WCW ─────────────────────────────────
print("Syncing match data: World Cup → World Cup Work")
print("-" * 50)
synced = []
for rel in SYNC_FILES:
    src = WC / rel
    dst = WCW / rel
    if src.exists():
        shutil.copy2(src, dst)
        print(f"  Copied  {rel}")
        synced.append(rel)
    else:
        print(f"  Skipped {rel} (not found in source)")

if not synced:
    print("Nothing to sync — exiting.")
    sys.exit(0)

# ── Step 2: commit + push both repos ───────────────────────────────────────
today = datetime.now().strftime("%Y-%m-%d")
msg = f"Update match results: {today}"

ok_wc  = push_repo(WC, msg)
ok_wcw = push_repo(WCW, msg)

sys.exit(0 if (ok_wc and ok_wcw) else 1)
