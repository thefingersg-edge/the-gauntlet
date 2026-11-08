# Findings — cost of carry on the SPX500 H4 strategy

VERDICT: FAILS condition 3 — not economic on this vehicle. 2005-2008 earns +0.39%/yr after financing against a risk-free 3.78%/yr, i.e. below cash. Carry is 6.1x the spread charge.

**Registration:** `PREREGISTRATION_SPX500_H4_CARRY.md` (2026-10-10)
**Run:** 2026-10-10, `carry_cost.py`
**Outcome: condition 3 fired. Not economic on this vehicle.**

In the 2005-2008 window the strategy earns **+0.39%/yr after financing** while
effective fed funds averaged **3.78%/yr**. It is below cash by over 3 points.
The 2023-2026 window survives comfortably at +10.85%/yr.

---

## 1. What was charged

OANDA's published index-CFD terms, confirmed 2026-10-10:

    long:   notional x (benchmark + 2.5%) x days/365    debited
    short:  notional x (benchmark - 2.5%) x days/365    credited

Accrual is per calendar day, which carries weekends automatically. Benchmark is
lagged one business day for publication.

### Benchmark: the registered series was used after all

The registration specified **DFF** (daily effective fed funds). It was then
amended to `DGS3MO` on the grounds that "FRED is unreachable" — which was
wrong, and overstated a narrower fact. FRED is blocked by the **Cowork VM's
proxy** (a limitation `flows/fetch_announce.py` already documents in its own
header), not from Dave's Mac, and other projects in this tree have been pulling
FRED series all along. `fastbot/data/v59/fred/DFF.csv` was already on disk,
daily, 1954-07-01 to 2026-10-08.

So the test was re-run on **DFF, the originally registered benchmark**. That is
a restoration of the registered spec, not a further amendment. **All three
benchmarks agree on all three conditions**, so nothing is inconclusive:

| benchmark | 2005-2008 mean | break-even | net %/yr at 2.5 | verdict |
|---|---|---|---|---|
| **DFF (registered)** | 3.78% | **5.51** | **+0.39%** | fails cond. 3 |
| DGS3MO (substitute) | 3.48% | 5.85 | +0.44% | fails cond. 3 |
| policy rate (cross-check) | 3.78% | 5.51 | +0.39% | fails cond. 3 |

DFF is the slightly harsher benchmark, as expected: effective fed funds ran
above the 3-month bill through 2005-2008, so the substitute I reached for was
mildly *favourable* to the strategy. The figures below are DFF.

The 2.5% admin fee is **OANDA's published figure**, not an assumption inherited
from the gold work — that was checked rather than carried over. A third-party
aggregator listing −6.4%/yr was discarded as irreconcilable with a positive
SOFR plus a positive markup; noted for the record in the registration.

---

## 2. Results

**2005-2008** — 59 trades, 4.0y, spread-only **+5.4% (+1.32%/yr)**

| markup | carry $ | carry %/yr | net % | net %/yr | Sharpe |
|---|---|---|---|---|---|
| 1.0 | 3,019 | 0.76% | +2.4 | +0.59% | 0.23 |
| **2.5 (OANDA)** | **3,809** | **0.95%** | **+1.6** | **+0.39%** | **0.16** |
| 4.0 | 4,600 | 1.15% | +0.8 | +0.20% | 0.09 |
| 6.0 | 5,653 | 1.42% | −0.3 | −0.06% | −0.01 |

Break-even markup **5.51** on DFF. Risk-free over the window: **3.78%/yr**.

**2023-2026** — 53 trades, 3.6y, spread-only **+63.2% (+14.53%/yr)**

| markup | carry $ | carry %/yr | net % | net %/yr | Sharpe |
|---|---|---|---|---|---|
| 1.0 | 14,455 | 4.00% | +48.8 | +11.63% | 1.00 |
| **2.5 (OANDA)** | **18,147** | **5.03%** | **+45.1** | **+10.85%** | **0.92** |
| 4.0 | 21,839 | 6.05% | +41.4 | +10.06% | 0.84 |
| 6.0 | 26,762 | 7.41% | +36.5 | +8.99% | 0.74 |

Break-even markup **20.80**. Risk-free over the window: 4.60%/yr.

### Kill conditions

| # | condition | verdict |
|---|---|---|
| 1 | break-even markup ≥ 2.5 on both windows | **pass** (5.51 and 20.80) |
| 2 | 2005-2008 still positive at 2.5 | **pass** (+1.6%) |
| 3 | post-carry return ≥ 2.0%/yr on both windows | **FAIL** — 2005-2008 = +0.39%/yr |

§4: "not economic on this vehicle if **any** of" — so condition 3 settles it.

### Robustness check added 2026-10-11: the markup assumption does not matter here

OANDA's live **XAU_USD** card turned out to carry a **1.19%** markup, not the
2.5% published for index CFDs (see `journal/FINDINGS_GOLD_4H_CARRY.md` §0,
where that error inflated the gold estimate 2.3×). So the markup used here was
re-tested:

| window | markup 0.00 | markup 1.19 | markup 2.50 |
|---|---|---|---|
| **2005-2008 net %/yr** | **+0.72%** | **+0.57%** | **+0.39%** |
| 2023-2026 net %/yr | +12.13% | +11.53% | +10.85% |

**Condition 3 (≥ 2.0%/yr) fires at every markup, including zero.** The verdict
does not rest on the 2.5% figure — it rests on the benchmark rate and on how
little gross return the 2005-2008 window has to charge against. The gold
mistake does not propagate here.

(SPX500's own live rate card has not been read; it should be, but the
robustness above means it cannot change the outcome.)

---

## 3. The number that matters

Carry takes **72% of the pre-window return** — 0.95%/yr out of 1.32%/yr —
leaving +0.39%/yr against a risk-free 3.78%/yr. **Cash beat it by over 3 points
a year**, and that is before considering that the strategy carried leverage and
drawdown to earn it.

This is the gold 15m outcome almost exactly: there, Sharpe 0.86 became
2.93%/yr net and a CFD at rf+2.5% was worse than cash with break-even carry
4.35%. Here the break-even markup is 5.51 points, so H4 clears the fee itself —
but clearing the fee is not the same as beating cash, and the registration's
condition 3 is what caught the difference. Condition 1 alone would have passed
it.

---

## 4. Predictions scored

| # | prediction | outcome |
|---|---|---|
| 1 | 2005-2008 fails conditions 1, 2 and 3 | **partly right** — fails 3, but **passes 1 and 2**. Break-even is 5.51 points, inside the ~4-7 range I estimated, yet that does not sink it: the strategy pays the fee and still cannot beat cash. The mechanism I predicted was wrong even though the verdict was right. |
| 2 | 2023-2026 passes all three | **RIGHT** — +10.85%/yr, break-even 20.80 |
| 3 | the windows disagree, pre window is the honest reading | **RIGHT** |
| 4 | carry exceeds spread in the pre window | **RIGHT, and far larger than expected** — carry is **6.1x** the spread charge in the pre window and **29.8x** in the post window |

Prediction 1 is the instructive miss. I estimated break-even near a 4-7 point
markup from a back-of-envelope "return / financed notional" and got 5.51, which
is inside that range — but I then reasoned that this meant the fee would sink
it. It does not: 5.51 > 2.5. What sinks it is the *level* of the surviving
return relative to cash, which is a different test, and only condition 3
expressed it. Writing three conditions rather than one is what saved the
verdict from my own arithmetic.

---

## 5. What this adds to the programme

**The spread-only accounting used throughout this tree is not adequate for
strategies that hold overnight.** Carry is 6.1x the spread charge in the pre
window and 29.8x in the post window. Every backtest here charges spread and
nothing else, and every one of those that holds positions for days is
understating its costs by roughly an order of magnitude.

This does not invalidate the tree's conclusions, because they were nearly all
*negative* — adding an uncharged cost makes a failing strategy fail harder.
The exposure is to the positives:

- **The live gold 4h forward test (`journal/`) has the same unpriced charge.**
  `RULES.md` v2 is frozen and `FORWARD_TEST_SETUP.md` works in ~33 trades to a
  verdict. If that strategy holds for days at meaningful notional, its expected
  net is overstated by the same mechanism measured here. **This should be
  checked against its own spec before the forward test reports** — not by
  changing frozen rules, but by computing what carry will cost it so the
  verdict can be read correctly when it arrives.
- **Family F (IV sizing), pineport's one positive result**, sizes positions to
  a risk target. Larger notional means larger carry. Whether its replication
  survives financing has not been asked.

`carry_cost.py` is written to be reused for exactly this: point it at any
results dir with a `config.json` and a price CSV.

**And a second-order point.** H4 passed the condition I expected to be
decisive (break-even markup) and failed one I added almost as a floor
(2.0%/yr). Had the registration contained only condition 1 — the condition the
§2 arithmetic was built around — this would have been recorded as surviving
carry. The habit of writing several independent conditions, not just the one
the reasoning points at, is what produced the right answer here.

---

## 6. Status of the H4 strategy

Unchanged and closed. It failed conditions 1 and 4 of
`PREREGISTRATION_SPX500_timeframes.md` on risk-adjusted return, and this test
adds that it would not have been economic even had it passed. Per §6 of this
registration, nothing here returns it to live consideration, and the
post-2023 window may not be quoted as the result.

The recommendation from the timeframes findings stands: **stop the live
SPX500 H4 strategy.**

*Not financial advice. Measurement, not recommendation.*
