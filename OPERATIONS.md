# WC 2026 Sweepstake — Operations Guide

Step-by-step reference for running the sweepstake from draw to prize day.

**Live app:** https://fellas-wc2026-sweepstake.streamlit.app/  
**Admin password:** set in Streamlit Cloud Secrets as `ADMIN_PASSWORD`  
**Repo:** push to `master` → live in ~30 s

---

## Tournament Timeline

| Date | Deadline |
|------|----------|
| 10 Jun 20:00 UTC+1 | Mulligan deadline |
| 11 Jun 20:00 UTC+1 | Prediction lock + pre-tournament captain deadline |
| 19 Jun 20:00 UTC+1 | Buy-in deadline (before last group game) |
| 28 Jun 03:00 UTC+1 | Group stage closes |
| 28 Jun 19:00 UTC+1 | Knockout captain deadline |
| 28 Jun 20:00 UTC+1 | Ninth Team draw |
| 29 Jun 19:00 UTC+1 | Resurrection window closes |
| 19 Jul 22:00 UTC+1 | Tournament ends |

Deadlines are editable via **Admin → Deadlines** without a code change.

---

## Before the Draw

### 1. Snapshot the current state

Before running any draw, take a snapshot in **Admin → Snapshots → Take Snapshot**.  
Label it `pre_draw`. This lets you undo anything that goes wrong.

You can also do this from the terminal:

```powershell
cd "c:\World Cup"
python tools/reset_for_draw.py
```

This takes an automatic snapshot labelled `pre_draw_reset`, then clears all simulation data (allocation, match stats, events) while keeping real purchases, player names, and deadlines. Run this if you had test data you want to wipe before the real draw.

To undo:
```powershell
python tools/restore.py pre_draw_reset
```

---

### 2. Run the Initial Draw

Go to **Admin → Draw Events**, select `INITIAL_DRAW`, and click **Run**.

- Each player gets 2 teams per tier (8 total)
- Portfolios are balanced so strongest − weakest ≤ 20 pts
- The seed is recorded in `data/events.csv` — the exact same allocation can be reproduced at any time by restoring the pre-draw snapshot and re-running with the same seed

After the draw completes, go to **Admin → Draw Broadcast**, select `Initial Draw`, and click **Generate Broadcast**. Copy the WhatsApp text and send it to the group.

---

### 3. Collect Buy-Ins and Optional Purchases

When a player sends money to the **Shared Revolut Pocket**, go to **Admin → Purchases → Add Purchase**.

| Type | Cost | Notes |
|------|------|-------|
| `BuyIn` | €5 | Marks player as PAID immediately |
| `PredictionPack` | €5 | Unlocks predictions; collect picks separately |
| `Insurance` | €2 | +25 pts if a T1 team exits in the group stage |
| `Mulligan` | €3 | Full redraw; run `MULLIGAN_DRAW` event after adding |
| `NinthTeam` | €3 | Random surviving team added to knockout roster; run `NINTH_TEAM_DRAW` event later |
| `Resurrection` | €5 | Random same-tier replacement; run `RESURRECTION_DRAW` event when used |

> **Purchase type casing matters.** Use exactly: `BuyIn`, `PredictionPack`, `Insurance`, `Mulligan`, `NinthTeam`, `Resurrection`. Wrong casing = scoring engine ignores it.

`BuyIn`, `PredictionPack`, and `Insurance` are processed immediately when added.  
`Mulligan`, `NinthTeam`, and `Resurrection` stay **PENDING** until you run their draw event.

---

### 4. Mulligan Draw (if anyone bought one)

Deadline: **10 Jun 20:00 UTC+1**

1. Make sure the `Mulligan` purchase is added in Admin → Purchases
2. Go to **Admin → Draw Events**, select `MULLIGAN_DRAW`, click **Run**
3. Go to **Draw Broadcast**, select `Mulligan Draw`, generate and send the announcement

The player gets a completely new set of 8 teams. Must still pass all allocation rules.

---

### 5. Collect Predictions (Prediction Pack buyers only)

Deadline: **11 Jun 20:00 UTC+1** (same as prediction lock)

Ask each Prediction Pack holder to send you three picks:

- **World Cup Winner** — any team
- **Golden Boot** — player name (free text)
- **Dark Horse** — must be Tier 3 or 4, and a team they do NOT own

Edit `data/predictions.csv` directly:

```csv
Player,WorldCupWinner,GoldenBoot,DarkHorse
Alice,Brazil,Vinicius Jr,Tunisia
```

---

### 6. Collect Pre-Tournament Captains

Deadline: **11 Jun 20:00 UTC+1**

Each player sends you their Pre-Tournament captain. Edit `data/captains.csv` directly:

```csv
Player,CaptainType,Team
Alice,PreTournament,Brazil
```

- Each player gets one Pre-Tournament captain
- Pre-Tournament captain earns ×1.5 on that team's total points (group + knockout)
- Cannot be the same team as their Knockout captain

---

### 7. Lock Predictions and Buy-Ins

**1 hour before the opening match (11 Jun ~20:00 UTC+1):**

Go to **Admin → Locking**:

1. Click **Lock Predictions** — all prediction picks become publicly visible on the Predictions Centre page
2. Click **Lock Buy-Ins** — the prize leaderboard freezes to PAID players only; prize shares are calculated from this point

> To unlock if you pressed too early: **Admin → Locking → Unlock Predictions / Unlock Buy-Ins** (in the Emergency Reset expander at the bottom of that tab).

---

## During the Group Stage

### 8. Enter Match Results

**Admin → Results Entry → By Match (recommended)**

1. Select the date
2. Select the match (e.g. `M1: Qatar v Ecuador`)
3. Enter home goals and away goals
4. Tick **Comeback win** for either team if they won after being behind in normal/extra time (not penalty wins)
5. In knockout matches: tick **Went to extra time** and select penalty winner if applicable
6. Click **Save Result**

Goals, clean sheets, and all match stats are calculated automatically and applied to both teams. The "Who Benefits" panel shows you which players gained points from the result.

> **Group Winners** and **Round Reached** cannot be set via By Match — use Advanced mode for these.

**Admin → Results Entry → Advanced / Special Stats**

Use this for:
- Marking a team as Group Winner (`GroupWinner = 1`)
- Updating `Round Reached` as teams are eliminated (see table below)
- Any manual correction

| `RoundReached` value | Meaning |
|----------------------|---------|
| *(blank)* | Still active / not yet set |
| `GroupStage` | Eliminated in groups |
| `R16` | Reached R16, then went out |
| `QF` | Reached QF, then went out |
| `SF` | Reached SF, then went out |
| `Final` | Runner-up (lost the final) |
| `Winner` | World Cup champion |

Set `RoundReached` for every eliminated team as they go out. Teams with a blank value are treated as still alive for potential calculations.

---

### 9. Push Results to the Live App

After entering results:

```powershell
cd "c:\World Cup"
git add data/
git commit -m "Scores: 2026-MM-DD"
git push
```

The live app redeploys in ~30 seconds. That's it.

---

### 10. Send WhatsApp Updates (optional but fun)

**Admin → WhatsApp → Generate Update**

Generates a formatted standings message to paste into the group chat. Do this after each matchday if you want to keep people engaged.

---

## Group Stage Close

### 11. Run Group Stage Close Event

After the last group game is entered (around **28 Jun**):

1. Enter all remaining results via Admin → Results Entry
2. Mark all eliminated teams in Advanced mode (`RoundReached = GroupStage`)
3. Mark all Group Winners (`GroupWinner = 1`)
4. Go to **Admin → Draw Events**, select `GROUP_STAGE_CLOSE`, click **Run**

---

### 12. Run Ninth Team Draw

For anyone who bought a `NinthTeam` purchase (deadline also ~28 Jun):

1. Confirm the `NinthTeam` purchase is added via Admin → Purchases
2. Go to **Admin → Draw Events**, select `NINTH_TEAM_DRAW`, click **Run**
3. Go to **Draw Broadcast**, select `Ninth Team Draw`, generate and send the announcement

A random surviving team the player doesn't already own is assigned to their knockout roster only.

---

### 13. Collect Knockout Captains

Deadline: **28 Jun 20:00 UTC+1**

Ask each player for their Knockout captain pick before the Round of 16 starts. Add to `data/captains.csv`:

```csv
Alice,Knockout,France
```

- Knockout captain earns ×1.5 on that team's knockout points only
- Cannot be the same team as their Pre-Tournament captain

---

## During the Knockouts

### 14. Enter Knockout Results

Same process as group stage — **Admin → Results Entry → By Match**.

Remember to:
- Tick **Went to extra time** for any match that went beyond 90 minutes
- Select the penalty winner if it went to a shootout
- Tick **Comeback win** for the appropriate team if they came from behind in normal/extra time

After each round, go to **Advanced mode** and update `RoundReached` for all eliminated teams.

---

### 15. Resurrection Draw (optional)

If a player's team is eliminated and they want to buy a Resurrection (€5):

1. Add the `Resurrection` purchase via Admin → Purchases (no Selection needed — the draw picks it)
2. Go to **Admin → Draw Events**, select `RESURRECTION_DRAW`, click **Run**
3. Go to **Draw Broadcast**, select `Resurrection Draw`, generate and send the announcement

The engine finds a surviving team of the same tier that the player doesn't already own and replaces the eliminated team in their knockout roster.

**Resurrection window closes 29 Jun 20:00 UTC+1** — after that, no more Resurrections.

---

### 16. Keep Pushing Results

After each knockout round:

```powershell
git add data/
git commit -m "QF results"
git push
```

---

## End of Tournament

### 17. Enter the Final

1. Enter the final match result via Admin → Results Entry
2. In Advanced mode: set the runner-up's `RoundReached = Final`, the winner's `RoundReached = Winner`
3. Push to git

### 18. Run Tournament Complete Event

**Admin → Draw Events → `TOURNAMENT_COMPLETE`** — logs the official end.

### 19. Generate Final Standings

**Admin → WhatsApp → Generate Update** — produces the final rankings message.

Check the **Prize Leaderboard** page for the final prize breakdown. Prizes are paid out to PAID players only, ordered by their final score.

---

## Snapshot System

Always snapshot before any significant action. Snapshots copy every file in `data/` so you can restore to a known state at any time.

**In the app:** Admin → Snapshots → Take Snapshot (label it something meaningful)

**From the terminal:**
```powershell
# Take a snapshot
python tools/snapshot.py

# List available snapshots and restore one interactively
python tools/restore.py

# Restore a specific snapshot by label
python tools/restore.py pre_draw_reset
```

All draw seeds are recorded in `data/events.csv`. A snapshot + the same seed = perfectly reproducible allocation.

---

## Emergency Fixes

All data is stored in plain CSV files in `data/`. You can edit any of them directly.

| Problem | Fix |
|---------|-----|
| Wrong purchase entered | Open `data/purchases.csv`, delete or correct the row, push to git |
| Wrong captain entered | Edit `data/captains.csv` directly |
| Wrong prediction entered | Edit `data/predictions.csv` directly (before prediction lock only) |
| Predictions locked too early | Admin → Locking → Unlock Predictions |
| Buy-ins locked too early | Admin → Locking → Unlock Buy-Ins |
| Wrong match result | Re-enter via Admin → Results Entry → By Match (overwrites) |
| Wrong RoundReached | Admin → Results Entry → Advanced, select the team, correct it |
| Draw went wrong | Restore a snapshot from Admin → Snapshots → Restore |
| Scores look wrong | Admin → Draw Broadcast tab → Refresh All Scores (clears cache) |
| Prize pool shows €0 | Hard-refresh the browser (Ctrl+Shift+R) or wait 30 s for cache to expire |
| App won't load | Check Streamlit Cloud logs at share.streamlit.io |

---

## Key Files Reference

| File | What it contains | Updated by |
|------|-----------------|------------|
| `data/player_status.csv` | PAID / UNPAID per player | Admin → Purchases (automatic) |
| `data/purchases.csv` | All purchases | Admin → Purchases |
| `data/allocation.csv` | Which 8 teams each player owns | Admin → Draw Events (INITIAL_DRAW) |
| `data/match_results.csv` | Raw match-by-match results | Admin → Results Entry |
| `data/match_stats.csv` | Cumulative per-team stats | Auto-calculated from match_results |
| `data/predictions.csv` | Player predictions | Edit directly |
| `data/captains.csv` | Captain selections | Edit directly |
| `data/events.csv` | Event log (with seeds) | Automatic |
| `data/audit_log.csv` | Full action audit trail | Automatic |
| `data/score_history.csv` | Historical score snapshots | Automatic |
| `data/deadlines.json` | Deadline timestamps | Admin → Deadlines |
| `data/purchases.csv` | Purchase ledger | Admin → Purchases |

---

## Scoring Quick Reference

### Match Points

| Event | Points |
|-------|--------|
| Goal scored | 1 |
| Clean sheet | 2 |
| Penalty shootout win | 3 |
| Comeback win (normal/extra time only, not pens) | 3 |
| Finish top of group | 3 |

### Progression Bonuses (cumulative per round cleared)

| Round | T1 | T2 | T3 | T4 |
|-------|----|----|----|----|
| R16   | 2  | 4  | 8  | 12 |
| QF    | 4  | 8  | 15 | 25 |
| SF    | 8  | 12 | 20 | 30 |
| Final | 12 | 18 | 32 | 45 |
| Winner| 20 | 28 | 46 | 65 |

### Captains
- **Pre-Tournament captain:** ×1.5 on all that team's points (group + knockout combined)
- **Knockout captain:** ×1.5 on that team's knockout points only
- Same team cannot fill both roles

### Insurance
- +25 pts if either of your original T1 teams is eliminated in the group stage
- +50 pts if both are eliminated
- Only counts the original 8-team allocation (not Ninth/Resurrection teams)

### Prediction Pack

| Pick | Bonus |
|------|-------|
| Correct WC Winner | +30 |
| Correct Golden Boot | +25 |
| Dark Horse reaches QF | +15 |
| Dark Horse reaches SF | +30 |
| Dark Horse reaches Final | +40 |
| Dark Horse wins | +50 |

Dark Horse bonuses are cumulative — if your dark horse wins, you get +50 (not +15+30+40+50).  
Dark Horse must be Tier 3 or 4, and a team you do not own.

### Tiebreakers (in order)
1. Most goals scored by all owned teams
2. Most owned teams reaching QF or further
3. Coin toss (seeded random — reproducible)
