"""The VAR Room — transparency centre with full audit trail."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import pandas as pd

from dashboard.data import (
    get_purchases, get_statuses, get_events, get_audit_log,
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
    "Payment Ledger", "Prize Pool", "Event Timeline",
    "Audit Log", "Draw History", "Random Seeds", "Transaction History",
])

# ── 1. Payment Ledger ──────────────────────────────────────────────────────
with tabs[0]:
    st.subheader("💳 Payment Ledger")
    df = get_purchases()
    if not df.empty:
        # Show processed purchases only in a clean view
        show_cols = [c for c in ["Player", "PurchaseType", "Amount", "Reference", "Timestamp", "Status"] if c in df.columns]
        searchable_table(df[show_cols], "Search player or purchase type…", key="tbl_payment_ledger")
    else:
        empty_state("No payment data yet.")

# ── 2. Prize Pool Breakdown ────────────────────────────────────────────────
with tabs[1]:
    st.subheader("💰 Prize Pool Breakdown")
    from dashboard.data import get_prize_pool
    pool = get_prize_pool()
    st.metric("Total Pot",   f"€{pool.get('current_pot',0):.2f}")
    st.metric("1st Prize",   f"€{pool.get('first_prize',0):.2f}")
    st.metric("2nd Prize",   f"€{pool.get('second_prize',0):.2f}")
    st.metric("3rd Prize",   f"€{pool.get('third_prize',0):.2f}")
    st.divider()
    # Per-type breakdown
    p = get_purchases()
    if not p.empty:
        from src.competition import PRICES
        processed = p[p["Status"] == "PROCESSED"]
        rows = []
        for ptype, price in PRICES.items():
            cnt = int((processed["PurchaseType"] == ptype).sum())
            rows.append({"Type": ptype, "Count": cnt, "Amount": f"€{cnt * price:.2f}"})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ── 3. Event Timeline ──────────────────────────────────────────────────────
with tabs[2]:
    st.subheader("📅 Event Timeline")
    ev = get_events()
    if ev.empty:
        empty_state("No events recorded.")
    else:
        st.dataframe(ev, use_container_width=True, hide_index=True)

# ── 4. Audit Log ──────────────────────────────────────────────────────────
with tabs[3]:
    st.subheader("📋 Audit Log")
    audit = get_audit_log()
    if audit.empty:
        empty_state("No audit entries yet.")
    else:
        searchable_table(audit.iloc[::-1].reset_index(drop=True), "Search events, players, actions…", key="tbl_audit_log")

# ── 5. Draw History ───────────────────────────────────────────────────────
with tabs[4]:
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
with tabs[5]:
    st.subheader("🎯 Random Seeds")
    st.caption("All random seeds used in draws are recorded here for full auditability.")
    df = _load_csv("random_seeds.csv") if (EXPORTS / "random_seeds.csv").exists() else pd.DataFrame()
    searchable_table(df, key="tbl_seeds") if not df.empty else empty_state("No seeds recorded yet.")

# ── 7. Transaction History ─────────────────────────────────────────────────
with tabs[6]:
    st.subheader("📑 Transaction History")
    p = get_purchases()
    if p.empty:
        empty_state("No transactions recorded.")
    else:
        searchable_table(p.iloc[::-1].reset_index(drop=True), "Search player, type, status…", key="tbl_transactions")
