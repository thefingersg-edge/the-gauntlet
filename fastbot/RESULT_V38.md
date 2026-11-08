# RESULT — v38: the noise-band rule on five markets it had never seen. Gross effect: same sign, smaller, not significant. Net: costs win.

```
SPEC:     PREREGISTRATION_v38.md  sha 9311b00c…   SCRIPT noise_v38.py 1.0   LOG data/v38/run_v38.log
DATA:     OANDA 5m bid/ask UK100 DE30 EU50 JP225 AU200 (pulled 2026-09-26 by Dave, checked: no dups, ask >= bid)
GATE 0:   generalised code reproduces v36 N on SPX exactly (3,319 days, max diff 0)
VERDICT:  G1 GROSS FAIL (t 1.83 < 2.0)   G2 NET FAIL
```

**I am not a financial adviser. This is a measurement, not a recommendation.**

## Numbers (bp per instrument-day, gated 2013/14 → 2026-09-25, t clustered by date)
```
            gross           net              eras (gross)           
POOLED      +1.31 (t 1.83)  -4.14 (t -5.70)   +1.67 +1.83 +0.52   ex-2020/21 +1.36 (t 1.88)
UK100       +0.65 (0.62)    -2.58
DE30        +2.15 (1.69)    -0.21
EU50        +0.07 (0.06)    -9.21
JP225       +3.17 (2.43)    -4.80
AU200       +0.75 (0.90)    -3.98
cost/day    3.2 / 2.4 / 9.3 / 8.0 / 4.7 bp (budget, read before the run)
```

## Read it plainly
- **The momentum effect travels, weakly.**
  - The gross result is positive in every era and on every market, which is what a real effect would do.
  - It is about 40% the size of the US effect (+1.3 against +3.4 bp/day) and just short of the gate (t 1.83 against 2.0).
  - That is not a replication, but it is the opposite of the usual pattern in this project, where effects vanish on new data.
- **None of these markets can pay for it.** Their CFD spreads cost 2–9 bp a day against a 1–3 bp gross edge. DE30 comes nearest (−0.2 bp net).
- **B (reported): the VIX-stress idea points the wrong way.** On days after the VIX curve inverted, the US rule made +0.86 gross (t 0.2). On all other days it made +3.88 (t 4.1). The momentum lives in normal markets, not stressed ones. That contradicts the dealer-gamma proxy story.
- **C (reported): volatility sizing** cut the worst drawdown by about 16% and nudged the Sharpe up (−1.21 → −1.08). It controls risk; it does not create return, as RESULT_VOLTARGET found.

## What it means
The noise-band edge is real but small and US-concentrated. It is tradeable only where costs are lowest: NAS100 at about 0.4 bp. The FORWARD_v36 NAS100 test stays the right vehicle.
