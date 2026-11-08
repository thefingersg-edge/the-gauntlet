# AUDIT 2026-10-04 — look-ahead check of the index results behind live forward records

**I am not a financial adviser. This is a measurement, not a recommendation.**

Checked: does any decision use information not yet available at that moment? Code read line by line.

| Result / record | Signal known at | Entry | Verdict |
|---|---|---|---|
| v36 / FORWARD_v36 noise band (`momentum_v36.noise_rows`) | close of the 30-min checkpoint bar; band sigma from the prior 14 sessions; VWAP up to that bar | open of the next bar | **clean** |
| v56 breadth (`breadth_v56.py`) | S5FI daily close of t | OANDA open of t+1 | **clean** |
| v52 / C1 (`ma_overlay_v52.py`, `c1_forward.py`) | prior close vs 200-day mean; VIX close dated t−1 | position held over day t, starting at the t−1 15:45/15:55 bar | **minor:** VIX's official close (16:15 ET) is 20–30 minutes after the index bar that starts the position. Small in practice (VIX moves little in that window), but a strictly real-time version would use the 15:45 VIX level. Noted, not changed. |
| v39 / v41 forest (`tl_build2.macro_events`) | each input stamped at its availability: VIX/VX/SKEW 16:15, put/call 18:00, AAII next day, COT Friday 15:30, gasoline next day | session decision bars | **one problem:** the broad dollar index (FRED DTWEXBGS, Fed H.10) is stamped 18:00 on its own date, but the Fed publishes H.10 **weekly** (Mondays, for the prior week). So `usd_chg5` and the `usd_up1/usd_dn1` events were up to about a week early in v39's training and test data, and the v41 forward recorder can only record a session after that data arrives. Needs a v41.2 amendment (stamp DTWEXBGS at its weekly release) before v41's forward record means anything; v39/v40 conclusions carry this caveat. (Release timing to be verified against the Fed's H.10 calendar.) |

**Also confirmed today:** PEAD1/PEAD2/PEAD5 entries are after the signal (k+2 / known close); BATCHB/ADD1 use the effective date, announced days earlier; BREADTH2 uses closes to t and enters at t+1's open.
