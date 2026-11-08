# Where we actually are — what fifteen rejections do and do not mean

Written 2026-08-17, after v1, v2 and v3, at the point where the fair question
is whether the whole premise is sound.

---

## 1. The Fed paper, and the line that matters

The study covers traders with a **300-millisecond** feed from newswire to
machine-readable sentiment. They are the fastest participants in the market
and they do have an edge:

- HFT share of trading rises 1.8pp in the 5 seconds after an article
- they trade *aggressively and directionally* on it, not defensively
- only **25% of the information is priced in the first 5 seconds**; the rest
  over the following two minutes
- the advantage was **not competed away** across 2009–2012

And then:

> the advantage **does not generate risk-adjusted excess returns once
> liquidity costs are considered**

Read that against everything in this project. The participants with a
300ms information advantage, custom infrastructure and institutional
execution end up with an edge that liquidity costs consume. That is the same
arithmetic that closed FX at 1–5 minutes here, arriving from the opposite end
of the technology spectrum.

It also kills the news idea in its cheap form. The window is ~2 minutes and
the front of it is taken by people 300ms from the wire. A retail RSS feed is
not late by a margin that better sentiment analysis closes.

## 2. What we have actually tested — narrower than it feels

Across silver15, pineport and fastbot: **fifteen hypotheses, one venue family,
one cost regime.**

| dimension | covered | not covered |
|---|---|---|
| instruments | ~30 FX/metal/index CFDs, gold, NAS100/SPX500/US30 | single stocks, options, futures, crypto spot |
| venue | OANDA retail CFD; Dukascopy data | any exchange with real order-book depth |
| horizon | 15m–8 days heavily; 3–12m once | intraday <5m; multi-month with proper construction |
| signal type | **directional prediction** | **risk premia** |
| data | price, spread, COT, FRED rates, crypto funding | options surface, futures term structure, event calendars, fundamentals |

The last row of that table is the whole point of this document.

**Fourteen of the fifteen were attempts to predict direction.** The one that
was not — silver15's crypto cash-and-carry — came back **real**. It was
rejected on *size* (+1.46% against T-bills at 3.66%), not on existence. That
is a different kind of result and it went by almost unremarked.

## 3. So is the premise a lie?

No. But the sentence needs splitting, because two very different activities
share the word "trading".

**Prediction is zero-sum before costs and negative-sum after.** Every pound
you make predicting direction is one someone else lost, minus the spread you
both paid. There is no economic reason for a candlestick pattern to pay you.
Nobody is on the other side *needing* to hand you money for identifying a
doji. The evidence in this project is unusually clean on this, and it agrees
with the published record.

**Risk premia are positive-sum, and they are why the industry exists.** You
get paid because you take something someone else genuinely wants to be rid
of:

| premium | you bear | roughly pays |
|---|---|---|
| equity | the business cycle, drawdowns | ~0.4–0.5 Sharpe, a century of record |
| variance | selling insurance against crashes | positive, with a fat left tail |
| carry | funding/liquidity risk | positive, periodic violent unwinds |
| trend | the discomfort of buying strength | weaker, ~0.3 Sharpe diversified |

`DESIGN_BRIEF.md` reached this independently after eleven failures:

> **Accepting market risk.** Equity beta has paid ~0.4–0.5 Sharpe for a
> century with an undisputed mechanism. Eleven strategies failed to beat it.

**And the industry's revenue is not mostly trading profit.** Brokers earn the
spread on volume regardless of direction. Exchanges earn fees. Asset managers
earn on assets. Market makers earn the bid-ask with infrastructure that costs
millions. Educators earn course fees. Of that list, only the market makers
make money from short-horizon price movement, and their edge is the spread —
the thing that has been *charged against us* in every test here.

**So the retail-facing part of the industry sells prediction, and prediction
is precisely the part with the worst evidence.** That is not a conspiracy; it
is what sells. Risk premia are boring, slow, and occasionally terrifying, and
nobody buys a course about them.

### Our numbers predict the industry statistic

The commonly cited figures — 70–80% of retail CFD accounts losing, and a
Brazilian futures study finding 97% of persistent day traders unprofitable
with **no learning effect** — are usually presented as a mystery about
discipline or psychology.

They are not mysterious. If price geometry carries no directional edge at
these horizons, and you pay ~1.7bp per round trip, you lose at approximately
the rate the spread implies. **Our measurements produce that statistic.** The
convergence is evidence the measurements are right, not that the market is
rigged.

## 4. What this project has NOT shown

Being precise, because over-claiming here would be the same error in the other
direction:

- **Not** that markets are efficient. They are not; v1 measured a real
  continuation effect (8.8% of dispersion). It was too small and too rare to
  trade *at retail cost*, which is a different statement.
- **Not** that no short-horizon edge exists. HFTs demonstrably have one. It
  requires infrastructure we do not have.
- **Not** that these instruments are special. One venue, one cost regime.
- **Not** that discretionary skill is absent. silver15 left that open
  explicitly: *"0.45 vol units per trade is implausible for a written-down
  rule but not for a trader selecting a few setups a day. That is outside
  what backtesting can validate."*

## 5. The genuinely unexplored space, ranked by honest prior

Everything below is untouched by all fifteen tests.

**1. Variance risk premium.** Implied volatility exceeds subsequent realised
volatility most of the time, because people pay for crash insurance. It is
among the most robustly documented effects in finance, it is a *premium* not
a prediction, and it is accessible to retail through listed options. The risk
is honest and severe: you are short a fat left tail and position sizing is
the entire game. **Highest prior of anything remaining.**

**2. Futures term structure / roll yield.** `DESIGN_BRIEF` named this as a
candidate — *"carry, one of the few effects with a published out-of-sample
record"* — and it was never tested. Needs futures data rather than CFDs.

**3. Crypto, directly.** You hold a Kraken account that this project has
barely used. silver15 measured perpetual funding and found it real but below
cash. Crypto has real order books, 24/7 sessions, higher volatility, and
documented basis and funding structures. The cost/vol arithmetic that closed
FX may invert there — silver15 already found the crypto cost structure
behaves differently (fees amortise over the hold rather than scaling with
trade count).

**4. Volatility targeting as the strategy, not the overlay.**
`DESIGN_BRIEF` found this was the *one* thing that worked — every one of six
settings beat buy-and-hold on Sharpe, with a plateau rather than a spike. It
was noted and never built on. It is not a trading bot; it is a risk system.

**5. Event-driven with known timestamps.** Economic releases and earnings
have publication times known in advance. That removes the latency problem in
§1 — you can be positioned *before* rather than racing after.

**6. Cross-sectional equity factors.** The classic value/quality/momentum
space on a broad universe. Well documented, heavily arbitraged, needs breadth
rather than speed.

## 6. The honest recommendation

The original goal was a bot on a short interval that profits after costs. On
the evidence assembled, **that specific goal has a poor prior** — not because
the market is a lie, but because short-horizon directional prediction is the
one part of the space where retail cost structure and information position are
both at their worst, and where fifteen tests have now found nothing.

The same apparatus points at a different question with a much better prior:
**what can you get paid to bear, rather than to predict?**

That is a different project. Slower, less exciting, and with an actual
mechanism behind it. The tooling — cost budgets, pre-registration, matched
benchmarks, controls that must fail — transfers to it entirely, and it is the
part of this work that has real value.

If the short-interval goal stays, the honest framing is that it is a research
bet against a strong prior, and the next candidate should be from a family
that has not already been closed: not price geometry, not dealer quotes, not
exit structures.
