# WC 2026 Sweepstake — Operations Guide

Everything you need to run the sweepstake from first setup to prize day, in order.

---

## Before You Start: Install & Run

```powershell
cd "c:\World Cup"
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
streamlit run dashboard/app.py
```

The dashboard opens at `http://localhost:8501`. Keep that terminal window open whenever the app should be live.

**Admin password:** `wc2026admin`  
To change it: `$env:ADMIN_PASSWORD = "newpassword"` before running streamlit.

---

## How to Wipe Everything and Start Fresh

If you ran test draws or made mistakes during setup, run the reset script:

```powershell
.\.venv\Scripts\python.exe scripts/reset_data.py
```

This will:
- Keep all 13 player names
- Reset every player to UNPAID
- Clear all purchases, draws, events, predictions, and captains
- Reset all match stats to zero
- Remove prediction and buy-in locks
- Clear all exports

The script asks you to type `yes` to confirm before doing anything.

---

## Step 1: Add All 13 Players

Edit `data/player_status.csv` directly in Excel or a text editor:

```
Player,Status,PaidTimestamp
Lobber,UNPAID,
Guilly,UNPAID,
...
```

One row per player. Status must be `UNPAID` at this stage.

---

## Step 2: Run the Initial Draw

Go to **Admin → Draw Events**, select `INITIAL_DRAW`, and click **Run**.

This randomly assigns each player 2 teams per tier, balances portfolios so the strongest minus weakest is ≤ 20 pts, and saves the result to `data/allocation.csv`.

After it runs, you'll see the results on screen.

---

## Step 3: Broadcast the Draw

Go to **Admin → Draw Broadcast**, select `Initial Draw`, and click **Generate Broadcast**.

Copy the WhatsApp text and paste it into your group chat.

> **If the broadcast says "No draws to report"** — the draw hasn't been run yet, or failed. Go back to Draw Events and run INITIAL_DRAW first.

---

## Step 4: Collect Money and Record Purchases

When a player sends money, go to **Admin → Purchases → Add Purchase**.

- Set Type to `BUYIN`
- Fill in a payment reference (e.g. `ALICE - BUY IN`)
- Click **Add Purchase**

Buy In, Prediction Pack, and Insurance are processed immediately. You do not need to press any other button. The player's status is updated to PAID automatically when a BUYIN is added.

Mulligan, Ninth Team, and Resurrection purchases stay pending until their draw event runs — this is intentional.

### Optional purchases at this stage:

| Purchase | Cost | What it does |
|----------|------|--------------|
| PACK | €5 | Unlocks predictions |
| MULLIGAN | €3 | Full redraw of 8 teams — run the MULLIGAN_DRAW event after adding |
| INSURANCE | €2 | +25 pts if a T1 team exits in the group stage |

---

## Step 5: Collect Predictions (Pack buyers only)

Before the prediction lock (1 hour before the opening match), collect three picks from each player who bought a Prediction Pack:

- **World Cup Winner** — any team
- **Golden Boot** — player name (free text)
- **Dark Horse** — must be a T3 or T4 team they don't own

Edit `data/predictions.csv` directly:

```
Player,WorldCupWinner,GoldenBoot,DarkHorse
Alice,Brazil,Vinicius Jr,Tunisia
```

---

## Step 6: Collect Captain Selections

Each player picks two captains — one before the tournament, one before the knockouts.

Edit `data/captains.csv` directly:

```
Player,CaptainType,Team
Alice,PreTournament,Brazil
Alice,Knockout,France
```

`CaptainType` must be `PreTournament` or `Knockout`. Each player can have one of each. They cannot be the same team.

---

## Step 7: Lock Predictions and Buy-Ins

**1 hour before the opening match:**

Go to **Admin → Locking** and click **Lock Predictions**.

This reveals all predictions publicly on the Predictions Centre page. It cannot be undone via the button, but you can unlock manually (see *Emergency Fixes* below).

Then click **Lock Buy-Ins**. After this, the prize leaderboard is frozen to only paid players and their prize shares are calculated.

After locking, the status bar shows how many players are paid and a summary of unpaid players.

---

## Step 8: During the Group Stage — Enter Results

After each matchday, go to **Admin → Results Entry**.

**Single Team mode:** select a team, fill in their cumulative stats, and save.

**Excel mode (easier):** generate the template once, fill it in throughout the group stage, then upload it:

```powershell
.\.venv\Scripts\python.exe scripts/generate_results_excel.py
```

This creates `data/results_template.xlsx` with all 48 teams sorted by group. Fill in the Group Stage sheet and upload via **Admin → Results Entry → Upload Excel**.

### What the stats mean:

| Field | What to enter |
|-------|--------------|
| Goals | Total goals scored by that team in the group stage |
| Clean Sheets | Number of group matches where they conceded zero goals |
| Penalty Wins | Group stage matches won via shootout (very rare, not applicable in groups) |
| Comeback Wins | Matches won in normal/extra time after being behind |
| Group Winner | 1 if they finished top of their group, 0 otherwise |

### What tells the app who is knocked out:

The `RoundReached` field in `data/match_stats.csv`. This is the furthest round a team reached:

| Value | Meaning |
|-------|---------|
| *(blank)* | Still in the tournament / not yet set |
| `GroupStage` | Eliminated in the group stage |
| `R16` | Reached the Round of 16 but went out |
| `QF` | Reached the Quarter Final but went out |
| `SF` | Reached the Semi Final but went out |
| `Final` | Reached the Final but lost |
| `Winner` | Won the World Cup |

Update this field for each team as they are eliminated. Teams with a blank RoundReached are treated as still active.

---

## Step 9: Close the Group Stage

After all 48 group games are played, go to **Admin → Draw Events**, select `GROUP_STAGE_CLOSE`, and click **Run**. This logs the event with a timestamp.

Then run the Ninth Team draw if anyone bought a Ninth Team:

1. Make sure all Ninth Team purchases are added (go to **Purchases → Add Purchase**, type `NINTH`)
2. Go to **Draw Events**, select `NINTH_TEAM_DRAW`, and click **Run**
3. Go to **Draw Broadcast**, select `Ninth Team Draw`, and generate the broadcast

---

## Step 10: Knockout Captains

Before the Round of 16 begins, collect a Knockout Captain from each player. Add to `data/captains.csv`:

```
Alice,Knockout,France
```

The knockout captain earns ×1.5 on all their knockout-stage points.

---

## Step 11: During Knockouts — Resurrections

If a player's team is eliminated and they want a Resurrection (€5):

1. Add the `RESURRECTION` purchase via **Admin → Purchases**
2. Go to **Draw Events**, select `RESURRECTION_DRAW`, and click **Run**
3. The engine finds a surviving same-tier team the player doesn't already own and assigns it
4. Generate a broadcast if you want to announce it

---

## Step 12: Update Knockout Results

Keep entering results via **Admin → Results Entry** throughout the knockouts.

For the knockout round stats, use the Knockout section of the form or the Knockout Rounds sheet in the Excel template. Remember to update each team's **Round Reached** field as they are eliminated.

---

## Step 13: End of Tournament

When the final is played:

1. Enter full stats for both finalists (including `RoundReached = Final` for the runner-up and `RoundReached = Winner` for the champion)
2. The Prize Leaderboard updates automatically
3. Go to **Admin → WhatsApp** and generate a final standings update
4. Pay out the prizes based on what the Prize Leaderboard shows

---

## Sharing the Dashboard With Everyone

### Option A: Everyone on the Same WiFi (Party / Watch Night)

Run streamlit with your local IP visible:

```powershell
streamlit run dashboard/app.py --server.address 0.0.0.0
```

Find your machine's IP address:

```powershell
ipconfig
```

Look for **IPv4 Address** under your WiFi adapter (e.g. `192.168.1.42`). Share `http://192.168.1.42:8501` with everyone on the same network.

### Option B: Remote Access via ngrok (Anyone, Anywhere)

ngrok creates a public tunnel to your local app. Install from ngrok.com, then:

```powershell
ngrok http 8501
```

ngrok gives you a public URL like `https://abc123.ngrok.io`. Share this with your group. It stays live as long as ngrok is running. Free tier works fine for 13 people.

### Option C: Permanent Hosting on Streamlit Cloud

1. Push the project to a GitHub repository
2. Go to share.streamlit.io and sign in
3. Click **New app**, point it at your repo, set main file to `dashboard/app.py`
4. Under Advanced → Secrets, add `ADMIN_PASSWORD = "yourpassword"`
5. Deploy — you get a permanent public URL

Note: Streamlit Cloud does not persist file writes between redeploys. Back up `data/*.csv` regularly.

---

## What's Missing / Not Yet in the Dashboard

- No captain deadline enforcement (you can add captains at any time; you are responsible for enforcing deadlines)
- No group draw stage locking (draw can technically be re-run; use common sense / lock the allocation file manually)
- Resurrection scoring note: the app currently counts the replacement team's full knockout points from R16 onward, not strictly from the moment of assignment. This is a minor edge case for mid-round resurrections.

---

## Emergency Fixes (Plan B)

**All data is stored in plain CSV files in the `data/` folder. You can always edit them directly in Excel.**

| Problem | Fix |
|---------|-----|
| Made a wrong purchase entry | Open `data/purchases.csv` in Excel, delete or correct the row |
| Predictions locked too early | Go to **Admin → Locking → Unlock Predictions** or delete `data/predictions_lock.txt` manually |
| Buy-ins locked too early | Go to **Admin → Locking → Unlock Buy-Ins** or delete `data/buyin_lock.txt` manually |
| Wrong captain entered | Edit `data/captains.csv` directly |
| Wrong prediction entered | Edit `data/predictions.csv` directly (only before prediction lock) |
| Wrong match stats | Edit `data/match_stats.csv` directly or re-enter via Admin → Results Entry (overwrites) |
| Draw went wrong | Run `scripts/reset_data.py` and redo the draw |
| App won't start | Run `.\.venv\Scripts\python.exe -m pytest -q` to check for errors |
| Scores look wrong | Go to **Admin → Refresh All Scores** (clears the cache) |

**Before the tournament starts:** make a backup copy of the entire `data/` folder. If anything goes badly wrong, you can restore it.

---

## Key File Reference

| File | What it contains | How it gets updated |
|------|-----------------|---------------------|
| `data/player_status.csv` | Who is PAID / UNPAID | Admin → Purchases (automatic) |
| `data/purchases.csv` | All purchases | Admin → Purchases |
| `data/allocation.csv` | Which 8 teams each player owns | Admin → Draw Events (INITIAL_DRAW) |
| `data/match_stats.csv` | Live stats for all 48 teams | Admin → Results Entry |
| `data/predictions.csv` | Player predictions | Edit directly |
| `data/captains.csv` | Captain selections | Edit directly |
| `data/events.csv` | Event log | Automatic |
| `data/audit_log.csv` | Full audit trail | Automatic |
| `data/predictions_lock.txt` | Exists = predictions are locked | Admin → Locking |
| `data/buyin_lock.txt` | Exists = buy-ins are locked | Admin → Locking |
| `exports/` | Draw results, seeds, ledger | Automatic |

---

## Scoring Quick Reference

### Match Stats (group stage and knockout, separately tracked)

| Event | Points |
|-------|--------|
| Goal | 1 |
| Clean Sheet | 2 |
| Penalty shootout win | 3 |
| Comeback win | 3 |
| Group stage winner (top of group) | 3 |

### Progression Bonuses (cumulative per round cleared)

| Round | T1 | T2 | T3 | T4 |
|-------|----|----|----|----|
| R16 | 2 | 4 | 8 | 12 |
| QF | 4 | 8 | 15 | 25 |
| SF | 8 | 12 | 20 | 30 |
| Final | 12 | 18 | 32 | 45 |
| Winner | 20 | 28 | 46 | 65 |

### Captains
- Pre-Tournament Captain: ×1.5 on all that team's points (group + knockout)
- Knockout Captain: ×1.5 on that team's knockout points only

### Insurance: +25 pts if either original T1 team exits in the group stage

### Predictions (requires Prediction Pack)

| Pick | Bonus |
|------|-------|
| Correct WC Winner | +30 |
| Correct Golden Boot | +25 |
| Dark Horse reaches QF | +15 |
| Dark Horse reaches SF | +30 |
| Dark Horse reaches Final | +40 |
| Dark Horse wins | +50 |

### Tiebreakers (in order)
1. Most goals scored by all owned teams
2. Most owned teams reaching QF or further
3. Lowest original portfolio strength (weakest draw wins the tiebreak)
4. Random draw (logged, reproducible)
