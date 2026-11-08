# Result v1 — REJECTED at Gate A

```
RUN:        2026-08-17
SPEC:       PREREGISTRATION_v1.md + v1.1 correction, unmodified
WINDOW:     fit, 2014-01-01 -> 2020-12-31
VERDICT:    FAIL. Project stops. Holdout remains sealed.
```

Recorded immediately, before any change to anything.

---

## The result

```
trades          484        (0.27/day, 69/yr over 7.0 years)
mean per trade  -3.60bp
total           -17.4%
NET SHARPE      -1.091     against a pre-registered bar of +0.76
```

| criterion | required | actual | |
|---|---|---|---|
| net Sharpe | ≥ +0.76 | **−1.091** | ✗ |
| trades | ≥ 200 | 484 | ✓ |
| round trips/day | ≤ 4 | 0.27 | ✓ |

**The two gates that passed are what make the failure meaningful.** With 484
trades and the frequency cap never binding, this is not an underpowered run
that happened to land badly. The sample was there and the answer was no.

## This is not a null. It is a rejection.

The standard error of an annualised Sharpe over 7 years is roughly
`1/sqrt(7)` = 0.38. A reading of −1.09 is about **2.9 standard errors below
zero**, and 4.9 below the bar it had to clear.

The hypothesis was that a sharp 5-minute move is partly an inventory shock
that reverts. Fading those moves lost money at 3.6bp a trade, consistently
enough to produce a Sharpe of −1.09 over seven years.

## What the pre-registration said would happen if this were wrong

From `PREREGISTRATION_v1.md` §1, written before the run:

> **Stated in advance — what would make this false.** If the sharp move is
> information rather than inventory, price does not revert and the
> reversed-side null will beat the primary. That is a real possibility, it is
> the single most likely way this fails, and it is measured rather than
> argued.

That is what happened. The falsifier named in advance is the one that fired.

On NAS100 in the US session, a 3-sigma 5-minute bar is **information**, not an
inventory shock. The move continues more often than it reverts. Whatever
liquidity premium exists at this horizon is not available to a retail account
entering at the next bar's open — which is, as §8 warned, the moment least
likely to be favourably fillable.

## Diagnosis — the gross signal is negative

Same 484 trades, nothing re-fitted:

```
GROSS (mid-to-mid)   Sharpe -0.725    mean -2.39bp
NET   (bid/ask)      Sharpe -1.091    mean -3.60bp
cost paid                             1.20bp/trade   drag 0.37 Sharpe
```

**Cost is not the problem.** Of the −3.60bp, 1.20bp is spread and −2.39bp is
the signal itself. This is silver15's central finding arriving again:

> the gross signal in price history is ~zero *before* cost. No filter,
> barrier, horizon or execution improvement can help, because there is
> nothing being eaten.

Here it is not merely zero. It is negative, and it is negative **in every one
of the seven years:**

| 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 |
|---|---|---|---|---|---|---|
| −0.40bp | −4.68 | −4.97 | −1.84 | −1.65 | −3.06 | **−7.54** |

Seven years, seven negatives. By this project's own era-sign-consistency
criterion — the one `DESIGN_BRIEF.md` used to reject fourteen conditions and
twenty-five indicators — **this is a robustly sign-consistent effect pointing
the opposite way to the hypothesis.** The worst year is 2020, the
highest-volatility year in the sample, which is what one expects if larger
shocks carry more information.

The pipeline behaved as designed: 1,579 signals at |z|≥3, **39% blocked by the
spread gate**, 484 surviving overlap, session and the daily cap. §3 predicted
the gate would bite hard in 2014–2017 and rarely after; the per-year trade
counts (32 in 2017 against 97 in 2019) match.

## The sign flip does not clear the bar either

The reversed side reads **net +0.359**, and its gross is the mirror of the
primary's, **+0.725**.

Against a Gate A bar of **0.76**, momentum is **0.47× the bar net**, and still
short of it gross. So the temptation to flip the sign is closed by arithmetic
as well as by the pre-registration: even taking the number at face value —
which §6 forbids — **momentum would not have passed Gate A on the window it
was measured on.** There is no version of this run that produces a strategy.

## One reusable finding, and it is favourable, so treat it carefully

The measured cost drag was **0.37 Sharpe. The budget predicted 0.64.** The
budget was too pessimistic by **1.74×**, and the reason is structural rather
than a bug:

```
observed drag 0.366 at 69 trades/yr  ->  cost/vol at the hold = 0.0441
                                     ->  per-trade sd = 27.2bp over 30 min
unconditional sd (2.86bp/min x sqrt30)  = 15.7bp
                                    ratio 1.74x
```

Entering **after** a 3-sigma bar roughly doubles the per-trade return
dispersion relative to the unconditional estimate, because volatility
clusters. cost/vol is `cost / dispersion`, so a conditional entry of this kind
is about **1.7× cheaper in Sharpe terms** than `REGIME_FINDINGS.md` assumed.

Restated for any future candidate that fires on a volatility spike:

| round trips/day | budget drag | conditional drag | hurdle (12.6y) |
|---|---|---|---|
| 1 | 0.35 | **0.20** | 0.77 |
| 2 | 0.50 | **0.29** | 0.85 |
| 4 | 0.70 | **0.41** | 0.97 |
| 12 | 1.22 | **0.70** | 1.27 |

**Two cautions, because this is the one number that moved in a helpful
direction.** It is measured on 484 trades in one window, so it is an estimate
and not a constant. And it applies *only* to entries conditioned on high
volatility — an unconditional or time-based entry gets no such discount and
the original figures stand.

> Note also that this lands the 4/day hurdle at 0.97, close to v1's original
> 0.94. That is a coincidence of two errors, not a vindication: v1 used the
> wrong formula and was rescued by an unmodelled effect pointing the other
> way. A right answer from a wrong method is still a wrong method, and the
> v1.1 correction stands.

## What this licenses — and what it explicitly does not

**Licensed:** the liquidity-provision hypothesis, at N=24 / k=3 / H=6 on
NAS100 M5 in the US cash session, is rejected on 2014–2020.

**Not licensed, and stated before the diagnostic was run:**

> The mirror image of a failed reversion hypothesis is a momentum one. If
> `--diagnose` shows the reversed side would have made money, **that cannot be
> promoted.** It is a sign flip on a window that has now been spent, which is
> precisely what `FINDINGS.md` forbids — *"Pre-register, then one run. No
> sweeps, no sign flips, no retuning."*

A momentum reading here is one number on one window, discovered *after* a
failure, on data that can no longer test it. It would be a hypothesis, not a
result — and it would need its own pre-registration and its own untouched
data.

As it happens the question is moot: at net +0.359 it is under half the bar it
would have to clear, so there is nothing to be tempted by. That is luck rather
than virtue, and the rule would apply identically if the number had been +1.5.

Also not licensed:

- No retuning of N, k or H. `PREREGISTRATION_v1` §5 already binds: *"If H=6
  fails and H=12 passes, the strategy has failed."*
- No v2 of this hypothesis. The failure is not a near miss to be recovered by
  a better exit.
- Nothing about other instruments, other sessions, or other horizons. This
  tested one thing.

## What survives

**The holdout is intact.** 2021-01-01 → 2026-08-17, 5.6 years of NAS100 M5,
never examined. That was the entire point of stopping at Gate A rather than
"just having a look". `pineport` reached the end of its work with the line
*"out-of-sample evidence exists: ❌ none left — fitted on everything"*. This
project has not spent that yet.

**The budget stands and is reusable.** The instrument selection, the session,
the cost arithmetic and the sample map were established independently of any
signal and none of them is invalidated by this failure. A different hypothesis
inherits all of it and can be tested in an afternoon.

**The apparatus caught its own errors before they reached a result.** Four
real bugs, each found by a control designed to fail: a crossed-quote check
that crashed on duplicate timestamps; a `COARSE-GRID` gate that fired on every
year because it compared against an absolute constant; a `FLAT` gate that
missed 26.5% zero-range bars because a 0.35 floor sat ahead of the relative
test; and a chunked loader that misaligned returns against spread by one bar.
Plus the v1.1 arithmetic correction, which raised the bar 60% before the run
rather than after it.

**One measured fact about the instrument, which is not a strategy.** A
3-sigma 5-minute bar on NAS100 in the US session is followed, on average, by
continuation rather than reversion — sign-consistent across all seven years,
strongest in the highest-volatility year. That is a property of the market,
established here at a cost of one pre-registered test, and it is now a fixed
input to any future candidate at this horizon: **do not build anything that
assumes intraday shocks revert.**

## The honest scoreboard

Across silver15, pineport and fastbot, the count is now **thirteen hypotheses
tested and thirteen rejected.** That is not a run of bad luck. It is what the
`DESIGN_BRIEF` measurement predicted — 0 of 14 price conditions and 0 of 25
indicators sign-consistent across eras at intraday horizons — arriving one
more time, with a number attached, four days after the question was asked.

The process rejecting a thirteenth candidate quickly and cleanly is the
process working. What would be worth worrying about is a pass.
