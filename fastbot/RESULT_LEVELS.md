# RESULT — v33: level magnets and the Rule of 16. Both fail.

```
SPEC:     PREREGISTRATION_v33.md  sha a730ea5e…  (frozen before any fade was read)
METHOD:   scripts/premarket_levels.py 1.0   log data/levels_v33_run.log
GATE 0:   31,610 trades matched v27 gross_H0, max |diff| 5e-7 bp  PASS
VERDICT:  VWAP FAIL   POC FAIL   Rule of 16 FAIL
```

**I am not a financial adviser. This is a measurement, not a recommendation.**

## What was asked
Two ideas from the TradingView public-script survey (claude/survey_tradingview_2026-09.md):
A. Is the release fade heading back to a pre-release level (overnight VWAP,
   volume point-of-control, the 08:15 bar's edge)?
B. Does a move that is big *relative to the VIX-implied daily move* fade more?

## Numbers (fade = 08:45→09:45, bp; SEs clustered by date)
```
                 S1 CPI+NFP     S2 claims      S1 ex-2020/21   S3 control
magnet b on D    b      t       b      t       b      t        b      t
 VWAP          -0.008 -0.17   +0.022 +0.50   -0.028 -0.58    +0.064 +2.18
 POC           -0.003 -0.09   +0.033 +1.04   -0.017 -0.45    +0.049 +2.14
 GAP (report)  +0.004 +0.03   -0.049 -0.23   +0.005 +0.05    +0.239 +2.30
Rule of 16 b   +0.015 +0.43   +0.084 +1.08   +0.014 +0.40    +0.034 +1.08
```
Not blind, reported only: fade on the VIX-implied move itself, c +0.052 t +1.51
(v31 had already seen VIX vs bounce at t +1.20).

## Read it plainly
- **On release mornings, where the level sits tells you nothing** about the
  fade: b is ≈ 0 with the wrong sign in S1. The budget could see a magnet of
  b ≥ 0.17 (POC) / 0.20 (VWAP); if the whole 3.6 bp fade were a trip back to
  the level, b would be ≈ 0.16. It isn't there. Small magnets (b ≈ 0.10) stay
  invisible to this sample — a null here means "no strong magnet".
- **On ordinary mornings there is a faint pull to VWAP/POC** (b ≈ 0.05–0.06,
  t ≈ 2.1–2.2 — below the 2.39 gate, and not a pre-registered claim). Even if
  real it is ~1 bp on a typical distance: far inside costs.
- **Using the level as a take-profit makes the release trade worse**, even
  with fills assumed exactly at the level: S1 +3.61 fixed vs +2.88 (VWAP),
  +3.09 (POC), +2.57 (GAP). Price touches the level about a third of the
  time and the fixed hour captures more than the level exit gives up.
- **Rule of 16 adds nothing** beyond v28's trailing-sigma scaling: the fade
  does not grow with the move measured against option-implied volatility.

## What this closes
The survey's two best-prior ideas. Add to the dead list: level magnets
(VWAP/POC/gap fill) and implied-move scaling. The release fade remains a
roughly fixed-size, release-specific bounce with no known driver.

## Caveats in the body, not the end
- OANDA tick volume is quote count, not exchange volume.
- VIX is used for all six instruments, including EUR/USD and gold.
- GAP correlates 0.94 with |move|; it could not be separated (budget said so).
