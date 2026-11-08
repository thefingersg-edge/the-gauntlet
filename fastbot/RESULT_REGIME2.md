# RESULT — REGIME2: ADX "trend strength" rescues neither direction nor patterns, and on strongly trending days the trend direction pointed the wrong way

```
SPEC:     PREREGISTRATION_REGIME2.md  sha 88569758…  (frozen before any number)
METHOD:   scripts/regime2_run.py (sha in PROVENANCE); Wilder ADX(14) on cash-session daily bars and on 15m bars;
          SESSION1 trade-level output; OANDA 15m bid/ask to 2026-09-25
LOGS:     data/run_regime2_q1.log, _q2.log, _q3.log
RUN:      2026-10-09
VERDICT:  Q1 0 of 6   Q2 0 of 86   Q3 0 of 2   -> FAIL
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

Self-test passed:
- a synthetic trend gave ADX 84;
- a random walk gave 17;
- truncating the data changed nothing earlier, so the calculation uses no future data.

The SESSION1 random partners were reproduced exactly from their seed.

## Q1 — on trending days (ADX ≥ 25), does the trend direction tell you where price goes next?
Trending days are 24–36% of days, depending on the market. b = average return when the signal says "up" minus when it says "down".
```
                        next day b (t)     next week b (t)    eras (next day)          instruments (next day)
D1 +DI > -DI            -11.2 (-2.2)       -46.6 (-2.7)       -8.8 / -13.8 / -14.8     all 4 negative
D2 close > SMA200        -9.8 (-1.5)        -5.0 (-0.2)       all negative             all 4 negative
D3 20-day breakout      -10.2 (-1.9)       -40.4 (-2.3)       all negative             all 4 negative
on ranging days (ADX < 20) the same signals are about zero (+2.2, -3.2, +0.1 bp next day)
```
**0 of 6 pass.**
- The surprise is the sign. On strongly trending days, betting with the trend lost money. After an up-trend, the next day averaged about 11 bp worse than after a down-trend. That held in every era and on all four markets.
- Strong trends tended to **snap back**: sharp sell-offs were followed by sharp rebounds, and strong rallies by give-backs. Volatility is about 50% higher on trending days (150 vs 101 bp a day), so these are the most violent periods.
- **Post hoc, a lead and not a finding.** "Fade the trend when ADX is high" was not the hypothesis, and the next-day version (t 2.2) would not clear the multiple-test bar anyway. If pursued, it needs its own pre-registration (REGIME3). It also has to beat the known short-term reversal in indices, which is probably what this is.

## Q2 — the right setup in the right regime (SESSION1 trades, daily ADX)
Rules:
- Continuation setups (breaks of structure, breakouts, marubozu, three soldiers…) were kept only when ADX ≥ 25 *and* in the DI direction.
- Reversal setups (CHoCH, pin bar, hammer, engulfing…) were kept only when ADX < 20.
- Random partners were filtered the same way.

**0 of 86 pass.**
- **Breaks of structure in confirmed trends are worse, not better:** 1h −10.1 bp (t −2.1), 30m −5.1 bp.
- **"Regime lift"** is the gain from the right regime beyond what the regime gives random entries:
  - continuation: +0.5 bp median, positive in 58% of tests (a coin flip);
  - reversal: +1.0 bp median, positive in 68% of 44 tests. This is a faint hint that reversal setups do a little better in quiet markets, which fits the Q1 snap-back. It is far below what would cover the spread.

## Q3 — ADX on the 15-minute chart itself (the SMC / structure trader's version)
| Test | Net | Verdict |
|---|---|---|
| Break of structure, kept only with 15m ADX ≥ 25 in the DI direction | −0.2 bp (t −0.2) | FAIL |
| Change of character, kept only with 15m ADX < 20 | −1.1 bp (t −1.9) | FAIL |

**0 of 2 pass.** Neither beats random entries filtered the same way.

## Read it plainly
- ADX does what it says: it measures how strongly price has been moving. That is not the same as knowing where it goes next. On these markets, strong moves were followed by partial reversals more often than by continuation.
- Matching setups to the regime does not create an edge. It slightly reduces the losses on reversal patterns.
- Together with REGIME1: **neither moving averages nor ADX gives a usable "overall direction" for intraday entries on SPX, NAS, UK100 or gold.** What trend tools do reliably is identify high-volatility periods (v52, v50). Their value is in sizing and risk, not entries.
