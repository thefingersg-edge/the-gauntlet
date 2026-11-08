# RESULT — v50: the news-based fear index tracks volatility, but VIX already carries all of it. It adds nothing to the forecast and does not rescue VIX carry.

```
SPEC:     PREREGISTRATION_v50.md  sha 8560ed09…  +  amendment PREREGISTRATION_v50.1.md  sha 6beae2ec…
METHOD:   fear_v50.py 1.0; fear table data/v50/fear_table.csv sha e58d9de5… (fear_build_v50.py, from raw files hashed before reading);
          SPX500/NAS100 OANDA 5m RTH RV; VIXCLS; VX1!/VX2! via vix_daily_risk; log data/run_v50.log
RUN:      2026-09-28
VERDICT:  G1 FAIL   G2 FAIL   G3 FAIL   -> NOT USEFUL
```

**I am not a financial adviser. This is a measurement, not a recommendation.**

## Amendment (v50.1, frozen before the table was built)
TPU daily only starts in 2015. The primary composite therefore became C = mean(z_EPU, z_GPR), which covers the full sample. The three-part composite with TPU was reported only. Google Trends arrived as monthly UK data and is reported only.

## Numbers
```
SPX500, 5,364 days 2005-02 -> 2026-08; NW-HAC 5 lags; gate t >= 2.39
self-test: planted +10% RV per sd -> t +12.1; planted -10% -> FAIL  (OK)

G1  HAR+VIX+C      b -0.0007  t -0.07   (-0.1% next-day RV per sd of C)
    eras  2005-12 +0.009 (t 0.5)   2013-19 -0.025 (t -1.3)   2020-26 +0.016 (t 0.9)          FAIL
G2  OOS 2009+, DM  loss gain -0.00023  t -1.50  (adding C made forecasts slightly WORSE)
    eras  all three negative                                                                  FAIL
G3  short VX1, 2006-01 -> 2026-08, vol points, gross
    always short            total +173.5   worst DD -65.5   total/|DD| 2.65   in market 100%
    fear rule (C top 5th)   total +157.1   worst DD -51.0   total/|DD| 3.08   in market  77%
    VIX control (top 5th)   total +127.4   worst DD -30.8   total/|DD| 4.13   in market  80%  FAIL

reported:
  C alone, without HAR/VIX         b +0.233  t +6.03   <- fear does track volatility...
  EPU alone +0.7% per sd (t 0.75);  GPR alone -0.7% (t -0.91)   <- ...but none of it survives VIX
  t-1 timing t -0.26;  5-day horizon t -0.39;  NAS100 t -0.63, OOS DM t -1.08
  direction: SPX RTH return on C  t -0.38
  C3 incl. TPU (2016+, n 2,555)   +3.0% per sd  t +2.11
  TPU alone (2016+)                b +0.031  t +2.83
  Google Trends UK monthly: 'crash' t -0.02, 'recession' t +1.50
  G3 with 1 tick per switch: fear 2.68, VIX control 3.64
  G3 flat when EITHER fires (post-hoc): total +137.7, DD -20.7, ratio 6.63, in market 64%
```

## Read it plainly
- **The idea behind the table is right, but the market got there first.** Newspaper fear moves with volatility: on its own, t is 6. But once yesterday's VIX and recent volatility are known, it adds nothing (t −0.07). Out of sample it makes the forecast slightly worse. The options market already prices what the papers are writing.
- **For VIX carry, VIX itself is the better alarm.** Stepping aside when fear is high cut the worst drawdown from −66 to −51. Stepping aside when VIX is high cut it further, to −31, with a better ratio.
  - Using both together looks better still (ratio 6.6). That is post-hoc and not a finding. Most of that improvement comes from the VIX rule.
- **The one thread worth noting is tariffs.** Trade Policy Uncertainty since 2016 adds to VIX at t 2.8, and the three-part composite at t 2.1. That is reported only, on a short sample dominated by the 2018 and 2025 tariff episodes. It would need its own pre-registration and a forward test before it means anything.
- **This matches the programme's pattern.** Free public information, however it is combined, is already in the price. VIX is the market's own fear index, and it is hard to beat with slower, cruder versions of the same thing.

## Caveats
- The index histories are snapshots and may have been rescaled. The forward record (v50 §Forward record) is the clean test.
- G3 turns on a handful of crisis episodes and has no significance test. It is gross of switching costs, which are reported separately.

## CLOSED 2026-09-28 (Dave's decision)
v50 is closed. The fear composite duplicates what VIX already prices, with more effort: G1 t −0.07, and the VIX rule beat it in G3. The forward record in v50 §Forward record is **not** started, and no monthly downloads are needed. The TPU (tariff) lead stays in this file as a reported observation only. It is not queued.
