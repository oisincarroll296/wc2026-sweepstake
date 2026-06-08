"""Tournament Bracket — surviving teams at each knockout round, coloured by tier."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st

from dashboard.data import get_match_stats, get_assignments, get_tier_map
from dashboard.config import TIER_COLORS
from dashboard.components.ui import page_header, empty_state

page_header("🏟️ Tournament Bracket", "Knockout survivors coloured by tier")

match_stats = get_match_stats()
assignments = get_assignments()
tier_map    = get_tier_map()

if match_stats.empty:
    empty_state("No match data yet — bracket appears as results are entered.")
    st.stop()

# Map team → all owners
_owner_map: dict[str, list[str]] = {}
for player, teams in assignments.items():
    for team in teams:
        _owner_map.setdefault(team, []).append(player)

ROUND_ORDER = ["GroupStage", "R16", "QF", "SF", "Final", "Winner"]
KO_ROUNDS   = ["R16", "QF", "SF", "Final", "Winner"]

_by_round: dict[str, list[str]] = {r: [] for r in KO_ROUNDS}
for _, row in match_stats.iterrows():
    team = str(row.get("Team", ""))
    rnd  = str(row.get("RoundReached", "") or "").strip()
    if rnd in KO_ROUNDS:
        _by_round[rnd].append(team)

_any_ko = any(_by_round[r] for r in KO_ROUNDS)
if not _any_ko:
    st.info("No knockout teams yet — bracket will populate as the group stage ends.")
    st.stop()

# Tier colour legend
TIER_LABELS = {1: "Tier 1", 2: "Tier 2", 3: "Tier 3", 4: "Tier 4"}
_leg = st.columns(4)
for i, (tier, label) in enumerate(TIER_LABELS.items()):
    clr = TIER_COLORS.get(tier, "#9CA3AF")
    with _leg[i]:
        st.markdown(
            f'<span style="background:{clr};color:#fff;border-radius:4px;'
            f'padding:3px 10px;font-size:0.75rem;font-weight:700">{label}</span>',
            unsafe_allow_html=True,
        )

st.divider()

ROUND_LABELS = {
    "R16":    "Round of 16",
    "QF":     "Quarter-Finals",
    "SF":     "Semi-Finals",
    "Final":  "Final",
    "Winner": "Winner 🏆",
}

def _team_card(team: str) -> str:
    tier   = tier_map.get(team, 1)
    bg     = TIER_COLORS.get(tier, "#1E2937")
    owners = _owner_map.get(team, [])
    owner_txt = "  ·  ".join(owners) if owners else "Unowned"
    return (
        f'<div style="background:{bg}22;border-left:4px solid {bg};border-radius:4px;'
        f'padding:0.4rem 0.7rem;margin-bottom:0.35rem">'
        f'<div style="color:#F1F5F9;font-weight:700;font-size:0.9rem">{team}</div>'
        f'<div style="color:#94A3B8;font-size:0.65rem;margin-top:1px">{owner_txt}</div>'
        f'</div>'
    )

for rnd in reversed(KO_ROUNDS):
    teams = _by_round[rnd]
    if not teams:
        continue
    label = ROUND_LABELS.get(rnd, rnd)
    st.markdown(f"### {label}")
    n_cols = min(len(teams), 4)
    cols   = st.columns(n_cols) if n_cols > 1 else [st.container()]
    for i, team in enumerate(sorted(teams)):
        with cols[i % n_cols]:
            st.markdown(_team_card(team), unsafe_allow_html=True)
    st.markdown("")
