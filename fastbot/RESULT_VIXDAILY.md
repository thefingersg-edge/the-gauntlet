# Daily resolution — the measurement that turns the verdict over

```
RUN:      2026-08-18
METHOD:   vix_daily_risk.py v1.2 — MEASUREMENT ONLY, no strategy optimised
DATA:     VX1!/VX2!, TradingView daily, 5,505 sessions, 2004-03 to 2026-08
VERDICT:  the worst drawdown is -68.20 vol points, not -47.57. Sized to the
          same 30% budget the trade returns 3.4-4.0% of account against a
          risk-matched index at 5.1%. The index now wins at every plausible
          cash rate.
```


> **RESTATEMENT NOTE — 2026-10-29.** `--monthly-dd` in `vix_daily_risk.py`
> defaults to a hardcoded **-47.57**, which is the pre-fix monthly drawdown.
> The script never recomputes it, so every comparison against "the monthly
> measure" in the original of this file inherited a stale constant. Re-run
> against the corrected monthly drawdown (-55.97 from `vix_carry_budget.py`),
> the gap narrows: the monthly series oversizes by **23%**, not 43%. Every
> figure measured by this script itself -- -68.20, -17.60, -56.39, +174.3,
> the -6 roll offset -- reproduces exactly and is unchanged. **The verdict is
> unchanged.**

---

## 1. What the monthly measure could not see

`RESULT_VIXCARRY.md` sized everything off a monthly premium series and named
this as its own blind spot. It was right to.

```
worst drawdown, monthly measure    -55.97 vol pts
worst drawdown, DAILY              -68.20 vol pts   2007-02-22 -> 2008-11-20
   recovered 2012-03-23 — 1,856 days, five years and one month, peak to peak
same daily curve marked at MONTH ENDS   -56.39
```

Marking the same position at month ends understates the loss actually
carried by **21%**. Sizing off the monthly series overstated the position
that survives by **23%**.

```
                     drawdown    size on $10,000    return on account
monthly measure        55.97      0.54 contracts          4.7%
DAILY                  68.20      0.44 contracts          3.8%
```

## 2. And the benchmark comparison flips

Against the index over the same window, scaled to the same 30% drawdown
budget (from `vix_carry_budget.py --diagnose`):

| cash | index, sized | VIX carry, monthly dd | VIX carry, DAILY dd |
|---|---|---|---|
| 0% | 6.3% | 4.7% | **3.8%** |
| 2% | 5.1% | 4.7% | **3.8%** |
| 4% | 4.0% | 4.7% | **3.8%** |

On corrected dates the monthly measure already loses to the index at 0% and
2% cash, and wins only at 4%. **On the daily measure it loses at every cash
rate**, and it still has to pay for a futures broker neither account
provides.

`DESIGN_BRIEF.md`'s bar is to beat equity beta. This does not.

## 3. February 2018, which was invisible monthly, is the worst day in the sample

```
worst single DAY   -17.60 vol pts  =  $1,760 per mini contract   2018-02-05
worst 5 days       -31.90
Feb 2018 peak-to-trough in window   -20.90
```

The single worst session in twenty-two years is **not** in 2008 and **not**
in 2020. It is 5 February 2018 — the day XIV collapsed — and the monthly
series did not rank that month in its worst five, because most of the move
retraced before month end.

That is the entire case for having built this file. A measurement that
cannot see the worst day in its own sample is not a conservative
measurement; it is a wrong one.

And this is still **close-to-close**. VIX futures traded far beyond the
settlement print that evening. The true intraday figure is worse and is not
in this data at any resolution available here.

## 4. What the roll correction was worth, which is everything

```
corrected, net of cost   +174.3 vol pts over 22.4 years  = +0.65/month
naive -diff(VX1!)          +2.1 vol pts
difference               +172.2
```

Differencing a continuous contract returns **approximately zero**. The whole
premium lives in the roll, and a continuous series jumps *upward* at each
roll, so the naive calculation charges the position for the carry it is
collecting. Had this been done without the correction, the strategy would
have measured as flat and been written up as a rejection — the right verdict
for entirely the wrong reason.

The corrected +0.65/month also cross-checks the monthly measure's +0.88
gross: this reconstruction is short the FRONT month, the monthly measure is
short the SECOND. Different exposures, same order of magnitude, arrived at
by different arithmetic.

## 5. Four errors on the way here, and what each one cost

**The scan span.** `scan_offsets` searched ±4 trading days around
settlement, a number chosen for no reason. The real switch is at **−6**. The
answer was outside the search window, so no amount of data could have found
it. An arbitrary search window is an assumption wearing a search's clothes.

**The ranking.** Candidates were ranked by |t|, so a large *negative* step
counted as a strong rival. A contract switch can only step **up** — the
outgoing front month is replaced by a dearer one. A negative step is not a
weak roll, it is a different phenomenon, and letting it hold the runner-up
slot vetoed a correctly identified roll (t=6.8) on the strength of noise
pointing the wrong way (t=−3.8).

**The timestamps.** TradingView stamps a daily futures bar at the moment the
session *opens* — 17:00 America/Chicago on the previous calendar day, which
is 23:00 UTC in winter and 22:00 UTC in summer. Every date in the whole VIX
analysis was one day early, by an amount that changed with daylight saving.
All 5,636 bars sit at exactly 17:00 Chicago; the +17.60 bar stamped
`2018-02-04 23:00 UTC` is the **2018-02-05** session. Fixed in
`vix_curve_budget.load_csv`, so every file downstream inherits it.

**The detector I did not build.** The obvious empirical fix — pick, in each
expiry cycle, the day that most looks like a switch — would have found a
"roll" in pure noise. Worked through: on a random walk with no rolls at all,
the argmax day shows a step of roughly 1.5× the slope, comfortably inside
the band I had set for "this is real". That detector manufactures the thing
it is looking for. It was never written.

Three of the four were caught by a gate designed to fail. The scan span was
caught by the guard **refusing** rather than returning the best of a bad
set — which is the behaviour that guard exists for, and the first time in
this project one has paid off by declining to answer.

## 6. Verdict

**Rejected, on the project's own criterion.**

The premium in `RESULT_VIXCURVE.md` is still real: ~0.34 vol pts of genuine
carry, sign-consistent across three eras including two crises. Nothing here
touches that.

What is now measured is that its risk is **22% larger than the monthly
series implied**, and at that risk it returns less than a risk-matched
holding of the index, before a broker, before intraday, and before a margin
regime that tightens in exactly the episodes that produce the drawdown.

The honest one-line summary: **a genuine risk premium that does not survive
being measured at the resolution its own risk occurs at.**

## 7. Scoreboard

**Twenty investigations. Sixteen rejections, one measured-but-unreachable
premium, one headline that dissolved on decomposition, and one real premium
whose edge over the index dissolved when the drawdown was measured daily
instead of monthly.**

The one thing that has beaten equity beta in this entire project is still
equity beta.
