"""
One-off script: backfill score_history.csv from existing match_results.

Replays results day by day, reconstructing match_stats for each date and
running the scoring engine to produce a historical score snapshot.

Run from project root:
    python backfill_score_history.py
"""
import sys, json
from pathlib import Path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import pandas as pd

from src.competition import load_player_status, load_purchases, overall_leaderboard
from src.scoring_engine import load_predictions, load_captains


def _v(row, col, default=0):
    try:
        return int(float(row.get(col, default) or default))
    except (ValueError, TypeError):
        return default


def reconstruct_match_stats(res_subset: pd.DataFrame, teams_df: pd.DataFrame) -> pd.DataFrame:
    """Build a match_stats-compatible DataFrame from a subset of joined match_results."""
    tier_map = {str(r["Team"]): int(r.get("Tier", 4)) for _, r in teams_df.iterrows()}
    all_teams = [str(r["Team"]) for _, r in teams_df.iterrows()]

    STAT_KEYS = [
        "GroupGoals", "GroupCleanSheets", "GroupPenaltyWins", "GroupComebackWins",
        "GroupWinner", "GroupWins", "GroupHatTricks",
        "KnockoutGoals", "KnockoutCleanSheets", "KnockoutPenaltyWins", "KnockoutComebackWins",
        "KnockoutWins", "KnockoutHatTricks",
        "GroupUpsetWins1", "GroupUpsetWins2", "GroupUpsetWins3",
        "KnockoutUpsetWins1", "KnockoutUpsetWins2", "KnockoutUpsetWins3",
        "ShirtRemovals", "GKGoals", "RedCards", "FirstEliminated",
    ]
    stats = {t: {k: 0 for k in STAT_KEYS} | {"RoundReached": ""} for t in all_teams}

    for _, row in res_subset.iterrows():
        home = str(row.get("home_team", "") or "")
        away = str(row.get("away_team", "") or "")
        if not home or not away or home not in stats or away not in stats:
            continue

        hg  = _v(row, "home_goals")
        ag  = _v(row, "away_goals")
        pw  = str(row.get("penalty_winner", "") or "").strip()
        grp = str(row.get("group", "") or "").strip()
        pfx = "Group" if grp else "Knockout"

        # Goals
        stats[home][f"{pfx}Goals"] += hg
        stats[away][f"{pfx}Goals"] += ag

        # Clean sheets
        if ag == 0:
            stats[home][f"{pfx}CleanSheets"] += 1
        if hg == 0:
            stats[away][f"{pfx}CleanSheets"] += 1

        # Winner / loser
        winner = loser = None
        if hg > ag:
            winner, loser = home, away
            stats[home][f"{pfx}Wins"] += 1
        elif ag > hg:
            winner, loser = away, home
            stats[away][f"{pfx}Wins"] += 1
        elif pw:
            winner = pw
            loser  = away if pw == home else home
            stats[pw][f"{pfx}PenaltyWins"] += 1

        # Comeback wins
        if winner == home and _v(row, "comeback_home"):
            stats[home][f"{pfx}ComebackWins"] += 1
        if winner == away and _v(row, "comeback_away"):
            stats[away][f"{pfx}ComebackWins"] += 1

        # Hat tricks
        stats[home][f"{pfx}HatTricks"] += _v(row, "home_hat_tricks")
        stats[away][f"{pfx}HatTricks"] += _v(row, "away_hat_tricks")

        # Special events
        stats[home]["RedCards"]        += _v(row, "home_red_cards")
        stats[away]["RedCards"]        += _v(row, "away_red_cards")
        stats[home]["ShirtRemovals"]   += _v(row, "home_shirt_off")
        stats[away]["ShirtRemovals"]   += _v(row, "away_shirt_off")
        stats[home]["GKGoals"]         += _v(row, "home_gk_goals")
        stats[away]["GKGoals"]         += _v(row, "away_gk_goals")
        stats[home]["FirstEliminated"] += _v(row, "home_first_eliminated")
        stats[away]["FirstEliminated"] += _v(row, "away_first_eliminated")

        # Upset wins: lower-ranked (higher tier number) beats higher-ranked (lower tier number)
        if winner and loser:
            wt   = tier_map.get(winner, 4)
            lt   = tier_map.get(loser, 4)
            diff = wt - lt  # positive means winner has higher tier = worse team won
            if 1 <= diff <= 3:
                stats[winner][f"{pfx}UpsetWins{diff}"] += 1
            elif diff > 3:
                stats[winner][f"{pfx}UpsetWins3"] += 1

    rows = [{"Team": t} | stats[t] for t in all_teams]
    return pd.DataFrame(rows)


def main():
    # ── Load raw sources ─────────────────────────────────────────────────────
    fix = pd.read_csv(ROOT / "data/fixtures.csv", dtype=str).fillna("")
    fix["match_number"] = pd.to_numeric(fix["match_number"], errors="coerce").astype("Int64")
    fix["match_date"]   = pd.to_datetime(fix["match_date"], dayfirst=True, errors="coerce").dt.date

    res = pd.read_csv(ROOT / "data/match_results.csv", dtype=str).fillna("")
    if res.empty:
        print("No match results found — nothing to backfill.")
        return
    res["match_number"] = pd.to_numeric(res["match_number"], errors="coerce").astype("Int64")
    for c in ["home_goals", "away_goals"]:
        res[c] = pd.to_numeric(res[c], errors="coerce").fillna(0).astype(int)
    for c in ["extra_time", "comeback_home", "comeback_away"]:
        res[c] = pd.to_numeric(res[c], errors="coerce").fillna(0).astype(int)

    # Join team names + dates from fixtures
    res = res.merge(
        fix[["match_number", "match_date", "home_team", "away_team", "group"]],
        on="match_number", how="left",
    )
    res = res.dropna(subset=["match_date"]).sort_values("match_date")

    teams_df = pd.read_csv(ROOT / "data/teams.csv", dtype=str).fillna("")
    teams_df["Tier"] = pd.to_numeric(teams_df["Tier"], errors="coerce").fillna(4).astype(int)

    # ── Scoring inputs ───────────────────────────────────────────────────────
    statuses    = load_player_status()
    participants = statuses["Player"].tolist() if not statuses.empty else []
    if not participants:
        print("No players found.")
        return

    alloc_csv = ROOT / "data/allocation.csv"
    alloc_df  = pd.read_csv(alloc_csv, dtype=str).fillna("")
    assignments: dict[str, list[str]] = {}
    for _, r in alloc_df.iterrows():
        assignments.setdefault(str(r["Player"]), []).append(str(r["Team"]))

    purchases   = load_purchases()
    captains    = load_captains()
    predictions = load_predictions()
    tr_path     = ROOT / "data/tournament_results.json"
    tr          = json.loads(tr_path.read_text()) if tr_path.exists() else {}

    # ── Existing history ─────────────────────────────────────────────────────
    history_p = ROOT / "data/score_history.csv"
    if history_p.exists() and history_p.stat().st_size > 20:
        hist = pd.read_csv(history_p, dtype=str)
    else:
        hist = pd.DataFrame(columns=["Date", "Player", "Points"])

    existing_dates = set(hist["Date"].astype(str).tolist())

    # ── Replay day by day ────────────────────────────────────────────────────
    unique_dates = sorted(res["match_date"].dropna().unique())
    new_rows     = []

    for d in unique_dates:
        d_str = str(d)
        if d_str in existing_dates:
            print(f"  {d_str}: already in history, skipping")
            continue

        subset = res[res["match_date"] <= d]
        ms     = reconstruct_match_stats(subset, teams_df)

        lb = overall_leaderboard(
            participants, assignments, ms, purchases, captains, predictions, statuses,
            tournament_results=tr,
        )
        if lb.empty or "TotalPoints" not in lb.columns:
            print(f"  {d_str}: scoring returned empty — skipping")
            continue

        for _, r in lb.iterrows():
            new_rows.append({
                "Date":   d_str,
                "Player": str(r["Player"]),
                "Points": f"{float(r['TotalPoints']):.2f}",
            })
        print(f"  {d_str}: {len(lb)} players snapshotted")

    if not new_rows:
        print("Nothing new to add.")
        return

    hist = pd.concat([hist, pd.DataFrame(new_rows)], ignore_index=True)
    hist = hist.sort_values(["Date", "Player"]).reset_index(drop=True)
    hist.to_csv(history_p, index=False)
    print(f"\nDone — {len(new_rows)} rows written to {history_p}")


if __name__ == "__main__":
    main()
