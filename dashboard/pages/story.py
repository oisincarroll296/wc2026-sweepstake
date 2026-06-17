"""Tournament News — AI-generated newspaper-style narrative."""
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

# ── Newspaper colour palette ──────────────────────────────────────────────────
_BG      = "#F7F3EB"   # aged newsprint
_INK     = "#1A1008"   # near-black ink
_RED     = "#8B0000"   # headline red
_BORDER  = "#2A1A0A"
_MID     = "#5C4033"
_LIGHT   = "#9E8B7A"
_SECTION = "#D4A017"   # gold section rule (matches app)

# ── Flag CDN ──────────────────────────────────────────────────────────────────
_FLAG: dict[str, str] = {
    "Argentina":"ar","Australia":"au","Austria":"at","Belgium":"be",
    "Bosnia and Herzegovina":"ba","Brazil":"br","Canada":"ca","Cabo Verde":"cv",
    "Colombia":"co","Congo DR":"cd","Croatia":"hr","Curacao":"cw","Czechia":"cz",
    "Ecuador":"ec","Egypt":"eg","England":"gb-eng","France":"fr","Germany":"de",
    "Ghana":"gh","Haiti":"ht","IR Iran":"ir","Iraq":"iq","Japan":"jp","Jordan":"jo",
    "Korea Republic":"kr","Mexico":"mx","Morocco":"ma","Netherlands":"nl",
    "New Zealand":"nz","Norway":"no","Panama":"pa","Paraguay":"py","Portugal":"pt",
    "Qatar":"qa","Saudi Arabia":"sa","Scotland":"gb-sct","Senegal":"sn",
    "South Africa":"za","Spain":"es","Sweden":"se","Switzerland":"ch",
    "Cote d Ivoire":"ci","Tunisia":"tn","Tuerkiye":"tr","Uruguay":"uy",
    "USA":"us","Uzbekistan":"uz","Algeria":"dz",
}

def _flag_url(team: str, w: int = 40) -> str:
    c = _FLAG.get(team, "")
    return f"https://flagcdn.com/w{w}/{c}.png" if c else ""

# ── Player image library ──────────────────────────────────────────────────────
_PLAYER_IMG: dict[str, str] = {
    "Lionel Messi":   "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b4/Lionel-Messi-Argentina-2022-FIFA-World-Cup_%28cropped%29.jpg/400px-Lionel-Messi-Argentina-2022-FIFA-World-Cup_%28cropped%29.jpg",
    "Messi":          "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b4/Lionel-Messi-Argentina-2022-FIFA-World-Cup_%28cropped%29.jpg/400px-Lionel-Messi-Argentina-2022-FIFA-World-Cup_%28cropped%29.jpg",
    "Cristiano Ronaldo": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8c/Cristiano_Ronaldo_2018.jpg/400px-Cristiano_Ronaldo_2018.jpg",
    "Ronaldo":        "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8c/Cristiano_Ronaldo_2018.jpg/400px-Cristiano_Ronaldo_2018.jpg",
    "Kylian Mbappé":  "https://upload.wikimedia.org/wikipedia/commons/thumb/5/57/2019-07-17_SG_Dynamo_Dresden_vs_Paris_Saint-Germain_by_Sandro_Halank%E2%80%93165_%28cropped%29.jpg/400px-2019-07-17_SG_Dynamo_Dresden_vs_Paris_Saint-Germain_by_Sandro_Halank%E2%80%93165_%28cropped%29.jpg",
    "Mbappé":         "https://upload.wikimedia.org/wikipedia/commons/thumb/5/57/2019-07-17_SG_Dynamo_Dresden_vs_Paris_Saint-Germain_by_Sandro_Halank%E2%80%93165_%28cropped%29.jpg/400px-2019-07-17_SG_Dynamo_Dresden_vs_Paris_Saint-Germain_by_Sandro_Halank%E2%80%93165_%28cropped%29.jpg",
    "Erling Haaland": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/59/Erling_Haaland_2023_%28cropped%29.jpg/400px-Erling_Haaland_2023_%28cropped%29.jpg",
    "Haaland":        "https://upload.wikimedia.org/wikipedia/commons/thumb/5/59/Erling_Haaland_2023_%28cropped%29.jpg/400px-Erling_Haaland_2023_%28cropped%29.jpg",
    "Vinicius Junior":"https://upload.wikimedia.org/wikipedia/commons/thumb/0/04/Vinicius_Jr_2023.jpg/400px-Vinicius_Jr_2023.jpg",
    "Neymar":         "https://upload.wikimedia.org/wikipedia/commons/thumb/b/bc/Neymar_2022.jpg/400px-Neymar_2022.jpg",
}

def _player_img_url(name: str) -> str:
    for key, url in _PLAYER_IMG.items():
        if key.lower() in name.lower() or name.lower() in key.lower():
            return url
    return ""


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
    for col in ["match_number","home_goals","away_goals","extra_time",
                "comeback_home","comeback_away","home_hat_tricks","away_hat_tricks",
                "home_red_cards","away_red_cards","home_shirt_off","away_shirt_off",
                "home_gk_goals","away_gk_goals","home_first_eliminated","away_first_eliminated"]:
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
    pay_status: dict[str, str] = {}
    if not players_df.empty:
        pcols = ["WorldCupWinner","RunnerUp","BronzeMedal","GoldenBoot","DarkHorse","FirstKnockedOut"]
        for _, row in players_df.iterrows():
            p = str(row.get("Player",""))
            pay_status[p] = str(row.get("Status","UNPAID"))
            preds = {c: str(row.get(c,"") or "") for c in pcols
                     if str(row.get(c,"") or "") not in ("","nan")}
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
        home, away = str(m.get("home_team","")), str(m.get("away_team",""))
        hg, ag     = int(m.get("home_goals",0)), int(m.get("away_goals",0))
        match_num  = int(m.get("match_number",0))

        entry: dict = {
            "match": match_num, "date": str(m.get("match_date","")),
            "group": str(m.get("group","")), "home": home, "away": away,
            "score": f"{hg}–{ag}",
            "home_owners": ownership.get(home,[]),
            "away_owners": ownership.get(away,[]),
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
        for side, team in (("home",home),("away",away)):
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
        if abs(hg-ag) >= 3 and winner:
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
                "paid": pay_status.get(p,"UNPAID") == "PAID",
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

    n_players = len(standings)
    unpaid_top = [s for s in standings if not s["paid"] and s["rank"] <= max(1, n_players//2)]

    return {
        "sweepstake_info": (
            "14 friends, each owning 8 teams (2 per tier across 4 FIFA tiers). "
            "Points: Goal 1pt · Clean sheet 2pt · Win 3pt · "
            "Upset vs 1 tier higher +15pt, 2 tiers +30pt, 3 tiers +50pt · "
            "Hat trick 10pt · Shirt removal 25pt · GK goal 75pt · Red card −5pt. "
            "Captain earns ×1.5 their points. Only PAID players are eligible for prizes."
        ),
        "period": period_label,
        "matches_in_period": n_matches,
        "total_matches_played": n_all,
        "goals_in_period": total_goals,
        "avg_goals_per_game": round(total_goals/n_matches,2) if n_matches else 0,
        "current_standings": standings,
        "unpaid_players_in_top_half": unpaid_top,
        "match_results": match_narratives,
        "upsets": upsets,
        "hat_tricks": hat_tricks,
        "special_events": special_events,
        "top_scoring_teams": top_teams,
        "featured_teams": sorted(featured_teams),
    }


# ── LLM ──────────────────────────────────────────────────────────────────────

def _generate_story(context: dict, api_key: str, topic: str = "", suggestions: str = "") -> dict:
    from groq import Groq
    client = Groq(api_key=api_key)

    extras = []
    if topic.strip():
        extras.append(f"ANGLE: {topic.strip()}")
    if suggestions.strip():
        extras.append(f"SPECIFIC POINTS TO INCLUDE:\n{suggestions.strip()}")
    extras_block = ("\n\n" + "\n\n".join(extras)) if extras else ""

    system = (
        "You are a sharp tabloid football journalist writing the front page of a private World Cup 2026 sweepstake newspaper. "
        "Your audience is 14 friends. You write like a passionate sports tabloid — vivid, dramatic, specific, occasionally cheeky. "
        "You always connect on-pitch events to their sweepstake consequences (who owns the team, how many points they earned)."
    )

    user = f"""Write a full newspaper edition covering: {context['period']}.
{extras_block}

DATA:
<data>
{json.dumps(context, indent=2)}
</data>

OUTPUT: a single valid JSON object with exactly these keys:

{{
  "headline": "ALL-CAPS PUNCHY FRONT-PAGE HEADLINE (max 10 words)",
  "subheadline": "One dramatic sentence expanding on the headline",
  "lead_paragraph": "The single most dramatic moment, vividly told. 3-4 sentences. Name players and scorelines.",
  "sections": [
    {{"title": "SECTION TITLE IN CAPS", "content": "3-4 sentences. Each section covers a distinct theme with no repeated facts from other sections."}},
    {{"title": "...", "content": "..."}},
    {{"title": "...", "content": "..."}},
    {{"title": "...", "content": "..."}}
  ],
  "player_spotlight": {{
    "name": "Full player name",
    "team": "Their national team",
    "achievement": "One-line stat or moment",
    "narrative": "2-3 sentences telling their story dramatically"
  }},
  "featured_players": ["Full player name", ...],
  "sweepstake_digest": "3-4 sentences: who leads, who's struggling, any unpaid players doing well",
  "pull_quote": "One vivid sentence — a stat or moment — perfect as a big pull quote",
  "looking_ahead": "2-3 sentences on what fixtures or moments to watch next"
}}

RULES:
- Include 4 sections, each with a different theme (e.g. biggest results, upsets, special events, goals, sweepstake drama)
- Name sweepstake players when their teams do something notable
- Use real scorelines and team names — never invent facts
- Each section must cover new ground — no repeated information across sections
- player_spotlight must be a real player involved in a notable event from the data
- featured_players is the list of player names to display photos for — only include players with notable events
- Tone: tabloid football journalist — passionate, vivid, specific
- Respond ONLY with the JSON object — no markdown fences, no extra text
"""

    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role":"system","content":system},{"role":"user","content":user}],
        max_tokens=2000,
        temperature=0.75,
        response_format={"type":"json_object"},
    )
    raw = resp.choices[0].message.content
    try:
        return json.loads(raw)
    except Exception:
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            return json.loads(m.group())
        return {"headline":"STORY GENERATED","subheadline":"","lead_paragraph":raw,
                "sections":[],"player_spotlight":{},"featured_players":[],
                "sweepstake_digest":"","pull_quote":"","looking_ahead":""}


# ── Newspaper renderer ────────────────────────────────────────────────────────

def _ink(text: str, size: str = "0.92rem", weight: str = "400", extra: str = "") -> str:
    return f'<span style="color:{_INK};font-size:{size};font-weight:{weight};{extra}">{text}</span>'

def _score_card(home: str, away: str, hg: int, ag: int) -> str:
    hf = _flag_url(home, 40)
    af = _flag_url(away, 40)
    hf_img = f'<img src="{hf}" style="height:28px;border-radius:2px;vertical-align:middle;margin-right:6px">' if hf else ""
    af_img = f'<img src="{af}" style="height:28px;border-radius:2px;vertical-align:middle;margin-left:6px">' if af else ""
    winner_home = "font-weight:800" if hg > ag else "font-weight:400;opacity:0.6"
    winner_away = "font-weight:800" if ag > hg else "font-weight:400;opacity:0.6"
    return (
        f'<div style="display:flex;align-items:center;justify-content:space-between;'
        f'background:white;border:1px solid {_BORDER}22;border-radius:6px;'
        f'padding:0.5rem 0.8rem;margin-bottom:0.5rem">'
        f'<span style="color:{_INK};{winner_home};font-size:0.85rem">{hf_img}{home}</span>'
        f'<span style="color:{_RED};font-weight:900;font-size:1.1rem;padding:0 0.6rem">{hg}–{ag}</span>'
        f'<span style="color:{_INK};{winner_away};font-size:0.85rem;text-align:right">{away}{af_img}</span>'
        f'</div>'
    )

def _stat_box(value: str, label: str, color: str = _RED) -> str:
    return (
        f'<div style="background:white;border-top:3px solid {color};'
        f'border:1px solid {_BORDER}22;border-top:3px solid {color};'
        f'padding:0.7rem 0.6rem;text-align:center;border-radius:4px">'
        f'<div style="font-size:1.8rem;font-weight:900;color:{color};line-height:1">{value}</div>'
        f'<div style="font-size:0.68rem;color:{_MID};letter-spacing:0.08em;margin-top:0.15rem;text-transform:uppercase">{label}</div>'
        f'</div>'
    )

def _section_rule(title: str) -> str:
    return (
        f'<div style="display:flex;align-items:center;gap:0.6rem;margin:1.4rem 0 0.7rem">'
        f'<div style="flex:1;height:2px;background:{_BORDER}"></div>'
        f'<div style="color:{_INK};font-size:0.7rem;font-weight:900;letter-spacing:0.12em;'
        f'white-space:nowrap">{title}</div>'
        f'<div style="flex:1;height:2px;background:{_BORDER}"></div>'
        f'</div>'
    )

def _render_newspaper(story: dict, meta: dict, context: dict) -> None:
    today_str  = datetime.now().strftime("%A, %d %B %Y").upper()
    ft         = context.get("featured_teams", [])
    matches    = context.get("match_results", [])
    upsets     = context.get("upsets", [])
    specials   = context.get("special_events", [])
    top_teams  = context.get("top_scoring_teams", [])
    standings  = context.get("current_standings", [])
    fp_names   = story.get("featured_players", [])
    spotlight  = story.get("player_spotlight", {})

    # Wrapper: cream newspaper background
    st.markdown(
        f'<div style="background:{_BG};color:{_INK};font-family:Georgia,serif;'
        f'border-radius:8px;padding:1.2rem 1rem 1.5rem;'
        f'box-shadow:0 4px 24px #0006;max-width:900px;margin:0 auto">',
        unsafe_allow_html=True,
    )

    # ── Masthead ──
    flag_strip = ""
    for t in ft[:10]:
        u = _flag_url(t, 40)
        if u:
            flag_strip += f'<img src="{u}" style="height:22px;border-radius:2px;margin:0 2px;vertical-align:middle" title="{t}">'

    st.markdown(
        f'<div style="border-top:3px solid {_BORDER};border-bottom:3px solid {_BORDER};'
        f'padding:0.5rem 0;margin-bottom:0.1rem">'
        f'<div style="font-size:clamp(1.6rem,5vw,2.8rem);font-weight:900;text-align:center;'
        f'letter-spacing:0.06em;color:{_INK};line-height:1.1">THE SWEEPSTAKE GAZETTE</div>'
        f'</div>'
        f'<div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:0.3rem;'
        f'font-size:0.65rem;color:{_MID};padding:0.3rem 0;border-bottom:1px solid {_BORDER}55;'
        f'margin-bottom:0.6rem">'
        f'<span>WC 2026 · Private Edition</span>'
        f'<span style="text-align:center">{flag_strip}</span>'
        f'<span>{today_str}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Stat bar ──
    n_matches = context.get("matches_in_period", 0)
    n_goals   = context.get("goals_in_period", 0)
    n_upsets  = len(upsets)
    n_special = len(specials)
    avg       = context.get("avg_goals_per_game", 0)

    s1, s2, s3, s4 = st.columns(4)
    s1.markdown(_stat_box(str(n_matches), "Matches Played", _RED),    unsafe_allow_html=True)
    s2.markdown(_stat_box(str(n_goals),   "Goals Scored",   "#1a5c1a"), unsafe_allow_html=True)
    s3.markdown(_stat_box(str(n_upsets),  "Upsets",         "#8B4500"), unsafe_allow_html=True)
    s4.markdown(_stat_box(str(n_special), "Special Events",  "#2A4A8B"), unsafe_allow_html=True)

    # ── Headline ──
    headline    = story.get("headline","").upper()
    subheadline = story.get("subheadline","")
    st.markdown(
        f'<div style="text-align:center;padding:1rem 0 0.8rem;'
        f'border-bottom:2px solid {_BORDER}">'
        f'<div style="font-size:clamp(1.4rem,4vw,2.2rem);font-weight:900;line-height:1.15;'
        f'color:{_INK};letter-spacing:0.01em">{headline}</div>'
        f'<div style="color:{_RED};font-size:1rem;margin-top:0.4rem;font-style:italic">{subheadline}</div>'
        f'<div style="color:{_LIGHT};font-size:0.7rem;margin-top:0.3rem">'
        f'By Your Sweepstake Correspondent'
        + (f' &nbsp;·&nbsp; {meta.get("topic")}' if meta.get("topic") else "")
        + f'</div></div>',
        unsafe_allow_html=True,
    )

    # ── Lead + pull quote ──
    lead = story.get("lead_paragraph","")
    pull = story.get("pull_quote","")

    col_lead, col_pull = st.columns([2,1])
    with col_lead:
        if lead:
            st.markdown(
                f'<p style="font-size:1.05rem;line-height:1.85;font-weight:600;'
                f'color:{_INK};margin:0.9rem 0 0">{lead}</p>',
                unsafe_allow_html=True,
            )
    with col_pull:
        if pull:
            st.markdown(
                f'<div style="background:{_RED}11;border-left:4px solid {_RED};'
                f'padding:0.9rem 0.9rem 0.9rem 1rem;margin-top:0.9rem;border-radius:0 4px 4px 0">'
                f'<div style="color:{_LIGHT};font-size:0.62rem;letter-spacing:0.1em;margin-bottom:0.4rem">'
                f'PULL QUOTE</div>'
                f'<div style="color:{_RED};font-size:1rem;font-style:italic;line-height:1.55">"{pull}"</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ── Sections ──
    sections = story.get("sections", [])
    for i, sec in enumerate(sections):
        title   = sec.get("title","")
        content = sec.get("content","")
        if not content:
            continue

        st.markdown(_section_rule(title), unsafe_allow_html=True)

        # Intersperse match score cards after "results" sections
        is_results = any(w in title.upper() for w in ["RESULT","MATCH","SCORE","WIN","GOAL","FIXTURE"])
        is_upset   = "UPSET" in title.upper()

        st.markdown(
            f'<p style="font-size:0.92rem;line-height:1.8;color:{_INK};margin:0">{content}</p>',
            unsafe_allow_html=True,
        )

        # Show score cards for notable matches after results sections
        if is_results and matches:
            notable = [m for m in matches if abs(int(m.get("score","0–0").split("–")[0]) -
                       int(m.get("score","0–0").split("–")[1])) >= 3
                       or m.get("notable_events")]
            if notable:
                st.markdown(_section_rule("NOTABLE SCORELINES"), unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                for j, m in enumerate(notable[:6]):
                    home  = m.get("home","")
                    away  = m.get("away","")
                    score = m.get("score","0–0")
                    parts = score.split("–")
                    hg_   = int(parts[0]) if len(parts)==2 else 0
                    ag_   = int(parts[1]) if len(parts)==2 else 0
                    card  = _score_card(home, away, hg_, ag_)
                    if j % 2 == 0:
                        c1.markdown(card, unsafe_allow_html=True)
                    else:
                        c2.markdown(card, unsafe_allow_html=True)

        # Upset graphic
        if is_upset and upsets:
            for u in upsets:
                wf = _flag_url(u["winner"], 40)
                lf = _flag_url(u["loser"],  40)
                wf_img = f'<img src="{wf}" style="height:24px;border-radius:2px;vertical-align:middle;margin-right:5px">' if wf else ""
                lf_img = f'<img src="{lf}" style="height:24px;border-radius:2px;vertical-align:middle;margin-right:5px">' if lf else ""
                st.markdown(
                    f'<div style="background:#FFF3E0;border:1px solid #E65100;border-left:4px solid #E65100;'
                    f'border-radius:0 6px 6px 0;padding:0.6rem 0.9rem;margin:0.6rem 0">'
                    f'<div style="font-size:0.62rem;font-weight:700;letter-spacing:0.1em;'
                    f'color:#E65100;margin-bottom:0.3rem">⚡ UPSET ALERT — TIER {u["winner_tier"]} BEATS TIER {u["loser_tier"]}</div>'
                    f'<div style="color:{_INK};font-size:0.9rem">'
                    f'{wf_img}<strong>{u["winner"]}</strong> {u["score"]} '
                    f'{lf_img}{u["loser"]} &nbsp;'
                    f'<span style="color:#E65100;font-weight:700">+{u["bonus_pts_each_owner"]} pts</span>'
                    f' for owners: {", ".join(u.get("winner_owners",[]))}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    # ── Player spotlight ──
    if spotlight and spotlight.get("name"):
        pname    = spotlight.get("name","")
        pteam    = spotlight.get("team","")
        pachieve = spotlight.get("achievement","")
        pnarr    = spotlight.get("narrative","")
        pimg_url = _player_img_url(pname)
        pflag    = _flag_url(pteam, 40)

        st.markdown(_section_rule("PLAYER SPOTLIGHT"), unsafe_allow_html=True)

        pcol_img, pcol_text = st.columns([1,2])
        with pcol_img:
            if pimg_url:
                st.markdown(
                    f'<img src="{pimg_url}" '
                    f'style="width:100%;max-width:220px;border-radius:6px;'
                    f'border:2px solid {_BORDER};display:block;margin:0 auto"'
                    f'onerror="this.style.display=\'none\'">',
                    unsafe_allow_html=True,
                )
            elif pflag:
                st.markdown(
                    f'<img src="{pflag}" style="width:80px;border-radius:4px;'
                    f'display:block;margin:0 auto">',
                    unsafe_allow_html=True,
                )
        with pcol_text:
            flag_badge = f'<img src="{pflag}" style="height:16px;vertical-align:middle;border-radius:2px;margin-right:4px">' if pflag else ""
            st.markdown(
                f'<div style="padding:0.4rem 0">'
                f'<div style="font-size:1.4rem;font-weight:900;color:{_INK}">{pname}</div>'
                f'<div style="font-size:0.78rem;color:{_MID};margin:0.2rem 0 0.6rem">'
                f'{flag_badge}{pteam} &nbsp;·&nbsp; <em>{pachieve}</em></div>'
                f'<p style="font-size:0.9rem;line-height:1.75;color:{_INK};margin:0">{pnarr}</p>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ── Sweepstake digest + top scorers (side by side) ──
    digest    = story.get("sweepstake_digest","")
    looking   = story.get("looking_ahead","")

    st.markdown(_section_rule("SWEEPSTAKE DIGEST"), unsafe_allow_html=True)

    dcol, tcol = st.columns([3,2])
    with dcol:
        if digest:
            st.markdown(
                f'<p style="font-size:0.9rem;line-height:1.8;color:{_INK};margin:0">{digest}</p>',
                unsafe_allow_html=True,
            )
        # Top 5 leaderboard mini-table
        if standings:
            rows_html = ""
            for s in standings[:5]:
                paid_badge = (
                    f'<span style="background:#1a5c1a;color:white;font-size:0.58rem;'
                    f'padding:1px 4px;border-radius:3px;margin-left:4px">PAID</span>'
                    if s.get("paid") else
                    f'<span style="background:{_RED};color:white;font-size:0.58rem;'
                    f'padding:1px 4px;border-radius:3px;margin-left:4px">UNPAID</span>'
                )
                rows_html += (
                    f'<tr>'
                    f'<td style="color:{_MID};font-size:0.75rem;padding:0.25rem 0.4rem;'
                    f'text-align:center;border-bottom:1px solid {_BORDER}22">{s["rank"]}</td>'
                    f'<td style="color:{_INK};font-size:0.8rem;font-weight:600;padding:0.25rem 0.4rem;'
                    f'border-bottom:1px solid {_BORDER}22">{s["player"]}{paid_badge}</td>'
                    f'<td style="color:{_RED};font-size:0.8rem;font-weight:700;padding:0.25rem 0.4rem;'
                    f'text-align:right;border-bottom:1px solid {_BORDER}22">{s["total_pts"]}</td>'
                    f'</tr>'
                )
            st.markdown(
                f'<div style="margin-top:0.8rem">'
                f'<div style="font-size:0.62rem;font-weight:700;letter-spacing:0.1em;'
                f'color:{_MID};margin-bottom:0.4rem">CURRENT STANDINGS (TOP 5)</div>'
                f'<table style="width:100%;border-collapse:collapse">'
                f'<thead><tr>'
                f'<th style="color:{_LIGHT};font-size:0.62rem;padding:0.2rem 0.4rem;text-align:center">#</th>'
                f'<th style="color:{_LIGHT};font-size:0.62rem;padding:0.2rem 0.4rem;text-align:left">Player</th>'
                f'<th style="color:{_LIGHT};font-size:0.62rem;padding:0.2rem 0.4rem;text-align:right">Pts</th>'
                f'</tr></thead><tbody>{rows_html}</tbody></table>'
                f'</div>',
                unsafe_allow_html=True,
            )
    with tcol:
        if top_teams:
            bars_html = ""
            max_g = top_teams[0]["group_goals"] if top_teams else 1
            for t in top_teams[:6]:
                tf  = _flag_url(t["team"], 40)
                tf_img = f'<img src="{tf}" style="height:16px;border-radius:2px;vertical-align:middle;margin-right:4px">' if tf else ""
                pct = round(t["group_goals"] / max_g * 100)
                bars_html += (
                    f'<div style="margin-bottom:0.35rem">'
                    f'<div style="display:flex;justify-content:space-between;'
                    f'font-size:0.75rem;color:{_INK};margin-bottom:2px">'
                    f'<span>{tf_img}{t["team"]}</span>'
                    f'<span style="font-weight:700;color:{_RED}">{t["group_goals"]} ⚽</span></div>'
                    f'<div style="background:{_BORDER}22;border-radius:2px;height:6px">'
                    f'<div style="background:{_RED};width:{pct}%;height:6px;border-radius:2px"></div>'
                    f'</div></div>'
                )
            st.markdown(
                f'<div style="background:white;border:1px solid {_BORDER}22;border-radius:6px;'
                f'padding:0.8rem">'
                f'<div style="font-size:0.62rem;font-weight:700;letter-spacing:0.1em;'
                f'color:{_MID};margin-bottom:0.6rem">TOP SCORERS BY TEAM</div>'
                f'{bars_html}</div>',
                unsafe_allow_html=True,
            )

    # ── Looking ahead ──
    if looking:
        st.markdown(
            f'<div style="border-top:2px solid {_BORDER};margin-top:1.2rem;padding-top:0.7rem">'
            f'<span style="font-size:0.62rem;font-weight:900;letter-spacing:0.12em;color:{_RED}">'
            f'LOOKING AHEAD &nbsp;</span>'
            f'<span style="font-size:0.88rem;color:{_MID}">{looking}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Footer ──
    st.markdown(
        f'<div style="text-align:center;margin-top:1.2rem;padding-top:0.6rem;'
        f'border-top:1px solid {_BORDER}33;font-size:0.62rem;color:{_LIGHT}">'
        f'Generated {meta.get("generated_at","?")} &nbsp;·&nbsp; '
        f'{meta.get("matches_covered","?")} matches covered &nbsp;·&nbsp; '
        f'The Sweepstake Gazette © 2026</div>',
        unsafe_allow_html=True,
    )

    # Close wrapper div
    st.markdown("</div>", unsafe_allow_html=True)


# ── Page ──────────────────────────────────────────────────────────────────────

page_header("Tournament News", "AI-generated newspaper from live match data")

_api_key  = st.secrets.get("GROQ_API_KEY", "")
_admin_pw = st.secrets.get("ADMIN_PASSWORD", "wc2026admin")
_cache    = _load_cache()
_is_admin = st.session_state.get("_story_admin", False)

# ── Admin login ────────────────────────────────────────────────────────────────
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

# ── Admin newsroom ─────────────────────────────────────────────────────────────
_date_from: date | None = None
_date_to:   date | None = None
_topic       = ""
_suggestions = ""
_generate_clicked = False

if _is_admin:
    st.markdown(
        f'<div style="background:#0D1B2A;border:1px solid {_SECTION};'
        f'border-radius:10px;padding:1.25rem 1.5rem 1.2rem;margin-bottom:1.5rem">',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div style="color:{_SECTION};font-weight:700;font-size:1rem;'
        f'letter-spacing:0.05em;margin-bottom:1rem">📰 NEWSROOM</div>',
        unsafe_allow_html=True,
    )

    _today = date.today()
    _rc1, _rc2, _rc3 = st.columns([2,1,1])
    with _rc1:
        _period_choice = st.radio(
            "Time period",
            ["Full tournament","Last 3 days","Last 7 days","Custom"],
            horizontal=True, key="story_period",
        )
        if _period_choice == "Last 3 days":
            _date_from = _today - timedelta(days=3)
        elif _period_choice == "Last 7 days":
            _date_from = _today - timedelta(days=7)
        elif _period_choice == "Custom":
            _dc1, _dc2 = st.columns(2)
            _date_from = _dc1.date_input("From", value=_today-timedelta(days=7), key="story_from")
            _date_to   = _dc2.date_input("To",   value=_today,                   key="story_to")
    with _rc2:
        _topic = st.text_input("Angle", placeholder="e.g. red card chaos", key="story_topic")
    with _rc3:
        st.write("")
        st.write("")
        _generate_clicked = st.button(
            "Generate" if not _cache else "Regenerate",
            type="primary", use_container_width=True,
            disabled=not _api_key,
            help="Add GROQ_API_KEY to secrets" if not _api_key else "",
        )

    _suggestions = st.text_area(
        "Specific points / players to include (one per line)",
        placeholder=(
            "Messi scored the hat trick for Argentina vs Algeria\n"
            "Focus on unpaid players doing well\n"
            "Highlight the red card chaos in match 1"
        ),
        height=100, key="story_suggestions",
    )

    if _cache:
        st.caption(
            f"Last: **{_cache.get('generated_at','?')}** · "
            f"{_cache.get('matches_covered','?')} matches · "
            f"Period: {_cache.get('period','?')}"
            + (f" · _{_cache.get('topic','')}_" if _cache.get("topic") else "")
        )

    st.markdown("</div>", unsafe_allow_html=True)

# ── Generation ────────────────────────────────────────────────────────────────
if _generate_clicked:
    with st.spinner("Building context and writing the story…"):
        try:
            ctx   = _build_story_context(date_from=_date_from, date_to=_date_to)
            story = _generate_story(ctx, _api_key, topic=_topic, suggestions=_suggestions)
            _cache = {
                "generated_at":    datetime.now().strftime("%d %b %Y at %H:%M"),
                "matches_covered": ctx["total_matches_played"],
                "period":          ctx["period"],
                "topic":           _topic.strip(),
                "story":           story,
                "context":         ctx,
            }
            _save_cache(_cache)
            st.rerun()
        except Exception as exc:
            st.error(f"Generation failed: {exc}")

# ── Display ───────────────────────────────────────────────────────────────────
if _cache and "story" in _cache and "context" in _cache:
    _render_newspaper(
        story  = _cache["story"],
        meta   = _cache,
        context= _cache["context"],
    )
elif _cache and "story" in _cache:
    # Legacy cache without context — rebuild it for rendering
    try:
        _ctx = _build_story_context()
        _render_newspaper(story=_cache["story"], meta=_cache, context=_ctx)
    except Exception:
        st.markdown(_cache["story"])
else:
    if _is_admin:
        st.info("Configure settings above and hit **Generate**.")
    else:
        st.info("No story published yet — check back soon.")
