# PREREGISTRATION FLOWS-3 — the overnight drift after a US sell-off

```
WRITTEN:   2026-09-26, before any 02:00-03:00 ET return has been computed
           on OANDA data for this question. No harness exists yet.
STATUS:    FROZEN at its first commit. The harness must pin this file's
           sha256 and refuse to run if it has changed.
SOURCE:    research/LITERATURE_2026-09_market_behaviour_change.md, rank 3
           -- REFRAMED here: see section 0
VEHICLE:   OANDA CFD SPX500_USD (NAS100_USD, US30_USD confirmatory)
```

*Measurement, not a recommendation. Not financial advice.*

---

## 0. The claim, and why the question changed before it was registered

Boyarchenko, Larsen & Whelan, *The Overnight Drift* (RFS 2023; NY Fed SR 917):
US equity index futures earn large positive returns when European markets
open, driven by order imbalances at the previous US close — dealers who
absorbed selling at the close unload inventory as overseas flow arrives. The
reversal after sell-offs is robust; after rallies it is modest.

**The same authors report it has disappeared** (*The Disappearing Overnight
Drift*, Liberty Street Economics, July 2026). Measured in the **02:00-03:00
ET** window: about 3.7% a year before 2021 — over 60% of the E-mini's 5.9%
annual close-to-close return — and **close to zero from January 2021 to
December 2025**, in S&P, Nasdaq and Dow contracts alike. Their explanation:
the dispersion of end-of-day order imbalances halved (s.d. 6.5% to 2.9%),
while volatility and overnight liquidity barely changed.

The literature report ranked the unconditional trade third. **That trade is
already dead by its authors' account, and registering it would be testing a
known answer.** Their explanation leaves one live question: if what shrank is
the *size* of closing imbalances, not the market's *response* to them, the
drift should still appear after the large sell-offs that still happen.

**Registered expectation.** G1 is more likely to fail than pass. It is
registered because a pass would be informative and the test is cheap.

## 1. Data

- `fastbot/data/v24/{spx500usd,nas100usd,us30usd,de30eur}_{bid,ask}_15m.csv`,
  timestamps UTC (pull_m1.py writes tz-aware UTC). Mid = (bid + ask) / 2.
- Frozen end: 2026-08-31. v24 is appended by `forward_tick.sh`; later bars
  are ignored so the result cannot drift.
- Clock conversion to America/New_York, DST-aware.
- **P1** 2005-01 to 2020-12 (before the decay). **P2** 2021-01 to 2026-08 (the
  period the authors call dead). P1 vs P2 is the era test.

## 2. Definitions

- **Window** = 02:00-03:00 ET: from the open of the M15 bar starting 02:00 ET
  to the close of the bar starting 02:45 ET. Return on mid for gross.
- **Prior session** = the most recent US cash session, 09:30-16:00 ET, before
  the window. Return from the mid open of the 09:30 bar to the mid close of
  the 15:45 bar. This stands in for the closing order imbalance, which the
  authors measure directly and OANDA data cannot.
- A session with fewer than 20 of its 26 bars (half-days, holidays, gaps) is
  dropped, and so is its window.
- **Sell-off day** = prior-session return below the 10th percentile of all
  earlier sessions (expanding, at least 250 sessions of history). Causal.
  Expected about 145 events in P2 and about 400 in P1.

## 3. Hypotheses and gates — thresholds fixed now

| gate | test | pass |
|---|---|---|
| H1 replication (not a kill) | unconditional mean window return, P1 | > 0 |
| H2 decay (not a kill) | unconditional mean, P2 | reported; the authors predict ≈ 0 |
| **G1** the live question | mean window return after sell-off days, **P2** | > 0 and t ≥ 2.0 |
| **G2** mechanism held before | same, P1 | > 0 and t ≥ 2.0 |
| **G3** response not collapsed | P2 conditional mean ÷ P1 conditional mean | ≥ 0.5 |
| **G4** placebo window | 20:00-21:00 ET, same conditioning, P2 | t < 2.0 and smaller than G1 |
| **G5** plateau | windows 01:45-03:00 and 02:00-03:15, P2 conditional | same sign as G1 |
| **G6** vehicle and cost | buy at ask at the window open, sell at bid at its close, P2 conditional | mean net > 0 |

The trade crosses no 17:00 NY rollover and pays no financing, so the spread
measured from the bid and ask bars is the only cost. Stress at +1 bp and +3 bp.

**Confirmatory, sign only:** G1 on NAS100_USD and US30_USD. **Descriptive:**
DE30_EUR over the same window (Xetra opens 03:00 ET); Monday windows, which
sit after a weekend, reported separately from the rest.

## 4. Kill conditions

- **K1** G1 fails — the drift is dead after sell-offs too, as the authors'
  unconditional result suggests. Stop.
- **K2** G4 placebo as large as G1 — not a European-open effect.
- **K3** G6 net ≤ 0.

## 5. Declared test count

Inferential: G1, G2, G4. Benjamini-Hochberg at q < 0.10. H1, H2, G3, G5 and
the secondary instruments are descriptive or sign-only.

## 6. Out of scope, declared now

The alternative imbalance proxy (the 15:00-16:00 ET last hour alone) and any
magnitude-scaled definition of a sell-off. One definition is registered; the
others would be a sweep.

## 7. Files

    flows/overnight.py            harness — pins this file's sha256
    flows/RESULT_OVERNIGHT.md     result
