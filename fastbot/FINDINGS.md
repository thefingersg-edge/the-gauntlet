# What 26 investigations actually taught — and why the Fed idea was dismissed wrongly

```
WRITTEN:  2026-08-29, after RESULT_LIQUIDITY closed the crypto basis line
PURPOSE:  consolidate what has been learned into rules, and test one of
          them against a candidate we rejected early
```

---

## 1. The four rules the evidence supports

Not opinions. Each is what the record shows.

**Rule 1 — Measuring beats backtesting, by a lot.**
Fifteen-odd strategy backtests found nothing. Four attempts to *measure a
premium directly* found four real effects. Same person, same tooling, same
markets. The difference is that a backtest asks "did this rule make money"
— a question with thousands of ways to accidentally answer yes — while a
measurement asks "is this spread positive", which has one.

**Rule 2 — Nothing died of absence. Everything died of access.**

```
VRP                  premium real, the hedge it needed did not exist
VIX term structure   premium real, edge vanished at daily resolution
Kraken inverse       structure exact, zero bid, zero volume
Kraken quarterly     every gate passed, then 4 BTC traded in a month
```

Four for four. **The bottleneck in this project has never been finding an
edge. It has been reaching one.**

**Rule 3 — Risk premia persisted. Anomalies decayed.**
Everything that survived measurement was compensation for bearing
something unpleasant — carry, short volatility, convergence risk. Nothing
that survived was a pattern in prices.

**Rule 4 — More bars is not more evidence.**
The standard error of an annualised Sharpe goes as 1/√**years**, not
1/√bars. The 15m universe on disk is 4,846 bars over 68 days and has the
same statistical power as 68 daily bars. This is why the "short intervals"
premise kept losing: short intervals need the same calendar span as
anything else to prove themselves, while paying far more in spread to get
there.

## 2. Rule 4 has a corollary that changes what is testable

The 2/√years floor applies to a **continuously held** strategy. It does
not apply to an **event study**.

An event study has N events, not N years:

```
FOMC meetings       8 per year     20 years = 160 events
CPI releases       12 per year     20 years = 240
Payrolls           12 per year     20 years = 240
```

**That is a completely different statistical regime.** Seven hundred-odd
scheduled events over two decades is enough to measure an effect, split it
by state, and still have subsamples — on a span where a signal backtest
could not distinguish a Sharpe of 0.8 from zero.

Event studies are the one design in this whole project that escapes the
resolution floor. **They were never tried.**

## 3. The Fed idea was dismissed for the wrong reason

It was written off as "too late" — the assumption being that the effect
had been discovered, published, arbitraged away, and was gone.

**That is not what happened, and the people who documented its
disappearance say so explicitly.**

The pre-FOMC announcement drift (Lucca & Moench, NY Fed): equities earned
**49 basis points in the 24 hours before scheduled FOMC announcements**,
September 1994 to March 2011 — roughly **80% of the annual equity return**
in that window.

Kurov, Wolfe & Gilbert then tracked what happened next:

| period | mean pre-announcement return |
|---|---|
| 1994-09 → 2011-03 (original) | ~0.49% per event |
| 2011-04 → 2015-12 | **0.445%** |
| 2016-01 → 2019-12 | **0.092%** |

**They explicitly reject arbitrage as the cause**, on the grounds that the
drift persisted for four and a half years *after* Lucca & Moench published
it. Publication did not kill it.

What did? **Uncertainty falling.** Average VIX dropped from 17.7 to 14.7
across the break. When VIX is added to the regression, the post-2015
indicator **goes insignificant and VIX becomes significant.**

## 4. Why that matters more than it looks

If the effect were an anomaly, "it decayed after publication" would be the
end of it.

**It is not an anomaly. It is compensation for holding equity risk into a
scheduled uncertainty event, and it scales with how much uncertainty there
is.** That is a risk premium — exactly the category Rule 3 says survives.

So the honest correction to the dismissal is neither "we were too late"
nor "there's still free money":

> **The effect is state-dependent, and we mistook a low state for a dead
> effect.**

Dave's question was *were we too late for any money, or just for the
initial profit?* The answer is neither. We were early enough — we
just measured it in the wrong regime and read the result as terminal.

## 5. This is also the adaptive-signal idea, arriving from the other side

A premium that scales with VIX is not a signal to be periodically
retrained. **It is a signal whose parameter is published in real time, for
free, by someone else.** The environment variable is the input, not
something to be re-fitted to the environment.

That is the thing to test — not "does the pre-FOMC window pay", which is
answered and currently no, but **does the pre-announcement premium track a
published uncertainty measure across event types, and is the relationship
stable enough to condition on.**

## 6. Why most people will not do this

Not because the idea is secret — the papers are public and free.

Because the work is unglamorous and fiddly, which is precisely what this
project has already learned gets paid:

- **Exact release timestamps.** FOMC statements move between 14:00 and
  14:15 ET across the sample, press conferences were added in 2011, and
  most retail event calendars have the dates without correct times.
- **Press-conference meetings behave differently** from non-press-conference
  ones — Kurov et al. found the split matters and it is invisible in any
  dataset that just says "FOMC day".
- **Surprise needs consensus data**, which is not free and not tidy.
- **The conditioning variable must be lagged correctly.** VIX at the close
  before the window opens, never VIX during it. One line of lookahead
  turns this from a test into a fantasy.
- **The whole thing spans 1994-2026** and crosses several regime changes,
  which is the point and also why the plumbing is annoying.

Anyone can read the paper. Assembling the event table correctly is a week
of tedium, and that is the moat.

## 7. What I am not claiming

**I am not a financial adviser and none of this is a recommendation.**

Three specific cautions, all earned by this project's own record:

1. **Costs will probably be the killer, again.** Four for four so far. A
   0.09%-per-event premium is 13 bp/year over 8 events after nothing at
   all goes wrong. That does not survive much friction, and a
   VIX-conditional version trades less often, not more.
2. **The 0.445% figure is the high-uncertainty regime, not the base case.**
   Conditioning on VIX means holding through the periods when holding is
   unpleasant, which is why the premium exists.
3. **One published relationship is not a strategy.** Whether it generalises
   across event types is exactly what has not been tested, and it may not.

## 8. What I would do next, in order

1. **Build the event table.** FOMC, CPI, payrolls, 1994-2026, with correct
   release timestamps and the press-conference flag. Nothing clever, just
   right. This is the moat and it is reusable for every event study after.
2. **Measure, do not backtest** (Rule 1). For each event type and window,
   the mean excess return and its standard error — no positions, no
   rules, no P&L curve.
3. **Condition on published uncertainty** with the conditioning variable
   strictly lagged, and check whether the Kurov relationship holds out of
   their sample, on other event types.
4. **Only then** ask what it costs to trade, using the access-first screen
   that four failures say should have come earlier.

Steps 1-3 need no capital and no venue. Step 4 is where every previous
candidate has died, and knowing that in advance is worth more than another
clever signal.

## 9. On whether the ecosystem is crackable

It is not a scam and money is genuinely made in it — but mostly by people
being paid for something other than prediction: for providing liquidity,
for bearing risk others will not, for infrastructure, or for access.

**Every one of the four real effects this project found was a payment for
discomfort, not a pattern in a chart.** That is a narrower answer than
"find a signal that works", and it is a more useful one, because it says
where to look: not for cleverness in the same data everyone has, but for
something unpleasant that you are able to hold and others are not.

The pre-announcement premium is exactly that shape. Whether it survives
costs is the only remaining question, and it is the one this project has
learned to ask first.

---

**Sources:** Lucca & Moench, *The Pre-FOMC Announcement Drift*, FRBNY
Staff Report 512 · Kurov, Wolfe & Gilbert, *The Disappearing Pre-FOMC
Announcement Drift*, Finance Research Letters 40 (2021)


---

## 10. Addendum, 2026-09-26 — v26 to v40

The four rules above still stand. The record since this document was written is:

- **v26–v32 (release fade): the fade is a fixed-size, release-specific bounce with no known driver.** Twelve candidate mechanisms were tested and none survived: overshoot, participation, content, sentiment, public predictors, surprise size and others. It is recording forward under v25 and v32.
- **v33–v36:** VWAP/POC, Rule of 16, shocks and first-30-minute momentum all fail. Noise-band momentum (v36) has the only gross edge (+3.4 bp/day). It fails net, and FORWARD_v36 now records it on NAS100.
- **v37–v40 (Dave's event timeline):** 125 time-stamped events and states. Direction information is faint (AUC about 0.55 on SPX) but real. **v40 confirmed it on five unseen markets** (AUC 0.512, 5/5, pre-registered PASS). It is too weak to pay spreads outside US indices.

Rule 1 (*measuring beats backtesting*) held up again. The timeline's strongest output was volatility, the thing that forecasts. Rule 3's corollary gained a new form: **no single signal predicts direction, but many weak ones pooled can, a little.** Every result has its own RESULT_*.md, and REGISTRY.md links each to its pre-registration.
