# PREREGISTRATION v35 — reactive signals: does the first step say "keep going"?

Frozen 2026-09-25 before any signed return was read (the budget read spreads
and squared returns only). Script: scripts/reactive.py v1.0.

I am not a financial adviser. This is a measurement, not a recommendation.

## 1. Why
v1 measured that a 3-sigma 5m NAS100 bar is followed by continuation
(an unregistered side-finding). Every snap-back hypothesis has since failed.
Here continuation is the pre-registered hypothesis, with the direction fixed
in advance: WITH the move.

## 2. Data
OANDA 5m bid/ask SPX500, NAS100, US30, bars 09:30–15:55 ET, sessions with
≥ 70 bars. Discovery 2005–2012 is gross only (bid = ask before 2012).
**Gated: 2013-01-01 → 2026-09-17, NET of the quoted spread.**

## 3. Signals
- z = the 5m bar return ÷ the RMS of the same time slot's return over the
  prior 20 sessions (trailing only).
- Shock = the day's first bar with |z| ≥ 3, starting 09:30–14:55.
- **A1 every shock:** enter at the next bar's open, with the shock; exit at
  the 15:55 bar's close.
- **A2 shock that holds:** the next bar gives back less than half the
  shock's body. Enter at the bar after that, same exit.
- **A3 shock out of calm:** the 12 bars before the shock had less total
  |return| than the median of the same 12 bars over the prior 20 sessions.
  Same trade as A1.
- **B intraday momentum** (the published "market intraday momentum" effect):
  the sign of the prior 15:55 close → 10:00 open sets the direction of a
  15:30 open → 15:55 close trade.
- Reported only: the A1 60-minute gross.

## 4. Gates (four tests, Bonferroni t ≥ 2.50, SEs clustered by date)
PASS needs all of:
1. holdout net > 0 with t ≥ 2.50;
2. net > 0 in each of 2013–17, 2018–21 and 2022–26;
3. holdout excluding 2020–21: net > 0 with t ≥ 1.64.

## 5. Power budget (holdout)
| test | trades | dates | RMS | cost | MDE (80%) |
|---|---|---|---|---|---|
| A1 | 5,101 | 2,110 | 86 bp | 0.96 bp | ≈ 6.3 bp |
| A2 | 4,589 | 2,029 | 84 bp | 0.97 bp | ≈ 6.2 bp |
| A3 | 1,354 | 827 | 58 bp | 0.99 bp | ≈ 6.8 bp |
| B | 10,150 | 3,388 | 30 bp | 0.94 bp | ≈ 1.7 bp |

**What the budget cannot see.**
- Holding a shock to the close is noisy. A shock edge between the ~1 bp cost
  and ~6 bp is invisible, so a FAIL for A means "no big-trend payoff of about
  6 bp or more per trade", not "no follow-through".
- For B, an effect smaller than about 1.7 bp is invisible, and B's published
  size may be about that small.
- The three indices move together, so they are close to one market. The
  date clustering is what keeps that honest.
- Breadth across markets (the DAX, gold) is not tested: those series exist
  only on 15m bars.

## 6. One run. No change of z threshold, sigma window, hold or eras after it.
