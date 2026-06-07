"""Rules — official competition rules and scoring system."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st

from dashboard.components.ui import page_header

_ROOT = Path(__file__).parent.parent.parent
_RULES = _ROOT / "RULES.md"

page_header("Rules", "Official competition rules and scoring system")

if _RULES.exists():
    st.markdown(_RULES.read_text(encoding="utf-8"))
else:
    st.warning("Rules file not found.")
