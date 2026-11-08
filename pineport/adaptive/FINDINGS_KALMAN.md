# Findings — O1: Kalman velocity trend (external replication)

Run 2026-09-19 against PREREGISTRATION_KALMAN.md (frozen same day, amendments
A6–A10 all added before any code executed). 16 markets, 4h bars on the
DST-aware 17:00-NY grid, 2005–2026-08-07, 21.4 years.

## VERDICT: DEAD — G1 fails. Kill condition 1.

But not for the reason I registered, and the way it dies is worth more than the
death itself.

---

## 1. My registered prediction was wrong

The pre-registration recorded, before the run: *"the primary statistic will not
clear G2."*

It cleared G2 comfortably.

    T1 primary Sharpe      +0.5396
    2 SE noise floor        0.1528       (N_eff 8.01 of 16, rho_bar 0.067)
    ratio to floor           3.5x
    block bootstrap        median +0.5394, 5-95% +0.1634 to +0.9079
    p = 0.0146,  q = 0.0292 (BH across the 12 declared tests)

This is the first externally-sourced strategy in the project to clear its noise
floor on the full panel. Recording that plainly because the prediction was mine
and it was wrong.

## 2. What killed it — G1, era sign consistency

    E1 2005-2012   +0.94
    E2 2012-2019   -0.03
    E3 2019-2026   +0.63

Seven years in the middle of the sample produce nothing at all. This is worse
than a clean sign flip: a flip suggests a regime the rule is on the wrong side
of, whereas a flat middle era means the rule simply stops working for a third of
the record and then starts again. Whatever drives E1 and E3 is absent from E2.

Pre-registered kill condition 1. The family ends here; no further variants run.

## 3. The finding that matters more than the verdict

**The Kalman filter is not measurably better than a 200-period moving average.**

    T1  full rule (Kalman + EMA200 + chandelier)   +0.5396
    ABL2  EMA(200) alone, no Kalman at all         +0.4163
    margin                                         +0.1233
    2 SE noise floor on the estimate                0.1528

The margin over the dumb version is **smaller than the noise floor**. G6(b)
passes on the point estimate and means nothing. Two state variables, a
covariance recursion and a tuned process-noise ratio buy less than the
measurement error on a moving-average crossover.

Component decomposition:

    EMA(200) trend filter alone                    +0.4163
    Kalman velocity alone, no EMA (ABL1)           +0.2424
    full rule                                      +0.5396
    full rule minus chandelier (ABL3)              +0.4633

The trend filter carries the result. The filter is decoration on it.

## 4. The ATR scaling is a no-op — as predicted before the run

Section 1.2 of the pre-registration argued analytically that scaling Q and R by
the same ATR(14)^2 leaves the Kalman gain, and hence sign(x2), unchanged, so the
scaling could not be load-bearing. Measured:

    ABL4  no ATR scaling at all (Q=0.01, R=1.0)    +0.5453
    T1    with ATR^2 scaling on both               +0.5396
    difference                                     -0.0057

and on the raw filter output for xauusd, scaled vs unscaled agree on **98.95%**
of velocity signs (correlation 0.9953). The effective free parameter is the
ratio Q/R = 0.01. One knob, not two — which was the one genuinely favourable
thing about this specification, and it survives.

## 5. Gates

| Gate | Result | |
|---|---|---|
| G0 pre-registration | **MET** | frozen before any outcome |
| G1 era sign consistency | **FAIL** | +0.94 / −0.03 / +0.63 |
| G2 noise floor | PASS | +0.5396 vs 0.1528, 3.5x |
| G3 destroyed timing | PASS | 750-bar lag +0.0918 vs +0.5396 — timing carries real information |
| G4 matched control | not run | family killed at G1 |
| G5 cost | **FAIL as written** | see below |
| G6(a) mirror | PASS | +0.5396 vs −0.3199 |
| G6(b) vs plain EMA200 | PASS, meaninglessly | margin +0.123 < floor 0.153 |
| G7 vehicle | not run | family killed at G1 |
| G8 inference | PASS | p 0.0146, q 0.0292 |

G3 deserves a note: the destroyed-timing null collapses to +0.09. The entry
timing is doing real work — this is not merely unconditional long exposure
dressed up as a signal. That is more than most of what this project has tested
can say.

## 6. Cost — the honest version

    0 bp/side   +0.9382
    1 bp/side   +0.5396
    3 bp/side   -0.2562
    break-even   2.36 bp per side (~4.7 bp round trip)
    turnover     36.1 trades per market-year

G5 as written requires survival at 3 bp/side and it does not. But 3 bp/side is
punitive for the markets that actually carry the result: OANDA majors and gold
run roughly 0.5–0.6 bp/side. The fair statement is that the rule is comfortably
inside costs on the liquid half of the panel and outside them on the illiquid
half — not that costs kill it. **G1 kills it. Costs merely narrow where it could
ever have been run.**

## 7. Where the result actually lives

    xauusd    +0.826      eurusd    -0.013
    usdjpy    +0.688      spx500usd -0.031
    xptusd    +0.623      eurgbp    -0.139
    xagusd    +0.498      usb10yusd -0.241
    natgasusd +0.398      audusd    -0.267
    eurjpy    +0.250      gbpusd    -0.371
    bcousd    +0.231      usdcad    -0.429
    nas100usd +0.118
    xcuusd    +0.117

    9/16 positive, median +0.117, mean +0.141

Precious metals plus the yen. Gold, platinum and silver are three of the top
four, and they are the three markets with the largest sustained multi-year
trends in this sample. Every FX major except usdjpy is flat or negative. This is
not a general edge with some noise around it; it is a metals-trend result with
eleven other markets attached.

## 8. On the source claim

The video reported Sharpe 2.51 on crypto perps over ~1.5 years, selected from
~2,000 backtests. Expected best-of-search Sharpe from zero edge at that width
and horizon: 3.18. On 16 markets over 21.4 years the same rules produce +0.54
before the era split disqualifies them. The gap between 2.51 and 0.54 is what
selection over 2,000 candidates on one 18-month crypto sample buys you.

The reported +117% return and 10.9% drawdown are sizing artefacts of the
40%-of-equity rule and carry no information about the signal.

## 9. Harness verification

Run after the results, before writing them up.

    era coverage          33,773 of 33,774 bars assigned; 1 bar (pre-2005) unassigned
    cost arithmetic       xauusd drag 0.15140 observed vs 757 x 2 x 1bp = 0.15140 exact
    gap-through-stop      forcing every stop to fill AT the level instead of at a
                          worse open raises Sharpe +0.5396 -> +0.5482, so the
                          pessimistic fill convention is live and costs 0.0086
    A8 causality probe    making the peak include the current bar gives +0.3748,
                          i.e. WORSE than causal

That last probe did not test what I intended. Including bar t's high raises the
peak, which raises the stop level and tightens the stop — so it is a different
(worse) rule, not a profitable lookahead. It does establish that the causal
version is not harvesting a lookahead advantage, since the peeking variant loses,
but it is not a clean causality test and is not claimed as one.

## 10. Files

    PREREGISTRATION_KALMAN.md   frozen spec, A1–A10
    make_h4.py                  4h builder, DST-aware NY-17:00 (0/316,570 mismatches)
    o1_kalman.py                harness
    o1_kalman_h4.csv            12 declared tests + G3 + cost curve
    o1_panel_h4.csv             per-market vol-normalised return panel

T2/T4 (H1) were pre-declared but are NOT run: kill condition 1 ends the family.
They remain available as post-kill documentation only, and could not change the
verdict if run.
