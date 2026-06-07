"""Cached data-loading layer for the dashboard.

All functions are decorated with @st.cache_data (TTL 30 s) so that rapid
page switches don't re-hit the filesystem on every render.  Admin actions
call st.cache_data.clear() to force a refresh after writes.
"""
import sys
from pathlib import Path

# Ensure project root is on sys.path regardless of working directory
_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st
import pandas as pd

from src.team_database  import load_teams
from src.scoring_engine import load_match_stats, load_predictions, load_captains
from src.competition    import (
    load_player_status, load_purchases, load_events, load_audit_log,
    calculate_prize_pool, prize_leaderboard, overall_leaderboard,
    get_team_ownership, get_predictions_centre,
)
from src.event_engine      import load_allocation


# ── Raw loaders (TTL 30 s) ──────────────────────────────────────────────────

@st.cache_data(ttl=30)
def get_teams() -> pd.DataFrame:
    return load_teams()


@st.cache_data(ttl=30)
def get_match_stats() -> pd.DataFrame:
    return load_match_stats()


@st.cache_data(ttl=30)
def get_purchases() -> pd.DataFrame:
    return load_purchases()


@st.cache_data(ttl=30)
def get_statuses() -> pd.DataFrame:
    return load_player_status()


@st.cache_data(ttl=30)
def get_events() -> pd.DataFrame:
    return load_events()


@st.cache_data(ttl=30)
def get_audit_log() -> pd.DataFrame:
    return load_audit_log()


@st.cache_data(ttl=30)
def get_predictions() -> pd.DataFrame:
    return load_predictions()


@st.cache_data(ttl=30)
def get_captains() -> pd.DataFrame:
    return load_captains()


@st.cache_data(ttl=30)
def get_assignments() -> dict[str, list[str]]:
    return load_allocation().assignments


# ── Derived loaders ─────────────────────────────────────────────────────────

@st.cache_data(ttl=30)
def get_prize_pool() -> dict:
    return calculate_prize_pool(get_purchases())


@st.cache_data(ttl=30)
def get_tier_map() -> dict[str, int]:
    df = get_teams()
    return dict(zip(df["Team"], df["Tier"].astype(int)))


@st.cache_data(ttl=30)
def get_participants() -> list[str]:
    st = get_statuses()
    return sorted(st["Player"].unique().tolist()) if not st.empty else []


@st.cache_data(ttl=30)
def get_prize_leaderboard() -> pd.DataFrame:
    parts = get_participants()
    if not parts:
        return pd.DataFrame()
    return prize_leaderboard(
        parts, get_assignments(), get_match_stats(),
        get_purchases(), get_captains(), get_predictions(),
        get_statuses(),
    )


@st.cache_data(ttl=30)
def get_overall_leaderboard() -> pd.DataFrame:
    parts = get_participants()
    if not parts:
        return pd.DataFrame()
    return overall_leaderboard(
        parts, get_assignments(), get_match_stats(),
        get_purchases(), get_captains(), get_predictions(),
        get_statuses(),
    )


@st.cache_data(ttl=30)
def get_team_ownership_data() -> dict:
    return get_team_ownership(
        get_assignments(), get_captains(), get_predictions(), get_purchases()
    )


@st.cache_data(ttl=30)
def get_predictions_centre_data() -> dict:
    return get_predictions_centre(get_predictions())


@st.cache_data(ttl=30)
def get_next_event() -> dict | None:
    ev = get_events()
    if ev.empty:
        return None
    pending = ev[ev["Status"].isin(["SCHEDULED", "OPEN"])]
    if pending.empty:
        return None
    row = pending.iloc[0]
    return {"type": row["EventType"], "time": row.get("ScheduledTime", "")}


@st.cache_data(ttl=30)
def get_paid_count() -> int:
    st = get_statuses()
    if st.empty:
        return 0
    return int((st["Status"] == "PAID").sum())


@st.cache_data(ttl=30)
def get_pack_count() -> int:
    p = get_purchases()
    if p.empty:
        return 0
    return int(((p["PurchaseType"] == "PACK") & (p["Status"] == "PROCESSED")).sum())


@st.cache_data(ttl=30)
def get_top_team() -> tuple[str, float] | tuple[None, None]:
    ms   = get_match_stats()
    tmap = get_tier_map()
    if ms.empty:
        return None, None
    from src.scoring_engine import calculate_team_points
    best, best_pts = None, -1.0
    for _, row in ms.iterrows():
        t    = str(row["Team"])
        tier = tmap.get(t, 1)
        pts  = calculate_team_points(t, ms, tier)["total"]
        if pts > best_pts:
            best_pts = pts
            best = t
    return best, best_pts


def is_predictions_locked() -> bool:
    lock = _ROOT / "data" / "predictions_lock.txt"
    return lock.exists() and lock.stat().st_size > 0


def get_deadlines() -> dict:
    """Load deadlines from data/deadlines.json. Returns {} if file absent."""
    import json
    p = _ROOT / "data" / "deadlines.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_deadlines(d: dict) -> None:
    import json
    p = _ROOT / "data" / "deadlines.json"
    p.write_text(json.dumps(d, indent=2), encoding="utf-8")


def countdown(iso: str) -> str:
    """Return 'Xd Yh Zm' remaining, or 'PASSED' if in the past."""
    from datetime import datetime, timezone
    try:
        target = datetime.fromisoformat(iso).astimezone(timezone.utc)
        diff = target - datetime.now(timezone.utc)
        if diff.total_seconds() <= 0:
            return "PASSED"
        s = int(diff.total_seconds())
        parts = []
        if s >= 86400:
            parts.append(f"{s // 86400}d")
            s %= 86400
        if s >= 3600:
            parts.append(f"{s // 3600}h")
            s %= 3600
        parts.append(f"{s // 60}m")
        return " ".join(parts)
    except Exception:
        return "—"


DEADLINE_LABELS: dict[str, str] = {
    "prediction_lock":           "Prediction Lock",
    "buy_in_deadline":           "Buy-In Deadline",
    "pre_tournament_captain":    "Pre-Tournament Captain",
    "mulligan_deadline":         "Mulligan Deadline",
    "group_stage_closes":        "Group Stage Closes",
    "ninth_team_draw":           "Ninth Team Draw",
    "knockout_captain_deadline": "Knockout Captain Deadline",
    "resurrection_window_close": "Resurrection Window Closes",
    "tournament_end":            "Tournament End",
}
