# Part G re-run after the R1/R2/R3/R5 fixes — 2026-09-11

All four defects fixed, everything re-run on the post-R4 bars.

## What changed

| rule | before | after | start before | start after |
|---|---|---|---|---|
| equal | +0.114 | **+0.330** | 2007 | 2006-01-23 |
| invvol | +0.078 | **+0.339** | 2013-04 | 2006-01-23 |
| riskparity | +0.101 | **+0.372** | 2013-04 | 2006-01-23 |
| cluster | +0.164 | **+0.354** | 2013-04 | 2006-01-23 |
| null | -0.058 | +0.055 | — | 2008-12-09 |
| buy and hold | +0.624 | +0.694 | 2005 | 2005-01-04 |

Every rule roughly tripled, and — the point of the exercise — **all four now
run on the same 5,349 rows starting the same day.** The old table compared
different samples *and* different market sets.

- **R2** `rolling(win)` defaults to `min_periods=win`, so on a ragged
  multi-market index it needed 252 *consecutive* non-NaN rows. Five markets
  never got one and were silently dropped from every vol-weighted rule, while
  `equal` — which never touches vol — kept all 21. `min_periods=int(win*0.8)`
  now matches the `live` threshold already used a few lines below.
- **R3** `.sum(axis=1)` returns 0.0 on an all-NaN row, so `.dropna()` removed
  nothing and ~2,900 leading zeros sat inside the Sharpe. `min_count=1` fixes it.
- **R5** already fixed: `rf_daily` uses `core.ppy`, not 252.

## Gate 0 — and a correction to what I reported

The gate now **FAILS**, but not for the reason I gave earlier.

    N_eff on strategy returns = 5.98   [threshold >= 6.0]
    stationary block bootstrap: median 6.06, 5th-95th 5.06 - 7.24
    fraction of draws clearing 6.0: 53.4%

**I previously reported the bootstrap as 3.98-5.85, "entirely below the
gate". That figure came from the code-review agent, ran on the pre-R4 data,
and my own measurement does not reproduce it.** The interval straddles the
threshold rather than sitting below it. The gate still fails — the point
estimate is 5.98, under 6.0, and only 53% of draws clear — but "entirely
below" was wrong and is withdrawn.

The substantive point survives and is unchanged: at dN_eff/drho = -34.4 a
hundredth of N_eff is a correlation difference of 0.0003, so the original
"6.01, PASS" had no resolution at its own threshold. A gate that cannot
distinguish pass from fail is not a gate. It now reports the interval.

## Does the conclusion change? Mostly no — but one gate flips

- **Gate 2 still FAILS.** No rule beats equal weighting in all three eras.
- **Gate 3 now PASSES.** The covariance-window sweep gives +0.332 / +0.368 /
  +0.372 / +0.367 — range 0.040, a genuine plateau. The old version spanned
  0.157 *and flipped sign* at 504 days. That sign flip was R2 and R3, not the
  world.
- **Gate 6 improves.** At 5bp risk parity is +0.175 and equal +0.142; before
  the fix every rule was negative at 5bp.
- **Gate 7 still FAILS, decisively.** Best allocation +1.34%/yr against
  buy-and-hold's +6.23%, at +0.372 against +0.694.
- **R9, now visible:** shifting the weights by 750 bars also shifts the
  null's start, so rule and benchmark ran on different spans. Matched:
  risk parity **+0.144** on the null's own span against the null's +0.055.
  Still ahead, and on a fairer comparison than before.

## The thing to be uncomfortable about

**The fix made the numbers better.** That is exactly what the project's own
standing note about the silver loader bug says to distrust: "the result got
better when the bug was fixed, which is not a reason to trust it more — that
is also what a bug still flattering the result would look like."

Three reasons to accept it anyway, none of them conclusive. The mechanism is
mechanical and inspectable, not a tuning choice. All four rules moved
together and now share a start date, which is what a sample-alignment fix
looks like. And the headline conclusion did not move: buy-and-hold still wins
by nearly five to one on return.

What changed is that Part G's numbers are now *right*, and one of its seven
gates turns out to have been failed by a bug rather than by the data.
