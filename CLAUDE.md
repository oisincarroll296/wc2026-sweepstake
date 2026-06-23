# World Cup 2026 Sweepstake - Project Notes

## Live App
**https://fellas-wc2026-sweepstake.streamlit.app/**

Private GitHub repo: `oisincarroll296/wc2026-sweepstake`  
Push to `master` → Streamlit Cloud auto-redeploys in ~30 s.

---

## Architecture

This is a **Python + Streamlit** application. The Excel/VBA approach was replaced entirely.

### Source files

| File | Purpose |
|------|---------|
| `src/team_database.py` | 48-team loader (teams.csv) |
| `src/allocation_engine.py` | Draw engine + tier-aware balancing |
| `src/scoring_engine.py` | Full points calculator (teams, captains, insurance, predictions) |
| `src/competition.py` | Competition logic layer |

### Dashboard files

| File | Purpose |
|------|---------|
| `dashboard/app.py` | Streamlit entry point — registers all pages |
| `dashboard/data.py` | All cached data loaders + `save_match_result_and_recalculate()` |
| `dashboard/config.py` | `TIER_COLORS`, `COLORS` constants |
| `dashboard/components/ui.py` | Shared UI helpers (`page_header`, `empty_state`, etc.) |
| `dashboard/pages/home.py` | Overview: prize pool, countdown, top team, recent log |
| `dashboard/pages/leaderboard.py` | Prize Standings + All Players tabs with stacked score breakdown |
| `dashboard/pages/player_portfolios.py` | Per-player portfolio, H2H comparison, insurance status |
| `dashboard/pages/teams.py` | Groups, Standings, Fixtures, Ownership tabs |
| `dashboard/pages/analytics.py` | Charts: goals, form, remaining potential, insurance tracker, captains |
| `dashboard/pages/bracket.py` | Knockout bracket coloured by tier, all owners listed |
| `dashboard/pages/predictions_centre.py` | Prediction picks overview |
| `dashboard/pages/purchases.py` | Purchase ledger and prize pool |
| `dashboard/pages/var_room.py` | Full transparency — payments, draws, audit log |
| `dashboard/pages/rules.py` | Official rules and scoring reference |
| `dashboard/pages/admin.py` | Password-protected: result entry, who-benefits panel |

### Data files (all committed to git — private repo)

| File | Purpose |
|------|---------|
| `data/teams.csv` | 48-team database with tier + strength scores |
| `data/allocation.csv` | `Player,Team` — 14 players × 8 teams each |
| `data/match_stats.csv` | Per-team stats: goals, CS, penalty/comeback wins, upset wins, special events, RoundReached |
| `data/match_results.csv` | Raw match-by-match result entries |
| `data/fixtures.csv` | Full fixture list with match numbers |
| `data/purchases.csv` | Purchase ledger — columns: `Player, PurchaseType, Selection, Reference, Timestamp` (no Amount or Status column) |
| `data/players.csv` | One row per player: Status, PaidTimestamp, Budget, PreTournamentCaptain, KnockoutCaptain, WorldCupWinner, RunnerUp, BronzeMedal, GoldenBoot, DarkHorse, FirstKnockedOut |
| `data/events.csv` | Draw events (INITIAL_DRAW, GROUP_STAGE_CLOSE, etc.) |
| `data/audit_log.csv` | Full action audit trail |
| `data/score_history.csv` | Historical score snapshots (`Date,Player,Points`) |
| `data/deadlines.json` | Editable deadline timestamps |
| `data/tournament_results.json` | Final results: world_cup_winner, runner_up, bronze_winner, golden_boot_winner, first_knocked_out |

---

## Team Database

- **Source**: FIFA official draw pots (December 2025)
- **48 teams** across 4 tiers of 12
- **Tier assignment**: ranked by FIFA position among the 48 qualifiers
- **Strength Score** = `101 - FIFA Rank`

### Teams by Tier

**Tier 1** (FIFA ranks 1-11, 13): Spain, Argentina, France, England, Brazil, Portugal, Netherlands, Belgium, Germany, Croatia, Morocco, Colombia

**Tier 2** (ranks 14-27 excl gaps): USA, Mexico, Uruguay, Switzerland, Japan, Senegal, Iran, South Korea, Ecuador, Austria, Australia, Canada

**Tier 3** (ranks 29-50 excl gaps): Norway, Panama, Sweden, Egypt, Algeria, Scotland, Turkey, Paraguay, Tunisia, Ivory Coast, Czech Republic, Uzbekistan

**Tier 4** (ranks 51-86 excl gaps): Qatar, Saudi Arabia, South Africa, DR Congo, Jordan, Iraq, Cape Verde, Ghana, Bosnia and Herzegovina, Curacao, Haiti, New Zealand

---

## Allocation Rules

- 14 participants, 8 teams each (2 per tier)
- Each team appears 2-3 times across all participants
- Balance threshold: max portfolio - min portfolio <= 20 pts
- Balancing uses iterative tier-aware swapping (max 1000 iterations)

---

## Scoring Engine (`src/scoring_engine.py`)

### Match points

| Event | Points |
|-------|--------|
| Goal scored | 1 pt |
| Clean sheet | 2 pts |
| Win (any) | 3 pts |
| Penalty shootout win | 3 pts |
| Comeback win (not pens) | 3 pts |
| Hat trick | 10 pts |
| Group stage winner | 3 pts |

Win, penalty win, and comeback win bonuses stack. Hat tricks manually entered, go in group/knockout bucket (not special).

### Upset win bonuses

| Upset | Bonus |
|-------|-------|
| Beat a team 1 tier above | +15 |
| Beat a team 2 tiers above | +30 |
| Beat a team 3 tiers above | +50 |

### Special event bonuses (manually entered, preserved on recalculation)

| Event | Points |
|-------|--------|
| Shirt removal celebration | +25 |
| Goalkeeper scores | +75 |
| Red card | -5 |
| First team eliminated | +35 |

Special events count toward Pre-Tournament Captain bonus but NOT Knockout Captain.

### Progression bonuses (awarded for reaching each round, cumulative)

| Tier | R32 | R16 | QF | SF | Final | Winner |
|------|-----|-----|----|----|-------|--------|
| T1   | 2   | 4   | 8  | 16 | 24    | 30     |
| T2   | 4   | 8   | 16 | 24 | 36    | 42     |
| T3   | 10  | 16  | 30 | 40 | 64    | 69     |
| T4   | 16  | 24  | 50 | 60 | 90    | 98     |

### Captain bonuses
- **Pre-Tournament captain**: +0.5 × team's total points (all stages incl. special events)
- **Knockout captain**: +0.5 × team's knockout points only (excludes special events)
- Same team cannot be both captains

### Insurance
- `+25 pts` per Tier 1 team eliminated in Group Stage or Round of 32 (max +50 if both out)
- Only original 8-team allocation counts (not Ninth/Resurrection)

### Dark Horse bonuses (cumulative)
| Round reached | Bonus |
|--------------|-------|
| QF           | +15   |
| SF           | +30   |
| Final        | +40   |
| Winner       | +50   |

### Prediction Pack bonuses
- WC Winner correct: +30 pts
- Runner-Up correct: +20 pts
- Bronze Medal correct: +15 pts
- Golden Boot correct: +25 pts
- First Knocked Out correct: +20 pts
- Dark Horse bonuses: cumulative per round reached (QF to Winner, as above)

### Round order
`GroupStage → R32 → R16 → QF → SF → Final → Winner`

---

## Purchase Types

`purchases.csv` columns: `Player, PurchaseType, Selection, Reference, Timestamp`

| PurchaseType | Amount | Selection field |
|-------------|--------|-----------------|
| `BuyIn` | €5 | (empty) |
| `PredictionPack` | €5 | (empty) |
| `Mulligan` | €3 | (empty) — redraw for that player only |
| `CompleteRedraw` | €6 | (empty) — redraw for all players; before first game only |
| `NinthTeam` | €3 | Team name e.g. `"Japan"` |
| `Resurrection` | €5 | Eliminated team player wants to swap out e.g. `"Spain"` (replacement randomly drawn) |
| `Insurance` | €2 | (empty) |

> **Important**: PurchaseType casing must match exactly — the scoring engine does case-sensitive lookups.

---

## Rule Decisions (final)

| Rule | Decision |
|------|----------|
| Insurance bonus | +25 pts per Tier 1 team eliminated in Group Stage or Round of 32 (max +50 if both out) |
| Mulligan | Full redraw of that player's 8 teams only; must pass all allocation rules |
| Complete Redraw | Full redraw of ALL players' teams; must be done before first game kicks off |
| Buy-in deadline | 19 June 20:00 UTC+1 |
| Payment references | `"PLAYER - BUY IN, PREDICTION PACK"` |
| Prize Leaderboard | PAID players only (eligible for prizes) |
| Overall Leaderboard | All players, shows payment status |
| Dark Horse | Must be Tier 3 or 4; cannot be a team the player owns |
| Ninth Team | Random surviving unowned team; adds to knockout roster only |
| Resurrection | Player chooses which eliminated team to swap; same-tier replacement randomly drawn; once only |
| Tiebreaker 1 | Most goals scored by owned teams |
| Tiebreaker 2 | Most owned teams reaching QF+ |
| Tiebreaker 3 | Lowest original portfolio strength (original draw only, ignores Ninth/Resurrection) |
| Tiebreaker 4 | Coin toss (seeded random) |
| Comeback Win | Won in normal/extra time after being behind; NOT penalty wins |
| Prediction lock | 19 June (before first group stage games) |

---

## Prices

| Purchase | Cost |
|----------|------|
| Buy In | €5 |
| Prediction Pack | €5 |
| Mulligan | €3 |
| Complete Redraw | €6 |
| Ninth Team | €3 |
| Resurrection | €5 |
| Insurance | €2 |
| Team Swap | €5 |

---

## Colour Scheme

| Element | RGB |
|---------|-----|
| Header BG | 13, 27, 42 (near-black) |
| Header FG | 212, 160, 23 (gold) |
| Tier 1 | 16, 90, 172 (blue) |
| Tier 2 | 21, 128, 61 (green) |
| Tier 3 | 161, 98, 7 (amber) |
| Tier 4 | 185, 28, 28 (red) |
| Score BG | 30, 41, 59 (dark blue) |

---

## Day-to-day workflow (entering results)

1. Run locally: `streamlit run dashboard/app.py`
2. Admin page → Results Entry → enter match scores
3. Push to GitHub:
   ```powershell
   git add data/
   git commit -m "Update scores: 2026-MM-DD"
   git push
   ```
4. Streamlit Cloud redeploys in ~30 s.

Admin password: set in Streamlit Cloud Secrets as `ADMIN_PASSWORD` (default: `wc2026admin`).

---

## Tests

```powershell
pytest tests/ -v
```

Key test files:
- `tests/test_scoring_engine.py` — unit tests for scoring functions
- `tests/test_rules_alignment.py` — rule-alignment tests
- `tests/test_event_engine.py` — draw event tests (ninth team, resurrection, etc.)

All 598 tests pass as of last run.
