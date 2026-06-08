# World Cup 2026 Sweepstake - Project Notes

## Files

| File | Purpose |
|------|---------|
| `data/teams.csv` | 48-team database |
| `data/match_stats.csv` | Per-team tournament stats template |
| `data/purchases.csv` | Purchase ledger (BUYIN/PACK/MULLIGAN/NINTH/RESURRECTION/INSURANCE) |
| `data/player_status.csv` | PAID / UNPAID per participant |
| `data/predictions.csv` | World Cup Winner, Golden Boot, Dark Horse picks |
| `data/captains.csv` | Pre-Tournament and Knockout captain selections |
| `data/events.csv` | Draw events (INITIAL_DRAW, MULLIGAN_DRAW, etc.) |
| `data/audit_log.csv` | Full action audit trail |
| `src/team_database.py` | Team data loader |
| `src/allocation_engine.py` | Draw engine + balancing |
| `src/scoring_engine.py` | Points calculator |
| `src/competition.py` | Competition logic layer |

## Team Database

- **Source**: FIFA official draw pots (December 2025)
- **48 teams** across 4 tiers of 12
- **Tier assignment**: ranked by FIFA position among the 48 qualifiers
- **Strength Score** = `101 - FIFA Rank`
- Named ranges: `TeamList` (A5:A52), `TeamDatabase` (A4:F52), `TeamStrength` (A5:E52)

### Teams by Tier

**Tier 1** (FIFA ranks 1-11, 13): Spain, Argentina, France, England, Brazil, Portugal, Netherlands, Belgium, Germany, Croatia, Morocco, Colombia

**Tier 2** (ranks 14-27 excl gaps): USA, Mexico, Uruguay, Switzerland, Japan, Senegal, Iran, South Korea, Ecuador, Austria, Australia, Canada

**Tier 3** (ranks 29-50 excl gaps): Norway, Panama, Sweden, Egypt, Algeria, Scotland, Turkey, Paraguay, Tunisia, Ivory Coast, Czech Republic, Uzbekistan

**Tier 4** (ranks 51-86 excl gaps): Qatar, Saudi Arabia, South Africa, DR Congo, Jordan, Iraq, Cape Verde, Ghana, Bosnia and Herzegovina, Curacao, Haiti, New Zealand

## Allocation Rules

- 13 participants, 8 teams each (2 per tier)
- Each team appears 2-3 times across all participants
- Balance threshold: max portfolio - min portfolio <= 20 pts
- Balancing uses iterative tier-aware swapping (max 1000 iterations)

## VBA Functions (Sweepstake.bas)

| Function | Purpose |
|----------|---------|
| `AssignTeams()` | Random draw with pool building per tier |
| `BalancePortfolios(ws)` | Iterative swap to meet balance threshold |
| `CalculatePortfolioStrength(teamName)` | Lookup strength score for a team |
| `UpdatePortfolioColumns(ws)` | Write scores/rank/delta to cols J-L |
| `LockAllocation()` | Lock draw and protect range |
| `RefreshScores()` | Recalculate + snapshot |
| `SaveSnapshot()` | Append current scores to Update History |
| `ResetTournament()` | Clear all data for a new draw |

## Allocation Sheet Layout

| Col | Content |
|-----|---------|
| A | Participant name |
| B,C | Tier 1 teams (T1A, T1B) |
| D,E | Tier 2 teams (T2A, T2B) |
| F,G | Tier 3 teams (T3A, T3B) |
| H,I | Tier 4 teams (T4A, T4B) |
| J | Portfolio Score (VLOOKUP formula, live) |
| K | Portfolio Rank (RANK formula, live) |
| L | Delta From Average |

Lock flag: cell K1 ("LOCKED" when draw is locked)
Data rows: 8-20

## Setup Steps (first-time)

1. Open Excel, enable macros
2. Run `Build-TeamDatabase.ps1` (populates Teams & Tiers + Match Data Entry)
3. Run `Build-AllocationSheet.ps1` (builds allocation layout + imports VBA)
4. On Team Allocation sheet: enter participant names in col A rows 8-20
5. Click **Assign Teams** button
6. Verify portfolios, then click **Lock Allocation**

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

## Rule Decisions (final)

| Rule | Decision |
|------|----------|
| Insurance cost | €2 |
| Insurance bonus | +25 pts per Tier 1 team eliminated before R16 (max +50 if both out) |
| Mulligan | Full redraw of all 8 teams; must pass all allocation rules |
| Payment references | Full names: "PLAYER - BUY IN, PREDICTION PACK" |
| Prize Leaderboard | PAID players only (eligible for prizes) |
| Overall Leaderboard | All players, shows payment status |
| Dark Horse | Must be Tier 3 or 4; cannot be a team the player owns |
| Ninth Team | Random surviving unowned team; adds to knockout roster only |
| Resurrection | Same tier, surviving, unowned replacement; once only |
| Tiebreaker 1 | Most goals scored by owned teams |
| Tiebreaker 2 | Most owned teams reaching QF+ |
| Tiebreaker 3 | Coin toss (seeded random) |
| Comeback Win | Won in normal/extra time after being behind; NOT penalty wins |
| Prediction lock | 1 hour before opening match |

## Prices

| Purchase | Cost |
|----------|------|
| Buy In | €5 |
| Prediction Pack | €5 |
| Mulligan | €3 |
| Ninth Team | €3 |
| Resurrection | €5 |
| Insurance | €2 |

## Not Yet Implemented

- Streamlit dashboard / frontend
- Dashboard charts
