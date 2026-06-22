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
    "TeamSwap":       "team_swap_deadline",
}
_deadline_colour: dict[str, str] = {
    "BuyIn": _GRP, "PredictionPack": _GRP, "Mulligan": _GRP, "Insurance": _GRP,
    "NinthTeam": _KO, "Resurrection": _KO, "TeamSwap": _KO,
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

_PFLAG_COLS = ["BuyIn", "PredictionPack", "Mulligan", "CompleteRedraw",
               "NinthTeam", "Resurrection", "Insurance"]
processed: dict[str, set] = {}
if not statuses.empty:
    for _, r in statuses.iterrows():
        p = str(r.get("Player", ""))
        if p:
            processed[p] = {c for c in _PFLAG_COLS if str(r.get(c, "0")).strip() in ("1", "True", "true")}

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
            ("Team Swap", 8, _KO),
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
                   "Golden Boot (+25), First Knocked Out (+20), and Dark Horse (up to +135 cumulative). "
                   "<strong style='color:#D4A017'>Lock: 28 Jun</strong> before knockout stage.")
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
        _shop_card("TeamSwap", "Team Swap", 8, _KO,
                   "Two players swap one team each. The player who chose the swap pays €8. "
                   "Each team can only be swapped once — first come, first served. "
                   "Ninth Team and Resurrection follow your updated roster.")

    # ── Self-service purchasing ────────────────────────────────────────────────
    st.divider()
    _sv = st.session_state.get("viewer")

    if not _sv or _sv == "— select —":
        st.info("👆 Select your name in the sidebar to buy add-ons.")
    else:
        _has  = processed.get(_sv, set())
        _avail = [(pt, title, cost, colour) for pt, title, cost, colour in PTYPES
                  if pt not in _has and _is_open(pt)]
        _DATA = Path(__file__).resolve().parent.parent.parent / "data"

        # Shared data used by buy, edit, and selection forms
        from dashboard.data import (get_assignments, get_match_stats as _gms,
                                     get_tier_map, is_predictions_locked as _ipl)
        from src.event_engine import resurrection_candidates
        from src.team_database import load_teams as _ltsh
        _player_teams = get_assignments().get(_sv, [])
        _stats        = _gms()
        _tier_map     = get_tier_map()
        _purch_live   = get_purchases()
        _team_rounds: dict[str, str] = {}
        if not _stats.empty:
            for _, _sr in _stats.iterrows():
                _team_rounds[str(_sr["Team"])] = str(_sr.get("RoundReached", "") or "").strip()
        _gs_done = any(v not in ("", "GroupStage") for v in _team_rounds.values())

        def _save_and_push_purchases(df: pd.DataFrame, msg: str) -> None:
            from src.competition import save_purchases_to_players, load_player_status
            _pl = pd.read_csv(_DATA / "players.csv", dtype=str).fillna("") if (_DATA / "players.csv").exists() else load_player_status()
            _pl = save_purchases_to_players(df, _pl)
            _pl.to_csv(_DATA / "players.csv", index=False)
            from dashboard.github_sync import push_file as _pf
            try:
                _pf(_DATA / "players.csv", "data/players.csv", msg)
            except Exception as _pe:
                st.warning(f"⚠️ GitHub sync: {_pe}")
            st.cache_data.clear()

        # ── Buy available add-ons ──────────────────────────────────────────
        st.markdown(f"#### 🛒 Buy for {_sv}")

        if not _avail:
            st.success("✓ You have all currently available add-ons!")
        else:
            for _pt, _ptitle, _pcost, _pcol in _avail:
                st.markdown(
                    f'<span style="color:#D4A017;font-weight:700">{_ptitle}</span>'
                    f' — <span style="color:#D4A017">€{_pcost}</span>',
                    unsafe_allow_html=True,
                )

                if _pt == "Resurrection":
                    if not _gs_done:
                        st.caption("Available after the group stage — check back once groups are settled.")
                    else:
                        _knocked_out = [t for t in _player_teams
                                        if _team_rounds.get(t, "") in ("", "GroupStage")]
                        if not _knocked_out:
                            st.caption("None of your teams were knocked out of the group stage.")
                        else:
                            _elim_pick = st.selectbox(
                                "Which of your group-stage knockouts to replace?",
                                _knocked_out, key=f"res_elim_{_sv}",
                            )
                            _cands = resurrection_candidates(
                                _sv, _elim_pick, get_assignments(), _stats, _purch_live, _tier_map,
                            )
                            if not _cands:
                                st.caption("No valid same-tier replacements currently available.")
                            else:
                                _repl_pick = st.selectbox(
                                    "Replacement team (same tier, still in competition)?",
                                    _cands, key=f"res_repl_{_sv}",
                                )
                                if st.button(f"Buy Resurrection €{_pcost}", type="primary",
                                             key=f"buy_res_{_sv}"):
                                    try:
                                        from src.competition import add_purchase, load_purchases as _lp
                                        _p = _lp()
                                        _p = add_purchase(_sv, "Resurrection", "(self-service)", _p,
                                                          selection=f"{_elim_pick}->{_repl_pick}")
                                        _save_and_push_purchases(_p, f"Purchase: {_sv} Resurrection")
                                        st.success(
                                            f"✓ Resurrection recorded: {_elim_pick} → {_repl_pick}. "
                                            f"Send €{_pcost} to the Revolut pocket."
                                        )
                                        st.rerun()
                                    except Exception as _ex:
                                        st.error(f"Error: {_ex}")
                else:
                    with st.form(f"shop_{_pt}_{_sv}"):
                        if _pt == "PredictionPack":
                            st.caption("Your picks form will appear below as soon as you buy.")
                        elif _pt == "NinthTeam":
                            st.caption("Admin will randomly draw a surviving team you don't own.")
                        elif _pt == "Mulligan":
                            st.caption("Admin will redraw your 8 teams — message Oisin after buying.")
                        elif _pt == "Insurance":
                            st.caption("+25 pts if either original Tier 1 team is eliminated in Group Stage or R32.")
                        if st.form_submit_button(f"Buy €{_pcost}", type="primary"):
                            try:
                                from src.competition import add_purchase, load_purchases as _lp
                                _purch = _lp()
                                _purch = add_purchase(_sv, _pt, "(self-service)", _purch, selection="")
                                _save_and_push_purchases(_purch, f"Purchase: {_sv} {_pt}")
                                st.success(f"✓ {_ptitle} recorded! Send €{_pcost} to the shared Revolut pocket.")
                                st.rerun()
                            except Exception as _ex:
                                st.error(f"Error: {_ex}")

        # ── Already purchased + undo ───────────────────────────────────────
        _already = [(pt, title) for pt, title, _, _ in PTYPES if pt in _has]
        if _already:
            st.caption("Already purchased: " + " · ".join(f"✓ {lbl}" for _, lbl in _already))

        _own_p = purchases[purchases["Player"] == _sv].reset_index()
        if not _own_p.empty:
            st.markdown("---")
            st.markdown("##### Remove a purchase")
            for _, _ur in _own_p.iterrows():
                _u_orig = int(_ur["index"])
                _u_pt   = str(_ur.get("PurchaseType", ""))
                _u_lbl  = next((lbl for pt, lbl, _, _ in PTYPES if pt == _u_pt), _u_pt)
                _u_cost = COSTS.get(_u_pt, 0)
                _u_ts   = str(_ur.get("Timestamp", ""))[:16]
                _u_sel  = str(_ur.get("Selection", ""))
                _uc1, _uc2 = st.columns([4, 1])
                with _uc1:
                    _sel_txt = f" · {_u_sel}" if _u_sel else ""
                    st.markdown(
                        f'<span style="color:#F5F5F5">{_u_lbl}{_sel_txt}</span>'
                        f' <span style="color:#6B7280;font-size:0.78rem">{_u_ts}</span>',
                        unsafe_allow_html=True,
                    )
                with _uc2:
                    if st.button("Remove", key=f"undo_{_sv}_{_u_orig}", type="secondary"):
                        try:
                            from src.competition import load_purchases as _lp2, load_player_status, mark_unpaid
                            _pa = _lp2()
                            _pa = _pa.drop(index=_u_orig).reset_index(drop=True)
                            if _u_pt == "BuyIn":
                                _s2 = load_player_status()
                                _s2 = mark_unpaid(_sv, _s2)
                                _s2.to_csv(_DATA / "players.csv", index=False)
                                from dashboard.github_sync import push_file as _pfu
                                try:
                                    _pfu(_DATA / "players.csv", "data/players.csv", f"Undo BuyIn: {_sv}")
                                except Exception:
                                    pass
                            _save_and_push_purchases(_pa, f"Undo purchase: {_sv} {_u_pt}")
                            st.success(f"✓ {_u_lbl} removed.")
                            st.rerun()
                        except Exception as _ex2:
                            st.error(f"Error: {_ex2}")

        # ── Your Selections ────────────────────────────────────────────────
        _has_pred = "PredictionPack" in _has
        _has_res  = "Resurrection"   in _has

        st.markdown("---")
        st.markdown("### Your Selections")

        # Shared players.csv load (used by both captains + picks forms)
        _tdf_sh = _ltsh()
        _all_t  = sorted(_tdf_sh["Team"].tolist()) if not _tdf_sh.empty else []
        _tm_sh  = {str(r["Team"]): int(r.get("Tier", 4)) for _, r in _tdf_sh.iterrows()} if not _tdf_sh.empty else {}
        _low_sh = sorted([t for t, ti in _tm_sh.items() if ti in (3, 4) and t not in _player_teams])
        _ppdf   = pd.read_csv(_DATA / "players.csv", dtype=str).fillna("") if (_DATA / "players.csv").exists() else pd.DataFrame()
        _all_pick_cols = ["PreTournamentCaptain", "KnockoutCaptain",
                          "WorldCupWinner", "RunnerUp", "BronzeMedal",
                          "GoldenBoot", "DarkHorse"]
        for _c in _all_pick_cols:
            if not _ppdf.empty and _c not in _ppdf.columns:
                _ppdf[_c] = ""
        _rmask_sh = _ppdf["Player"] == _sv if not _ppdf.empty else pd.Series(dtype=bool)
        _rrow_sh  = _ppdf[_rmask_sh].iloc[0] if _rmask_sh.any() else pd.Series(dtype=str)

        def _vsh(col):
            v = _rrow_sh.get(col, "") if not _rrow_sh.empty else ""
            return str(v) if pd.notna(v) else ""

        def _save_players(df: pd.DataFrame, msg: str) -> None:
            df.to_csv(_DATA / "players.csv", index=False)
            from dashboard.github_sync import push_file as _pfsh
            try:
                _pfsh(_DATA / "players.csv", "data/players.csv", msg)
            except Exception as _egh:
                st.warning(f"⚠️ GitHub sync: {_egh}")
            st.cache_data.clear()

        # ── Captains (all players) ─────────────────────────────────────────
        st.markdown("#### Captains")
        if _ipl():
            st.success("Predictions are locked — captain selections are final.")
        else:
            st.caption("Pre-Tournament Captain: +0.5× all points. Knockout Captain: +0.5× knockout points only.")
            _cap_opts_sh = [""] + sorted(_player_teams)
            with st.form(f"sh_captains_{_sv}"):
                _sh_c1, _sh_c2 = st.columns(2)
                with _sh_c1:
                    st.markdown("**Pre-Tournament Captain**")
                    _ptc_cur = _vsh("PreTournamentCaptain")
                    _new_ptc = st.selectbox("One of your 8 teams", _cap_opts_sh,
                                             index=_cap_opts_sh.index(_ptc_cur) if _ptc_cur in _cap_opts_sh else 0,
                                             key="sh_ptc", label_visibility="collapsed")
                with _sh_c2:
                    st.markdown("**Knockout Captain**")
                    _new_kc = st.text_input("Surviving team you own (can be 9th/Resurrection)",
                                             value=_vsh("KnockoutCaptain"), key="sh_kc",
                                             label_visibility="collapsed", placeholder="e.g. France")
                if st.form_submit_button("Save Captains", type="primary"):
                    try:
                        if _rmask_sh.any():
                            _ppdf.loc[_rmask_sh, "PreTournamentCaptain"] = _new_ptc
                            _ppdf.loc[_rmask_sh, "KnockoutCaptain"]      = _new_kc
                            _save_players(_ppdf, f"Captains: {_sv}")
                            st.success("✓ Captains saved!")
                            st.rerun()
                        else:
                            st.error(f"Player {_sv!r} not found in players.csv.")
                    except Exception as _exsh:
                        st.error(f"Error: {_exsh}")

        # ── Prediction picks (pack holders only) ───────────────────────────
        if _has_pred:
            st.markdown("#### Prediction Picks")
            if _ipl():
                st.success("Predictions are locked — your picks are final.")
            else:
                st.caption("Editable until the prediction lock deadline.")
                _topts_sh = [""] + _all_t
                with st.form(f"sh_picks_{_sv}"):
                    _sh_d1, _sh_d2, _sh_d3 = st.columns(3)
                    with _sh_d1:
                        st.markdown("**World Cup Winner**")
                        _wcw_c = _vsh("WorldCupWinner")
                        _new_wcw = st.selectbox("Any team", _topts_sh,
                                                 index=_topts_sh.index(_wcw_c) if _wcw_c in _topts_sh else 0,
                                                 key="sh_wcw", label_visibility="collapsed")
                    with _sh_d2:
                        st.markdown("**Runner-Up**")
                        _ru_c = _vsh("RunnerUp")
                        _new_ru = st.selectbox("Any team", _topts_sh,
                                                index=_topts_sh.index(_ru_c) if _ru_c in _topts_sh else 0,
                                                key="sh_ru", label_visibility="collapsed")
                    with _sh_d3:
                        st.markdown("**Bronze Medal**")
                        _bm_c = _vsh("BronzeMedal")
                        _new_bm = st.selectbox("Any team", _topts_sh,
                                                index=_topts_sh.index(_bm_c) if _bm_c in _topts_sh else 0,
                                                key="sh_bm", label_visibility="collapsed")
                    _sh_d4, _sh_d5 = st.columns(2)
                    with _sh_d4:
                        st.markdown("**Golden Boot**")
                        _new_gb = st.text_input("Player name", value=_vsh("GoldenBoot"),
                                                 key="sh_gb", label_visibility="collapsed",
                                                 placeholder="e.g. Mbappé")
                    with _sh_d5:
                        st.markdown("**Dark Horse**")
                        st.caption("Tier 3/4 team you don't own")
                        _dh_opts_sh = [""] + _low_sh
                        _dh_c = _vsh("DarkHorse")
                        _new_dh = st.selectbox("Tier 3/4, not owned", _dh_opts_sh,
                                                index=_dh_opts_sh.index(_dh_c) if _dh_c in _dh_opts_sh else 0,
                                                key="sh_dh", label_visibility="collapsed")

                    if st.form_submit_button("Save Picks", type="primary"):
                        try:
                            if _rmask_sh.any():
                                for _col_sh, _val_sh in [
                                    ("WorldCupWinner", _new_wcw),
                                    ("RunnerUp",       _new_ru),
                                    ("BronzeMedal",    _new_bm),
                                    ("GoldenBoot",     _new_gb),
                                    ("DarkHorse",      _new_dh),
                                ]:
                                    _ppdf.loc[_rmask_sh, _col_sh] = _val_sh
                                _save_players(_ppdf, f"Picks: {_sv}")
                                st.success("✓ Picks saved!")
                                st.rerun()
                            else:
                                st.error(f"Player {_sv!r} not found in players.csv.")
                        except Exception as _exsh:
                            st.error(f"Error: {_exsh}")
        else:
            st.info("Buy a Prediction Pack above to unlock tournament predictions (World Cup Winner, Runner-Up, Golden Boot, etc.).")

            # ── Resurrection edit ──────────────────────────────────────────
            if _has_res:
                st.markdown("#### Resurrection Selection")
                if not _is_open("Resurrection"):
                    st.info("Resurrection window is closed — selection is final.")
                else:
                    st.caption("Update your team swap until the Resurrection deadline.")
                    _res_rows = _purch_live[
                        (_purch_live["Player"] == _sv) &
                        (_purch_live["PurchaseType"] == "Resurrection")
                    ]
                    if not _res_rows.empty:
                        _res_sel = str(_res_rows.iloc[0].get("Selection", ""))
                        _res_orig_idx = int(_res_rows.index[0])
                        _cur_elim = _res_sel.split("->")[0].strip() if "->" in _res_sel else _res_sel.strip()
                        _cur_repl = _res_sel.split("->")[1].strip() if "->" in _res_sel else ""

                        if not _gs_done:
                            st.caption("Group stage not yet concluded.")
                        else:
                            _ko_edit = [t for t in _player_teams
                                        if _team_rounds.get(t, "") in ("", "GroupStage")]
                            if not _ko_edit:
                                st.caption("None of your teams were knocked out of the group stage.")
                            else:
                                _elim_e = st.selectbox(
                                    "Which of your group-stage knockouts to replace?",
                                    _ko_edit,
                                    index=_ko_edit.index(_cur_elim) if _cur_elim in _ko_edit else 0,
                                    key=f"res_edit_elim_{_sv}",
                                )
                                _cands_e = resurrection_candidates(
                                    _sv, _elim_e, get_assignments(), _stats, _purch_live, _tier_map,
                                )
                                _repl_opts_e = _cands_e if _cands_e else ([_cur_repl] if _cur_repl else [])
                                if not _repl_opts_e:
                                    st.caption("No valid same-tier replacements currently available.")
                                else:
                                    _repl_e = st.selectbox(
                                        "Replacement team (same tier, still in competition)?",
                                        _repl_opts_e,
                                        index=_repl_opts_e.index(_cur_repl) if _cur_repl in _repl_opts_e else 0,
                                        key=f"res_edit_repl_{_sv}",
                                    )
                                    if st.button("Update Resurrection", type="primary", key=f"res_edit_save_{_sv}"):
                                        try:
                                            from src.competition import load_purchases as _lpe
                                            _pe_df = _lpe()
                                            _pe_df.loc[_res_orig_idx, "Selection"] = f"{_elim_e}->{_repl_e}"
                                            _save_and_push_purchases(_pe_df, f"Edit Resurrection: {_sv}")
                                            st.success(f"✓ Updated: {_elim_e} → {_repl_e}")
                                            st.rerun()
                                        except Exception as _exe:
                                            st.error(f"Error: {_exe}")

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
