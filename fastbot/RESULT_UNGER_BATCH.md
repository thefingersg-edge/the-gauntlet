# RESULT — UNGER BATCH (GOLDTREND1, CONTEXT1, MULTI1, ROTATE1, TURBO1): the public principles don't make money on our markets, but the contest maths explains the trophies

```
SPEC:     PREREGISTRATION_UNGER_BATCH.md  sha ce14205e…  (frozen 2026-10-09, before any number)
METHOD:   scripts/unger_batch.py  sha e31a29d2…  (frozen 2026-10-11, before any run; self-test passes; mechanical readings in its docstring)
DATA:     OANDA 15m bid/ask (data/v51 caches; shas in PROVENANCE), clean-day rule, end 2026-09-25
LOGS:     data/unger/run_goldtrend.log, run_context.log, run_multi.log, run_rotate.log, run_turbo.log
RUN:      2026-10-11, each once, in the registered order (PROBE1-OIL ran 2026-10-10)
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

| test | the Unger principle | result | verdict |
|---|---|---|---|
| GOLDTREND1 | gold trends; trade it more slowly to save costs | weekly probe −0.84, close-confirmed −1.68, 20-day channel +0.20 bp/day net (none above t 0.2) | **FAIL** 0/3 |
| CONTEXT1 | a simple idea plus "context" | none of 6 filters beats the unfiltered probe out of sample with t ≥ 2.39; best F4 inside day, t 1.79 | **FAIL** 0/6 |
| MULTI1 | several system types per market, combined | portfolio Sharpe **−0.68** (t −3.20); buy and hold +0.64 out of sample | **FAIL** |
| ROTATE1 | rotate monthly to recent winners | −0.07%/month vs hold-all (t −0.83); bottom-4 check +0.01 | **FAIL** |
| TURBO1 | how a contest is won (simulation) | with **zero** edge at 100% vol, the best of 200 entrants makes a median **+615%** in a year | descriptive |

## GOLDTREND1: slower is cheaper, but not enough
- **Spreads did fall.** Reversals per year dropped from 111 (daily probe) to 23 (weekly) and 7 (channel).
- **Financing then did the damage.** CFD financing costs about 1 bp/day while a position is held (policy rate + 2.5%). That took 158% of the weekly probe's gross and 68% of the channel's.
- **The futures route is reported, not gated:** +0.48, +0.94 and +1.42 bp/day (Sharpe 0.07, 0.13, 0.20). It is positive but nowhere near significant.
- **Buy and hold gold beat every rule:** Sharpe +0.40 (2006–26), +0.59 out of sample.
- **Close-confirmed entries were the worst.** "Next open" is the first bar after 17:00 New York, where gold's quoted spread is widest. That is the frozen spec, and it is disclosed.

## CONTEXT1: context filters remove trades, not losers
- The unfiltered clean-day probe made +3.37 bp/day (t 2.37), but almost all of it before 2013 (+7.79). Out of sample it made +0.86 (t 0.48).
- **Every filter cut 2005–12 profits.** F5 ("no gap") was the only one to beat the base in both halves (G2), but its out-of-sample t was 1.11.
- **The best out-of-sample t was F4 (after an inside day): t 1.79,** at 15% time in the market. It is a lead only if a fresh spec is written for it, and the multiple-testing bar applies.

## MULTI1: diversification works, but you can't diversify losers into a winner
- **The components barely move together:** average pairwise correlation +0.03. The portfolio's volatility is only 0.35× the average component's.
- **Only 3 of 12 core systems are positive:** SPX mean reversion (+0.38), gold trend (+0.11), NAS mean reversion (+0.05). Combining twelve mostly negative uncorrelated streams produces a **steadier negative** (t −3.20), not a positive.
- **On the futures route** the same portfolio is Sharpe +0.07: costs turn a flat mix into a losing one.
- **Oil (reported only):** WTI and Brent trend at +0.32 and +0.53. Adding them helps (Sharpe −0.51) but doesn't save it.
- **Disclosure:** UK100 clean days start in 2008-06, because earlier source data is sparse. Its systems join the portfolio from 2008-08.

## ROTATE1: no "strategy momentum"
- Top-4 by 6-month return lost 0.07%/month vs holding all 12. The 3- and 12-month lookbacks were also near zero (t −0.53, +0.73).
- The "bottom 4" check behaves like chance, except the 12-month bottom-4, which loses (t −2.21). Picking last year's worst systems is mildly worse.

## TURBO1: the trophy maths (descriptive)
One-year outcomes, 100,000 paths from the gold probe's own return shape:

| true Sharpe | vol | median year | P(≥ +100%) | P(≥ +600%) | P(ruin, −90%) |
|---|---|---|---|---|---|
| 0.0 | 100% | −39% | 8.9% | 0.35% | 3.2% |
| 0.5 | 100% | +0.5% | 21.5% | 1.5% | 0.9% |
| 1.0 | 25% | +24% | 1.9% | 0% | 0% |
| 1.0 | 100% | +66% | 41.5% | 5.1% | 0.2% |
| 1.0 | 200% | −4.6% | 34.5% | 13.7% | 22.4% |

- **Leverage beyond the edge destroys the median.** A Sharpe 1.0 trader is best off at about 100% volatility. At 200% their median year is negative and 1 in 5 is ruined.
- **The contest, with 200 entrants at 100% volatility:**
  - **If nobody has any edge, the winner still makes a median +615%.** That is about Unger's 2008 +672%.
  - **Mix 190 zero-edge traders with 10 Sharpe-1.0 traders: a zero-edge trader wins 58% of the time.**
- **A contest win is consistent with skill, but alone it can't prove it.** Unger's **three consecutive wins** are much harder to luck into, and that is the real evidence. It also explains the 99% card: copying contest-style leverage without the edge is a fast route to ruin.

## What this does to the puzzle
- **Confirmed:** commodities trend (gold, WTI) and indices don't. Diversifying across uncorrelated systems lowers volatility (correlation +0.03).
- **Not confirmed on our markets and costs:** the generic versions of context filters, multi-system combination and monthly rotation.
- **The missing piece is still the specific rules.** Unger trades about 30–40 futures with futures costs. The CFD route charges policy rate + 2.5% to hold, which is a cost he never pays, and it kills slow trend rules here.
- **Leads, not money:**
  - the futures-route gold channel (Sharpe 0.20);
  - F4 inside-day context (t 1.79);
  - oil trend (S1 Sharpe 0.32–0.53).
  - None passes, and each would need a fresh pre-registration.
