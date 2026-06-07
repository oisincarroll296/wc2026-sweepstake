"""Player Portfolios — per-player deep-dive."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from dashboard.data import (
    get_participants, get_assignments, get_match_stats, get_purchases,
    get_captains, get_predictions, get_statuses, get_tier_map,
    is_predictions_locked,
)
from dashboard.config import TIER_COLORS, PLOTLY_LAYOUT
from dashboard.components.ui import page_header, empty_state, tier_badge


page_header("Player Portfolios", "Per-player team breakdown and points")

participants = get_participants()
if not participants:
    empty_state("No participants yet.")
    st.stop()

# ── URL param: ?player=Name lets players bookmark their own page ───────────
url_player = st.query_params.get("player", "")
default_idx = participants.index(url_player) if url_player in participants else 0

player = st.selectbox("Select Player", participants, index=default_idx)
if not player:
    st.stop()

# Keep URL in sync so the current player is always bookmarkable
st.query_params["player"] = player

# Shareable link hint (shown once, collapsed)
with st.expander("My Teams link", expanded=False):
    st.caption(
        "Bookmark or share this URL — it opens straight to your portfolio:"
    )
    st.code(f"?player={player}", language=None)
    st.caption("Append the above to your dashboard URL, e.g. `http://192.168.1.42:8501/player_portfolios?player={}`".format(player))

assignments  = get_assignments()
match_stats  = get_match_stats()
purchases    = get_purchases()
captains     = get_captains()
predictions  = get_predictions()
statuses     = get_statuses()
tier_map     = get_tier_map()
pred_locked  = is_predictions_locked()

from src.scoring_engine import (
    calculate_player_points, get_effective_teams, calculate_team_points,
)
from src.competition import purchases_to_scoring_format

scoring_purch = purchases_to_scoring_format(purchases)
eff   = get_effective_teams(player, assignments, scoring_purch)
result = calculate_player_points(
    player, assignments, match_stats, scoring_purch,
    captains, predictions, tier_map=tier_map,
)

# Payment status
status_val = "UNPAID"
if not statuses.empty and player in statuses["Player"].values:
    status_val = statuses.loc[statuses["Player"] == player, "Status"].iloc[0]

grand_total   = result.get("grand_total", 0.0)
base_total    = result.get("base_total", 0.0)
captain_bonus = result.get("captain", {}).get("total", 0.0)
insurance_pts = result.get("insurance_bonus", 0.0)

# ── Summary metrics ────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
with c1: st.metric("Total Points",   f"{grand_total:.0f}")
with c2: st.metric("Base Points",    f"{base_total:.0f}")
with c3: st.metric("Captain Bonus",  f"+{captain_bonus:.0f}")
with c4: st.metric("Insurance",      f"+{insurance_pts:.0f}")
with c5:
    paid_colour = "normal" if status_val == "PAID" else "off"
    st.metric("Status", status_val, delta=None)

st.divider()

# Captain sets for this player
pre_cap_team = kn_cap_team = ""
if not captains.empty:
    pc = captains[(captains["Player"] == player) & (captains["CaptainType"] == "PreTournament")]
    kc = captains[(captains["Player"] == player) & (captains["CaptainType"] == "Knockout")]
    pre_cap_team = pc.iloc[0]["Team"] if not pc.empty else ""
    kn_cap_team  = kc.iloc[0]["Team"] if not kc.empty else ""

# Round Reached helper
ROUND_LABELS = {
    "GroupStage": "Eliminated (Groups)",
    "R16":        "Eliminated (R16)",
    "QF":         "Eliminated (QF)",
    "SF":         "Eliminated (SF)",
    "Final":      "Runner-up",
    "Winner":     "Champion",
    "":           "Active",
}

def _round_reached(team: str) -> str:
    if match_stats.empty:
        return ""
    row = match_stats[match_stats["Team"] == team]
    if row.empty:
        return ""
    return str(row.iloc[0].get("RoundReached", "") or "")

def _is_eliminated(rnd: str) -> bool:
    return rnd in ("GroupStage", "R16", "QF", "SF", "Final")

# ── Two-column layout ──────────────────────────────────────────────────────
col_teams, col_extras = st.columns([3, 2], gap="large")

with col_teams:
    st.subheader("Teams & Points")

    all_teams = list(dict.fromkeys(eff["group_stage"] + eff["knockout"]))
    team_rows = []
    for team in all_teams:
        tier  = tier_map.get(team, 1)
        rnd   = _round_reached(team)
        eliminated = _is_eliminated(rnd)
        in_gs = team in eff["group_stage"]
        in_ko = team in eff["knockout"]

        # Stage label
        if in_gs and in_ko:
            stage = "Group + KO"
        elif in_ko:
            stage = "KO only"
        else:
            stage = "Group"

        # Captain marker
        cap_label = ""
        if team == pre_cap_team and team == kn_cap_team:
            cap_label = "Pre + KO"
        elif team == pre_cap_team:
            cap_label = "Pre-Tournament"
        elif team == kn_cap_team:
            cap_label = "Knockout"

        tp = calculate_team_points(team, match_stats, tier) if not match_stats.empty else {"total": 0}

        team_rows.append({
            "Team":     team,
            "T":        f"T{tier}",
            "Status":   ROUND_LABELS.get(rnd, "Active"),
            "Stage":    stage,
            "Captain":  cap_label,
            "Pts":      f"{tp['total']:.0f}",
        })

    team_df = pd.DataFrame(team_rows)

    def _team_style(row):
        status = row.get("Status", "")
        if status == "Champion":
            return ["background-color: rgba(212,160,23,0.2); font-weight:700"] * len(row)
        if "Eliminated" in status:
            return ["color: #6B7280"] * len(row)
        return [""] * len(row)

    st.dataframe(
        team_df.style.apply(_team_style, axis=1),
        use_container_width=True, hide_index=True,
    )

    # Points bar chart
    numeric_pts = [float(r["Pts"]) for r in team_rows]
    if any(p > 0 for p in numeric_pts):
        st.subheader("Points by Team")
        fig = go.Figure(go.Bar(
            x=[r["Team"] for r in team_rows],
            y=numeric_pts,
            marker_color=[TIER_COLORS.get(tier_map.get(r["Team"], 1), "#9CA3AF") for r in team_rows],
            hovertemplate="%{x}: %{y} pts<extra></extra>",
        ))
        fig.update_layout(**PLOTLY_LAYOUT, title="Points by Team", height=300)
        st.plotly_chart(fig, use_container_width=True)

    # Points by tier donut
    tier_totals: dict[int, float] = {}
    for r in team_rows:
        t = int(r["T"][1])
        tier_totals[t] = tier_totals.get(t, 0) + float(r["Pts"])
    if any(v > 0 for v in tier_totals.values()):
        st.subheader("Points by Tier")
        fig2 = go.Figure(go.Pie(
            labels=[f"Tier {k}" for k in sorted(tier_totals)],
            values=[tier_totals[k] for k in sorted(tier_totals)],
            marker_colors=[TIER_COLORS.get(k) for k in sorted(tier_totals)],
            hole=0.5,
            hovertemplate="%{label}: %{value:.0f} pts<extra></extra>",
        ))
        fig2.update_layout(**PLOTLY_LAYOUT, height=280)
        st.plotly_chart(fig2, use_container_width=True)

with col_extras:
    st.subheader("Portfolio Details")

    def _sel(ptype):
        if purchases.empty:
            return "—"
        rows = purchases[
            (purchases["Player"] == player) &
            (purchases["PurchaseType"] == ptype) &
            (purchases["Status"] == "PROCESSED")
        ]
        return rows.iloc[0]["Selection"] if not rows.empty else "—"

    has_ins = not purchases.empty and not purchases[
        (purchases["Player"] == player) &
        (purchases["PurchaseType"] == "INSURANCE") &
        (purchases["Status"] == "PROCESSED")
    ].empty

    # Predictions — only shown after lock
    if pred_locked:
        if not predictions.empty and player in predictions["Player"].values:
            pred_row = predictions[predictions["Player"] == player].iloc[0]
            pp_winner = pred_row.get("WorldCupWinner", "—") or "—"
            pp_golden = pred_row.get("GoldenBoot", "—") or "—"
            pp_dark   = pred_row.get("DarkHorse", "—") or "—"
        else:
            pp_winner = pp_golden = pp_dark = "—"
        pred_badge = "Revealed"
    else:
        pp_winner = pp_golden = pp_dark = "Hidden until lock"
        pred_badge = "Hidden"

    details = [
        ("Pre-Tournament Captain", pre_cap_team or "—"),
        ("Knockout Captain",       kn_cap_team or "—"),
        ("Insurance",              "Active" if has_ins else "No"),
        ("Ninth Team",             _sel("NINTH")),
        ("Resurrection",           _sel("RESURRECTION")),
        ("WC Winner Pick",         pp_winner),
        ("Golden Boot Pick",       pp_golden),
        ("Dark Horse",             pp_dark),
    ]

    for label, val in details:
        is_hidden = val == "Hidden until lock"
        val_colour = "#9CA3AF" if is_hidden else "#F5F5F5"
        st.markdown(
            f'<div class="card" style="display:flex;justify-content:space-between;'
            f'align-items:center;padding:0.45rem 0.75rem;margin-bottom:0.3rem">'
            f'<span style="color:#9CA3AF;font-size:0.82rem">{label}</span>'
            f'<span style="color:{val_colour};font-size:0.82rem;font-weight:600">{val}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
