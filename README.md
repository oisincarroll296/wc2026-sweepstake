# World Cup 2026 Sweepstake

14-participant sweepstake for FIFA World Cup 2026. Each participant draws 8 teams (2 per tier), balanced by FIFA strength score.

## Quick Start

```bash
pip install -r requirements.txt
streamlit run dashboard/app.py
```

App opens at `http://localhost:8501`. See [deployment.md](deployment.md) for full instructions.

## Application Pages

| Page | Description |
|------|-------------|
| Home | Prize pool, standings, next event, activity feed |
| Leaderboard | Prize standings + all players with stacked score breakdown |
| My Portfolio | Per-player teams, score breakdown, captain, picks |
| Teams | Groups, standings, fixtures, and ownership |
| Bracket | Knockout bracket coloured by tier |
| Predictions | Prediction picks overview |
| Analytics | Interactive Plotly charts |
| Purchases | Purchase ledger and prize pool |
| VAR Room | Full transparency — payments, draws, audit log |
| Rules | Official rules and scoring reference |
| Admin | Password-protected event engine and controls |

## Project Structure

```
data/           CSV data files (teams, purchases, events, etc.)
src/            Backend modules
  team_database.py     — 48-team loader
  allocation_engine.py — draw engine
  scoring_engine.py    — points calculator
  competition.py       — competition logic layer
  event_engine.py      — admin operations
dashboard/      Streamlit application
  app.py        — entry point (run this)
  config.py     — theme and constants
  data.py       — cached data loaders
  pages/        — one file per page
  components/   — shared UI helpers
  assets/       — CSS
tests/          598 tests (pytest)
exports/        Draw results, VAR Room exports
```

## Admin Password

Default: `wc2026admin`  
Override: `$env:ADMIN_PASSWORD = "yourpassword"` before running.

## Data

48 teams across 4 tiers. Strength score = 101 − FIFA rank. Balanced portfolios: max − min ≤ 20 pts.
