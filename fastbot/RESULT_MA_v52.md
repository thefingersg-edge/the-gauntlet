# RESULT — v52: 200-day moving average as a risk overlay. It cuts the drawdown by more than half, but on Sharpe its timing is no better than random. As pre-registered, it is NOT USEFUL. It does add to vol sizing on the US indices.

```
SPEC:     PREREGISTRATION_v52.md  sha 0101fb2f…
METHOD:   ma_overlay_v52.py 1.0; daily_close.py sha 617eadd2…; SPX500, NAS100, UK100, XAUUSD daily closes to 2026-09-25; DGS3MO financing; log data/run_v52.log
          post-hoc addendum: v52_posthoc_nulldd.py, log data/v52_posthoc_nulldd.log
RUN:      2026-10-01
VERDICT:  G1 PASS   G2 FAIL   G3 FAIL   -> NOT USEFUL      G4 PASS (adds to implied-vol sizing, SPX+NAS)
```

**I am not a financial adviser. This is a measurement, not a recommendation.**

Self-test passed: an always-on flag reproduces buy-and-hold, and a perfect-foresight flag has a very high Sharpe.

## Numbers (equal-weight portfolio of 4, 2005-10 → 2026-09, net of spread and financing)
```
                Sharpe   CAGR    max DD   Calmar   era max DD (05-12 / 13-19 / 20-26)
buy & hold      +0.476   +5.88%  -42.0%   0.140    -42.0 / -15.3 / -26.0
200-day MA      +0.411   +3.34%  -17.6%   0.190    -16.7 / -13.3 / -17.6
G1  DD -17.6% vs 0.75 x B&H = -31.5%, lower in every era                       PASS
G2  Sharpe +0.411 vs circular-shift null 95th pct +0.539 (null median +0.404)  FAIL
G3  Sharpe +0.411 < B&H +0.476 - 0.05; Calmar 0.190 > 0.140                    FAIL
G4  SPX+NAS IV-sized base Sharpe +0.481 DD -32.9% Calmar 0.171
    + 200-day MA            Sharpe +0.456 DD -21.1% Calmar 0.214               PASS

reported per instrument (Sharpe / max DD)        B&H              200-day MA       in market
    SPX500                                       +0.341 / -59.6%  +0.350 / -24.3%  78%
    NAS100                                       +0.565 / -55.8%  +0.589 / -25.0%  80%
    UK100                                        +0.039 / -51.9%  -0.355 / -68.8%  68%  (whipsaw; gross also negative)
    XAUUSD                                       +0.398 / -50.5%  +0.366 / -39.5%  68%
reported: 100-day MA Sharpe +0.357 DD -16.3%;  same-day execution Sharpe +0.391 DD -18.5%
reported: SPX+NAS  B&H +0.470 / -57.1%   200-day MA +0.514 / -23.0%   VIX rule (v50) +0.420 / -47.0%
```

## Post-hoc (not pre-registered, descriptive only)
The same 500 random-timing nulls, this time recording drawdown:
```
4-instrument   real DD -17.6% vs null median -37.2%   -> deeper in 100% of nulls;  Sharpe: 46% of nulls >= real
SPX+NAS        real DD -23.0% vs null median -52.2%   -> deeper in 100% of nulls;  Sharpe: 14% of nulls >= real
```

## Read it plainly
- **As registered, it fails.** G2 tested whether the timing beats chance *on Sharpe*. It does not: random exits with the same time out of the market give the same Sharpe.
  - Return-to-risk also slipped (G3). Most of that is UK100, where the average just whipsaws (Sharpe −0.36).
- **It does what a trend filter is supposed to do: avoid the big bear markets.**
  - Its drawdown was smaller than every one of the 500 random-timed versions.
  - On SPX and NAS it halves the worst loss (−57% → −23%) without hurting Sharpe.
  - That drawdown check was added after the run, so it is a lead, not a finding.
- **It stacks with implied-vol sizing (G4 PASS).** On SPX+NAS, adding the filter to vol sizing cuts the drawdown from −33% to −21% and raises Calmar from 0.17 to 0.21, for a small Sharpe cost. That is the label the pre-registration allowed for.
- **This is the same family as the other survivors: risk control, not return.** If it is pursued, the honest next step is a fresh pre-registration on US equities with drawdown against the random-timing null as the primary gate, judged forward.

## Caveats
- The drawdown result rests on two or three bear markets (2008, 2020, 2022).
- The CFD earns nothing when flat, and the overlay saves financing while flat.
- UK100 and gold were included by design. Their poor showing is part of the result.
