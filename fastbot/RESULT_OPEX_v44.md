# RESULT — v44: options-expiry week and the week after. Nothing there.

```
SPEC:     PREREGISTRATION_v44.md  sha 7917ad0e…
METHOD:   opex_v44.py 1.0; SPX500 + NAS100 OANDA 5m; GEX prior-day; log data/gex/run_v44.log
RUN:      2026-09-27
VERDICT:  H1 FAIL   H2 FAIL
```

**I am not a financial adviser. This is a measurement, not a recommendation.**

## Numbers (2011-05 → 2026-08; 183 expiry cycles per index)
```
H1 direction   week after expiry +49.5 bp  vs other weeks +62.9 bp   difference -13.4 bp  t -0.32   short-after net -50.9 bp   FAIL
H2 volatility  log(RV after / RV into) -0.016 (x0.98)  t -0.65   eras -0.048 +0.031 -0.029                                   FAIL
reported by GEX tercile at expiry:  low -0.096 (after-week +128.6 bp)   mid +0.014 (-26.2)   high +0.033 (+46.0)
expiry week itself (IN): SPX +13.8 bp, NAS +19.3 bp (weekly average about +25 bp)
```

## Read it plainly
- **There is no post-expiry weakness.** The week after monthly expiry is an ordinary week (difference −13 bp, t −0.3).
- **There is no volatility release either.** Volatility after expiry is 2% LOWER than into it, not higher.
- **Low-GEX cycles show volatility falling after expiry** (−0.096) and strong returns. That looks like ordinary volatility mean-reversion after stressed periods, not an expiry effect.
- **The popular "pinned into expiry, released after" story is not visible at the index level in 2011–26.** A plausible reason is that weekly and 0DTE expiries have spread the hedging roll-off across every day.

## Caveats
- **Weak comparison group:** the no-overlap rule leaves only 93 clean comparison weeks, so the H1 comparison is noisy. The MDE was about 56 bp in any case.
- **Quarterly expiries mix with rebalancing:** v45 separates the two.
