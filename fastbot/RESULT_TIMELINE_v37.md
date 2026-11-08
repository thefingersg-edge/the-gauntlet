# RESULT — v37: the event timeline (Dave's hindsight-label idea). FAIL, but the closest miss yet.

```
SPEC:     PREREGISTRATION_v37.md, v37.1 (direction only), v37.2 (VX date fix); LOCKs in PREREGISTRATION_v37_LOCK.md
BUILD:    tl_build.py 1.1  -> data/timeline_v37/ (matrix.npz sha 6fc354b2…)
TEST:     timeline_v37_2.py (-> timeline_v37_1.py 1.1.1); logs fit_v37_2.log, test_v37_2.log
SAMPLE:   SPX500 5m, 91,116 decision points 2005-2026, 125 features from 70 event types
VERDICT:  G1 FAIL (validation)   G2 model FAIL   G3 patterns FAIL (significance), sealed 2020-26
```

**I am not a financial adviser. This is a measurement, not a recommendation.**

## What was built
- **Trade points:** 17 decision points a day. Each is marked LONG-wanted or SHORT-wanted if a ±1σ(2h) move went that way first within 2 hours. The table is in data/timeline_v37/trade_points.csv.
- **Event timeline:** 516,120 events, each stamped when it was known, in data/timeline_v37/event_timeline.csv. It covers:
  - every signal tested in v1–v36;
  - standard indicators (RSI, MACD, Bollinger);
  - the release calendar;
  - VIX and the VIX curve, SKEW, AAII, put/call, COT, yields, the dollar and petrol.
- **Models:** LightGBM on "minutes since each event" plus states, and a miner for "A then B within 60 min / 1 day / 5 days".

## Two voided runs, both caught before the sealed data was touched
1. **v37 labelled "a move happens" together with "which way".** Validation AUC was 0.70 and tripped the pre-registered leak void. The diagnostic showed the models were predicting volatility (the realised-vol ratio alone gave AUC 0.74), not direction. Amended to direction-only.
2. **v37.1 PASSED the information gate (AUC 0.558) because of a bug.** Every VIX-futures close was dated a day early, since TradingView stamps CBOE daily bars at the prior evening's open. The model could see tomorrow's VIX curve. "VIX curve inverted within a day → down first 74%" was the next day's panic leaking backwards. Fixed and self-tested, then rerun as v37.2.

## v37.2, the only valid run
```
                        validation 2015-19            sealed 2020-26 (net of spread)
direction AUC           0.527 (null max 0.528) FAIL   0.551 (reported)
model trades                                          990 trades  +1.51 bp  t 1.44   eras +2.76 +1.70 +0.47   FAIL
pattern trades                                        2,295 trades +1.23 bp t 1.62   eras +2.81 +0.67 +0.46   FAIL
random-entry 95th pct                                 +0.32 / -0.12
```

## Read it plainly
- **On 2015–19 the timeline knew nothing about direction.** Its AUC sat exactly on the null, and trading it lost 2.4 bp a trade.
- **On 2020–26 the same frozen model did better:** positive in all three eras, above random entry, and a sealed AUC of 0.55. But t is 1.44 (model) and 1.62 (patterns) against a 2.24 gate. That is FAIL, not "nearly".
- The edge shrinks era by era (+2.8 → +1.7 → +0.5 bp), with the most in the 2020–21 high-volatility period.
- The patterns that survived are weak, e.g. "noise-band break down, then price back above SMA20 within a day → up first 50% against a 47% base". No string of events is a strong predictor of direction.
- **What the timeline CAN predict is size, not direction.** The strongest thing in this whole exercise, the voided AUC 0.70–0.75, was volatility. That matches every earlier result (VOLCAUSE: magnitude t 47, direction |t| ≤ 1.6).
- This is the fourth time a "pass" in this project has been a bug (v24, v28 Gate 0, Q2, and now v37.1). The pre-registered voids and planted-fail checks earned their keep.

## Caveats in the body
- The model was fitted on 2005–14 and never retrained, which was deliberate. A walk-forward version might track regime change better, and it could be pre-registered as its own test.
- The sealed period is spent. Any follow-up needs forward data or new instruments.
- There is no order-book, options-flow or news-text data. The free sources were used as far as they go.
