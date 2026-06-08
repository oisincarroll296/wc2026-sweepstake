"""Tournament Bracket — surviving teams at each knockout round, coloured by owner."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st

from dashboard.data import get_match_stats, get_assignments, get_tier_map
from dashboard.config import TIER_COLORS, COLORS
from dashboard.components.ui import page_header, empty_state

page_header("🏟️ Tournament Bracket", "Knockout survivors — coloured by owner")

match_stats = get_match_stats()
assignments = get_assignments()
tier_map    = get_tier_map()

if match_stats.empty:
    empty_state("No match data yet — bracket appears as results are entered.")
    st.stop()

# Map team → list of owners
_owner_map: dict[str, list[str]] = {}
for player, teams in assignments.items():
    for team in teams:
        _owner_map.setdefault(team, []).append(player)

# Player colour palette — assign each player a distinct colour
_all_players = sorted(assignments.keys())
_PALETTE = [
    "#D4A017","#6EE7B7","#93C5FD","#F472B6","#FB923C",
    "#A78BFA","#34D399","#F87171","#38BDF8","#FBBF24",
    "#4ADE80","#E879F9","#22D3EE",
]
_player_color = {p: _PALETTE[i % len(_PALETTE)] for i, p in enumerate(_all_players)}

ROUND_ORDER = ["GroupStage", "R16", "QF", "SF", "Final", "Winner"]
KO_ROUNDS   = ["R16", "QF", "SF", "Final", "Winner"]

# Group teams by their furthest round reached
_by_round: dict[str, list[str]] = {r: [] for r in KO_ROUNDS}
for _, row in match_stats.iterrows():
    team = str(row.get("Team", ""))
    rnd  = str(row.get("RoundReached", "") or "").strip()
    if rnd in KO_ROUNDS:
        _by_round[rnd].append(team)

# Check if any KO teams exist
_any_ko = any(_by_round[r] for r in KO_ROUNDS)
if not _any_ko:
    st.info("No knockout teams yet — bracket will populate as the group stage ends.")
    st.stop()

# Colour legend
st.markdown("**Player colour key:**")
_leg_cols = st.columns(min(len(_all_players), 7))
for _i, _pl in enumerate(_all_players):
    with _leg_cols[_i % len(_leg_cols)]:
        st.markdown(
            f'<span style="background:{_player_color[_pl]};color:#000;'
            f'border-radius:4px;padding:2px 8px;font-size:0.75rem;font-weight:700">{_pl}</span>',
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

def _team_card(team: str):
    owners = _owner_map.get(team, [])
    tier   = tier_map.get(team, 1)
    tc     = TIER_COLORS.get(tier, "#9CA3AF")
    if len(owners) == 1:
        bg = _player_color.get(owners[0], "#1E2937")
        fg = "#000"
    elif owners:
        # Multi-owner: use first owner colour, add indicator
        bg = _player_color.get(owners[0], "#1E2937")
        fg = "#000"
    else:
        bg = "#1E2937"
        fg = "#9CA3AF"

    owner_txt = " · ".join(owners) if owners else "Unowned"
    return (
        f'<div style="background:{bg};border-left:3px solid {tc};border-radius:4px;'
        f'padding:0.35rem 0.6rem;margin-bottom:0.3rem;min-width:120px">'
        f'<div style="color:{fg};font-weight:700;font-size:0.85rem">{team}</div>'
        f'<div style="color:{"#000" if fg == "#000" else "#9CA3AF"};font-size:0.65rem;opacity:0.8">{owner_txt}</div>'
        f'</div>'
    )

# Display rounds from deepest (Winner) to shallowest (R16)
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
