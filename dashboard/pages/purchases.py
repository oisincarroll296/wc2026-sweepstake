"""Shop & Purchases — buy add-ons, view your budget, track who has what."""
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
_p = str(Path(__file__).resolve().parent.parent.parent); sys.path.insert(0, _p) if _p not in sys.path else None

import streamlit as st
import pandas as pd

from dashboard.data import (
    get_purchases, get_statuses, get_participants,
    get_player_budgets, get_prize_pool, get_deadlines,
)
from dashboard.components.ui import page_header, empty_state

# ── Colour tokens ─────────────────────────────────────────────────────────────
_GRP = "#F59E0B"   # amber  — before group stage closes
_KO  = "#22D3EE"   # cyan   — before knockout stage

# ── Deadline helpers (read fresh from disk each page render) ──────────────────
_deadline_key: dict[str, str] = {
    "BuyIn":          "buy_in_deadline",
    "PredictionPack": "prediction_lock",
    "Mulligan":       "mulligan_deadline",
    "Insurance":      "group_stage_closes",
    "NinthTeam":      "ninth_team_draw",
    "Resurrection":   "resurrection_window_close",
}
_deadline_colour: dict[str, str] = {
    "BuyIn": _GRP, "PredictionPack": _GRP, "Mulligan": _GRP, "Insurance": _GRP,
    "NinthTeam": _KO, "Resurrection": _KO,
}


def _deadline_dt(pt: str) -> datetime | None:
    key = _deadline_key.get(pt, "")
    if not key:
        return None
    raw = get_deadlines().get(key, "")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except Exception:
        return None


def _is_open(pt: str) -> bool:
    dl = _deadline_dt(pt)
    return dl is None or datetime.now(tz=timezone.utc) < dl


def _deadline_label(pt: str) -> str:
    dl = _deadline_dt(pt)
    if dl is None:
        return ""
    now = datetime.now(tz=timezone.utc)
    if now >= dl:
        return "🔒 Closed"
    _IST = timezone(timedelta(hours=1))
    local = dl.astimezone(_IST)
    return f"⏰ Closes {local.day} {local.strftime('%b %H:%M')}"


# ── Page ──────────────────────────────────────────────────────────────────────
page_header("Shop & Purchases", "Add-ons, your budget, and the full purchase ledger")

participants = get_participants()
purchases    = get_purchases()
statuses     = get_statuses()
budgets_df   = get_player_budgets()
prize_pool   = get_prize_pool()

if not participants:
    empty_state("No participants found.")
    st.stop()

# ── Build lookup structures ───────────────────────────────────────────────────
status_map: dict[str, str] = {}
if not statuses.empty:
    for _, r in statuses.iterrows():
        status_map[r["Player"]] = r.get("Status", "UNPAID")

PTYPES = [
    ("BuyIn",         "Buy In",      5,  _GRP),
    ("PredictionPack","Pack",        5,  _GRP),
    ("Insurance",     "Insurance",   2,  _GRP),
    ("Mulligan",      "Mulligan",    3,  _GRP),
    ("NinthTeam",     "Ninth",       3,  _KO),
    ("Resurrection",  "Resurrection",5,  _KO),
]
COSTS = {pt: cost for pt, _, cost, _ in PTYPES}

processed: dict[str, set] = {}
if not purchases.empty:
    for _, r in purchases.iterrows():
        processed.setdefault(r["Player"], set()).add(r["PurchaseType"])

# ── Budget notice ──────────────────────────────────────────────────────────────
st.markdown(
    '<div style="background:#1A2535;border:1px solid #2A3A4A;border-radius:8px;'
    'padding:0.75rem 1rem;margin-bottom:1rem;font-size:0.84rem;color:#E5E7EB;line-height:1.6">'
    '<strong style="color:#D4A017">ℹ️ How budgets work</strong><br>'
    'Budgets represent money you\'ve contributed to the Revolut pocket — not a virtual allowance. '
    'They are updated manually by the administrator each evening when the latest data is published. '
    'Your available balance = Budget minus the total of your recorded purchases.'
    '</div>',
    unsafe_allow_html=True,
)

# ── Tabs: Shop · My Budget · Ledger ──────────────────────────────────────────
tab_shop, tab_budget, tab_ledger = st.tabs(["🛒 Shop", "💰 My Budget", "📋 Ledger"])

# ═══════════════════════════════════════
# TAB 1: SHOP
# ═══════════════════════════════════════
with tab_shop:

    # How-to-buy instructions
    _price_chips = "".join(
        f'<span style="background:#0D1B2A;border:1px solid {c}44;border-left:3px solid {c};'
        f'border-radius:6px;padding:0.2rem 0.6rem;font-size:0.78rem;color:#F5F5F5;white-space:nowrap">'
        f'{lbl} <strong style="color:#D4A017">€{cost}</strong></span> '
        for lbl, cost, c in [
            ("Buy In", 5, _GRP), ("Prediction Pack", 5, _GRP),
            ("Insurance", 2, _GRP), ("Mulligan", 3, _GRP),
            ("Ninth Team", 3, _KO), ("Resurrection", 5, _KO),
        ]
    )
    _legend = (
        f'<div style="margin-top:0.4rem;display:flex;gap:1rem;font-size:0.74rem;color:#9CA3AF">'
        f'<span><span style="color:{_GRP};font-weight:700">▌</span> Before group stage closes</span>'
        f'<span><span style="color:{_KO};font-weight:700">▌</span> Before knockout stage</span>'
        f'</div>'
    )
    st.markdown(
        '<div style="background:#1A2535;border:1px solid #D4A01744;border-radius:10px;'
        'padding:0.85rem 1.1rem;margin-bottom:1.1rem">'
        '<div style="color:#D4A017;font-weight:700;font-size:0.92rem;margin-bottom:0.45rem">'
        '💳 How to Buy an Add-On</div>'
        '<div style="color:#E5E7EB;font-size:0.84rem;line-height:1.7">'
        '1. Send the money to the <strong style="color:#D4A017">Shared Revolut Pocket</strong> '
        'and include what you\'re buying in the transaction message<br>'
        '2. <strong>Ninth Team</strong> — randomly drawn from surviving teams you don\'t own<br>'
        '&nbsp;&nbsp;&nbsp;<strong>Resurrection</strong> — you choose which eliminated team to replace; '
        'a same-tier replacement is chosen by you and recorded by admin<br>'
        '3. <strong>Prediction Pack</strong> — send your picks (World Cup winner, Golden Boot, Dark Horse, etc.) '
        'in a separate message<br>'
        '4. <strong>Captains</strong> — send your Pre-Tournament and Knockout captain picks separately'
        '</div>'
        f'<div style="display:flex;flex-wrap:wrap;gap:0.4rem;margin-top:0.65rem">{_price_chips}</div>'
        f'{_legend}'
        '</div>',
        unsafe_allow_html=True,
    )

    # Per-item shop cards
    col1, col2 = st.columns(2)

    def _shop_card(pt: str, title: str, cost: int, colour: str, description: str):
        open_   = _is_open(pt)
        dl_lbl  = _deadline_label(pt)
        lock_banner = (
            '<div style="background:#EF444422;border-radius:4px;padding:0.2rem 0.5rem;'
            'font-size:0.75rem;color:#EF4444;margin-top:0.35rem">🔒 Window closed — no longer available</div>'
            if not open_ else ""
        )
        st.markdown(
            f'<div class="card" style="opacity:{"1" if open_ else "0.55"}">'
            f'<div style="display:flex;align-items:center;gap:0.5rem;flex-wrap:wrap;margin-bottom:0.1rem">'
            f'<h4 style="color:#D4A017;margin:0">{title} — €{cost}</h4>'
            f'<span style="background:{colour}22;border:1px solid {colour};border-radius:4px;'
            f'padding:0.1rem 0.4rem;font-size:0.71rem;color:{colour};white-space:nowrap">'
            f'{dl_lbl if open_ else "🔒 Closed"}</span>'
            f'</div>'
            f'<p style="color:#9CA3AF;font-size:0.88rem;margin:0">{description}</p>'
            f'{lock_banner}'
            f'</div>',
            unsafe_allow_html=True,
        )

    with col1:
        _shop_card("BuyIn", "Buy In", 5, _GRP,
                   "Entry into the competition. Required to receive prizes. "
                   "You still appear on the Overall Leaderboard without it, but are excluded from prize money.")
        _shop_card("PredictionPack", "Prediction Pack", 5, _GRP,
                   "Unlocks six predictions: World Cup Winner (+30), Runner-Up (+20), Bronze Medal (+15), "
                   "Golden Boot (+25), Dark Horse (up to +135 cumulative), and First Knocked Out (+20). "
                   "<strong style='color:#D4A017'>Lock: 19 June</strong> before first kick-off.")
        _shop_card("Mulligan", "Mulligan", 3, _GRP,
                   "Complete redraw of your 8 teams before the tournament starts. "
                   "Must satisfy all allocation rules. Multiple allowed.")
        _shop_card("Insurance", "Insurance", 2, _GRP,
                   "If either of your original Tier 1 teams is eliminated in the "
                   "<strong>Group Stage or Round of 32</strong>, you receive <strong>+25 points</strong>. "
                   "Max +50 if both exit early.")

    with col2:
        _shop_card("NinthTeam", "Ninth Team", 3, _KO,
                   "After the Group Stage, receive one randomly drawn surviving team you don't already own. "
                   "Added to your roster for knockout rounds only. Can be your Knockout Captain.")
        _shop_card("Resurrection", "Resurrection", 5, _KO,
                   "You choose which of your eliminated teams gets swapped out, and you choose the "
                   "replacement from surviving same-tier teams you don't own. "
                   "Replacement earns knockout points only. Maximum one per player.")

    # ── Self-service purchasing ────────────────────────────────────────────────
    st.divider()
    _sv = st.session_state.get("viewer")

    if not _sv or _sv == "— select —":
        st.info("👆 Select your name in the sidebar to buy add-ons.")
    else:
        _has = processed.get(_sv, set())
        _avail = [(pt, title, cost, colour) for pt, title, cost, colour in PTYPES
                  if pt not in _has and _is_open(pt)]

        st.markdown(f"#### 🛒 Buy for {_sv}")

        if not _avail:
            st.success("✓ You have all currently available add-ons!")
        else:
            from dashboard.data import get_assignments, get_match_stats as _gms
            _player_teams = get_assignments().get(_sv, [])
            _stats = _gms()
            _eliminated: set[str] = set()
            if not _stats.empty:
                _eliminated = set(
                    _stats[_stats["RoundReached"].fillna("").str.strip() == ""]["Team"].tolist()
                )
            _DATA = Path(__file__).resolve().parent.parent.parent / "data"

            for _pt, _ptitle, _pcost, _pcol in _avail:
                with st.form(f"shop_{_pt}_{_sv}"):
                    st.markdown(
                        f'<span style="color:#D4A017;font-weight:700">{_ptitle}</span>'
                        f' — <span style="color:#D4A017">€{_pcost}</span>',
                        unsafe_allow_html=True,
                    )
                    _sel_val = ""
                    _disabled = False

                    if _pt == "Resurrection":
                        _elig = [t for t in _player_teams if t in _eliminated]
                        if _elig:
                            _sel_val = st.selectbox("Which of your teams to replace?", _elig)
                        else:
                            st.caption("No eliminated teams yet — available after the group stage.")
                            _disabled = True
                    elif _pt == "NinthTeam":
                        st.caption("Admin will randomly draw a surviving team you don't own.")
                    elif _pt == "PredictionPack":
                        st.caption("After purchasing, submit your picks on the Predictions page.")
                    elif _pt == "Mulligan":
                        st.caption("Admin will redraw your 8 teams — message Oisin after buying.")
                    elif _pt == "Insurance":
                        st.caption("+25 pts if either original Tier 1 team is eliminated in Group Stage or R32.")

                    _buy = st.form_submit_button(f"Buy €{_pcost}", type="primary", disabled=_disabled)

                    if _buy:
                        try:
                            from src.competition import add_purchase, load_purchases as _lp
                            _purch = _lp()
                            _sel = _sel_val if _pt == "Resurrection" else ""
                            _purch = add_purchase(_sv, _pt, "(self-service)", _purch, selection=_sel)
                            _purch.to_csv(_DATA / "purchases.csv", index=False)
                            st.cache_data.clear()
                            st.success(f"✓ {_ptitle} recorded! Send €{_pcost} to the shared Revolut pocket.")
                            st.rerun()
                        except Exception as _ex:
                            st.error(f"Error: {_ex}")

        _already = [(pt, title) for pt, title, _, _ in PTYPES if pt in _has]
        if _already:
            st.caption("Already purchased: " + " · ".join(f"✓ {lbl}" for _, lbl in _already))

# ═══════════════════════════════════════
# TAB 2: MY BUDGET
# ═══════════════════════════════════════
with tab_budget:
    viewer = st.session_state.get("viewer")

    _pool_c1, _pool_c2, _pool_c3, _pool_c4 = st.columns(4)
    with _pool_c1:
        st.metric("Prize Pool", f"€{prize_pool.get('current_pot', 0):.2f}",
                  help="Sum of all player budgets")
    with _pool_c2:
        st.metric("🥇 1st", f"€{prize_pool.get('first_prize', 0):.2f}")
    with _pool_c3:
        st.metric("🥈 2nd", f"€{prize_pool.get('second_prize', 0):.2f}")
    with _pool_c4:
        st.metric("🥉 3rd", f"€{prize_pool.get('third_prize', 0):.2f}")

    st.divider()

    if viewer and viewer != "— select —":
        # Personal budget card
        if not budgets_df.empty:
            row = budgets_df[budgets_df["Player"] == viewer]
            if not row.empty:
                r = row.iloc[0]
                budget    = float(r["Budget"])
                spent     = float(r["Spent"])
                available = float(r["Available"])
                avail_col = "#6EE7B7" if available >= 0 else "#EF4444"
                st.markdown(
                    f'<div style="background:#1A2535;border:1px solid #D4A01744;border-radius:10px;'
                    f'padding:1rem 1.25rem;margin-bottom:1rem">'
                    f'<div style="color:#D4A017;font-weight:700;font-size:1rem;margin-bottom:0.6rem">'
                    f'💰 {viewer}\'s Budget</div>'
                    f'<div style="display:flex;gap:2rem;flex-wrap:wrap">'
                    f'<div><div style="color:#9CA3AF;font-size:0.75rem">Budget</div>'
                    f'<div style="color:#D4A017;font-size:1.4rem;font-weight:700">€{budget:.2f}</div></div>'
                    f'<div><div style="color:#9CA3AF;font-size:0.75rem">Spent</div>'
                    f'<div style="color:#F5F5F5;font-size:1.4rem;font-weight:700">€{spent:.2f}</div></div>'
                    f'<div><div style="color:#9CA3AF;font-size:0.75rem">Available</div>'
                    f'<div style="color:{avail_col};font-size:1.4rem;font-weight:700">€{available:.2f}</div></div>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.info(f"No budget data for {viewer}.")
    else:
        st.info("Select your name in the sidebar to see your personal budget.")

    st.subheader("All Players")

    if budgets_df.empty:
        empty_state("No budget data yet — admin must set budgets.")
    else:
        _bdisp = budgets_df.copy()

        def _bstyle(row):
            styles = []
            for col in row.index:
                if col == "Budget":
                    styles.append("color:#D4A017;font-weight:700")
                elif col == "Available":
                    try:
                        v = float(str(row[col]).replace("€", "") or 0)
                    except (ValueError, TypeError):
                        v = 0.0
                    if v < 0:
                        styles.append("color:#EF4444;font-weight:700")
                    elif v > 0:
                        styles.append("color:#6EE7B7;font-weight:600")
                    else:
                        styles.append("color:#9CA3AF")
                elif col == "Spent":
                    styles.append("color:#F5F5F5")
                else:
                    styles.append("")
            return styles

        for _c in ["Budget", "Spent", "Available"]:
            _bdisp[_c] = _bdisp[_c].apply(lambda v: f"€{float(v):.2f}")
        st.dataframe(_bdisp.style.apply(_bstyle, axis=1), use_container_width=True, hide_index=True)

    st.caption(
        "Budgets are based on money contributed to the Revolut pocket. "
        "They are updated manually by the administrator. "
        "The live app is updated every evening when the latest data is published."
    )

# ═══════════════════════════════════════
# TAB 3: LEDGER
# ═══════════════════════════════════════
with tab_ledger:
    st.subheader("Purchase Overview")

    # Matrix table: who has bought what
    rows = []
    for player in sorted(participants, key=lambda p: (status_map.get(p, "UNPAID") != "PAID", p)):
        has   = processed.get(player, set())
        spent = sum(COSTS[pt] for pt in has if pt in COSTS)
        row: dict = {
            "Player": player,
            "Status": status_map.get(player, "UNPAID"),
        }
        for pt, label, _, colour in PTYPES:
            open_ = _is_open(pt)
            if pt in has:
                row[label] = "✓"
            elif open_:
                row[label] = "Available"
            else:
                row[label] = "Closed"
        row["Spent"] = f"€{spent}"
        rows.append(row)

    df = pd.DataFrame(rows)

    def _style(row: pd.Series):
        styles = []
        for col in row.index:
            if col == "Player":
                styles.append("font-weight: 600")
            elif col == "Status":
                if row[col] == "PAID":
                    styles.append("color: #6EE7B7; font-weight: 600")
                else:
                    styles.append("color: #EF4444; font-weight: 600")
            elif col == "Spent":
                styles.append("color: #D4A017; font-weight: 700")
            elif row[col] == "✓":
                styles.append("color: #6EE7B7; font-weight: 700")
            elif row[col] == "Available":
                styles.append("color: #D4A017; font-weight: 600")
            elif row[col] == "Closed":
                styles.append("color: #4B5563; font-style: italic")
            else:
                styles.append("color: #4B5563")
        return styles

    st.dataframe(
        df.style.apply(_style, axis=1),
        use_container_width=True,
        hide_index=True,
    )
    st.caption("✓ Purchased  ·  Available — message Oisin to buy  ·  Closed — window has passed")

    st.divider()

    # Summary metrics
    n = len(participants)
    r1c1, r1c2, r1c3, r1c4 = st.columns(4)
    with r1c1:
        paid_in = sum(1 for p in participants if "BuyIn" in processed.get(p, set()))
        st.metric("Bought In (€5)", f"{paid_in} / {n}")
    with r1c2:
        has_pack = sum(1 for p in participants if "PredictionPack" in processed.get(p, set()))
        st.metric("Pred. Packs (€5)", f"{has_pack} / {n}")
    with r1c3:
        has_insurance = sum(1 for p in participants if "Insurance" in processed.get(p, set()))
        st.metric("Insurance (€2)", f"{has_insurance} / {n}")
    with r1c4:
        st.metric("Prize Pool", f"€{prize_pool.get('current_pot', 0):.0f}",
                  help="Sum of all player budgets")

    # Full purchase log
    if not purchases.empty:
        st.subheader("Full Purchase Log")
        from src.competition import PRICES as _PRICES
        _log = purchases.copy()
        _log.insert(2, "€", _log["PurchaseType"].map(_PRICES).fillna(0.0).astype(int))
        _show = _log[["Player", "PurchaseType", "€", "Selection", "Reference", "Timestamp"]].copy()
        _show = _show.sort_values("Timestamp", ascending=False)
        st.dataframe(_show, use_container_width=True, hide_index=True)
