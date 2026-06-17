"""Story of the Tournament — AI-generated narrative from live match data."""
import sys
import json
from datetime import datetime, timezone, date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import pandas as pd

from dashboard.data import (
    get_overall_leaderboard, get_assignments, get_match_stats,
    get_tier_map, get_captains,
)
from dashboard.components.ui import page_header

_ROOT          = Path(__file__).parent.parent.parent
_FIXTURES_PATH = _ROOT / "data" / "fixtures.csv"
_RESULTS_PATH  = _ROOT / "data" / "match_results.csv"
_PLAYERS_PATH  = _ROOT / "data" / "players.csv"
_CACHE_PATH    = _ROOT / "data" / "story_cache.json"

_UPSET_BONUS = {1: 15, 2: 30, 3: 50}


# ── Cache ─────────────────────────────────────────────────────────────────────

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

def _build_story_context(date_from: date | None = None, date_to: date | None = None) -> dict:
    fixtures = pd.read_csv(_FIXTURES_PATH, dtype=str)
    fixtures["match_number"] = pd.to_numeric(fixtures["match_number"], errors="coerce")
    # Parse match dates (DD/MM/YYYY)
    fixtures["_date"] = pd.to_datetime(fixtures["match_date"], format="%d/%m/%Y", errors="coerce").dt.date

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

    stats       = get_match_stats()
    tier_map    = get_tier_map()
    assignments = get_assignments()
    lb          = get_overall_leaderboard()
    captains_df = get_captains()
    players_df  = pd.read_csv(_PLAYERS_PATH, dtype=str).fillna("") if _PLAYERS_PATH.exists() else pd.DataFrame()

    # Ownership map
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

    # Predictions
    predictions: dict[str, dict] = {}
    if not players_df.empty:
        pred_cols = ["WorldCupWinner", "RunnerUp", "BronzeMedal", "GoldenBoot", "DarkHorse", "FirstKnockedOut"]
        for _, row in players_df.iterrows():
            p     = str(row.get("Player", ""))
            preds = {c: str(row.get(c, "") or "") for c in pred_cols
                     if str(row.get(c, "") or "") not in ("", "nan")}
            if preds:
                predictions[p] = preds

    # Merge fixtures + results, then apply date filter
    played = (
        pd.merge(results, fixtures, on="match_number", how="inner")
        .sort_values("match_number")
    )
    all_played = played.copy()  # keep full set for leaderboard context

    if date_from:
        played = played[played["_date"] >= date_from]
    if date_to:
        played = played[played["_date"] <= date_to]

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
        match_date= str(m.get("match_date", ""))

        entry: dict = {
            "match": match_num,
            "date": match_date,
            "group": group,
            "home": home,
            "away": away,
            "score": f"{hg}–{ag}",
            "home_owners": ownership.get(home, []),
            "away_owners": ownership.get(away, []),
        }

        if hg > ag:
            winner, loser = home, away
        elif ag > hg:
            winner, loser = away, home
        else:
            winner = loser = None

        if winner and loser:
            wt = tier_map.get(winner, 0)
            lt = tier_map.get(loser, 0)
            if wt > lt:
                bonus = _UPSET_BONUS.get(min(wt - lt, 3), 0)
                upsets.append({
                    "match": match_num,
                    "winner": winner, "winner_tier": wt,
                    "loser": loser,   "loser_tier": lt,
                    "score": f"{hg}–{ag}",
                    "bonus_pts_each_owner": bonus,
                    "winner_owners": ownership.get(winner, []),
                    "loser_owners":  ownership.get(loser,  []),
                })

        match_events: list[str] = []
        for side, team in (("home", home), ("away", away)):
            rc  = int(m.get(f"{side}_red_cards",        0))
            ht  = int(m.get(f"{side}_hat_tricks",       0))
            so_ = int(m.get(f"{side}_shirt_off",        0))
            gkg = int(m.get(f"{side}_gk_goals",         0))
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
                special_events.append({"type": "red_card", "team": team, "count": rc,
                                        "match": match_num, "owners": ownership.get(team, [])})
                match_events.append(f"{team} {rc} red card{'s' if rc>1 else ''} (−{rc*5} pts)")
            if so_:
                special_events.append({"type": "shirt_removal", "team": team,
                                        "match": match_num, "owners": ownership.get(team, [])})
                match_events.append(f"{team} shirt removal (+25 pts)")
            if gkg:
                special_events.append({"type": "gk_goal", "team": team,
                                        "match": match_num, "owners": ownership.get(team, [])})
                match_events.append(f"{team} GOALKEEPER GOAL (+75 pts!)")
            if fe:
                special_events.append({"type": "first_eliminated", "team": team,
                                        "match": match_num, "owners": ownership.get(team, [])})
                match_events.append(f"{team} FIRST TEAM ELIMINATED (+35 pts to owners)")

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

    # Leaderboard (always full tournament, regardless of date filter)
    standings: list[dict] = []
    if not lb.empty:
        for _, row in lb.iterrows():
            p = str(row.get("Player", ""))
            standings.append({
                "rank":          int(row.get("Rank", 0)),
                "player":        p,
                "total_pts":     round(float(row.get("TotalPoints", 0)), 1),
                "goals_pts":     round(float(row.get("GoalsPoints", 0)), 1),
                "upset_pts":     round(float(row.get("UpsetPoints", 0)), 1),
                "captain_bonus": round(float(row.get("CaptainBonus", 0)), 1),
                "captain":       pre_captains.get(p, "not set"),
                "teams":         assignments.get(p, []),
                "predictions":   predictions.get(p, {}),
            })

    # Top scoring teams in period
    top_teams: list[dict] = []
    if not stats.empty and "GroupGoals" in stats.columns:
        ts = (
            stats.assign(_g=pd.to_numeric(stats["GroupGoals"], errors="coerce").fillna(0))
            .query("_g > 0").sort_values("_g", ascending=False).head(8)
        )
        for _, row in ts.iterrows():
            team = str(row["Team"])
            top_teams.append({
                "team": team,
                "group_goals": int(float(row["GroupGoals"])),
                "tier": tier_map.get(team, 0),
                "owners": ownership.get(team, []),
            })

    total_goals  = int(played["home_goals"].sum() + played["away_goals"].sum())
    n_matches    = len(played)
    n_all        = len(all_played)

    period_label = "Full tournament so far"
    if date_from and date_to:
        period_label = f"{date_from.strftime('%-d %b')} – {date_to.strftime('%-d %b %Y')}"
    elif date_from:
        period_label = f"From {date_from.strftime('%-d %b %Y')}"
    elif date_to:
        period_label = f"Up to {date_to.strftime('%-d %b %Y')}"

    return {
        "sweepstake_info": (
            "14 friends, each owning 8 teams (2 from each of 4 FIFA tiers). "
            "Points: Goals 1pt · Clean sheets 2pt · Win 3pt · "
            "Upset vs 1 tier higher +15pt, 2 tiers +30pt, 3 tiers +50pt · "
            "Hat trick 10pt · Shirt removal 25pt · GK goal 75pt · Red card −5pt. "
            "Captain earns ×1.5 their points."
        ),
        "period":              period_label,
        "matches_in_period":   n_matches,
        "total_matches_played": n_all,
        "goals_in_period":     total_goals,
        "avg_goals_per_game":  round(total_goals / n_matches, 2) if n_matches else 0,
        "current_standings":   standings,
        "match_results":       match_narratives,
        "upsets":              upsets,
        "hat_tricks":          hat_tricks,
        "special_events":      special_events,
        "top_scoring_teams":   top_teams,
    }


# ── LLM call (Groq) ──────────────────────────────────────────────────────────

def _generate_story(context: dict, api_key: str, topic: str = "") -> str:
    from groq import Groq

    client = Groq(api_key=api_key)

    topic_line = (
        f"\nThe user has also asked you to specifically focus on or address this angle: {topic.strip()}\n"
        if topic.strip() else ""
    )

    system = (
        "You are a witty sports commentator writing for a private sweepstake WhatsApp group. "
        "The audience is 14 friends watching World Cup 2026 together. "
        "You write punchy, cheeky football commentary — like that one mate who insists on "
        "providing live commentary with way too much energy."
    )

    user = f"""Write a story for the sweepstake dashboard covering the period: {context['period']}.
{topic_line}
Here is all the live tournament data for this period:
<data>
{json.dumps(context, indent=2)}
</data>

Requirements:
- Bold headline at the top (use ##)
- 3–4 short punchy paragraphs (no bullet points, no sub-headers)
- Cover the most dramatic moments: biggest wins, upsets, hat tricks, special events, comeback wins
- Name sweepstake players when their teams do something notable — e.g. "Oisin C's Germany ran riot..." or "whoever owns South Africa will be hiding after those red cards"
- Include the current leaderboard situation: who's leading, who's waiting for their teams to wake up
- End with a 1–2 sentence forward look
- Tone: enthusiastic WhatsApp banter, cheeky, football-obsessed. Not corporate.
- Length: 350–450 words
- Only use facts from the <data> block — do not invent events
- Format: ## headline, then plain paragraphs separated by blank lines, nothing else
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        max_tokens=1200,
        temperature=0.8,
    )
    return response.choices[0].message.content


# ── Page ──────────────────────────────────────────────────────────────────────

page_header("Story of the Tournament", "AI-generated narrative from live match data")

_api_key      = st.secrets.get("GROQ_API_KEY", "")
_admin_pw     = st.secrets.get("ADMIN_PASSWORD", "wc2026admin")
_cache        = _load_cache()
_date_from: date | None = None
_date_to:   date | None = None
_topic        = ""
_generate_clicked = False

# ── Admin panel (hidden from regular users) ───────────────────────────────────
_is_admin = st.session_state.get("_story_admin", False)

with st.sidebar:
    if not _is_admin:
        with st.expander("Admin", expanded=False):
            _pw_input = st.text_input("Password", type="password", key="story_pw")
            if st.button("Unlock", key="story_unlock"):
                if _pw_input == _admin_pw:
                    st.session_state["_story_admin"] = True
                    st.rerun()
                else:
                    st.error("Wrong password")
    else:
        st.success("Admin unlocked")
        if st.button("Lock", key="story_lock"):
            st.session_state["_story_admin"] = False
            st.rerun()

if _is_admin:
    _today = date.today()
    with st.expander("Story settings", expanded=not bool(_cache)):
        _period_options = [
            "Full tournament so far",
            "Last 3 days",
            "Last 7 days",
            "Custom date range",
        ]
        _period_choice = st.radio(
            "Time period", _period_options, horizontal=True, label_visibility="collapsed"
        )

        if _period_choice == "Last 3 days":
            _date_from = _today - timedelta(days=3)
        elif _period_choice == "Last 7 days":
            _date_from = _today - timedelta(days=7)
        elif _period_choice == "Custom date range":
            _c1, _c2 = st.columns(2)
            _date_from = _c1.date_input("From", value=_today - timedelta(days=7), key="story_from")
            _date_to   = _c2.date_input("To",   value=_today,                     key="story_to")

        _topic = st.text_input(
            "Focus on a specific angle (optional)",
            placeholder="e.g. who's benefiting most from upsets · the red card chaos · Germany's goal machine",
            key="story_topic",
        )

        _col_btn, _col_meta = st.columns([1, 3])
        with _col_btn:
            _btn_disabled = not _api_key
            _btn_label    = "Regenerate" if _cache else "Generate Story"
            _generate_clicked = st.button(
                _btn_label,
                type="primary",
                use_container_width=True,
                disabled=_btn_disabled,
                help="Add GROQ_API_KEY to Streamlit secrets" if _btn_disabled else "",
            )
        with _col_meta:
            if _cache:
                st.caption(
                    f"Last generated: {_cache.get('generated_at', '?')}  ·  "
                    f"{_cache.get('matches_covered', '?')} matches at generation  ·  "
                    f"Period: {_cache.get('period', '?')}"
                    + (f"  ·  Topic: _{_cache.get('topic', '')}_" if _cache.get("topic") else "")
                )
            elif not _api_key:
                st.caption("Add `GROQ_API_KEY` to Streamlit secrets.")

# ── Generation ────────────────────────────────────────────────────────────────
if _generate_clicked:
    with st.spinner("Building match context and generating story…"):
        try:
            ctx   = _build_story_context(date_from=_date_from, date_to=_date_to)
            story = _generate_story(ctx, _api_key, topic=_topic)
            _cache = {
                "generated_at":    datetime.now().strftime("%d %b %Y at %H:%M"),
                "matches_covered": ctx["total_matches_played"],
                "period":          ctx["period"],
                "topic":           _topic.strip(),
                "story":           story,
            }
            _save_cache(_cache)
            st.rerun()
        except Exception as exc:
            st.error(f"Generation failed: {exc}")

# ── Display (visible to everyone) ─────────────────────────────────────────────
if _cache and "story" in _cache:
    if _cache.get("period") or _cache.get("topic"):
        _meta_parts = []
        if _cache.get("period") and _cache["period"] != "Full tournament so far":
            _meta_parts.append(_cache["period"])
        if _cache.get("topic"):
            _meta_parts.append(f"Focus: _{_cache['topic']}_")
        if _meta_parts:
            st.caption("  ·  ".join(_meta_parts))
    st.markdown(
        f'<div style="background:#1A2535;border:1px solid #D4A01733;border-radius:12px;'
        f'padding:1.75rem 2rem 1.5rem;line-height:1.8;font-size:0.96rem">'
        f'{_cache["story"].replace(chr(10), "<br>")}'
        f'</div>',
        unsafe_allow_html=True,
    )
else:
    st.info("No story generated yet — check back soon.")

# ── Raw context (admin only) ──────────────────────────────────────────────────
if _is_admin:
    with st.expander("Raw context sent to AI", expanded=False):
        try:
            st.json(_build_story_context(date_from=_date_from, date_to=_date_to))
        except Exception as e:
            st.warning(f"Could not build context: {e}")
