"""The VAR Room — transparency centre with full audit trail."""
import sys
from pathlib import Path
_p = str(Path(__file__).resolve().parent.parent.parent); sys.path.insert(0, _p) if _p not in sys.path else None

import streamlit as st
import pandas as pd

from dashboard.data import (
    get_purchases, get_statuses, get_events, get_audit_log,
    get_player_budgets,
)
from dashboard.components.ui import page_header, searchable_table, empty_state

_ROOT = Path(__file__).parent.parent.parent
EXPORTS = _ROOT / "exports"


def _load_csv(name: str) -> pd.DataFrame:
    path = _ROOT / "data" / name
    if path.exists():
        try:
            return pd.read_csv(path, dtype=str).fillna("")
        except Exception:
            pass
    path2 = EXPORTS / name
    if path2.exists():
        try:
            return pd.read_csv(path2, dtype=str).fillna("")
        except Exception:
            pass
    return pd.DataFrame()


page_header("🔍 The VAR Room", "Full transparency — every transaction, draw, and decision")

tabs = st.tabs([
    "Purchases", "Payment Ledger", "Prize Pool", "Event Timeline",
    "Audit Log", "Draw History", "Random Seeds", "Transaction History",
])

# ── 0. Purchases ───────────────────────────────────────────────────────────
with tabs[0]:
    from src.competition import PRICES as _PRICES_0
    _pur0 = get_purchases()
    _pur_statuses = get_statuses()

    st.subheader("💳 Payment Ledger")
    st.caption("Status of each player's buy-in, packs, and add-ons.")
    if not _pur_statuses.empty:
        _ledger_rows = []
        for _, _sr in _pur_statuses.iterrows():
            _pl = _sr["Player"]
            _pp = _pur0[_pur0["Player"] == _pl] if not _pur0.empty else pd.DataFrame()
            _status_val = _sr.get("Status", "UNPAID")
            _has_buyin = (
                (not _pp.empty and not _pp[_pp["PurchaseType"] == "BuyIn"].empty)
                or _status_val == "PAID"  # implicit Buy In for manually-marked PAID players
            )
            _has_pack  = not _pp.empty and not _pp[_pp["PurchaseType"] == "PredictionPack"].empty
            _has_ins   = not _pp.empty and not _pp[_pp["PurchaseType"] == "Insurance"].empty
            _has_9th   = not _pp.empty and not _pp[_pp["PurchaseType"] == "NinthTeam"].empty
            _has_res   = not _pp.empty and not _pp[_pp["PurchaseType"] == "Resurrection"].empty
            _total = sum(
                float(_PRICES_0.get(_r["PurchaseType"], 0))
                for _, _r in _pp.iterrows()
            ) if not _pp.empty else 0.0
            _ledger_rows.append({
                "Player":      _pl,
                "Status":      _sr.get("Status", "UNPAID"),
                "Buy In":      "✓" if _has_buyin else "—",
                "Pred Pack":   "✓" if _has_pack  else "—",
                "Insurance":   "✓" if _has_ins   else "—",
                "9th Team":    "✓" if _has_9th   else "—",
                "Resurrection":"✓" if _has_res   else "—",
                "Total":       f"€{_total:.0f}",
            })
        _ledger_df = pd.DataFrame(_ledger_rows)

        # Highlight invalid paid players (PAID but missing BuyIn or budget < €5)
        _budgets_tab0 = get_player_budgets()
        _budget_map   = dict(zip(_budgets_tab0["Player"], _budgets_tab0["Budget"])) if not _budgets_tab0.empty else {}

        _invalid_paid = [
            r["Player"] for r in _ledger_rows
            if r["Status"] == "PAID" and float(_budget_map.get(r["Player"], 0)) < 5.0
        ]
        if _invalid_paid:
            st.warning(f"⚠️ Validation issue — PAID status requires budget ≥ €5: **{', '.join(_invalid_paid)}**")

        def _lstyle(row):
            _bgt = float(_budget_map.get(row.get("Player", ""), 0))
            if row.get("Status") == "PAID" and _bgt < 5.0:
                return ["background-color:#7F1D1D;color:#FCA5A5"] * len(row)
            if row.get("Status") == "UNPAID":
                return ["color:#6B7280"] * len(row)
            return [""] * len(row)

        st.dataframe(
            _ledger_df.style.apply(_lstyle, axis=1),
            use_container_width=True, hide_index=True,
        )
        st.caption("PAID status requires budget ≥ €5. Buy In is recorded automatically when budget is saved; players marked PAID before that system existed show ✓ implicitly.")
    else:
        empty_state("No payment data yet.")

    st.divider()
    st.subheader("🛒 All Purchases")
    if not _pur0.empty:
        _pur_disp = _pur0.copy()
        _pur_disp.insert(2, "Amount", _pur_disp["PurchaseType"].map(_PRICES_0).fillna(0.0).apply(lambda x: f"€{x:.0f}"))
        _show0 = [c for c in ["Player", "PurchaseType", "Amount", "Selection", "Reference", "Timestamp"] if c in _pur_disp.columns]
        searchable_table(_pur_disp[_show0], "Search player or purchase type…", key="tbl_purchases_main")
    else:
        empty_state("No purchases recorded yet.")


# ── 1. Payment Ledger (detailed) ────────────────────────────────────────────
with tabs[1]:
    st.subheader("💳 Payment Ledger")
    df = get_purchases()
    if not df.empty:
        from src.competition import PRICES as _PRICES
        disp = df.copy()
        disp.insert(2, "Amount", disp["PurchaseType"].map(_PRICES).fillna(0.0).apply(lambda x: f"€{x:.0f}"))
        show_cols = [c for c in ["Player", "PurchaseType", "Amount", "Selection", "Reference", "Timestamp"] if c in disp.columns]
        searchable_table(disp[show_cols], "Search player or purchase type…", key="tbl_payment_ledger")
    else:
        empty_state("No payment data yet.")

# ── 2. Prize Pool Breakdown ────────────────────────────────────────────────
with tabs[2]:
    st.subheader("💰 Prize Pool Breakdown")
    from dashboard.data import get_prize_pool
    pool = get_prize_pool()
    _pp_c1, _pp_c2, _pp_c3, _pp_c4 = st.columns(4)
    with _pp_c1: st.metric("Total Pot",  f"€{pool.get('current_pot',0):.2f}")
    with _pp_c2: st.metric("🥇 1st Prize", f"€{pool.get('first_prize',0):.2f}")
    with _pp_c3: st.metric("🥈 2nd Prize", f"€{pool.get('second_prize',0):.2f}")
    with _pp_c4: st.metric("🥉 3rd Prize", f"€{pool.get('third_prize',0):.2f}")

    st.caption("Prize pool = sum of all player budgets (money contributed to the Revolut pocket).")
    st.divider()

    st.subheader("💳 Player Budgets")
    _budgets_df = get_player_budgets()
    if not _budgets_df.empty:
        def _bstyle(row):
            styles = []
            for col in row.index:
                if col == "Available":
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
                elif col == "Budget":
                    styles.append("color:#D4A017;font-weight:700")
                else:
                    styles.append("")
            return styles

        _bdisp = _budgets_df.copy()
        for _c in ["Budget", "Spent", "Available"]:
            _bdisp[_c] = _bdisp[_c].apply(lambda v: f"€{float(v):.2f}")
        st.dataframe(_bdisp.style.apply(_bstyle, axis=1), use_container_width=True, hide_index=True)
    else:
        st.caption("No budget data yet.")

    st.divider()
    st.subheader("🛒 Purchase Spend Breakdown")
    p = get_purchases()
    from src.competition import PRICES
    rows = []
    for ptype, price in PRICES.items():
        cnt = int((p["PurchaseType"] == ptype).sum()) if not p.empty else 0
        rows.append({"Type": ptype, "Count": cnt, "Unit Price": f"€{price:.0f}", "Total": f"€{cnt * price:.0f}"})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.caption("This breakdown counts purchase records × unit price. It is informational — the prize pool figure above is based on actual Revolut contributions (Budget column).")

# ── 3. Event Timeline ──────────────────────────────────────────────────────
with tabs[3]:
    st.subheader("📅 Event Timeline")
    ev = get_events()
    if ev.empty:
        empty_state("No events recorded.")
    else:
        from dashboard.components.ui import _fmt_iso, _TS_COLS
        disp_ev = ev.copy()
        for _c in _TS_COLS & set(disp_ev.columns):
            disp_ev[_c] = disp_ev[_c].apply(lambda v: _fmt_iso(str(v)) if v else v)
        st.dataframe(disp_ev, use_container_width=True, hide_index=True)

# ── 4. Audit Log ──────────────────────────────────────────────────────────
with tabs[4]:
    st.subheader("📋 Audit Log")
    audit = get_audit_log()
    if audit.empty:
        empty_state("No audit entries yet.")
    else:
        searchable_table(audit.iloc[::-1].reset_index(drop=True), "Search events, players, actions…", key="tbl_audit_log")

# ── 5. Draw History ───────────────────────────────────────────────────────
with tabs[5]:
    st.subheader("🎲 Draw History")
    audit = get_audit_log()
    sub = st.tabs(["Initial Draw", "Mulligan Draws", "Ninth Team Draws", "Resurrection Draws"])
    with sub[0]:
        st.caption("The original team allocation draw.")
        from dashboard.data import get_assignments
        alloc = get_assignments()
        if alloc:
            draw_rows = []
            for player, teams in sorted(alloc.items()):
                draw_rows.append({"Player": player, "Teams": ", ".join(teams)})
            st.dataframe(pd.DataFrame(draw_rows), use_container_width=True, hide_index=True)
        else:
            empty_state("Draw not yet completed.")
    with sub[1]:
        if not audit.empty:
            df = audit[audit["Event"] == "MULLIGAN_DRAW"].reset_index(drop=True) if "Event" in audit.columns else pd.DataFrame()
        else:
            df = pd.DataFrame()
        # Also try exports file as fallback
        if df.empty:
            df = _load_csv("mulligan_results.csv") if (EXPORTS / "mulligan_results.csv").exists() else pd.DataFrame()
        searchable_table(df, key="tbl_mulligan") if not df.empty else empty_state("No mulligan draws recorded.")
    with sub[2]:
        if not audit.empty:
            df = audit[audit["Event"] == "NINTH_TEAM_DRAW"].reset_index(drop=True) if "Event" in audit.columns else pd.DataFrame()
        else:
            df = pd.DataFrame()
        if df.empty:
            df = _load_csv("ninth_team_results.csv") if (EXPORTS / "ninth_team_results.csv").exists() else pd.DataFrame()
        searchable_table(df, key="tbl_ninth_team") if not df.empty else empty_state("No ninth team draws recorded.")
    with sub[3]:
        if not audit.empty:
            df = audit[audit["Event"] == "RESURRECTION_DRAW"].reset_index(drop=True) if "Event" in audit.columns else pd.DataFrame()
        else:
            df = pd.DataFrame()
        if df.empty:
            df = _load_csv("resurrection_results.csv") if (EXPORTS / "resurrection_results.csv").exists() else pd.DataFrame()
        searchable_table(df, key="tbl_resurrection") if not df.empty else empty_state("No resurrection draws recorded.")

# ── 6. Random Seeds ───────────────────────────────────────────────────────
with tabs[6]:
    st.subheader("🎯 Draw Seeds")
    st.caption(
        "Every random draw uses a seed so results can be verified and reproduced. "
        "The seed is recorded in the Event Timeline above."
    )
    ev = get_events()
    if not ev.empty:
        draw_ev = ev[ev["EventType"].isin(["INITIAL_DRAW","MULLIGAN_DRAW","NINTH_TEAM_DRAW","RESURRECTION_DRAW"])] if "EventType" in ev.columns else pd.DataFrame()
        if not draw_ev.empty:
            from dashboard.components.ui import _fmt_iso
            show = draw_ev[["EventType", "ExecutedTime", "RandomSeed"]].copy() if all(c in draw_ev.columns for c in ["EventType","ExecutedTime","RandomSeed"]) else draw_ev.copy()
            if "ExecutedTime" in show.columns:
                show["ExecutedTime"] = show["ExecutedTime"].apply(lambda v: _fmt_iso(str(v)) if v else v)
            st.dataframe(show, use_container_width=True, hide_index=True)
        else:
            empty_state("No draw events recorded yet.")
    else:
        empty_state("No events recorded yet.")

# ── 7. Transaction History ─────────────────────────────────────────────────
with tabs[7]:
    st.subheader("📑 Transaction History")
    p = get_purchases()
    if p.empty:
        empty_state("No transactions recorded.")
    else:
        searchable_table(p.iloc[::-1].reset_index(drop=True), "Search player or purchase type…", key="tbl_transactions")
