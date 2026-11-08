# All four gates pass, and the last two cycles say don't believe it

```
RUN:      2026-08-29
METHOD:   exec_cost.py v1.0, PREREGISTRATION_v9. One run. No sweeps.
DATA:     14 quarterly roll dates, 2023-03 to 2026-06, 1m trade vs mark
VERDICT:  PROCEED on the frozen gates. Gate A 6.3%, Gate B 6.3 vs 8.0,
          Gate C 10/14, Gate D +2.42.
          AND: the two most recent cycles are 67.9% and 85.7% wide
          against a maximum of 12.3% across the previous eleven. The
          pass describes 2023-2025. It does not describe now.
```

**I am not a financial adviser. This is a measurement, not a
recommendation.**

---

## 1. The kill condition cleared first

Median deviation across 1,862 roll-date and ~30,000 prior-day traded
minutes: **3.727 bp.** Well above v9 §6's 0.5 bp floor.

`mark` is not derived from last trade. The two series are independent
enough to difference, and the measure is real. **That was the failure mode
I said was most likely, and it did not happen.**

## 2. The gates, as frozen

```
[PASS] Gate A  roll-date wide share      6.3%  (< 20%)
[PASS] Gate B  roll 6.3% vs prior 8.0%
[PASS] Gate C  10 of 14 dates, >= 30 minutes
[PASS] Gate D  drag 0.137 pts -> era 3 +2.42
```

Thresholds unchanged from the document delivered before any price was
read. **The result is a PASS and I am not moving anything.**

## 3. Gate B is a genuine win, and it is the one that needed this data

Settlement days are **not** worse than the twenty days around them — 6.3%
versus 8.0% pooled, and per cycle the median roll date is 2.1 points worse
with a maximum excess of 9.9, never breaching the +10 allowance on a single
cycle.

**No amount of forward daily sampling could have established this.** Track A
would have needed four roll dates a year for years. It is answered, and it
holds on both weightings.

## 4. Now the table, which says something the verdict line does not

| roll date | traded share of window | roll minutes | median dev | wide % |
|---|---|---|---|---|
| 2023-03-31 | 19.96% | 398 | 2.97 bp | 1.8% |
| 2023-09-29 | 0.98% | 14 | 3.07 | 7.1% |
| 2023-12-29 | 3.64% | 212 | 3.90 | 12.3% |
| 2024-03-29 | 5.90% | 133 | 3.45 | 6.0% |
| 2024-06-28 | 13.12% | 104 | 3.06 | 4.8% |
| 2024-09-27 | 18.86% | 241 | 3.15 | 2.9% |
| 2024-12-27 | 11.44% | 99 | 3.35 | 8.1% |
| 2025-03-28 | 7.97% | 120 | 3.01 | 2.5% |
| 2025-06-27 | 8.09% | 299 | 2.82 | 0.3% |
| 2025-09-26 | 4.93% | 50 | 2.32 | 6.0% |
| 2025-12-26 | 13.73% | 143 | 5.48 | 7.7% |
| **2026-03-27** | **0.46%** | **28** | **36.59** | **67.9%** |
| **2026-06-26** | **1.27%** | **21** | **66.24** | **85.7%** |

Eleven cycles between 0.3% and 12.3% wide, with median deviations clustered
between 2.3 and 5.5 bp. Then two cycles at **67.9% and 85.7%**, with median
deviations of **36.6 and 66.2 bp**.

That is not a tail. It is a different market, and it is the most recent one.

## 5. Why the pooled gate did not see it

Gate A pools every roll-date minute and takes the share that were wide.
The two 2026 cycles contribute **49 minutes out of 1,862** — because they
were too illiquid to produce more.

**Pooling by minute gives the liquid cycles the most weight and the
illiquid ones the least, which is exactly backwards for a cost measure.**

```
pooled by minute (what v9 froze)    6.3%   PASS
equal-weighted per cycle           16.4%   PASS, but four points off the bar
```

Both readings pass. The gate stands as written and pooling is a defensible
choice. But the second number is the one that describes what a randomly
chosen future roll would meet, and it is close to failing.

## 6. Gate C excluded the evidence, for the reason that is the evidence

Four dates fell below the 30-minute minimum: 2026-06-26 (21), 2026-03-27
(28), 2023-09-29 (14), 2023-06-30 (0).

**Two of the four are the two most recent cycles.** They were excluded for
insufficient data *because they were illiquid* — which is the thing being
measured. A data-sufficiency test that discards the observations carrying
the finding will always report a healthier market than exists.

I did not anticipate this when writing v9 §5, and it is not a reason to
change Gate C now. It is a reason not to read 10-of-14 as reassurance.

## 7. The bias in §7 of v9 turned out to be the dominant feature

v9 warned the measure only sees minutes where a trade printed. In the 2026
windows, **99.5% of minutes had no trade at all** — 30,101 untraded against
28 traded on the March roll.

A wide book with no trades is invisible here. So 67.9% and 85.7% are
**lower bounds**, computed from the handful of minutes when someone was
willing to transact. The true figures are worse by an unknown amount.

## 8. What it means forward

| assumption | drag | era 3 | |
|---|---|---|---|
| all 14 cycles (Gate D as frozen) | 0.137 pts | **+2.42** | PASS |
| the last two cycles only | 2.06 pts | **+0.50** | **FAIL, not narrowly** |

If the liquidity regime of the last six months persists, the roll alone
costs four times era 3's entire headroom over its counterparty-risk bar.

And this is not an extrapolation from two backtest points. Track A saw the
September book at **158 bp** on 25 August, live, three days ago. The
retrospective and forward evidence agree that something changed in 2026.

## 9. Verdict

**The gates pass and the candidate does not clear.**

Both halves are meant. Moving a threshold now because the answer is
uncomfortable would destroy the only thing twenty-five investigations have
built. The pre-registered result is PROCEED.

But a pre-registered gate answers the question it was written to ask, and
the question I wrote in v9 was *"what did a roll cost?"* — past tense,
across 14 cycles. The answer is: about 3 bp, until this year, when it
became about 50, on a book where almost nobody trades.

**The right conclusion is not that entry cost is fine. It is that entry
cost was fine, and the thing that changed is not in the gates.**

## 10. What is now the open question

Not "how wide is the spread" — measured, twice, from two directions.

**Why did liquidity in Kraken's dated BTC quarterlies collapse in 2026, and
is it structural?** The traded share of the roll window went from 13.7% in
December to 0.46% in March. If that is a permanent migration — to perps, to
another venue, to the ETF complex — then the premium `RESULT_KRAKENBASIS`
measured over 18 cycles is real, historical, and no longer reachable, for
the same reason the inverse contract is not.

That would be the fourth time this candidate has been killed by
availability rather than by the premium being absent.

## 11. Scoreboard

**Twenty-five investigations. Twenty rejections, one
measured-but-unreachable premium, one headline that dissolved on
decomposition, one real premium whose edge vanished at daily resolution,
and one that clears every pre-registered gate on a market that appears to
have stopped trading six months ago.**
