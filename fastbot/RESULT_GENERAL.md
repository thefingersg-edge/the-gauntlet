# RESULT — v34: VWAP / POC magnets and Rule-of-16 levels as general signals. All fail.

```
SPEC:     PREREGISTRATION_v34.md  sha 546725b2…
METHOD:   scripts/general_levels.py 1.0   log data/general_v34_run.log
DATA:     OANDA 5m bid/ask SPX500, NAS100, US30; every cash session 2005 → 2026-09-17
GATED:    holdout 2013 → 2026-09-17, NET of the quoted spread
VERDICT:  VWAP FAIL   POC FAIL   Rule of 16 FAIL
```

**I am not a financial adviser. This is a measurement, not a recommendation.**

## Numbers (bp per trade, 60-minute hold, t clustered by date)
```
                disc gross   hold gross     HOLD NET        2013-17  2018-21  2022-26  ex-20/21
VWAP rule        -0.00        -0.90 (-1.4)   -2.21 (t -3.6)   -2.18    -2.43    -2.05    -2.41
POC rule         +1.53 (1.5)  -0.87 (-1.5)   -2.20 (t -3.7)   -2.10    -1.76    -2.70    -2.44
Rule-of-16 fade  (disc cont. -0.47, t -0.26)
                              -1.49 (-1.3)   -2.75 (t -2.3)   -2.90    -2.33    -2.96    -3.57
```
All-slot slope of the 60-minute return on distance to VWAP/POC: +0.007/+0.025 in
2005–12 and −0.012/−0.009 in 2013–26 (|t| < 1.5). No pull either way.

## Read it plainly
- **Price does not return to the session VWAP or POC within an hour**, even
  when it is unusually far away. Gross is slightly negative in the holdout.
  After the quoted spread (about 1.3 bp over entry and exit) every era and
  every instrument loses about 2 bp a trade.
- **The Rule-of-16 band is not a turning point or a breakout point.** In
  2005–12 continuation after the first close beyond ±1 implied move was a
  coin toss (−0.47 bp, t −0.26). The pre-registered rule therefore faded it,
  and the fade lost. The holdout's unsigned continuation is +1.49 bp (t 1.25),
  the opposite sign to discovery. By rule it is **not** reversed, and even
  reversed it would be about 0 net.
- These are the TradingView scripts' best cases: level lines that look
  meaningful on a chart but carry no forward information once you measure
  them without hindsight and pay the spread.

## Caveats in the body
- The budget MDE is about 3 bp. A net edge near 1 bp would be invisible, but
  gross is negative, not small and positive, so there is no hint of one.
- Tick volume is OANDA's quote count. POC and VWAP from exchange volume could differ.
- This is the 60-minute hold only. Other holds were not tried, and trying them
  now would be a sweep.
- The v33 control-morning hint (b ≈ 0.06 toward VWAP, t 2.2) does not
  reproduce on the full every-day sample (holdout slope −0.012).
