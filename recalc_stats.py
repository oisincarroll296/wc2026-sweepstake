"""recalc_stats.py — rebuild match_stats.csv and score_history.csv from match_results.csv.

Run after entering results directly or after a git pull:
    python "c:\\World Cup\\recalc_stats.py"
"""
import sys
import json
from pathlib import Path
from datetime import date

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import pandas as pd
from src.team_database import load_teams
from src.scoring_engine import load_match_stats
from src.event_engine import load_allocation
from src.competition import load_player_status, load_purchases, overall_leaderboard
from src.scoring_engine import load_predictions, load_captains

DATA = ROOT / "data"


def _int(val, default=0):
    try:
        return int(float(val or default))
    except Exception:
        return default


# ── Step 1: rebuild match_stats.csv ────────────────────────────────────────────
print("Recalculating match_stats.csv...")

fixtures_p = DATA / "fixtures.csv"
results_p  = DATA / "match_results.csv"

fixtures = pd.read_csv(fixtures_p, dtype=str).fillna("")
results  = pd.read_csv(results_p,  dtype=str).fillna("")
ms       = load_match_stats()

teams_df = load_teams()
tier_map = dict(zip(teams_df["Team"], teams_df["Tier"].astype(int))) if not teams_df.empty else {}

# Ensure columns exist
for col in ["GroupUpsetWins1","GroupUpsetWins2","GroupUpsetWins3",
            "KnockoutUpsetWins1","KnockoutUpsetWins2","KnockoutUpsetWins3",
            "GroupWins","KnockoutWins",
            "ShirtRemovals","GKGoals","RedCards","FirstEliminated",
            "GroupHatTricks","KnockoutHatTricks"]:
    if col not in ms.columns:
        ms[col] = 0

# Zero all auto-derived columns
for col in ["GroupGoals","GroupCleanSheets","GroupPenaltyWins","GroupComebackWins","GroupWins",
            "KnockoutGoals","KnockoutCleanSheets","KnockoutPenaltyWins","KnockoutComebackWins","KnockoutWins",
            "GroupUpsetWins1","GroupUpsetWins2","GroupUpsetWins3",
            "KnockoutUpsetWins1","KnockoutUpsetWins2","KnockoutUpsetWins3",
            "GroupHatTricks","KnockoutHatTricks",
            "ShirtRemovals","GKGoals","RedCards","FirstEliminated"]:
    if col in ms.columns:
        ms[col] = 0

# Reset KO-derived RoundReached (R16+) so it rebuilds from match results below.
# "GroupStage" and "R32" are preserved (manual/group-stage-derived).
_KO_RR_RESET = {"R16", "QF", "SF", "Final", "Winner"}
if "RoundReached" in ms.columns:
    ms.loc[ms["RoundReached"].isin(_KO_RR_RESET), "RoundReached"] = "R32"

_MATCH_TO_CUR_RR = (
    {mn: "R32"  for mn in range(73, 89)}  |
    {mn: "R16"  for mn in range(89, 97)}  |
    {mn: "QF"   for mn in range(97, 101)} |
    {mn: "SF"   for mn in range(101, 103)} |
    {104: "Final"}
)
_MATCH_TO_NEXT_RR = (
    {mn: "R16"   for mn in range(73, 89)}  |
    {mn: "QF"    for mn in range(89, 97)}  |
    {mn: "SF"    for mn in range(97, 101)} |
    {mn: "Final" for mn in range(101, 103)} |
    {104: "Winner"}
)

# Process in match_number order and resolve each fixture's home/away through
# the growing winner_of/loser_of dicts first. A QF fixture's text is itself a
# placeholder like "Winner match 89", and match 89's own fixture text is in
# turn a placeholder referencing an R32 match — resolving in order (instead
# of using the raw fixture text) is what makes R16+ stats actually attribute
# to a real team instead of silently matching no row in ms["Team"].
def _resolve(raw: str, winner_of: dict, loser_of: dict) -> str:
    s = str(raw or "").strip()
    seen = set()
    while (s.startswith("Winner match ") or s.startswith("Runner-up match ")) and s not in seen:
        seen.add(s)
        try:
            mn_ = int(s.split()[-1])
        except ValueError:
            break
        src = winner_of if s.startswith("Winner match ") else loser_of
        nxt = src.get(mn_, s)
        if nxt == s:
            break
        s = nxt
    return s

winner_of: dict[int, str] = {}
loser_of:  dict[int, str] = {}

_results_sorted = results.copy()
_results_sorted["_mn"] = pd.to_numeric(_results_sorted["match_number"], errors="coerce")
_results_sorted = _results_sorted.dropna(subset=["_mn"]).sort_values("_mn")

for _, res in _results_sorted.iterrows():
    mn = _int(res.get("match_number", 0))
    fix_rows = fixtures[pd.to_numeric(fixtures["match_number"], errors="coerce") == mn]
    if fix_rows.empty:
        continue
    fix = fix_rows.iloc[0]
    home = _resolve(str(fix["home_team"]), winner_of, loser_of)
    away = _resolve(str(fix["away_team"]), winner_of, loser_of)
    grp  = str(fix.get("group", "")).strip()
    pfx  = "Group" if grp else "Knockout"

    h_goals = _int(res.get("home_goals", 0))
    a_goals = _int(res.get("away_goals", 0))
    pwin    = str(res.get("penalty_winner", "")).strip()

    for team, gf, ga in [(home, h_goals, a_goals), (away, a_goals, h_goals)]:
        mask = ms["Team"] == team
        if not mask.any():
            continue
        ms.loc[mask, f"{pfx}Goals"]       = ms.loc[mask, f"{pfx}Goals"].astype(int)       + gf
        ms.loc[mask, f"{pfx}CleanSheets"] = ms.loc[mask, f"{pfx}CleanSheets"].astype(int) + (1 if ga == 0 else 0)

    # Win
    if pwin == "home":       win_team = home
    elif pwin == "away":     win_team = away
    elif h_goals > a_goals:  win_team = home
    elif a_goals > h_goals:  win_team = away
    else:                    win_team = None
    if win_team:
        ms.loc[ms["Team"] == win_team, f"{pfx}Wins"] = (
            ms.loc[ms["Team"] == win_team, f"{pfx}Wins"].astype(int) + 1
        )

    # Penalty win (KO only)
    if not grp:
        if pwin == "home":
            ms.loc[ms["Team"] == home, "KnockoutPenaltyWins"] = ms.loc[ms["Team"] == home, "KnockoutPenaltyWins"].astype(int) + 1
        elif pwin == "away":
            ms.loc[ms["Team"] == away, "KnockoutPenaltyWins"] = ms.loc[ms["Team"] == away, "KnockoutPenaltyWins"].astype(int) + 1

    # Comeback wins
    if _int(res.get("comeback_home", 0)):
        ms.loc[ms["Team"] == home, f"{pfx}ComebackWins"] = ms.loc[ms["Team"] == home, f"{pfx}ComebackWins"].astype(int) + 1
    if _int(res.get("comeback_away", 0)):
        ms.loc[ms["Team"] == away, f"{pfx}ComebackWins"] = ms.loc[ms["Team"] == away, f"{pfx}ComebackWins"].astype(int) + 1

    # Upset wins
    loser = None
    if win_team:
        loser = away if win_team == home else home
        w_tier = tier_map.get(win_team, 0)
        l_tier = tier_map.get(loser, 0)
        diff = w_tier - l_tier
        if diff in (1, 2, 3):
            col = f"{pfx}UpsetWins{diff}"
            ms.loc[ms["Team"] == win_team, col] = ms.loc[ms["Team"] == win_team, col].astype(int) + 1

    # Record winner/loser for resolving later placeholder fixtures, and
    # auto-advance RoundReached for both sides of a knockout match.
    if not grp and win_team and loser:
        winner_of[mn] = win_team
        loser_of[mn]  = loser
        _cur_rr  = _MATCH_TO_CUR_RR.get(mn)
        _next_rr = _MATCH_TO_NEXT_RR.get(mn)
        if _next_rr:
            ms.loc[ms["Team"] == win_team, "RoundReached"] = _next_rr
        if _cur_rr:
            ms.loc[ms["Team"] == loser, "RoundReached"] = _cur_rr

    # Special events
    ht_col = f"{pfx}HatTricks"
    for team, side in [(home, "home"), (away, "away")]:
        mask = ms["Team"] == team
        if not mask.any():
            continue
        ms.loc[mask, ht_col]          = ms.loc[mask, ht_col].astype(int)          + _int(res.get(f"{side}_hat_tricks", 0))
        ms.loc[mask, "RedCards"]      = ms.loc[mask, "RedCards"].astype(int)      + _int(res.get(f"{side}_red_cards", 0))
        ms.loc[mask, "ShirtRemovals"] = ms.loc[mask, "ShirtRemovals"].astype(int) + _int(res.get(f"{side}_shirt_off", 0))
        ms.loc[mask, "GKGoals"]       = ms.loc[mask, "GKGoals"].astype(int)       + _int(res.get(f"{side}_gk_goals", 0))
        if _int(res.get(f"{side}_first_eliminated", 0)):
            ms["FirstEliminated"] = 0
            ms.loc[mask, "FirstEliminated"] = 1

ms.to_csv(DATA / "match_stats.csv", index=False)
print(f"  match_stats.csv written ({len(ms)} teams).")


# ── Step 2: snapshot score history ─────────────────────────────────────────────
print("Snapshotting score_history.csv...")

today     = date.today().isoformat()
history_p = DATA / "score_history.csv"
tr_path   = DATA / "tournament_results.json"

statuses     = load_player_status()
participants = statuses["Player"].dropna().tolist() if not statuses.empty else []
if not participants:
    print("  No participants found — skipping score snapshot.")
    sys.exit(0)

alloc       = load_allocation()
assignments = alloc.assignments
tr          = json.loads(tr_path.read_text(encoding="utf-8")) if tr_path.exists() else {}

lb = overall_leaderboard(
    participants, assignments,
    load_match_stats(), load_purchases(), load_captains(), load_predictions(),
    statuses, tournament_results=tr,
)
if lb.empty or "TotalPoints" not in lb.columns:
    print("  Leaderboard empty — skipping score snapshot.")
    sys.exit(0)

if history_p.exists() and history_p.stat().st_size > 20:
    hist = pd.read_csv(history_p, dtype=str)
    hist = hist[hist["Player"].isin(set(participants))]
else:
    hist = pd.DataFrame(columns=["Date", "Player", "Points"])

hist = hist[hist["Date"].astype(str) != today]
new_rows = [
    {"Date": today, "Player": str(r["Player"]), "Points": f"{float(r['TotalPoints']):.2f}"}
    for _, r in lb.iterrows()
]
hist = pd.concat([hist, pd.DataFrame(new_rows)], ignore_index=True)
hist = hist.sort_values(["Date", "Player"]).reset_index(drop=True)
hist.to_csv(history_p, index=False)
print(f"  score_history.csv updated ({today}): {', '.join(r['Player'] for r in new_rows)}")
