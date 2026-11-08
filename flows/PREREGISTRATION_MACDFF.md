# PREREGISTRATION FLOWS-16 — the MACD "fake filter": exhaustion crosses on NQ futures

```
WRITTEN:   2026-10-19, before any MACD, ATR or wave statistic has been computed on any
           futures data for this purpose. The indicator was only read as code
           (pine/macd_fake_filter_fixed.pine, commit 5f1e952) and looked at on a chart.
STATUS:    FROZEN at its first commit. macdff.py must pin this file's sha256 and refuse to
           run if it has changed.
SOURCE:    "MACD Fake Filter [RH]" (HasanRifat, TradingView, MPL-2.0), as corrected here:
           show a MACD/signal cross only when MACD is more stretched than its usual wave.
DATA:      Databento GLBX.MDP3 NQ.v.0 1-minute bars, 2012-12 .. 2026-08 (already on disk,
           FLOWS-15, sha256s in data/futures.meta.json). No new purchase.
```

*Measurement, not a recommendation. Not financial advice.*

## 0. The claim, and what it really is

A plain MACD cross fires constantly. The filter keeps only the crosses
that come when momentum is unusually extended:
- a **bearish** cross while MACD sits above its average wave peak, which is
  read as "a rally is exhausted, sell";
- a **bullish** cross while MACD sits below its average wave trough, which
  is read as "a sell-off is exhausted, buy".

That makes it a **short-term reversal** signal. This programme has seen
reversal after extreme moves several times, each time small or found after
the fact:
- REGIME2 Q1: strong-trend days snap back the next day, t 2.2 (post-hoc);
- v39: the rule tree found reversal after strong 5-day rallies;
- v22: release moves revert +1.7 bp gross, which is less than the CFD
  spread.

None of these has been tested at futures costs. **Registered expectation:
modest.** If there is anything, it is likely real but small. The plain MACD
cross is expected to show nothing.

## 1. Construction, all fixed now

- **Bars:** 15-minute bars of the NQ cash session, 09:30–16:00 ET, built
  from the 1-minute bars as in vehicle.py (labelled by start, 26 per full
  session). Sessions with fewer than 20 bars are dropped. The first session
  after a front-month change is dropped (FLOWS-15 roll rule). The bar series
  runs through the RTH bars only, joined from one session to the next with
  overnight time removed.
- **Indicator** (pine/macd_fake_filter_fixed.pine defaults, unchanged):
  - MACD = EMA12 − EMA26 of the close, then divided by ATR(100) on the same
    bars;
  - signal = EMA9 of that;
  - waves run between zero crosses of MACD. Each completed wave stores one
    value, its peak (positive wave) or trough (negative wave);
  - the average peak and the average trough are taken over the **last 50
    completed waves**;
  - the filter is active once at least 10 of each are stored, and the
    threshold multiplier is **1.0**.
- **Signals**, on a bar's close:
  - **FF-short:** MACD crosses below signal and MACD > the average peak;
  - **FF-long:** MACD crosses above signal and MACD < the average trough;
  - **PLAIN:** every MACD/signal cross, which is the comparison in G3.
- **Entry:** the next bar's open. A signal whose entry bar would start
  after 15:30 is ignored. Only one trade is open at a time; a new signal
  while in a trade is ignored.
- **Exit:** the first of (a) the next opposite MACD/signal cross, filled at
  the following bar's open, or (b) the 15:45–16:00 bar's close. No overnight
  holding.
- **Costs** (as FLOWS-15): one tick (0.25 points) against the trader on
  every fill, plus $2.50 per contract round trip, converted to bp at the
  entry price × $20.
- **Sample:** trades entered 2013-01-02 .. 2026-08-31. Bars from 2012-12
  warm up the EMAs, ATR and wave history.

## 2. Random partners (G4)

For each FF trade, draw **20 partners**. Each enters at the same clock time
on a randomly chosen other session within ±250 sessions, takes the same
side, and is held for the same number of bars. Partner sessions run from
2013-01 to 2026-08, and no partner date repeats for the same trade. The
costs are the same. The seed is **20261019**.

## 3. Gates, fixed now (unit: net bp per FF trade, SE clustered by date)

| gate | test | pass |
|---|---|---|
| **G1** | mean net per FF trade | > 0 and t ≥ 2.0 |
| **G2** | eras 2013–17, 2018–21, 2022–26 | > 0 in all three **and 2022–26 ≥ 0.5 × full** |
| **G3** | the filter adds: mean FF net − mean PLAIN net | > 0 and t ≥ 1.65 (Welch) |
| **G4** | beats chance: mean of (FF trade − mean of its 20 partners) | > 0 and t ≥ 2.0 |
| **G5** | size | ≥ 300 FF trades |

**Kills:** K1 is G1 failing, K2 is G2, K3 is G4. If G1, G2 and G4 pass but G3
fails, the edge is real but the filter adds nothing: it is PLAIN's edge,
reported as such and not as a pass of the claim.

## 4. Power, stated before the run

Rough expectation: about 2–3 crosses per session, about 10–20% of them
stretched, so about 0.3–0.5 FF trades per session, which is **1,000–1,700
trades**. If the per-trade SD is about 40 bp, the standard error is about
1.0–1.3 bp, so **t = 2 needs about 2–2.5 bp net per trade**. If the trade
count comes in below G5's 300, the test is **void, not failed**.

## 5. Secondary, descriptive (gate nothing)

- FF-long and FF-short separately.
- Profit factor, win rate, and average win and loss, for FF and PLAIN.
- The same construction on 5-minute bars and on ES.
- Threshold multiplier 1.5 against 1.0, reported only, never used to choose.
- Holding time in bars, and the share of exits at 16:00.

## 6. Declared test count

Inferential: G1, G3 and G4. Benjamini-Hochberg at q < 0.10 is reported. The
rest is descriptive.

## 7. Files

    flows/macdff.py            harness: pins this file; --self-test / --run
    flows/RESULT_MACDFF.md     result
