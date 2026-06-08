"""Generate fake QF-stage test data for dashboard demonstration."""
import sys, random, csv
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

random.seed(2026)

DATA = ROOT / "data"

# ── QF scenario ──────────────────────────────────────────────────────────────
# 8 teams in QF, 8 eliminated in R16, rest out in group stage / R32
QF_TEAMS  = {"Spain", "France", "Argentina", "Brazil", "England", "Germany", "Morocco", "Norway"}
# Colombia eliminated in group stage — triggers insurance for Harry (who owns Colombia + has insurance)
R16_TEAMS = {"Netherlands", "Belgium", "Portugal", "Croatia", "USA", "Japan", "Uruguay", "South Korea"}
GROUP_WINNERS = {
    "Mexico", "Switzerland", "Brazil", "Germany", "Spain", "France", "Argentina",
    "England", "Belgium", "Portugal", "Netherlands",
    "Norway",  # Norway won Group I — the big upset
}

ROUNDS = {t: "QF" for t in QF_TEAMS}
for t in R16_TEAMS:
    ROUNDS[t] = "R16"

# ── Load teams ────────────────────────────────────────────────────────────────
teams_df = pd.read_csv(DATA / "teams.csv")

def rng(lo, hi): return random.randint(lo, hi)

# ── Build match_stats ─────────────────────────────────────────────────────────
rows = []
for _, row in teams_df.iterrows():
    team = str(row["Team"])
    tier = int(row.get("Tier", 4))
    reached = ROUNDS.get(team, "GroupStage")
    gwinner = 1 if team in GROUP_WINNERS else 0

    # Group stage stats (3 matches)
    if reached == "QF":
        gg, gcs = rng(7, 13), rng(1, 3)
        kg, kcs = rng(3, 6), rng(1, 2)
        gpw, gcw = (rng(0,1) if tier>=3 else 0), rng(0, 1)
        kpw, kcw = 0, rng(0, 1)
    elif reached == "R16":
        gg, gcs = rng(5, 10), rng(1, 3)
        kg, kcs = rng(1, 3), rng(0, 1)
        gpw, gcw = (rng(0,1) if tier>=3 else 0), rng(0, 1)
        kpw, kcw = 0, 0
    else:
        gg, gcs = rng(1, 7), rng(0, 2)
        kg, kcs = 0, 0
        gpw, gcw = 0, 0
        kpw, kcw = 0, 0
        gwinner = 0

    # Norway is the T3 dark horse — give her a scrappy run
    if team == "Norway":
        gg, gcs = 5, 2
        kg, kcs = 3, 1
        gpw, gcw = 0, 1
        kpw, kcw = 1, 0  # penalty win in R16!
        gwinner = 1

    rows.append({
        "Team": team,
        "GroupGoals": gg, "GroupCleanSheets": gcs,
        "GroupPenaltyWins": gpw, "GroupComebackWins": gcw,
        "GroupWinner": gwinner,
        "KnockoutGoals": kg, "KnockoutCleanSheets": kcs,
        "KnockoutPenaltyWins": kpw, "KnockoutComebackWins": kcw,
        "RoundReached": reached,
    })

ms = pd.DataFrame(rows)
ms.to_csv(DATA / "match_stats.csv", index=False)
print(f"✓ match_stats.csv — {len(ms)} teams")

# ── Player status — mark all as PAID ─────────────────────────────────────────
now = "2026-06-01T10:00:00+00:00"
statuses = pd.read_csv(DATA / "player_status.csv")
statuses["Status"] = "PAID"
statuses["PaidTimestamp"] = now
statuses.to_csv(DATA / "player_status.csv", index=False)
print(f"✓ player_status.csv — {len(statuses)} players marked PAID")

# ── Purchases ─────────────────────────────────────────────────────────────────
PLAYERS = statuses["Player"].tolist()
purchases = []

# Everyone buys in
for p in PLAYERS:
    purchases.append({
        "Player": p, "PurchaseType": "BUYIN", "Amount": 5,
        "Reference": f"{p} - BUY IN", "Timestamp": "2026-06-01T10:00:00+00:00",
        "Status": "PROCESSED",
    })

# Most buy prediction pack
pack_players = [p for p in PLAYERS if p not in {"Lobber"}]
for p in pack_players:
    purchases.append({
        "Player": p, "PurchaseType": "PACK", "Amount": 5,
        "Reference": f"{p} - PREDICTION PACK", "Timestamp": "2026-06-01T11:00:00+00:00",
        "Status": "PROCESSED",
    })

# Some buy insurance (Tier 1 owners who might get hit)
insurance_players = ["Aod", "Oisin C", "Moorsey", "Guilly", "Campo", "Harry", "Wheelo"]
for p in insurance_players:
    purchases.append({
        "Player": p, "PurchaseType": "INSURANCE", "Amount": 2,
        "Reference": f"{p} - INSURANCE", "Timestamp": "2026-06-02T09:00:00+00:00",
        "Status": "PROCESSED",
    })

# A few mulligans taken before tournament
for p in ["Jack C", "Lobber"]:
    purchases.append({
        "Player": p, "PurchaseType": "MULLIGAN", "Amount": 3,
        "Reference": f"{p} - MULLIGAN", "Timestamp": "2026-06-08T15:00:00+00:00",
        "Status": "PROCESSED",
    })

# Some ninth teams (post group stage)
for p in ["Oisin E", "Harry", "Ronan"]:
    purchases.append({
        "Player": p, "PurchaseType": "NINTH", "Amount": 3,
        "Reference": f"{p} - NINTH TEAM", "Timestamp": "2026-06-28T16:00:00+00:00",
        "Status": "PROCESSED",
    })

# One resurrection
purchases.append({
    "Player": "Mcgree", "PurchaseType": "RESURRECTION", "Amount": 5,
    "Reference": "Mcgree - RESURRECTION", "Timestamp": "2026-06-28T18:00:00+00:00",
    "Status": "PROCESSED",
})

pd.DataFrame(purchases).to_csv(DATA / "purchases.csv", index=False)
print(f"✓ purchases.csv — {len(purchases)} purchase records")

# ── Captains ──────────────────────────────────────────────────────────────────
captains = [
    # Pre-tournament captains (must be from original 8, best Tier 1)
    {"Player": "Guilly",  "CaptainType": "PreTournament",  "Team": "Spain"},
    {"Player": "Campo",   "CaptainType": "PreTournament",  "Team": "France"},
    {"Player": "Aod",     "CaptainType": "PreTournament",  "Team": "Brazil"},
    {"Player": "Moorsey", "CaptainType": "PreTournament",  "Team": "Argentina"},
    {"Player": "Harry",   "CaptainType": "PreTournament",  "Team": "Argentina"},
    {"Player": "Oisin C", "CaptainType": "PreTournament",  "Team": "Morocco"},
    {"Player": "Ronan",   "CaptainType": "PreTournament",  "Team": "Brazil"},
    {"Player": "Jack C",  "CaptainType": "PreTournament",  "Team": "Argentina"},
    {"Player": "Lobber",  "CaptainType": "PreTournament",  "Team": "Germany"},
    {"Player": "Oisin E", "CaptainType": "PreTournament",  "Team": "England"},
    {"Player": "Wheelo",  "CaptainType": "PreTournament",  "Team": "Portugal"},
    {"Player": "Mcgree",  "CaptainType": "PreTournament",  "Team": "Belgium"},
    {"Player": "Ian",     "CaptainType": "PreTournament",  "Team": "France"},

    # Knockout captains — all 13 players set, must be surviving team, different from pre-tournament
    {"Player": "Guilly",  "CaptainType": "Knockout",  "Team": "England"},
    {"Player": "Campo",   "CaptainType": "Knockout",  "Team": "Germany"},
    {"Player": "Aod",     "CaptainType": "Knockout",  "Team": "Spain"},
    {"Player": "Moorsey", "CaptainType": "Knockout",  "Team": "Morocco"},
    {"Player": "Harry",   "CaptainType": "Knockout",  "Team": "England"},
    {"Player": "Oisin C", "CaptainType": "Knockout",  "Team": "Norway"},
    {"Player": "Ronan",   "CaptainType": "Knockout",  "Team": "Spain"},
    {"Player": "Jack C",  "CaptainType": "Knockout",  "Team": "France"},
    {"Player": "Lobber",  "CaptainType": "Knockout",  "Team": "Brazil"},
    {"Player": "Oisin E", "CaptainType": "Knockout",  "Team": "France"},
    {"Player": "Wheelo",  "CaptainType": "Knockout",  "Team": "Norway"},
    {"Player": "Mcgree",  "CaptainType": "Knockout",  "Team": "Germany"},
    {"Player": "Ian",     "CaptainType": "Knockout",  "Team": "Argentina"},
]
pd.DataFrame(captains).to_csv(DATA / "captains.csv", index=False)
print(f"✓ captains.csv — {len(captains)} captain selections")

# ── Predictions ───────────────────────────────────────────────────────────────
preds = [
    {"Player": "Guilly",  "WorldCupWinner": "Spain",    "GoldenBoot": "Lamine Yamal",    "DarkHorse": "Norway"},
    {"Player": "Campo",   "WorldCupWinner": "France",   "GoldenBoot": "Mbappe",          "DarkHorse": "Norway"},
    {"Player": "Aod",     "WorldCupWinner": "Brazil",   "GoldenBoot": "Vinicius Jr",     "DarkHorse": "Czechia"},
    {"Player": "Moorsey", "WorldCupWinner": "Argentina","GoldenBoot": "Lionel Messi",    "DarkHorse": "Morocco"},
    {"Player": "Harry",   "WorldCupWinner": "Argentina","GoldenBoot": "Lionel Messi",    "DarkHorse": "Algeria"},
    {"Player": "Jack C",  "WorldCupWinner": "Argentina","GoldenBoot": "Julián Álvarez",  "DarkHorse": "Panama"},
    {"Player": "Oisin C", "WorldCupWinner": "Morocco",  "GoldenBoot": "Hakimi",          "DarkHorse": "Norway"},
    {"Player": "Ronan",   "WorldCupWinner": "Brazil",   "GoldenBoot": "Rodrygo",         "DarkHorse": "Scotland"},
    {"Player": "Oisin E", "WorldCupWinner": "England",  "GoldenBoot": "Harry Kane",      "DarkHorse": "Norway"},
    {"Player": "Wheelo",  "WorldCupWinner": "Portugal", "GoldenBoot": "Ronaldo",         "DarkHorse": "Czechia"},
    {"Player": "Mcgree",  "WorldCupWinner": "France",   "GoldenBoot": "Mbappe",          "DarkHorse": "Panama"},
    {"Player": "Ian",     "WorldCupWinner": "France",   "GoldenBoot": "Mbappe",          "DarkHorse": "Egypt"},
]
pd.DataFrame(preds).to_csv(DATA / "predictions.csv", index=False)
print(f"✓ predictions.csv — {len(preds)} prediction records")

# ── Lock predictions ──────────────────────────────────────────────────────────
(DATA / "predictions_lock.txt").write_text("2026-06-11T19:00:00+00:00")
# Remove buyin lock to keep it clean
bl = DATA / "buyin_lock.txt"
if bl.exists(): bl.unlink()
print("✓ predictions locked, buyin lock removed")

# ── Events ────────────────────────────────────────────────────────────────────
events = [
    {"EventID": "EVT001", "EventType": "INITIAL_DRAW",      "Status": "EXECUTED", "Seed": 2026, "ScheduledTime": "2026-06-07T18:00:00+00:00", "ExecutedTime": "2026-06-07T18:05:00+00:00"},
    {"EventID": "EVT002", "EventType": "GROUP_STAGE_CLOSE",  "Status": "EXECUTED", "Seed": "",   "ScheduledTime": "2026-06-27T21:00:00+00:00", "ExecutedTime": "2026-06-27T21:30:00+00:00"},
    {"EventID": "EVT003", "EventType": "NINTH_TEAM_DRAW",    "Status": "EXECUTED", "Seed": 42,   "ScheduledTime": "2026-06-28T16:00:00+00:00", "ExecutedTime": "2026-06-28T16:10:00+00:00"},
    {"EventID": "EVT004", "EventType": "RESURRECTION_DRAW",  "Status": "EXECUTED", "Seed": 99,   "ScheduledTime": "2026-06-28T18:00:00+00:00", "ExecutedTime": "2026-06-28T18:05:00+00:00"},
    {"EventID": "EVT005", "EventType": "TOURNAMENT_COMPLETE","Status": "SCHEDULED","Seed": "",   "ScheduledTime": "2026-07-19T20:00:00+00:00", "ExecutedTime": ""},
]
pd.DataFrame(events).to_csv(DATA / "events.csv", index=False)
print(f"✓ events.csv — {len(events)} events")

# ── Audit log snippet ─────────────────────────────────────────────────────────
audit = [
    {"Timestamp": "2026-06-07T18:05:00+00:00", "Event": "INITIAL_DRAW",     "Player": "ALL",     "Action": "DRAW",    "Result": "OK — 13 players allocated"},
    {"Timestamp": "2026-06-07T18:10:00+00:00", "Event": "BUYIN_LOCK",       "Player": "ALL",     "Action": "LOCK",    "Result": "OK — 13 paid"},
    {"Timestamp": "2026-06-11T19:00:00+00:00", "Event": "PREDICTION_LOCK",  "Player": "ALL",     "Action": "LOCK",    "Result": f"OK — 12 packs submitted"},
    {"Timestamp": "2026-06-27T21:30:00+00:00", "Event": "GROUP_STAGE_CLOSE","Player": "ALL",     "Action": "CLOSE",   "Result": "OK — 32 teams qualify"},
    {"Timestamp": "2026-06-28T16:10:00+00:00", "Event": "NINTH_TEAM_DRAW",  "Player": "Oisin E", "Action": "ASSIGN",  "Result": "Sweden assigned"},
    {"Timestamp": "2026-06-28T16:10:00+00:00", "Event": "NINTH_TEAM_DRAW",  "Player": "Harry",   "Action": "ASSIGN",  "Result": "Austria assigned"},
    {"Timestamp": "2026-06-28T16:10:00+00:00", "Event": "NINTH_TEAM_DRAW",  "Player": "Ronan",   "Action": "ASSIGN",  "Result": "Senegal assigned"},
    {"Timestamp": "2026-06-28T18:05:00+00:00", "Event": "RESURRECTION_DRAW","Player": "Mcgree",  "Action": "ASSIGN",  "Result": "Colombia (T2) → Austria"},
]
pd.DataFrame(audit).to_csv(DATA / "audit_log.csv", index=False)
print(f"✓ audit_log.csv — {len(audit)} records")

# ── A few match results (to show the system works) ────────────────────────────
# Enter 5 recent QF-adjacent fixtures
sample_results = [
    # Group C: Brazil 3-0 Morocco, Scotland 1-2 Brazil, Morocco 4-0 Haiti
    {"match_number": 7,  "home_goals": 3, "away_goals": 1, "extra_time": 0, "penalty_winner": "", "comeback_home": 0, "comeback_away": 0},
    {"match_number": 29, "home_goals": 4, "away_goals": 0, "extra_time": 0, "penalty_winner": "", "comeback_home": 0, "comeback_away": 0},
    {"match_number": 49, "home_goals": 1, "away_goals": 2, "extra_time": 0, "penalty_winner": "", "comeback_home": 1, "comeback_away": 0},
    # Group H: Spain 3-0 Cabo Verde
    {"match_number": 14, "home_goals": 3, "away_goals": 0, "extra_time": 0, "penalty_winner": "", "comeback_home": 0, "comeback_away": 0},
    # Group I: France 2-0 Senegal
    {"match_number": 17, "home_goals": 2, "away_goals": 0, "extra_time": 0, "penalty_winner": "", "comeback_home": 0, "comeback_away": 0},
]
pd.DataFrame(sample_results).to_csv(DATA / "match_results.csv", index=False)
print(f"✓ match_results.csv — {len(sample_results)} results entered")

# ── Score history (cumulative points by gameweek for line chart) ──────────────
# Synthetic trajectory: each player's points grow from 0 to a plausible final score.
# Dates correspond to: after MD1, MD2, MD3, R16, and QF stages.
# Final scores are rough estimates matching our QF scenario.

FINAL_SCORES = {
    "Campo":   176, "Oisin E": 175, "Oisin C": 173, "Guilly": 169,
    "Harry":   155, "Moorsey": 151, "Ronan":   147, "Aod":    143,
    "Ian":     132, "Jack C":  128, "Lobber":  117, "Wheelo": 109, "Mcgree": 98,
}
gameweeks  = ["2026-06-11", "2026-06-18", "2026-06-25", "2026-07-01", "2026-07-09"]
# Fraction of final score earned by each milestone
gw_weights = [0.28, 0.44, 0.59, 0.74, 1.00]

history_rows = []
for player in PLAYERS:
    final = FINAL_SCORES.get(player, 120)
    seed_p = sum(ord(c) for c in player)
    rng_p  = random.Random(2026 + seed_p)
    for gw_date, weight in zip(gameweeks, gw_weights):
        jitter = rng_p.uniform(-0.03, 0.03)
        cum_pts = round(final * max(0.0, weight + jitter), 1)
        history_rows.append({"Date": gw_date, "Player": player, "Points": cum_pts})

pd.DataFrame(history_rows).to_csv(DATA / "score_history.csv", index=False)
print(f"✓ score_history.csv — {len(history_rows)} rows ({len(PLAYERS)} players × {len(gameweeks)} gameweeks)")

print("\n✅ Done! Dashboard is ready for QF-stage demo.")
print(f"   QF teams: {sorted(QF_TEAMS)}")
