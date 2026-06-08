"""Groups — group stage overview: teams, ownership, standings, fixtures."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import pandas as pd
from datetime import date, timedelta

from dashboard.data import get_teams, get_assignments, get_match_stats, get_fixtures, get_match_results
from dashboard.components.ui import page_header

_ROOT = Path(__file__).parent.parent.parent

TIER_COLORS = {1: "#105AAC", 2: "#15803D", 3: "#A16207", 4: "#B91C1C"}
TIER_LABELS = {1: "T1", 2: "T2", 3: "T3", 4: "T4"}


page_header("Groups", "Group stage — teams, ownership, and fixtures")

teams_df    = get_teams()
assignments = get_assignments()
stats_df    = get_match_stats()
fixtures_df = get_fixtures()
results_df  = get_match_results()

# ── Build lookup maps ───────────────────────────────────────────────────────
ownership: dict[str, list[str]] = {}
for player, teams in assignments.items():
    for team in teams:
        ownership.setdefault(team, []).append(player)

goals_map: dict[str, int] = {}
if not stats_df.empty and "Goals" in stats_df.columns:
    for _, row in stats_df.iterrows():
        goals_map[str(row["Team"])] = int(float(row.get("Goals", 0) or 0))

# ── Build group → team list ─────────────────────────────────────────────────
groups: dict[str, list] = {}
for _, row in teams_df.iterrows():
    g = str(row.get("Group", "")).strip()
    if g and g.lower() != "nan":
        groups.setdefault(g, []).append(row)

tab_groups, tab_standings, tab_fixtures = st.tabs(["Groups", "Standings", "Fixtures"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — GROUPS
# ══════════════════════════════════════════════════════════════════════════════
with tab_groups:
    group_letters = sorted(groups.keys())

    # 3 columns of groups
    for row_start in range(0, len(group_letters), 3):
        cols = st.columns(3)
        for i, g in enumerate(group_letters[row_start:row_start + 3]):
            with cols[i]:
                st.markdown(
                    f'<div style="color:#D4A017;font-weight:700;font-size:1rem;'
                    f'border-bottom:1px solid #2A3A4A;padding-bottom:0.2rem;margin-bottom:0.4rem">'
                    f'Group {g}</div>',
                    unsafe_allow_html=True,
                )
                team_rows = sorted(groups[g], key=lambda r: int(r.get("Tier", 4)))
                for r in team_rows:
                    team  = str(r["Team"])
                    tier  = int(r.get("Tier", 4))
                    color = TIER_COLORS.get(tier, "#9CA3AF")
                    label = TIER_LABELS.get(tier, "T?")
                    owners = ownership.get(team, [])
                    goals  = goals_map.get(team, 0)
                    owner_str = ", ".join(owners) if owners else "Unowned"
                    owner_col = "#9CA3AF" if not owners else "#6EE7B7"
                    goals_html = (
                        f'<span style="color:#D4A017;font-size:0.7rem;margin-left:0.3rem">⚽{goals}</span>'
                        if goals > 0 else ""
                    )
                    st.markdown(
                        f'<div style="border-left:3px solid {color};padding:0.25rem 0.5rem;'
                        f'margin:0.2rem 0;background:#1E2937;border-radius:0 5px 5px 0">'
                        f'<span style="color:{color};font-size:0.65rem;font-weight:700;'
                        f'background:{color}22;border-radius:3px;padding:0 3px">{label}</span> '
                        f'<span style="color:#F5F5F5;font-size:0.82rem;font-weight:600">{team}</span>'
                        f'{goals_html}'
                        f'<div style="color:{owner_col};font-size:0.7rem;margin-top:0.05rem">'
                        f'{owner_str}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — STANDINGS
# ══════════════════════════════════════════════════════════════════════════════
with tab_standings:
    if results_df.empty or fixtures_df.empty:
        st.info("Group standings will appear here once match results have been entered.")
    else:
        # Calculate standings from match results
        standings: dict[str, dict] = {}
        for _, row in teams_df.iterrows():
            t = str(row["Team"])
            g = str(row.get("Group", "")).strip()
            if g and g.lower() != "nan":
                standings[t] = {"Group": g, "P": 0, "W": 0, "D": 0, "L": 0,
                                 "GF": 0, "GA": 0, "GD": 0, "Pts": 0}

        for _, res in results_df.iterrows():
            mn = int(pd.to_numeric(res.get("match_number", 0), errors="coerce") or 0)
            fix_row = fixtures_df[
                pd.to_numeric(fixtures_df["match_number"], errors="coerce") == mn
            ]
            if fix_row.empty:
                continue
            fx = fix_row.iloc[0]
            if not str(fx.get("group", "")).strip():
                continue  # skip knockout
            home, away = str(fx["home_team"]), str(fx["away_team"])
            hg = int(float(res.get("home_goals", 0) or 0))
            ag = int(float(res.get("away_goals", 0) or 0))
            for team, gf, ga in [(home, hg, ag), (away, ag, hg)]:
                if team not in standings:
                    continue
                standings[team]["P"]  += 1
                standings[team]["GF"] += gf
                standings[team]["GA"] += ga
                standings[team]["GD"]  = standings[team]["GF"] - standings[team]["GA"]
                if gf > ga:
                    standings[team]["W"]   += 1
                    standings[team]["Pts"] += 3
                elif gf == ga:
                    standings[team]["D"]   += 1
                    standings[team]["Pts"] += 1
                else:
                    standings[team]["L"] += 1

        stand_df = pd.DataFrame(standings.values(), index=standings.keys()).reset_index()
        stand_df.rename(columns={"index": "Team"}, inplace=True)

        for g_letter in sorted(stand_df["Group"].unique()):
            grp_df = (
                stand_df[stand_df["Group"] == g_letter]
                .sort_values(["Pts", "GD", "GF"], ascending=False)
                .reset_index(drop=True)
            )
            st.markdown(
                f'<div style="color:#D4A017;font-weight:700;font-size:0.95rem;'
                f'margin:1rem 0 0.2rem;border-bottom:1px solid #2A3A4A;padding-bottom:0.15rem">'
                f'Group {g_letter}</div>',
                unsafe_allow_html=True,
            )
            display = grp_df[["Team", "P", "W", "D", "L", "GF", "GA", "GD", "Pts"]].copy()

            def _stand_style(row):
                if row.name == 0:
                    return ["background-color:rgba(212,160,23,0.15);font-weight:700"] * len(row)
                if row.name == 1:
                    return ["background-color:rgba(21,128,61,0.12)"] * len(row)
                return ["color:#9CA3AF"] * len(row)

            st.dataframe(
                display.style.apply(_stand_style, axis=1),
                use_container_width=True, hide_index=True, height=185,
            )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — FIXTURES
# ══════════════════════════════════════════════════════════════════════════════
with tab_fixtures:
    if fixtures_df.empty:
        st.info("Fixture data not found.")
    else:
        all_owned = {t for ts in assignments.values() for t in ts} if assignments else set()

        # Entered match numbers
        entered_nums: set = set()
        if not results_df.empty and "match_number" in results_df.columns:
            entered_nums = set(results_df["match_number"].dropna().astype(int).tolist())

        today = date.today()
        col1, col2 = st.columns([2, 1])
        with col1:
            days_ahead = st.slider("Show fixtures for next N days", 1, 21, 7)
        with col2:
            owned_only = st.toggle("Only my teams' matches", value=False)

        cutoff = today + timedelta(days=days_ahead)
        mask = (
            fixtures_df["match_date"].notna()
            & (fixtures_df["match_date"] >= today)
            & (fixtures_df["match_date"] <= cutoff)
        )
        upcoming = fixtures_df[mask].copy()

        if upcoming.empty:
            st.info("No fixtures in the selected range.")
        else:
            if owned_only and all_owned:
                relevant = upcoming[
                    upcoming["home_team"].isin(all_owned) | upcoming["away_team"].isin(all_owned)
                ]
                upcoming = relevant if not relevant.empty else upcoming

            for match_date in sorted(upcoming["match_date"].unique()):
                day_matches = upcoming[upcoming["match_date"] == match_date]
                _ts = pd.Timestamp(match_date)
                day_label = f"{_ts.day} {_ts.strftime('%b')}"
                st.markdown(
                    f'<div style="color:#D4A017;font-weight:700;font-size:0.88rem;'
                    f'margin:0.75rem 0 0.3rem;border-bottom:1px solid #2A3A4A;padding-bottom:0.15rem">'
                    f'{day_label}</div>',
                    unsafe_allow_html=True,
                )
                for _, m in day_matches.iterrows():
                    home  = m["home_team"]
                    away  = m["away_team"]
                    grp   = m.get("group", "")
                    venue = m.get("venue", "")
                    mn    = int(pd.to_numeric(m["match_number"], errors="coerce") or 0)
                    done  = mn in entered_nums

                    # Get score if entered
                    score_html = ""
                    if done and not results_df.empty:
                        rr = results_df[results_df["match_number"] == mn]
                        if not rr.empty:
                            hg = int(float(rr.iloc[0].get("home_goals", 0) or 0))
                            ag = int(float(rr.iloc[0].get("away_goals", 0) or 0))
                            score_html = (
                                f'<span style="color:#6EE7B7;font-size:0.78rem;'
                                f'font-weight:700;margin:0 0.4rem">{hg}–{ag}</span>'
                            )

                    home_owned = home in all_owned
                    away_owned = away in all_owned
                    border = "border:1px solid #D4A017;" if (home_owned or away_owned) else ""
                    home_col = "#D4A017" if home_owned else "#F5F5F5"
                    away_col = "#D4A017" if away_owned else "#F5F5F5"
                    home_owners = ", ".join(ownership.get(home, []))
                    away_owners = ", ".join(ownership.get(away, []))
                    home_note = f'<span style="color:#6EE7B7;font-size:0.65rem"> ({home_owners})</span>' if home_owners else ""
                    away_note = f'<span style="color:#6EE7B7;font-size:0.65rem"> ({away_owners})</span>' if away_owners else ""
                    done_dot  = '<span style="color:#6EE7B7;font-size:0.7rem">✓</span>' if done else ""

                    st.markdown(
                        f'<div style="background:#1E2937;border-radius:6px;padding:0.4rem 0.7rem;'
                        f'margin:0.2rem 0;display:flex;align-items:center;gap:0.4rem;{border}">'
                        f'<span style="color:#6B7280;font-size:0.68rem;min-width:2rem">G{grp}</span>'
                        f'<span style="color:{home_col};font-weight:600;font-size:0.83rem">{home}</span>'
                        f'{home_note}{score_html}'
                        f'<span style="color:#6B7280;font-size:0.75rem">v</span>'
                        f'<span style="color:{away_col};font-weight:600;font-size:0.83rem">{away}</span>'
                        f'{away_note}'
                        f'<span style="margin-left:auto;display:flex;gap:0.3rem;align-items:center">'
                        f'<span style="color:#4B5563;font-size:0.65rem">{venue}</span>'
                        f'{done_dot}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
