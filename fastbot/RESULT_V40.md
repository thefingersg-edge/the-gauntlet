# RESULT — v40: the SPX-trained direction signal exists on five unseen markets, weaker; trading it there loses to costs.

```
SPEC:     PREREGISTRATION_v40.md  sha 19b05060…  (confirms the PREREGISTRATION_v39 winner)
METHOD:   v40_build.py (tl_build2, Gate 0 passed on 42,121 SPX rows) + v40_confirm.py 1.0; log data/v40/test_v40.log
RUN:      2026-09-26
VERDICT:  G1 PASS (direction)   G2 FAIL   G3 FAIL
```

**I am not a financial adviser. This is a measurement, not a recommendation.**

## G1 — direction, 2013–2026, on markets the model never saw (trained on SPX only, yearly walk-forward)
```
UK100 0.507   DE30 0.511   EU50 0.508   JP225 0.532   AU200 0.510
POOLED 0.512, day-bootstrap 95% lower bound 0.504  -> PASS (5 of 5 above 0.5)
```
**This is the project's first pre-registered PASS on a direction question.** It passed on markets, and in a design, that no model or researcher had fitted to. A random forest trained only on the S&P's event timeline ranks up-first against down-first 2-hour moves better than chance on the FTSE, DAX, Euro Stoxx, Nikkei and ASX.

It is also small: 0.512 against the 0.555 the same model scores on SPX itself. Most of the SPX-measured strength either does not travel, or is specific to the market the features describe (VIX, US releases, S&P positioning).

## G2 / G3 — trading it (first signal per market per day, net of the quoted spread)
```
                               trades   NET/trade   t      eras (net)             control   signal adds
E1 fixed 2h, stop 1σ           10,047   -2.21     -5.32   -2.52 -1.64 -2.38      -2.95     +0.75
E2 to close, tightening+b/e    10,047   -1.88     -5.29   -2.79 -1.25 -1.50      -2.50     +0.62
per market, E1 net (adds):  UK -1.22 (+0.10)  DE -0.76 (+0.25)  EU -4.39 (+0.63)  JP -3.06 (+1.63)  AU -1.59 (+1.13)
```
- The signal adds +0.6–0.75 bp a trade over random entries, against about +2.5 bp on SPX. The spreads here are 1–4.6 bp. Every market, era and exit loses.
- E2 (Dave's tightening stop) loses a little less than E1 and adds slightly less. It is the smoother ride, not the better edge, as on SPX.

## What it means
- **The direction information in the event timeline is real, not an SPX artefact.** It survived a clean out-of-sample, out-of-market test.
- **It is too weak to trade anywhere except where costs are lowest and the model is strongest: US indices at today's spreads.** The next piece of evidence therefore has to be forward data on SPX/NAS100, not more history.
- A market-specific timeline (local vol index, local releases) might strengthen the non-US signal. That would be a new pre-registration.
