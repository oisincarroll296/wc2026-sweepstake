"""Analytics — interactive charts using Plotly."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from dashboard.data import (
    get_overall_leaderboard, get_prize_pool, get_match_stats,
    get_tier_map, get_team_ownership_data, get_predictions_centre_data,
    get_captains, get_purchases, get_statuses, is_predictions_locked,
)
from dashboard.config import PLOTLY_LAYOUT, TIER_COLORS, COLORS
from dashboard.components.ui import page_header, empty_state


page_header("📊 Analytics", "Interactive charts — all data live from the tournament")

lb = get_overall_leaderboard()
match_stats = get_match_stats()
tier_map    = get_tier_map()

# ── 1. Leaderboard Bar Chart ───────────────────────────────────────────────
st.subheader("🏆 Current Standings")
if lb.empty:
    empty_state("No scores yet.")
else:
    colors = []
    for i, row in lb.iterrows():
        if row.get("PaymentStatus") == "UNPAID":
            colors.append(COLORS["muted"])
        elif i == 0:
            colors.append(COLORS["gold"])
        elif i == 1:
            colors.append(COLORS["silver"])
        elif i == 2:
            colors.append(COLORS["bronze"])
        else:
            colors.append("#4A6FA5")

    fig = go.Figure(go.Bar(
        x=lb["Player"].tolist(),
        y=lb["TotalPoints"].astype(float).tolist(),
        marker_color=colors,
        hovertemplate="%{x}: %{y:.0f} pts<extra></extra>",
    ))
    fig.update_layout(**PLOTLY_LAYOUT, title="Total Points by Player", height=350)
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── 2. Points Breakdown Stacked Bar ───────────────────────────────────────
if not lb.empty:
    breakdown_cols = ["BasePoints", "CaptainBonus", "InsuranceBonus", "PredictionBonus"]
    avail = [c for c in breakdown_cols if c in lb.columns]
    if avail:
        st.subheader("📐 Points Breakdown")
        fig2 = go.Figure()
        colors_stack = [COLORS["gold"], "#4A9A7A", "#A67C00", "#6A5ACD"]
        for i, col in enumerate(avail):
            fig2.add_trace(go.Bar(
                name=col.replace("Points", "").replace("Bonus", " Bonus").strip(),
                x=lb["Player"].tolist(),
                y=lb[col].astype(float).tolist(),
                marker_color=colors_stack[i % len(colors_stack)],
            ))
        fig2.update_layout(**PLOTLY_LAYOUT, barmode="stack", height=350, title="Points Breakdown by Source")
        st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ── 3. Top Scoring Teams ──────────────────────────────────────────────────
st.subheader("⚽ Top Scoring Teams")
if match_stats.empty:
    empty_state("No match data yet.")
else:
    from src.scoring_engine import calculate_team_points
    team_pts = []
    for _, row in match_stats.iterrows():
        team = str(row["Team"])
        tier = tier_map.get(team, 1)
        pts  = calculate_team_points(team, match_stats, tier)["total"]
        if pts > 0:
            team_pts.append({"Team": team, "Points": pts, "Tier": tier})

    if team_pts:
        tdf = pd.DataFrame(team_pts).sort_values("Points", ascending=False).head(15)
        fig3 = go.Figure(go.Bar(
            x=tdf["Team"].tolist(),
            y=tdf["Points"].tolist(),
            marker_color=[TIER_COLORS.get(t, "#9CA3AF") for t in tdf["Tier"].tolist()],
            hovertemplate="%{x}: %{y:.0f} pts<extra></extra>",
        ))
        fig3.update_layout(**PLOTLY_LAYOUT, title="Top 15 Scoring Teams", height=350)
        st.plotly_chart(fig3, use_container_width=True)
    else:
        empty_state("No team points yet.")

st.divider()

# ── 4. Team Ownership Distribution ────────────────────────────────────────
col_own, col_pop = st.columns(2)
with col_own:
    st.subheader("👥 Ownership Count")
    own = get_team_ownership_data()
    if own:
        owned_counts = [(t, len(d["owners"])) for t, d in own.items() if d["owners"]]
        owned_counts.sort(key=lambda x: -x[1])
        odf = pd.DataFrame(owned_counts[:15], columns=["Team", "Owners"])
        fig4 = go.Figure(go.Bar(
            x=odf["Team"].tolist(), y=odf["Owners"].tolist(),
            marker_color=COLORS["gold"],
            hovertemplate="%{x}: %{y} owners<extra></extra>",
        ))
        fig4.update_layout(**PLOTLY_LAYOUT, height=300, title="Teams by Owner Count")
        st.plotly_chart(fig4, use_container_width=True)
    else:
        empty_state()

with col_pop:
    st.subheader("🌟 Dark Horse Picks")
    if is_predictions_locked():
        preds = get_predictions_centre_data()
        dh = preds.get("dark_horse", {})
        if dh:
            dh_list = [(k, len(v)) for k, v in dh.items()]
            dh_list.sort(key=lambda x: -x[1])
            fig5 = go.Figure(go.Bar(
                x=[x[0] for x in dh_list],
                y=[x[1] for x in dh_list],
                marker_color=COLORS["t3"],
                hovertemplate="%{x}: %{y} pick(s)<extra></extra>",
            ))
            fig5.update_layout(**PLOTLY_LAYOUT, height=300, title="Dark Horse Picks")
            st.plotly_chart(fig5, use_container_width=True)
        else:
            empty_state("No dark horse picks.")
    else:
        st.markdown('<div class="lock-banner">🔒 Dark horse picks hidden until prediction lock</div>', unsafe_allow_html=True)

st.divider()

# ── 5. Prize Pool Growth ──────────────────────────────────────────────────
st.subheader("💰 Prize Pool Contribution by Type")
p = get_purchases()
if not p.empty:
    from src.competition import PRICES
    proc = p[p["Status"] == "PROCESSED"]
    breakdown = {}
    for ptype, price in PRICES.items():
        cnt = int((proc["PurchaseType"] == ptype).sum())
        if cnt:
            breakdown[ptype] = cnt * price

    if breakdown:
        fig6 = go.Figure(go.Pie(
            labels=list(breakdown.keys()),
            values=list(breakdown.values()),
            marker_colors=[COLORS["gold"], "#4A9A7A", "#A67C00", "#6A5ACD", "#B91C1C", "#15803D"],
            hole=0.45,
            hovertemplate="%{label}: €%{value:.2f}<extra></extra>",
        ))
        fig6.update_layout(**PLOTLY_LAYOUT, height=320, title="Prize Pool Composition")
        st.plotly_chart(fig6, use_container_width=True)
    else:
        empty_state("No processed purchases yet.")
else:
    empty_state("No purchase data.")

# ── 6. Captain Selections ─────────────────────────────────────────────────
st.divider()
caps = get_captains()
if not caps.empty:
    st.subheader("🎖️ Captain Selections")
    cap_col1, cap_col2 = st.columns(2)
    for col, cap_type, title in [
        (cap_col1, "PreTournament", "Pre-Tournament Captains"),
        (cap_col2, "Knockout",       "Knockout Captains"),
    ]:
        with col:
            st.markdown(f"**{title}**")
            subset = caps[caps["CaptainType"] == cap_type]
            if not subset.empty:
                counts = subset["Team"].value_counts().reset_index()
                counts.columns = ["Team", "Count"]
                fig7 = go.Figure(go.Bar(
                    x=counts["Team"].tolist(), y=counts["Count"].tolist(),
                    marker_color=COLORS["gold"],
                    hovertemplate="%{x}: %{y}<extra></extra>",
                ))
                fig7.update_layout(**PLOTLY_LAYOUT, height=250)
                st.plotly_chart(fig7, use_container_width=True)
