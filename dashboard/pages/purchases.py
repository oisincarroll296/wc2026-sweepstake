"""Purchases — who has bought what at a glance."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import pandas as pd

from dashboard.data import get_purchases, get_statuses, get_participants
from dashboard.components.ui import page_header, empty_state

page_header("Purchases", "Who has bought what — full purchase overview")

participants = get_participants()
purchases    = get_purchases()
statuses     = get_statuses()

if not participants:
    empty_state("No participants found.")
    st.stop()

# ── Build lookup structures ─────────────────────────────────────────────────
status_map: dict[str, str] = {}
if not statuses.empty:
    for _, r in statuses.iterrows():
        status_map[r["Player"]] = r.get("Status", "UNPAID")

PTYPES = [
    ("BuyIn",         "Buy In",       5),
    ("PredictionPack","Pack",         5),
    ("Insurance",     "Insurance",    2),
    ("Mulligan",      "Mulligan",     3),
    ("NinthTeam",     "Ninth",        3),
    ("Resurrection",  "Resurrection", 5),
]
COSTS = {pt: cost for pt, _, cost in PTYPES}

processed: dict[str, set] = {}
if not purchases.empty:
    proc = purchases[purchases["Status"] == "PROCESSED"]
    for _, r in proc.iterrows():
        p  = r["Player"]
        pt = r["PurchaseType"]
        processed.setdefault(p, set()).add(pt)

# ── Build matrix ────────────────────────────────────────────────────────────
rows = []
for player in sorted(participants, key=lambda p: (status_map.get(p, "UNPAID") != "PAID", p)):
    has = processed.get(player, set())
    spent = sum(COSTS[pt] for pt in has if pt in COSTS)
    row: dict = {
        "Player": player,
        "Status": status_map.get(player, "UNPAID"),
    }
    for pt, label, _ in PTYPES:
        row[label] = "✓" if pt in has else "—"
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
        else:
            styles.append("color: #4B5563")
    return styles


st.dataframe(
    df.style.apply(_style, axis=1),
    use_container_width=True,
    hide_index=True,
)

# ── Summary strip ───────────────────────────────────────────────────────────
st.divider()
n = len(participants)
c1, c2, c3, c4 = st.columns(4)
with c1:
    paid_in = sum(1 for p in participants if "BuyIn" in processed.get(p, set()))
    st.metric("Bought In", f"{paid_in} / {n}")
with c2:
    has_pack = sum(1 for p in participants if "PredictionPack" in processed.get(p, set()))
    st.metric("Prediction Packs", f"{has_pack} / {n}")
with c3:
    has_insurance = sum(1 for p in participants if "Insurance" in processed.get(p, set()))
    st.metric("Insurance", f"{has_insurance} / {n}")
with c4:
    total_collected = sum(
        COSTS.get(pt, 0) for player_set in processed.values() for pt in player_set
    )
    st.metric("Total Collected", f"€{total_collected}")
