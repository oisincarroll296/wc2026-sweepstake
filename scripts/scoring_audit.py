"""Scoring audit — verifies every calculation path with known inputs."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from src.scoring_engine import (
    calculate_team_points, calculate_captain_bonus,
    calculate_insurance_bonus, calculate_prediction_points,
    calculate_player_points,
)

errors = []

def check(label, got, expected):
    ok = abs(float(got) - float(expected)) < 1e-9
    status = "PASS" if ok else "FAIL"
    print(f"  {status}  {label}: got {got}, expected {expected}")
    if not ok:
        errors.append(f"{label}: got {got}, expected {expected}")

def ms_row(**kwargs):
    defaults = dict(
        Team="X", GroupGoals=0, GroupCleanSheets=0, GroupPenaltyWins=0,
        GroupComebackWins=0, GroupWinner=0, KnockoutGoals=0,
        KnockoutCleanSheets=0, KnockoutPenaltyWins=0, KnockoutComebackWins=0,
        RoundReached="GroupStage",
        GroupUpsetWins1=0, GroupUpsetWins2=0, GroupUpsetWins3=0,
        KnockoutUpsetWins1=0, KnockoutUpsetWins2=0, KnockoutUpsetWins3=0,
        ShirtRemovals=0, GKGoals=0, RedCards=0, FirstEliminated=0,
    )
    defaults.update(kwargs)
    return pd.DataFrame([defaults])

# -- 1. Group stage match events ----------------------------------------------
print("\n-- 1. Group stage match events --")
r = calculate_team_points("X", ms_row(GroupGoals=3, GroupCleanSheets=2,
                                       GroupPenaltyWins=1, GroupComebackWins=1, GroupWinner=1), 1)
# 3*1 + 2*2 + 1*3 + 1*3 + 3 = 3+4+3+3+3 = 16
check("Group total (goals+CS+pens+comeback+winner)", r["group_stage"], 16)
check("Knockout is 0",      r["knockout"],    0)
check("Special is 0",       r["special"],     0)
check("Total = GS+KO+Sp",   r["total"],       16)

# -- 2. Progression bonuses — cumulative per tier ----------------------------─
print("\n-- 2. Progression bonuses (cumulative) --")
# Each row = total knockout pts earned for a team reaching that round
# T1: R32=1, R16=1+2=3, QF=3+4=7, SF=7+8=15, Final=15+12=27, Winner=27+20=47
# T2: R32=2, R16=2+4=6, QF=6+8=14, SF=14+12=26, Final=26+18=44, Winner=44+28=72
# T3: R32=5, R16=5+8=13, QF=13+15=28, SF=28+20=48, Final=48+32=80, Winner=80+46=126
# T4: R32=8, R16=8+12=20, QF=20+25=45, SF=45+30=75, Final=75+45=120, Winner=120+65=185
expected_totals = {
    1: {"R32": 1,  "R16": 3,  "QF": 7,  "SF": 15, "Final": 27, "Winner": 47},
    2: {"R32": 2,  "R16": 6,  "QF": 14, "SF": 26, "Final": 44, "Winner": 72},
    3: {"R32": 5,  "R16": 13, "QF": 28, "SF": 48, "Final": 80, "Winner": 126},
    4: {"R32": 8,  "R16": 20, "QF": 45, "SF": 75, "Final": 120, "Winner": 185},
}
for tier in (1, 2, 3, 4):
    for rnd, exp in expected_totals[tier].items():
        r = calculate_team_points("X", ms_row(RoundReached=rnd), tier)
        check(f"Tier {tier} reaches {rnd} => {exp}", r["knockout"], exp)

# -- 3. Upset win bonuses ----------------------------------------------------─
print("\n-- 3. Upset win bonuses --")
r = calculate_team_points("X", ms_row(GroupUpsetWins1=1), 2)
check("1x group upset-1 = 15",  r["group_stage"], 15)

r = calculate_team_points("X", ms_row(GroupUpsetWins2=1), 2)
check("1x group upset-2 = 30",  r["group_stage"], 30)

r = calculate_team_points("X", ms_row(GroupUpsetWins3=1), 2)
check("1x group upset-3 = 50",  r["group_stage"], 50)

r = calculate_team_points("X", ms_row(GroupUpsetWins1=1, GroupUpsetWins2=1, GroupUpsetWins3=1), 2)
check("All 3 group upsets = 95", r["group_stage"], 95)

r = calculate_team_points("X", ms_row(KnockoutUpsetWins1=2, KnockoutUpsetWins3=1), 3)
check("2x KO upset-1 + 1x KO upset-3 = 80", r["knockout"], 2*15 + 50)

# -- 4. Special events --------------------------------------------------------
print("\n-- 4. Special events --")
r = calculate_team_points("X", ms_row(ShirtRemovals=1), 1)
check("1 shirt removal = 25",  r["special"], 25)

r = calculate_team_points("X", ms_row(GKGoals=1), 1)
check("1 GK goal = 75",        r["special"], 75)

r = calculate_team_points("X", ms_row(RedCards=1), 1)
check("1 red card = -15",      r["special"], -15)

r = calculate_team_points("X", ms_row(RedCards=3), 1)
check("3 red cards = -45",     r["special"], -45)

r = calculate_team_points("X", ms_row(FirstEliminated=1), 1)
check("First eliminated = 35", r["special"], 35)

r = calculate_team_points("X", ms_row(ShirtRemovals=2, GKGoals=1, RedCards=3, FirstEliminated=1), 1)
# 2*25 + 75 - 3*15 + 35 = 50+75-45+35 = 115
check("Combined special = 115", r["special"], 115)
check("Special NOT in GS",      r["group_stage"], 0)
check("Special NOT in KO",      r["knockout"],    0)

# -- 5. Captain bonus --------------------------------------------------------─
print("\n-- 5. Captain bonus --")
stats = ms_row(Team="Spain", GroupGoals=5, KnockoutGoals=2, RoundReached="QF")
stats["Team"] = "Spain"
team_pts = {"Spain": calculate_team_points("Spain", stats, 1)}
# Spain Tier 1 QF, 5 group goals, 2 KO goals:
#   group_stage = 5, knockout = 2 + R32(1)+R16(2)+QF(4) = 2+7 = 9, special = 0, total = 14
spain_total = team_pts["Spain"]["total"]
spain_ko    = team_pts["Spain"]["knockout"]
check("Spain total pts",   spain_total, 14)
check("Spain knockout pts", spain_ko,   9)

cap_pre = pd.DataFrame([{"Player": "Alice", "CaptainType": "PreTournament", "Team": "Spain"}])
eff = {"group_stage": ["Spain"], "knockout": ["Spain"]}
res = calculate_captain_bonus("Alice", team_pts, cap_pre, eff)
check("Pre-tournament bonus = 0.5×total", res["pre_tournament_bonus"], 0.5 * spain_total)
check("Pre-tournament bonus = 7.0",       res["pre_tournament_bonus"], 7.0)

cap_ko = pd.DataFrame([{"Player": "Alice", "CaptainType": "Knockout", "Team": "Spain"}])
res2 = calculate_captain_bonus("Alice", team_pts, cap_ko, eff)
check("Knockout bonus = 0.5×ko only",    res2["knockout_bonus"], 0.5 * spain_ko)
check("Knockout bonus = 4.5",            res2["knockout_bonus"], 4.5)

# Verify special is included in pre-tournament but not KO captain
stats_sp = ms_row(Team="Brazil", ShirtRemovals=1, RoundReached="R16")
stats_sp["Team"] = "Brazil"
team_pts_sp = {"Brazil": calculate_team_points("Brazil", stats_sp, 1)}
# Brazil: group_stage=0, knockout=R32(1)+R16(2)=3, special=25, total=28
check("Brazil total with special", team_pts_sp["Brazil"]["total"], 28)
cap_pre_sp = pd.DataFrame([{"Player": "Bob", "CaptainType": "PreTournament", "Team": "Brazil"}])
eff_sp = {"group_stage": ["Brazil"], "knockout": ["Brazil"]}
res_sp = calculate_captain_bonus("Bob", team_pts_sp, cap_pre_sp, eff_sp)
check("Pre-tournament includes special (0.5×28=14.0)", res_sp["pre_tournament_bonus"], 14.0)

cap_ko_sp = pd.DataFrame([{"Player": "Bob", "CaptainType": "Knockout", "Team": "Brazil"}])
res_ko_sp = calculate_captain_bonus("Bob", team_pts_sp, cap_ko_sp, eff_sp)
check("KO captain excludes special (0.5×3=1.5)",       res_ko_sp["knockout_bonus"], 1.5)

# -- 6. Insurance ------------------------------------------------------------─
print("\n-- 6. Insurance --")
assignments = {"Alice": ["Spain", "France", "Japan", "Mexico", "Norway", "Egypt", "Qatar", "Haiti"]}
tier_map = {"Spain": 1, "France": 1, "Japan": 2, "Mexico": 2,
            "Norway": 3, "Egypt": 3, "Qatar": 4, "Haiti": 4}

def ms2(*rows):
    base = {c: 0 for c in [
        "GroupGoals","GroupCleanSheets","GroupPenaltyWins","GroupComebackWins","GroupWinner",
        "KnockoutGoals","KnockoutCleanSheets","KnockoutPenaltyWins","KnockoutComebackWins",
        "GroupUpsetWins1","GroupUpsetWins2","GroupUpsetWins3",
        "KnockoutUpsetWins1","KnockoutUpsetWins2","KnockoutUpsetWins3",
        "ShirtRemovals","GKGoals","RedCards","FirstEliminated",
    ]}
    return pd.DataFrame([dict(base, **r) for r in rows])

stats_ins = ms2(
    {"Team": "Spain",  "RoundReached": "GroupStage"},
    {"Team": "France", "RoundReached": "QF"},
)
pur_ins = pd.DataFrame([{"Player": "Alice", "PurchaseType": "Insurance", "Selection": "", "Timestamp": ""}])
pur_none = pd.DataFrame(columns=["Player", "PurchaseType", "Selection", "Timestamp"])

check("1 T1 out (Spain) + Insurance = 25", calculate_insurance_bonus("Alice", assignments, stats_ins, pur_ins, tier_map), 25)
check("1 T1 out no Insurance = 0",         calculate_insurance_bonus("Alice", assignments, stats_ins, pur_none, tier_map), 0)

stats_both = ms2(
    {"Team": "Spain",  "RoundReached": "GroupStage"},
    {"Team": "France", "RoundReached": "GroupStage"},
)
check("2 T1 out + Insurance = 50",  calculate_insurance_bonus("Alice", assignments, stats_both, pur_ins, tier_map), 50)

stats_r16 = ms2({"Team": "Spain", "RoundReached": "R16"}, {"Team": "France", "RoundReached": "QF"})
check("T1 out in R16 = no insurance", calculate_insurance_bonus("Alice", assignments, stats_r16, pur_ins, tier_map), 0)

stats_r32 = ms2({"Team": "Spain", "RoundReached": "R32"}, {"Team": "France", "RoundReached": "QF"})
check("T1 out at R32 + Insurance = 25", calculate_insurance_bonus("Alice", assignments, stats_r32, pur_ins, tier_map), 25)

# -- 7. Prediction points ----------------------------------------------------─
print("\n-- 7. Prediction points --")
preds = pd.DataFrame([{
    "Player": "Alice",
    "WorldCupWinner": "Brazil",
    "RunnerUp": "France",
    "BronzeMedal": "Spain",
    "GoldenBoot": "Mbappe",
    "DarkHorse": "Norway",
    "FirstKnockedOut": "Qatar",
}])
tr = {
    "world_cup_winner": "Brazil",
    "runner_up": "France",
    "bronze_winner": "Spain",
    "golden_boot_winner": "Mbappe",
    "first_knocked_out": "Qatar",
    "dark_horse_rounds": {"Norway": "SF"},
}
p = calculate_prediction_points("Alice", preds, tr)
check("Winner correct +30",          p["winner_bonus"],             30)
check("Runner-up correct +20",       p["runner_up_bonus"],          20)
check("Bronze correct +15",          p["bronze_bonus"],             15)
check("Golden boot correct +25",     p["golden_boot_bonus"],        25)
check("First KO correct +20",        p["first_knocked_out_bonus"],  20)
# Dark horse Norway reaches SF: QF(15) + SF(30) = 45
check("Dark horse SF = 45",          p["dark_horse_bonus"],         45)
check("Prediction total = 155",      p["total"],                    155)

# All wrong = 0
preds_wrong = pd.DataFrame([{
    "Player": "Bob", "WorldCupWinner": "Germany", "RunnerUp": "Italy",
    "BronzeMedal": "England", "GoldenBoot": "Ronaldo",
    "DarkHorse": "Egypt", "FirstKnockedOut": "Morocco",
}])
p2 = calculate_prediction_points("Bob", preds_wrong, tr)
check("All wrong = 0",              p2["total"], 0)

# Dark horse reaches Winner: 15+30+40+50 = 135
tr2 = {"dark_horse_rounds": {"Norway": "Winner"}}
preds3 = pd.DataFrame([{"Player": "Alice", "DarkHorse": "Norway",
                          "WorldCupWinner": "", "RunnerUp": "", "BronzeMedal": "",
                          "GoldenBoot": "", "FirstKnockedOut": ""}])
p3 = calculate_prediction_points("Alice", preds3, tr2)
check("Dark horse Winner = 135",    p3["dark_horse_bonus"], 135)

# Dark horse only reaches QF = 15
tr3 = {"dark_horse_rounds": {"Norway": "QF"}}
p4 = calculate_prediction_points("Alice", preds3, tr3)
check("Dark horse QF = 15",         p4["dark_horse_bonus"], 15)

# -- 8. Grand total wires up --------------------------------------------------
print("\n-- 8. Grand total integration --")
assignments2 = {"Alice": ["Norway"]}
ms3 = pd.DataFrame([{
    "Team": "Norway", "GroupGoals": 2, "GroupCleanSheets": 1, "GroupPenaltyWins": 0,
    "GroupComebackWins": 1, "GroupWinner": 0, "KnockoutGoals": 1,
    "KnockoutCleanSheets": 0, "KnockoutPenaltyWins": 0, "KnockoutComebackWins": 0,
    "RoundReached": "QF",
    "GroupUpsetWins1": 1, "GroupUpsetWins2": 0, "GroupUpsetWins3": 0,
    "KnockoutUpsetWins1": 0, "KnockoutUpsetWins2": 0, "KnockoutUpsetWins3": 0,
    "ShirtRemovals": 1, "GKGoals": 0, "RedCards": 1, "FirstEliminated": 0,
}])
# Norway Tier 3 QF:
#   group_stage = 2*1 + 1*2 + 1*3 + 1*15(upset1) = 2+2+3+15 = 22
#   knockout    = 1*1 + R32(5)+R16(8)+QF(15) = 1+28 = 29
#   special     = 1*25 - 1*15 = 10
#   grand_total = 22 + 29 + 10 = 61
empty_caps  = pd.DataFrame(columns=["Player", "CaptainType", "Team"])
empty_purch = pd.DataFrame(columns=["Player", "PurchaseType", "Selection", "Timestamp"])
empty_preds = pd.DataFrame([{"Player": "Alice", "WorldCupWinner": "", "RunnerUp": "",
                              "BronzeMedal": "", "GoldenBoot": "", "DarkHorse": "",
                              "FirstKnockedOut": ""}])
info = calculate_player_points("Alice", assignments2, ms3, empty_purch, empty_caps, empty_preds,
                               tournament_results={}, tier_map={"Norway": 3})
check("Norway GS pts = 22",  info["group_stage_points"], 22)
check("Norway KO pts = 29",  info["knockout_points"],    29)
check("Norway special = 10", info["special_bonus"],      10)
check("Grand total = 61",    info["grand_total"],         61)

# -- 9. Edge cases ------------------------------------------------------------
print("\n-- 9. Edge cases --")
r = calculate_team_points("X", ms_row(RoundReached="GroupStage"), 1)
check("GroupStage only = no KO progression", r["knockout"], 0)

r = calculate_team_points("UNKNOWN", pd.DataFrame(columns=ms_row().columns), 1)
check("Unknown team = all zeros", r["total"], 0)

empty_preds2 = pd.DataFrame(columns=["Player","WorldCupWinner","RunnerUp","BronzeMedal","GoldenBoot","DarkHorse","FirstKnockedOut"])
p5 = calculate_prediction_points("Alice", empty_preds2, tr)
check("No predictions = 0 bonus", p5["total"], 0)

p6 = calculate_prediction_points("Alice", preds, {})
check("No tournament results = 0 bonus", p6["total"], 0)

# -- Summary ------------------------------------------------------------------
print(f"\n{'='*55}")
if errors:
    print(f"FAILED ({len(errors)}):")
    for e in errors:
        print(f"  - {e}")
else:
    print(f"All checks passed.")
