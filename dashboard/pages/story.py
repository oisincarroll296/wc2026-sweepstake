"""Story of the Tournament — AI-generated narrative from live match data."""
import sys
import json
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import pandas as pd

from dashboard.data import (
    get_overall_leaderboard, get_assignments, get_match_stats,
    get_teams, get_tier_map, get_captains,
)
from dashboard.components.ui import page_header

_ROOT          = Path(__file__).parent.parent.parent
_FIXTURES_PATH = _ROOT / "data" / "fixtures.csv"
_RESULTS_PATH  = _ROOT / "data" / "match_results.csv"
_PLAYERS_PATH  = _ROOT / "data" / "players.csv"
_CACHE_PATH    = _ROOT / "data" / "story_cache.json"

_UPSET_BONUS = {1: 15, 2: 30, 3: 50}


# ── Cache helpers ─────────────────────────────────────────────────────────────

def _load_cache() -> dict | None:
    if _CACHE_PATH.exists():
        try:
            return json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def _save_cache(data: dict) -> None:
    _CACHE_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ── Context builder ───────────────────────────────────────────────────────────

def _build_story_context() -> dict:
    # Raw files
    fixtures = pd.read_csv(_FIXTURES_PATH, dtype=str)
    fixtures["match_number"] = pd.to_numeric(fixtures["match_number"], errors="coerce")

    results = pd.read_csv(_RESULTS_PATH, dtype=str)
    _num_cols = [
        "match_number", "home_goals", "away_goals", "extra_time",
        "comeback_home", "comeback_away",
        "home_hat_tricks", "away_hat_tricks",
        "home_red_cards", "away_red_cards",
        "home_shirt_off", "away_shirt_off",
        "home_gk_goals", "away_gk_goals",
        "home_first_eliminated", "away_first_eliminated",
    ]
    for col in _num_cols:
        if col in results.columns:
            results[col] = pd.to_numeric(results[col], errors="coerce").fillna(0).astype(int)

    stats      = get_match_stats()
    tier_map   = get_tier_map()
    assignments= get_assignments()
    lb         = get_overall_leaderboard()
    captains_df= get_captains()
    players_df = pd.read_csv(_PLAYERS_PATH, dtype=str).fillna("") if _PLAYERS_PATH.exists() else pd.DataFrame()

    # Ownership: team → [players]
    ownership: dict[str, list[str]] = {}
    for player, teams in assignments.items():
        for team in teams:
            ownership.setdefault(team, []).append(player)

    # Captains
    pre_captains: dict[str, str] = {}
    if not captains_df.empty and "Player" in captains_df.columns:
        for _, row in captains_df.iterrows():
            p   = str(row.get("Player", ""))
            ptc = str(row.get("PreTournamentCaptain", "") or "")
            if ptc and ptc not in ("nan", ""):
                pre_captains[p] = ptc

    # Predictions (only from players who set them)
    predictions: dict[str, dict] = {}
    if not players_df.empty:
        pred_cols = ["WorldCupWinner", "RunnerUp", "BronzeMedal", "GoldenBoot", "DarkHorse", "FirstKnockedOut"]
        for _, row in players_df.iterrows():
            p = str(row.get("Player", ""))
            preds = {c: str(row.get(c, "") or "") for c in pred_cols if str(row.get(c, "") or "") not in ("", "nan")}
            if preds:
                predictions[p] = preds

    # Merge fixtures + results
    played = (
        pd.merge(results, fixtures, on="match_number", how="inner")
        .sort_values("match_number")
    )

    match_narratives: list[dict] = []
    upsets:           list[dict] = []
    hat_tricks:       list[dict] = []
    special_events:   list[dict] = []

    for _, m in played.iterrows():
        home      = str(m.get("home_team", ""))
        away      = str(m.get("away_team", ""))
        hg        = int(m.get("home_goals", 0))
        ag        = int(m.get("away_goals", 0))
        group     = str(m.get("group", ""))
        match_num = int(m.get("match_number", 0))

        entry: dict = {
            "match": match_num,
            "group": group,
            "home": home,
            "away": away,
            "score": f"{hg}–{ag}",
            "home_owners": ownership.get(home, []),
            "away_owners": ownership.get(away, []),
        }

        # Winner / upset detection
        if hg > ag:
            winner, loser = home, away
        elif ag > hg:
            winner, loser = away, home
        else:
            winner = loser = None

        if winner and loser:
            wt = tier_map.get(winner, 0)
            lt = tier_map.get(loser, 0)
            tier_diff = wt - lt  # positive = upset (lower-ranked team won)
            if tier_diff > 0:
                bonus = _UPSET_BONUS.get(min(tier_diff, 3), 0)
                upsets.append({
                    "match": match_num,
                    "winner": winner,
                    "winner_tier": wt,
                    "loser": loser,
                    "loser_tier": lt,
                    "score": f"{hg}–{ag}",
                    "bonus_pts_each_owner": bonus,
                    "winner_owners": ownership.get(winner, []),
                    "loser_owners":  ownership.get(loser,  []),
                })
        elif winner:
            wt = tier_map.get(winner, 0)
            lt = tier_map.get(loser,  0)

        # Per-side events
        match_events: list[str] = []
        for side, team in (("home", home), ("away", away)):
            rc  = int(m.get(f"{side}_red_cards",      0))
            ht  = int(m.get(f"{side}_hat_tricks",     0))
            so_ = int(m.get(f"{side}_shirt_off",      0))
            gkg = int(m.get(f"{side}_gk_goals",       0))
            fe  = int(m.get(f"{side}_first_eliminated", 0))

            if ht:
                hat_tricks.append({
                    "team": team, "match": match_num,
                    "opponent": away if side == "home" else home,
                    "score": f"{hg}–{ag}",
                    "owners": ownership.get(team, []),
                })
                match_events.append(f"{team} hat trick (+10 pts)")

            if rc:
                special_events.append({
                    "type": "red_card", "team": team,
                    "count": rc, "match": match_num,
                    "owners": ownership.get(team, []),
                    "points_impact": f"−{rc * 5} pts",
                })
                match_events.append(f"{team} {rc} red card{'s' if rc > 1 else ''} (−{rc*5} pts)")

            if so_:
                special_events.append({
                    "type": "shirt_removal", "team": team, "match": match_num,
                    "owners": ownership.get(team, []),
                    "points_impact": "+25 pts",
                })
                match_events.append(f"{team} shirt removal (+25 pts)")

            if gkg:
                special_events.append({
                    "type": "gk_goal", "team": team, "match": match_num,
                    "owners": ownership.get(team, []),
                    "points_impact": "+75 pts",
                })
                match_events.append(f"{team} GOALKEEPER GOAL (+75 pts!)")

            if fe:
                special_events.append({
                    "type": "first_eliminated", "team": team, "match": match_num,
                    "owners": ownership.get(team, []),
                    "points_impact": "+35 pts",
                })
                match_events.append(f"{team} FIRST TEAM ELIMINATED (+35 pts to owners)")

        # Comeback / pens
        if int(m.get("comeback_home", 0)):
            match_events.append(f"{home} comeback win (+3 bonus pts)")
        if int(m.get("comeback_away", 0)):
            match_events.append(f"{away} comeback win (+3 bonus pts)")
        pw = str(m.get("penalty_winner", "") or "")
        if pw and pw not in ("0", "nan", ""):
            match_events.append(f"Penalty shootout: {pw} wins (+3 bonus pts)")

        if match_events:
            entry["notable_events"] = match_events

        match_narratives.append(entry)

    # Leaderboard
    standings: list[dict] = []
    if not lb.empty:
        for _, row in lb.iterrows():
            p = str(row.get("Player", ""))
            standings.append({
                "rank":          int(row.get("Rank", 0)),
                "player":        p,
                "total_pts":     round(float(row.get("TotalPoints", 0)), 1),
                "goals_pts":     round(float(row.get("GoalsPoints", 0)), 1),
                "win_pts":       round(float(row.get("WinPoints", 0)), 1),
                "upset_pts":     round(float(row.get("UpsetPoints", 0)), 1),
                "captain_bonus": round(float(row.get("CaptainBonus", 0)), 1),
                "captain":       pre_captains.get(p, "not set"),
                "teams":         assignments.get(p, []),
                "predictions":   predictions.get(p, {}),
            })

    # Top scoring teams (group goals)
    top_teams: list[dict] = []
    if not stats.empty and "GroupGoals" in stats.columns:
        ts = (
            stats.assign(_g=pd.to_numeric(stats["GroupGoals"], errors="coerce").fillna(0))
            .query("_g > 0")
            .sort_values("_g", ascending=False)
            .head(8)
        )
        for _, row in ts.iterrows():
            team = str(row["Team"])
            top_teams.append({
                "team": team,
                "group_goals": int(float(row["GroupGoals"])),
                "tier": tier_map.get(team, 0),
                "owners": ownership.get(team, []),
            })

    # Goals totals
    total_goals = int(played["home_goals"].sum() + played["away_goals"].sum())
    n_matches   = len(played)

    return {
        "sweepstake_info": (
            "14 friends, each owning 8 teams (2 from each of 4 FIFA tiers). "
            "Points: Goals 1pt · Clean sheets 2pt · Win 3pt · "
            "Upset vs 1 tier higher +15pt, 2 tiers +30pt, 3 tiers +50pt · "
            "Hat trick 10pt · Shirt removal 25pt · GK goal 75pt · Red card −5pt. "
            "Captain earns ×1.5 their points (pre-tournament captain covers all stages)."
        ),
        "date":                 datetime.now(timezone.utc).strftime("%-d %B %Y"),
        "stage":                "Group Stage",
        "matches_played":       n_matches,
        "total_goals":          total_goals,
        "avg_goals_per_game":   round(total_goals / n_matches, 2) if n_matches else 0,
        "standings":            standings,
        "points_leader":        standings[0] if standings else None,
        "points_last":          standings[-1] if standings else None,
        "match_results":        match_narratives,
        "upsets":               upsets,
        "hat_tricks":           hat_tricks,
        "special_events":       special_events,
        "top_scoring_teams":    top_teams,
    }


# ── LLM call ─────────────────────────────────────────────────────────────────

def _generate_story(context: dict, api_key: str) -> str:
    import anthropic  # optional dep — only needed here

    client = anthropic.Anthropic(api_key=api_key)

    system = (
        "You are a witty sports commentator writing for a private sweepstake WhatsApp group. "
        "The audience is 14 friends watching World Cup 2026 together. "
        "You write punchy, cheeky football commentary — like that one mate who insists on "
        "providing live commentary with way too much energy."
    )

    user = f"""Write a "Story of the Tournament So Far" section for the sweepstake dashboard.

Here is all the live tournament data:
<data>
{json.dumps(context, indent=2)}
</data>

Requirements:
- Bold headline at the top
- 3–4 short punchy paragraphs (no bullet points)
- Cover the most dramatic match moments: biggest wins, upsets (if any), hat tricks, special events (red cards, shirt removals, GK goals), comeback wins
- Name the sweepstake players when their teams do something notable — say things like "Oisin C's Germany ran riot..." or "whoever owns South Africa will be hiding after those red cards"
- Mention the scoreline context naturally — e.g. "Germany didn't just beat Curacao, they dismantled them 7–1"
- Include the current leaderboard situation: who's flying, who's waiting for their teams to wake up
- End with a 1–2 sentence forward look (whose position looks strong, what upcoming fixtures could shake things up)
- Tone: enthusiastic WhatsApp banter, a bit cheeky, football-obsessed. Not corporate.
- Length: 350–450 words total
- Only use facts from the <data> block — do not invent events
- If no upsets or special events have happened yet, acknowledge that the tournament has been relatively straight-forward so far
- Format output as plain markdown (bold headline with ##, then paragraphs with blank lines between them — no other headers or lists)
"""

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1200,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return msg.content[0].text


# ── Page ──────────────────────────────────────────────────────────────────────

page_header("Story of the Tournament", "AI-generated narrative from live match data")

_api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
_cache   = _load_cache()

# Top bar: generate / regenerate button
_col_meta, _col_btn = st.columns([3, 1])
with _col_btn:
    if _api_key:
        if st.button(
            "Regenerate" if _cache else "Generate Story",
            type="primary" if not _cache else "secondary",
            use_container_width=True,
        ):
            st.session_state["_story_generate"] = True
    else:
        st.button("Generate Story", disabled=True, use_container_width=True,
                  help="Add ANTHROPIC_API_KEY to Streamlit secrets")

# Generation flow
if st.session_state.get("_story_generate"):
    st.session_state["_story_generate"] = False
    with st.spinner("Building match context and calling AI…"):
        try:
            ctx   = _build_story_context()
            story = _generate_story(ctx, _api_key)
            _cache = {
                "generated_at":    datetime.now().strftime("%-d %B %Y at %H:%M"),
                "matches_covered": ctx["matches_played"],
                "story":           story,
            }
            _save_cache(_cache)
            st.rerun()
        except Exception as exc:
            st.error(f"Generation failed: {exc}")

# Display
if _cache and "story" in _cache:
    with _col_meta:
        st.caption(
            f"Generated {_cache.get('generated_at', '?')}  ·  "
            f"{_cache.get('matches_covered', '?')} matches covered"
        )
    st.markdown(
        f'<div style="background:#1A2535;border:1px solid #D4A01733;border-radius:12px;'
        f'padding:1.75rem 2rem 1.5rem;line-height:1.75;font-size:0.96rem">'
        f'{_cache["story"].replace(chr(10), "<br>")}'
        f'</div>',
        unsafe_allow_html=True,
    )
elif not _api_key:
    st.info(
        "Add `ANTHROPIC_API_KEY` to your Streamlit Cloud secrets to enable story generation. "
        "The key is used only for generating the story narrative on demand."
    )
else:
    st.info("Hit **Generate Story** to produce the first tournament narrative.")

# Raw context expander (for debugging / curiosity)
with st.expander("Raw story context (what gets sent to the AI)", expanded=False):
    try:
        ctx_preview = _build_story_context()
        st.json(ctx_preview)
    except Exception as e:
        st.warning(f"Could not build context: {e}")
