# PREREGISTRATION v6 — volatility targeting on equity beta

```
WRITTEN:  2026-08-19, BEFORE any targeted series has been computed
STATUS:   FROZEN. One run. The parameter grid below is the whole grid.
WHY NOW:  REGIME.md ranked this first of what remains. DESIGN_BRIEF found
          it was the ONE thing that worked and never built on it.
DIFFERENT: this is not a premium hunt. It is a risk system applied to the
          only asset that has beaten equity beta -- equity beta.
```

---

## 1. Hypothesis and mechanism

**H1.** Scaling exposure inversely to recent realised volatility improves
risk-adjusted return on a long equity position.

**The mechanism is about the second moment, not the first.** Twenty-two
investigations have failed to predict returns. This does not try to.
It rests on two properties that are among the most robust in finance and
neither of which is a return forecast:

1. **Volatility clusters.** High volatility today predicts high volatility
   tomorrow. Variance is far more forecastable than direction.
2. **The leverage effect.** Volatility and returns are negatively
   correlated — high-volatility periods deliver worse returns on average.

If both hold, scaling down when volatility rises reduces exposure into the
periods that pay least and hurt most.

**What it is not.** Vol targeting is not a free lunch and the honest
literature is split. Moreira and Muir report Sharpe gains; Cederburg and
others show they are fragile out of sample and depend heavily on the
leverage assumption. **It levers up in calm periods**, so a fast crash out
of a quiet regime hits a larger position than buy-and-hold would have held
— February 2018 being the case in point.

## 2. Why era-consistency IS the right test here

`REGIME.md` argued, correctly, that demanding a positive sign in every era
is too strict for a **risk premium**, because a premium has a duty cycle:
it pays for bearing something and there are decades when nobody needs that
borne.

**That argument does not apply to this.** Volatility clustering is a
mechanical statistical property of price series, not a payment for bearing
a risk. It has no economic reason to switch off for a decade. If the
improvement appears in one era and not another, that is evidence of
fitting, not of a duty cycle.

So Gate B here is strict, deliberately, and on a stated basis.

## 3. My prediction, recorded so it can be scored

**I predict Gate A passes gross and fails net.**

Specifically: Sharpe improves by roughly 0.05–0.15 in most settings and
maximum drawdown improves meaningfully — but the gain is **concentrated in
2008 and 2020** rather than spread evenly, and it shrinks close to zero
once turnover and the venue's financing on the levered portion are charged.

**I further predict the leverage cap binds.** The improvement will require
going above 1× in calm periods; capped at 1×, the strategy will deliver
lower return with only marginally better Sharpe, because it can then only
ever reduce exposure.

`RESULT_FXCARRY` was the first time the mechanism was predicted right and
not just the verdict. This names the mechanism again so the same test
applies.

## 4. Phase 0 — what equity beta costs at this venue

This project has benchmarked twenty-two investigations against "equity beta
at 0.4–0.5 Sharpe", and has never once asked what holding it **through the
accounts actually available** costs.

An OANDA index CFD is not an index fund. It charges daily financing. The
same identity that decomposed FX financing applies:

```
D = (longRate - shortRate) / 2      m = -(longRate + shortRate) / 2
```

The manifest from `fx_carry_probe` already contains all 123 instruments,
including the 55 non-FX rows the carry gate excluded. **Nothing new needs
fetching.**

**Gate 0.** Report, for SPX500_USD, US30_USD and NAS100_USD, the annual
financing cost of a long position, against a long-run equity total return
of roughly 9–10%.

- If financing consumes **more than half** the equity premium, that is
  reported as the headline finding and vol targeting is measured on the
  index itself rather than on the CFD, with the venue cost stated
  separately. It does not stop the run — the question of whether vol
  targeting works is worth answering either way — but it stops the result
  being quoted as if it were reachable at this venue.

This gate exists because the benchmark the whole project has used may not
be purchasable at the price assumed.

## 5. The grid, frozen

```
lookback     20, 60, 120 trading days       (3)
target vol   10%, 15% annualised            (2)
leverage cap 2.0x                            fixed
rebalance    daily, with a 10% no-trade band fixed
                                            = 6 settings
```

Six settings, matching the six `DESIGN_BRIEF` used. **The no-trade band is
set at 10% and is not a tunable parameter** — it exists to stop daily
rebalancing generating turnover that no cost model would survive, and it is
declared before any result is seen.

A **cap of 1.0×** is reported for all six as a separate, pre-declared
variant, because it answers the leverage question in §3 directly.

The volatility estimator is the standard deviation of the trailing N daily
log returns, **using data strictly up to t−1**. Any estimator that peeks at
day t is a look-ahead bug and is tested for.

## 6. Gates

**Gate A — breadth, not a best setting.** Net Sharpe must exceed
buy-and-hold in **at least 5 of the 6** settings, after turnover and
financing costs.

This is the heart of it. `DESIGN_BRIEF`'s finding was *a plateau rather
than a spike* — every setting working, which is the signature of a real
effect. **One setting working is a fit and will be reported as one.**

**Gate B — every era.** The Sharpe improvement must hold in every one of
three disjoint eras. See §2 for why this is strict here and was too strict
elsewhere.

**Gate C — drawdown.** Maximum drawdown must not be worse than
buy-and-hold, measured at **daily** resolution on both sides.
`RESULT_VIXDAILY` recorded the cost of comparing a daily drawdown to a
monthly one; both sides here are daily.

**Gate D — the fast crash.** Report the strategy's loss in the specific
episodes where vol targeting is known to fail: 2018-02, 2020-02/03, and
2024-08. If it is levered above 1× entering any of them, say by how much
and what it cost. A method that improves the average by taking a worse tail
has not improved anything.

## 7. Kill conditions

- **Gate A fails** → stop. No widening the grid, no adding a lookback, no
  trying a different estimator. The grid in §5 is the whole grid.
- **The improvement is concentrated in one setting** → report as a fit,
  not a finding, even if Gate A's count passes.
- **The improvement is concentrated in 2008 and 2020** → report as a
  crisis-timing artefact rather than a general property, and say so in the
  headline.
- **No sign flip.** If inverse-vol scaling hurts, direct-vol scaling is not
  then tested.
- **No asset shopping.** SPX500 is the primary. NAS100 and US30 are
  pre-declared secondaries, reported for robustness; neither may rescue an
  SPX failure.

## 8. What this will not see

- **A sample with only two crises.** OANDA's history reaches 2005, so 2008
  and 2020 are in and 1987, 2000 and 1974 are not. With the gain likely
  concentrated in crises, two is a thin basis and the result should be read
  as such.
- **Intraday gaps.** Daily closes. A crash that happens between closes is
  invisible, and that is exactly when a levered position is worst placed.
- **Borrowing costs above 1× beyond OANDA's quoted financing**, and
  whether leverage is available at all at the moment it is most wanted.
- **Dividends.** An index CFD's dividend handling is a venue term, stated
  in Phase 0 rather than assumed.

## 9. Self-test requirements

Every gate shown failing on a planted case:

1. a series with **constant** volatility must show **no** improvement —
   if targeting "improves" a constant-vol series, the harness is wrong
2. a series with **planted volatility clustering** must show improvement
3. a vol estimator that includes day **t** must be caught as look-ahead
4. the no-trade band must demonstrably reduce turnover
5. a plateau and a spike must be distinguished — five settings improving
   must pass Gate A, one setting improving must fail it
6. a strategy improving in two eras and not the third must fail Gate B
7. drawdown must be computed peak-to-trough at daily resolution on both
   sides, and a planted intramonth round trip must be visible

## 10. Scoreboard entering this test

**Twenty-two investigations. Eighteen rejections, one
measured-but-unreachable premium, one headline that dissolved on
decomposition, one real premium whose edge vanished at daily resolution,
one real premium consumed by its own margin requirement.**

The only thing that has beaten equity beta here is equity beta. This asks
whether equity beta can be made to beat itself.
