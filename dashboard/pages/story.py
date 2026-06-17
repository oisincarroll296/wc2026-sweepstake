"""Story of the Tournament — AI-generated newspaper-style narrative."""
import sys
import json
import re
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

# ISO flag codes for all 48 WC 2026 teams
_FLAG: dict[str, str] = {
    "Argentina": "ar", "Australia": "au", "Austria": "at", "Belgium": "be",
    "Bosnia and Herzegovina": "ba", "Brazil": "br", "Canada": "ca",
    "Cabo Verde": "cv", "Colombia": "co", "Congo DR": "cd", "Croatia": "hr",
    "Curacao": "cw", "Czechia": "cz", "Ecuador": "ec", "Egypt": "eg",
    "England": "gb-eng", "France": "fr", "Germany": "de", "Ghana": "gh",
    "Haiti": "ht", "IR Iran": "ir", "Iraq": "iq", "Japan": "jp",
    "Jordan": "jo", "Korea Republic": "kr", "Mexico": "mx", "Morocco": "ma",
    "Netherlands": "nl", "New Zealand": "nz", "Norway": "no", "Panama": "pa",
    "Paraguay": "py", "Portugal": "pt", "Qatar": "qa", "Saudi Arabia": "sa",
    "Scotland": "gb-sct", "Senegal": "sn", "South Africa": "za",
    "Spain": "es", "Sweden": "se", "Switzerland": "ch", "Cote d Ivoire": "ci",
    "Tunisia": "tn", "Tuerkiye": "tr", "Uruguay": "uy", "USA": "us",
    "Uzbekistan": "uz", "Algeria": "dz",
}


def _flag_url(team: str, size: int = 40) -> str:
    code = _FLAG.get(team, "")
    if not code:
        return ""
    return f"https://flagcdn.com/w{size}/{code}.png"


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
    fixtures["_date"] = pd.to_datetime(fixtures["match_date"], format="%d/%m/%Y", errors="coerce").dt.date

    results = pd.read_csv(_RESULTS_PATH, dtype=str)
    for col in ["match_number","home_goals","away_goals","extra_time","comeback_home","comeback_away",
                "home_hat_tricks","away_hat_tricks","home_red_cards","away_red_cards",
                "home_shirt_off","away_shirt_off","home_gk_goals","away_gk_goals",
                "home_first_eliminated","away_first_eliminated"]:
        if col in results.columns:
            results[col] = pd.to_numeric(results[col], errors="coerce").fillna(0).astype(int)

    stats       = get_match_stats()
    tier_map    = get_tier_map()
    assignments = get_assignments()
    lb          = get_overall_leaderboard()
    captains_df = get_captains()
    players_df  = pd.read_csv(_PLAYERS_PATH, dtype=str).fillna("") if _PLAYERS_PATH.exists() else pd.DataFrame()

    ownership: dict[str, list[str]] = {}
    for player, teams in assignments.items():
        for team in teams:
            ownership.setdefault(team, []).append(player)

    pre_captains: dict[str, str] = {}
    if not captains_df.empty and "Player" in captains_df.columns:
        for _, row in captains_df.iterrows():
            p, ptc = str(row.get("Player","")), str(row.get("PreTournamentCaptain","") or "")
            if ptc and ptc not in ("nan",""):
                pre_captains[p] = ptc

    predictions: dict[str, dict] = {}
    if not players_df.empty:
        pcols = ["WorldCupWinner","RunnerUp","BronzeMedal","GoldenBoot","DarkHorse","FirstKnockedOut"]
        for _, row in players_df.iterrows():
            p = str(row.get("Player",""))
            preds = {c: str(row.get(c,"") or "") for c in pcols if str(row.get(c,"") or "") not in ("","nan")}
            if preds:
                predictions[p] = preds

    all_played = pd.merge(results, fixtures, on="match_number", how="inner").sort_values("match_number")
    played = all_played.copy()
    if date_from:
        played = played[played["_date"] >= date_from]
    if date_to:
        played = played[played["_date"] <= date_to]

    match_narratives, upsets, hat_tricks, special_events = [], [], [], []
    featured_teams: set[str] = set()

    for _, m in played.iterrows():
        home, away   = str(m.get("home_team","")), str(m.get("away_team",""))
        hg, ag       = int(m.get("home_goals",0)), int(m.get("away_goals",0))
        match_num    = int(m.get("match_number",0))

        entry: dict = {
            "match": match_num, "date": str(m.get("match_date","")),
            "group": str(m.get("group","")),
            "home": home, "away": away, "score": f"{hg}–{ag}",
            "home_owners": ownership.get(home,[]), "away_owners": ownership.get(away,[]),
        }

        winner = loser = None
        if hg > ag:   winner, loser = home, away
        elif ag > hg: winner, loser = away, home

        if winner and loser:
            wt, lt = tier_map.get(winner,0), tier_map.get(loser,0)
            if wt > lt:
                bonus = _UPSET_BONUS.get(min(wt-lt,3), 0)
                upsets.append({
                    "match": match_num, "winner": winner, "winner_tier": wt,
                    "loser": loser, "loser_tier": lt, "score": f"{hg}–{ag}",
                    "bonus_pts_each_owner": bonus,
                    "winner_owners": ownership.get(winner,[]),
                    "loser_owners":  ownership.get(loser,[]),
                })
                featured_teams.update([winner, loser])

        match_events: list[str] = []
        for side, team in (("home", home), ("away", away)):
            rc  = int(m.get(f"{side}_red_cards",0))
            ht  = int(m.get(f"{side}_hat_tricks",0))
            so_ = int(m.get(f"{side}_shirt_off",0))
            gkg = int(m.get(f"{side}_gk_goals",0))
            fe  = int(m.get(f"{side}_first_eliminated",0))
            if ht:
                hat_tricks.append({"team":team,"match":match_num,
                    "opponent": away if side=="home" else home,
                    "score":f"{hg}–{ag}","owners":ownership.get(team,[])})
                match_events.append(f"{team} hat trick (+10 pts)")
                featured_teams.add(team)
            if rc:
                special_events.append({"type":"red_card","team":team,"count":rc,
                    "match":match_num,"owners":ownership.get(team,[])})
                match_events.append(f"{team} {rc} red card{'s' if rc>1 else ''} (−{rc*5} pts)")
            if so_:
                special_events.append({"type":"shirt_removal","team":team,
                    "match":match_num,"owners":ownership.get(team,[])})
                match_events.append(f"{team} shirt removal (+25 pts)")
            if gkg:
                special_events.append({"type":"gk_goal","team":team,
                    "match":match_num,"owners":ownership.get(team,[])})
                match_events.append(f"{team} GOALKEEPER GOAL (+75 pts!)")
                featured_teams.add(team)
            if fe:
                special_events.append({"type":"first_eliminated","team":team,
                    "match":match_num,"owners":ownership.get(team,[])})
                match_events.append(f"{team} FIRST TEAM ELIMINATED (+35 pts to owners)")

        if int(m.get("comeback_home",0)):
            match_events.append(f"{home} comeback win (+3 bonus pts)")
        if int(m.get("comeback_away",0)):
            match_events.append(f"{away} comeback win (+3 bonus pts)")
        pw = str(m.get("penalty_winner","") or "")
        if pw and pw not in ("0","nan",""):
            match_events.append(f"Penalty shootout: {pw} wins")

        # Big wins always get featured teams
        margin = abs(hg - ag)
        if winner and margin >= 3:
            featured_teams.update([home, away])

        if match_events:
            entry["notable_events"] = match_events
        match_narratives.append(entry)

    standings: list[dict] = []
    if not lb.empty:
        for _, row in lb.iterrows():
            p = str(row.get("Player",""))
            standings.append({
                "rank": int(row.get("Rank",0)), "player": p,
                "total_pts": round(float(row.get("TotalPoints",0)),1),
                "goals_pts": round(float(row.get("GoalsPoints",0)),1),
                "upset_pts": round(float(row.get("UpsetPoints",0)),1),
                "captain_bonus": round(float(row.get("CaptainBonus",0)),1),
                "captain": pre_captains.get(p,"not set"),
                "teams": assignments.get(p,[]),
                "predictions": predictions.get(p,{}),
            })

    top_teams: list[dict] = []
    if not stats.empty and "GroupGoals" in stats.columns:
        ts = (stats.assign(_g=pd.to_numeric(stats["GroupGoals"],errors="coerce").fillna(0))
              .query("_g > 0").sort_values("_g",ascending=False).head(8))
        for _, row in ts.iterrows():
            team = str(row["Team"])
            top_teams.append({"team":team,"group_goals":int(float(row["GroupGoals"])),
                              "tier":tier_map.get(team,0),"owners":ownership.get(team,[])})
        # Top scorers always featured
        if top_teams:
            featured_teams.add(top_teams[0]["team"])

    total_goals = int(played["home_goals"].sum() + played["away_goals"].sum())
    n_matches   = len(played)
    n_all       = len(all_played)

    period_label = "Full tournament so far"
    if date_from and date_to:
        period_label = f"{date_from.strftime('%d %b')} – {date_to.strftime('%d %b %Y')}"
    elif date_from:
        period_label = f"From {date_from.strftime('%d %b %Y')}"
    elif date_to:
        period_label = f"Up to {date_to.strftime('%d %b %Y')}"

    return {
        "sweepstake_info": (
            "14 friends, each owning 8 teams (2 per tier across 4 FIFA tiers). "
            "Points: Goal 1pt · Clean sheet 2pt · Win 3pt · "
            "Upset vs 1 tier higher +15pt, 2 tiers +30pt, 3 tiers +50pt · "
            "Hat trick 10pt · Shirt removal 25pt · GK goal 75pt · Red card −5pt. "
            "Captain earns ×1.5 their points."
        ),
        "period": period_label,
        "matches_in_period": n_matches,
        "total_matches_played": n_all,
        "goals_in_period": total_goals,
        "avg_goals_per_game": round(total_goals / n_matches, 2) if n_matches else 0,
        "current_standings": standings,
        "match_results": match_narratives,
        "upsets": upsets,
        "hat_tricks": hat_tricks,
        "special_events": special_events,
        "top_scoring_teams": top_teams,
        "featured_teams": sorted(featured_teams),
    }


# ── LLM (Groq) ───────────────────────────────────────────────────────────────

def _generate_story(context: dict, api_key: str, topic: str = "", suggestions: str = "") -> dict:
    from groq import Groq

    client = Groq(api_key=api_key)

    extras = []
    if topic.strip():
        extras.append(f"ANGLE TO FOCUS ON: {topic.strip()}")
    if suggestions.strip():
        extras.append(f"SPECIFIC POINTS TO INCLUDE:\n{suggestions.strip()}")
    extras_block = ("\n\n" + "\n\n".join(extras)) if extras else ""

    system = (
        "You are a sharp, witty football journalist writing for a private World Cup 2026 sweepstake newspaper. "
        "Your readers are 14 friends watching the tournament together. "
        "You write like a tabloid sports desk — punchy sentences, cheeky banter, dramatic flair. "
        "You are deeply familiar with the sweepstake format and always connect match events to sweepstake consequences."
    )

    user = f"""Write a newspaper-style match report for the sweepstake covering: {context['period']}.
{extras_block}

TOURNAMENT DATA:
<data>
{json.dumps(context, indent=2)}
</data>

OUTPUT FORMAT — respond with a single valid JSON object with exactly these keys:

{{
  "headline": "SHORT ALL-CAPS PUNCHY HEADLINE (max 10 words)",
  "subheadline": "A more detailed one-sentence subheadline",
  "lead_paragraph": "The opening paragraph — the single most dramatic moment, told dramatically. 2-3 sentences.",
  "body_paragraphs": ["paragraph 1", "paragraph 2", "paragraph 3"],
  "sweepstake_digest": "2-3 sentences on the leaderboard — who's leading, who's struggling, any big point swings",
  "pull_quote": "One memorable sentence (a stat or dramatic moment) to display as a big pull quote",
  "looking_ahead": "1-2 sentences on what to watch for next"
}}

WRITING RULES:
- Use real player names from the data when their teams do something notable ("Oisin C's Germany", "whoever owns South Africa")
- Reference actual scorelines (e.g. "7–1", not "a big win")
- Mention sweepstake point values naturally where dramatic (e.g. "+15 upset points flooding in")
- Tone: tabloid football journalism with banter — passionate, a little over the top, fun
- Be specific: no vague phrases like "some great matches" — name the games, the teams, the moments
- Only use facts from the data — never invent events
- Each body paragraph should cover a different theme (e.g. biggest results, upsets/special events, standout teams)
- Respond ONLY with the JSON — no markdown fences, no extra text
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        max_tokens=1500,
        temperature=0.75,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: try to extract JSON from the response
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            return json.loads(m.group())
        return {"headline": "Story Generated", "body_paragraphs": [raw],
                "lead_paragraph": "", "subheadline": "", "sweepstake_digest": "",
                "pull_quote": "", "looking_ahead": ""}


# ── Newspaper renderer ────────────────────────────────────────────────────────

def _render_newspaper(story: dict, meta: dict, featured_teams: list[str]) -> None:
    today_str = datetime.now().strftime("%A, %d %B %Y").upper()

    # Masthead
    st.markdown(
        f"""
        <div style="border-top:4px solid #D4A017;border-bottom:4px solid #D4A017;
                    text-align:center;padding:0.6rem 0 0.5rem;margin-bottom:0.1rem">
            <div style="font-size:2.6rem;font-weight:900;letter-spacing:0.08em;
                        color:#F5F5F5;font-family:Georgia,serif;line-height:1">
                THE SWEEPSTAKE GAZETTE
            </div>
            <div style="display:flex;justify-content:space-between;
                        font-size:0.72rem;color:#9CA3AF;padding:0.3rem 0.5rem 0;
                        border-top:1px solid #374151;margin-top:0.4rem">
                <span>World Cup 2026 · Private Edition</span>
                <span>{today_str}</span>
                <span>Period: {meta.get('period','Full tournament')}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Flag strip for featured teams
    flag_imgs = [f for t in featured_teams if (f := _flag_url(t, 40))]
    if flag_imgs:
        flag_html = "".join(
            f'<img src="{u}" style="height:28px;border-radius:3px;'
            f'box-shadow:0 1px 4px #0004;margin:0 3px" title="{t}">'
            for t, u in zip(featured_teams, flag_imgs)
        )
        st.markdown(
            f'<div style="text-align:center;padding:0.5rem 0 0.3rem;'
            f'border-bottom:1px solid #374151;margin-bottom:0.75rem">'
            f'{flag_html}</div>',
            unsafe_allow_html=True,
        )

    # Headline + subheadline
    headline    = story.get("headline", "").upper()
    subheadline = story.get("subheadline", "")
    st.markdown(
        f"""
        <div style="text-align:center;padding:0.5rem 1rem 0.75rem;
                    border-bottom:2px solid #D4A017;margin-bottom:1rem">
            <div style="font-size:2rem;font-weight:900;line-height:1.15;
                        color:#F5F5F5;font-family:Georgia,serif;letter-spacing:0.02em">
                {headline}
            </div>
            <div style="color:#D4A017;font-size:1rem;margin-top:0.4rem;
                        font-style:italic;font-family:Georgia,serif">
                {subheadline}
            </div>
            <div style="color:#6B7280;font-size:0.72rem;margin-top:0.4rem">
                By Your Sweepstake Correspondent
                {"  ·  Topic: " + meta.get("topic") if meta.get("topic") else ""}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Lead paragraph + pull quote (side by side)
    lead = story.get("lead_paragraph", "")
    pull = story.get("pull_quote", "")
    body = story.get("body_paragraphs", [])

    col_main, col_side = st.columns([2, 1])

    with col_main:
        if lead:
            st.markdown(
                f'<p style="font-size:1.02rem;line-height:1.8;font-family:Georgia,serif;'
                f'font-weight:600;color:#E5E7EB;margin:0 0 1rem">{lead}</p>',
                unsafe_allow_html=True,
            )
        for para in body:
            st.markdown(
                f'<p style="font-size:0.93rem;line-height:1.8;color:#D1D5DB;margin:0 0 0.9rem">{para}</p>',
                unsafe_allow_html=True,
            )

    with col_side:
        if pull:
            st.markdown(
                f'<div style="background:#0D1B2A;border-left:4px solid #D4A017;'
                f'padding:1rem 1rem 1rem 1.1rem;margin-bottom:1rem;border-radius:0 6px 6px 0">'
                f'<div style="color:#9CA3AF;font-size:0.65rem;letter-spacing:0.12em;'
                f'margin-bottom:0.4rem">PULL QUOTE</div>'
                f'<div style="color:#D4A017;font-size:1.05rem;font-style:italic;'
                f'line-height:1.5;font-family:Georgia,serif">"{pull}"</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # Leaderboard snapshot
        digest = story.get("sweepstake_digest", "")
        if digest:
            st.markdown(
                f'<div style="background:#1A2535;border:1px solid #374151;'
                f'border-radius:6px;padding:0.9rem 1rem">'
                f'<div style="color:#9CA3AF;font-size:0.65rem;letter-spacing:0.12em;'
                f'margin-bottom:0.5rem;border-bottom:1px solid #374151;padding-bottom:0.4rem">'
                f'SWEEPSTAKE DIGEST</div>'
                f'<div style="color:#D1D5DB;font-size:0.85rem;line-height:1.6">{digest}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # Looking ahead footer
    ahead = story.get("looking_ahead", "")
    if ahead:
        st.markdown(
            f'<div style="border-top:1px solid #374151;margin-top:1rem;padding-top:0.75rem">'
            f'<span style="color:#D4A017;font-size:0.7rem;letter-spacing:0.1em;font-weight:700">'
            f'LOOKING AHEAD  </span>'
            f'<span style="color:#9CA3AF;font-size:0.85rem">{ahead}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ── Page ──────────────────────────────────────────────────────────────────────

page_header("Story of the Tournament", "AI-generated newspaper from live match data")

_api_key   = st.secrets.get("GROQ_API_KEY", "")
_admin_pw  = st.secrets.get("ADMIN_PASSWORD", "wc2026admin")
_cache     = _load_cache()
_is_admin  = st.session_state.get("_story_admin", False)

# ── Admin login (sidebar) ──────────────────────────────────────────────────────
with st.sidebar:
    if not _is_admin:
        with st.expander("Admin", expanded=False):
            _pw = st.text_input("Password", type="password", key="story_pw")
            if st.button("Unlock", key="story_unlock"):
                if _pw == _admin_pw:
                    st.session_state["_story_admin"] = True
                    st.rerun()
                else:
                    st.error("Wrong password")
    else:
        st.success("Admin mode")
        if st.button("Lock", key="story_lock"):
            st.session_state["_story_admin"] = False
            st.rerun()

# ── Admin newsroom panel ───────────────────────────────────────────────────────
_date_from: date | None = None
_date_to:   date | None = None
_topic      = ""
_suggestions = ""
_generate_clicked = False

if _is_admin:
    st.markdown(
        '<div style="background:#0D1B2A;border:1px solid #D4A017;border-radius:10px;'
        'padding:1.25rem 1.5rem 1rem;margin-bottom:1.5rem">'
        '<div style="color:#D4A017;font-weight:700;font-size:1rem;'
        'letter-spacing:0.05em;margin-bottom:1rem">📰 NEWSROOM</div>',
        unsafe_allow_html=True,
    )

    _today = date.today()
    _c1, _c2, _c3 = st.columns([2, 1, 1])

    with _c1:
        _period_choice = st.radio(
            "Time period",
            ["Full tournament", "Last 3 days", "Last 7 days", "Custom"],
            horizontal=True,
            key="story_period",
        )
        if _period_choice == "Last 3 days":
            _date_from = _today - timedelta(days=3)
        elif _period_choice == "Last 7 days":
            _date_from = _today - timedelta(days=7)
        elif _period_choice == "Custom":
            _dc1, _dc2 = st.columns(2)
            _date_from = _dc1.date_input("From", value=_today - timedelta(days=7), key="story_from")
            _date_to   = _dc2.date_input("To",   value=_today,                     key="story_to")

    with _c2:
        _topic = st.text_input(
            "Angle / focus",
            placeholder="e.g. red card chaos",
            key="story_topic",
        )

    with _c3:
        st.write("")
        st.write("")
        if not _api_key:
            st.button("Generate", disabled=True, use_container_width=True,
                      help="Add GROQ_API_KEY to secrets")
        else:
            _generate_clicked = st.button(
                "Generate Story" if not _cache else "Regenerate",
                type="primary", use_container_width=True,
            )

    _suggestions = st.text_area(
        "Specific points to include (one per line)",
        placeholder=(
            "e.g. Make sure to mention the Germany 7-1 scoreline\n"
            "Highlight that Ivory Coast's upset helped certain players\n"
            "Note that Spain were held to a draw by Cabo Verde"
        ),
        height=110,
        key="story_suggestions",
    )

    if _cache:
        st.caption(
            f"Last generated: **{_cache.get('generated_at','?')}**  ·  "
            f"{_cache.get('matches_covered','?')} matches  ·  "
            f"Period: {_cache.get('period','?')}"
            + (f"  ·  Angle: _{_cache.get('topic','')}_" if _cache.get("topic") else "")
        )

    st.markdown("</div>", unsafe_allow_html=True)

# ── Generation ────────────────────────────────────────────────────────────────
if _generate_clicked:
    with st.spinner("Building match context and writing the story…"):
        try:
            ctx   = _build_story_context(date_from=_date_from, date_to=_date_to)
            story = _generate_story(ctx, _api_key, topic=_topic, suggestions=_suggestions)
            _cache = {
                "generated_at":    datetime.now().strftime("%d %b %Y at %H:%M"),
                "matches_covered": ctx["total_matches_played"],
                "period":          ctx["period"],
                "topic":           _topic.strip(),
                "story":           story,
                "featured_teams":  ctx["featured_teams"],
            }
            _save_cache(_cache)
            st.rerun()
        except Exception as exc:
            st.error(f"Generation failed: {exc}")

# ── Display ───────────────────────────────────────────────────────────────────
if _cache and "story" in _cache:
    _render_newspaper(
        story         = _cache["story"],
        meta          = _cache,
        featured_teams= _cache.get("featured_teams", []),
    )
else:
    if _is_admin:
        st.info("Configure the settings above and hit **Generate Story**.")
    else:
        st.info("No story published yet — check back soon.")
