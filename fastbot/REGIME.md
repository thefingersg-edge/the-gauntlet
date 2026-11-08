# Is the last six years different enough? — and where this project's method was too strict

```
WRITTEN:  2026-08-19, after RESULT_FXCARRY
ASKING:   what survived 2020-2026, whether era-consistency is too demanding,
          and whether the costs that killed everything are regime-dependent
```

---

## 1. What survived the last six years — and it is one bet, not four

| investigation | window | result | what you were actually holding |
|---|---|---|---|
| FX carry, 13 JPY/AUD crosses | 2020-2026 | +4.62%/yr | short yen, long high-yielder |
| VIX term structure | 2018-2026 | Sharpe +0.65 | short volatility |
| Variance risk premium | 2018-2026 | Sharpe +0.21 | short volatility |
| Crypto dated basis | 2024 cycles | +6 to +10 pts | long leverage demand |

Four separate investigations, four apparent survivors, **one macro
exposure**: paid to be short volatility and long carry into a rising-rate,
risk-on regime.

A portfolio built from everything that worked since 2020 is not
diversified. It is the same position four times, and it has the property
that all four legs fail together — which is exactly what happened to all
four in 2013–2020 and would happen again in a convergence.

That is also the honest answer to the earlier stacking question. The
combination that "survived the last six years" stacks risk, not returns.

## 2. The legitimate version of the regime argument, and the counterfeit

**Counterfeit:** *the strategy worked recently, therefore the regime
changed.* This selects the window after seeing the result. With 46 pairs
and three eras, something is always positive in the most recent one.

**Legitimate:** *here is a structural change identified by its CAUSE,
independent of any return series; therefore I expect X; let me test X.*

Genuine structural changes since 2020, identifiable without looking at a
single P&L:

- policy rates left the zero bound and central banks **diverged**
- crypto institutionalised — spot ETFs, regulated venues, real depth
- 0DTE options became a distinct instrument class
- retail order flow became a persistent, intermediated feature

Every one of those is real. The question is whether any of them touches
**what actually killed the candidates.**

## 3. Where the method was too strict, and I should own it

**Era sign-consistency is the right test for a prediction signal and too
strict for a risk premium.**

A price pattern that flips sign by era has no mechanism to argue from —
sign instability is fatal because there was never a reason for it to pay.
`DESIGN_BRIEF` was right to reject fourteen price conditions and
twenty-five indicators on exactly that basis.

A **premium with a stated mechanism is different.** It pays for bearing
something, and there are periods when nobody needs that something borne.
FX carry pays when policy rates diverge; through 2013–2020 they did not.
That is a **duty cycle**, not evidence the premium is fake. Demanding a
positive sign in every era asks a premium to pay in periods when its
economic reason for existing is absent.

The criterion is also **window-dependent**, which is the deeper problem.
Equity beta — this project's benchmark — had a negative decade from 2000 to
2009. Cut the eras one way and it passes; cut them across that decade and
the benchmark fails its own test.

**So: yes, partly guilty.** Gate B should have been a diagnostic about duty
cycle, not a pass/fail, for anything with a mechanism behind it.

## 4. And it changes none of the conclusions

| candidate | binding constraint | was era-consistency decisive? |
|---|---|---|
| variance premium | unhedgeable skew; hedge needs paid data | no |
| VIX term structure | capital — 0.63 contracts; daily drawdown | **no — it passed 3 of 3** |
| crypto basis | Gate D collateral buffer, 1.73× | no — Gate A failed on the buffer alone |
| FX carry | Gate A — 0 of 46 reach 0.40 | no — Gate A failed independently |

**In none of the four premia was era-consistency the sole binding
constraint.** Relax Gate B entirely and every verdict stands.

## 5. The reason a new regime does not rescue any of this

The regime changed. **The cost and capital structure did not.**

```
OANDA financing        max(1.05% flat, ~26% of the differential)
Kraken collateral      buffer proportional to the worst rally
VXM contract           $100 per vol point, and the account is what it is
```

Look at the first one closely, because it is the general case. Above about
a 4% differential OANDA's charge is **proportional**. A regime that doubles
the carry available also doubles the broker's take, and the ratio that
decides Gate A does not move. The same is true of Kraken's buffer, which
scales with the drawdown, which scales with the premium.

**The part of the world that changed is not the part that was binding.**

Three of the four rejections were on cost or capital. Those are contractual
terms, not macro conditions. No amount of rate divergence renegotiates
them.

## 6. So should you just trade what is working?

You can, and it is a defensible thing to do, but it must be called by its
right name.

Holding short-yen carry and short-VIX into a divergent-rate regime is a
**macro bet that divergence persists.** It is not an edge, it has no
backtest that means anything, and it should be sized so that a repeat of
2013–2020 — seven years of nothing — is survivable rather than ruinous.

That is an honest position. What it is not is the thing this project set
out to find, and the failure mode is specific: it looks like an edge for as
long as the regime lasts, which is precisely how 2010–2017 sold short
volatility to an industry.

## 7. What is actually left

Ranked by whether the thing that killed everything else applies.

**1. Volatility targeting on equity beta.** `DESIGN_BRIEF` found this was
the *one* thing that worked — all six settings beat buy-and-hold, a plateau
rather than a spike, which is the signature of a real effect rather than a
fitted parameter. It has been deferred twice. It is **regime-adaptive by
construction**: it responds to realised volatility rather than predicting
anything, so it has no duty cycle to fail through. It applies to the only
asset that has beaten equity beta, and it needs no new broker, no new data
and no premium to be reachable.

**2. Capital efficiency as the objective.** Two candidates died on required
capital. Nothing has been designed around minimising it. This is where a
structural change *could* matter — cross-margining is a contractual term
that has actually moved in recent years.

**3. Forward pre-registration.** Fix a rule now, publish it, and measure it
going forward. It is the only evidence that cannot be contaminated by
hindsight. Slow, and the only genuine answer to "does history repeat".

**4. Cross-sectional.** Untested anywhere in silver15, pineport or fastbot.
More observations per calendar year, which is the cheapest way to lower the
resolution floor `AUDIT.md` §4 identified.

## 8. The one-line answer

**Yes, the last six years are genuinely different — and no, it does not
help, because what changed was the size of the premia and what was binding
was the price of reaching them.**
