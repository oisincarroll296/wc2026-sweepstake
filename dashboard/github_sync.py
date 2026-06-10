"""Push updated data files back to GitHub after writes.

Uses the GitHub Contents API so Streamlit Cloud doesn't need git.
Requires GITHUB_TOKEN in Streamlit secrets (fine-grained, contents R/W).
Silently skips if the token is absent (local dev).
"""
import base64
from pathlib import Path

import requests
import streamlit as st

_REPO = "oisincarroll296/wc2026-sweepstake"
_API  = "https://api.github.com/repos/" + _REPO + "/contents/"


def _token() -> str:
    try:
        return st.secrets.get("GITHUB_TOKEN", "") or ""
    except Exception:
        return ""


def push_file(local_path: str | Path, repo_path: str, message: str) -> None:
    """Commit a local file to GitHub.

    Silently no-ops when GITHUB_TOKEN is absent (local dev).
    Raises RuntimeError on API errors so callers can surface them.
    """
    token = _token()
    if not token:
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    content = Path(local_path).read_bytes()
    encoded = base64.b64encode(content).decode()

    url = _API + repo_path
    r = requests.get(url, headers=headers, timeout=10)
    sha = r.json().get("sha") if r.status_code == 200 else None

    payload: dict = {"message": message, "content": encoded}
    if sha:
        payload["sha"] = sha

    r = requests.put(url, json=payload, headers=headers, timeout=15)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"GitHub push failed ({r.status_code}): {r.json().get('message', r.text)}")
