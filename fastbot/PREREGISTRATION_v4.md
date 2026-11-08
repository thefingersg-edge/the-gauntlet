# PREREGISTRATION v4 — the dated crypto futures basis on Kraken

```
WRITTEN:  2026-08-18, BEFORE any basis has been measured
STATUS:   FROZEN. One run. No sweeps, no sign flips, no re-specification.
VENUE:    Kraken (spot + Kraken Futures), an account already open
PRIOR:    silver15 measured the PERPETUAL FUNDING leg and rejected it on
          size: +1.46%/yr against T-bills at 3.66%. It never touched the
          DATED futures basis. That is what this tests.
```

---

## 1. Hypothesis, and the mechanism it rests on

**H1.** Dated bitcoin futures trade at a premium to spot because leveraged
long demand persistently exceeds leveraged short supply. Someone must take
the other side, and is paid to do so. A cash-and-carry position — long spot,
short the dated future, held to expiry — collects that premium as the two
converge.

This is the same *class* of thing as the variance premium and the VIX term
structure: **paid to bear something, not paid to predict something.** That
class is positive-sum, which is why this project keeps returning to it after
nineteen price-prediction nulls.

**It is not, however, a free lunch, and the specific thing being borne must
be named before measuring anything:**

1. **Exchange counterparty risk.** Capital sits on a crypto exchange. Loss
   given default is 100%. Mt Gox, QuadrigaCX and FTX are the base rate.
2. **Margin risk on the short leg.** If spot rallies hard, the short future
   loses immediately even though the spot leg gains. Unless the two are
   perfectly cross-margined, that is a real liquidation risk on a position
   that is *economically* delta-neutral.
3. **Basis widening before convergence.** The terminal payoff is locked; the
   path is not.

## 2. The benchmark, stated before the result

This position is delta-neutral. It must **not** be compared to equity beta.
The correct benchmark is the **contemporaneous risk-free rate**, and the
comparison must be period-matched — the 3-month T-bill went from ~0% to ~5%
inside any plausible window, so a single remembered number is not admissible.

**Required excess: 2.0 percentage points over the contemporaneous T-bill,
after all costs, on total capital committed.**

That threshold is a judgement, not a calculation, and I am fixing it now so
it cannot move later. The reasoning: if exchange failure carries even a 1%
annual probability with total loss, one point of excess is needed merely to
break even on it, and a second point is the minimum I am willing to state in
advance as *compensation* rather than *insurance*. Anyone who thinks 1%/yr
is too high should note that three of the largest venues in the asset's
history have failed.

## 3. My prediction, recorded so it can be scored

**I predict this fails Gate A.**

Reasoning: the dated basis and the perpetual funding rate are linked by
arbitrage — they are two prices for the same leveraged-long demand. silver15
already measured funding at **+1.46% against T-bills at 3.66%**, a *negative*
excess. If the two legs are arbitrage-linked, the dated basis should be of
similar magnitude, and 2 points of excess is a long way above where funding
sat.

**I further predict Gate B fails specifically in 2022**, when leveraged long
demand collapsed and the basis compressed or inverted.

I got the direction of the VIX curve result wrong and recorded it. This is
the same commitment made in advance.

## 4. Phase 0 — the data probe, and its veto

Kraken is not reachable from the research sandbox, so the probe runs on the
local machine, like `pull_m1.py`. **No API key is required for public market
data and none should be used.**

The probe establishes, empirically rather than from documentation:

- which dated instruments exist and existed
- whether OHLC history is retrievable for **expired** contracts
- how far back it goes, and at what granularity
- whether a matching spot series covers the same window

**PROCEED only if all of the following hold:**

| condition | threshold |
|---|---|
| retrievable dated-contract history | **≥ 3 years** |
| distinct quarterly cycles observed | **≥ 12** |
| window contains calendar 2022 | **required** |
| matching spot series over the same window | **required** |

**The 2022 requirement is not negotiable.** `RESULT_VRP.md` recorded that
selling variance measured over 2010–2017 gives a Sharpe of +1.34 and over
the full sample +0.32, and that *"the difference is not skill, analysis or
timing. It is which decade you happened to sample."* A crypto basis measured
only across bull years is that same error with a different asset. If 2022 is
not in the window, the measurement is not worth making.

**If Phase 0 fails, this stops and is written up as a cost-of-information
result.** It does **not** fall back to perpetual funding rates. silver15
already did that, and re-running a measurement that has already been made
and rejected, because the one I wanted was unavailable, is choosing the
answer I can get over the question I asked.

## 5. The position, specified exactly

```
long   1 BTC spot, held CONTINUOUSLY
short  the nearest dated BTC future, rolled at expiry into the next
```

Holding spot continuously rather than round-tripping it each quarter is a
cost decision and is frozen here: it pays the spot fee twice in total
instead of eight times a year.

## 6. The measure

For each quarterly cycle with `T` days to expiry:

```
annualised basis   =  (F/S - 1) x 365/T
realised           =  the actual convergence, F_entry -> S_expiry
net                =  realised - costs
excess             =  net - contemporaneous 3-month T-bill
```

The **realised** convergence is what counts, not the quoted basis at entry.
They differ whenever the position cannot be held cleanly to expiry, and that
difference is the finding, not an inconvenience.

## 7. Costs, charged before any result is seen

```
futures roll        2 x 0.05% taker per quarter        = 0.40%/yr
spot entry + exit   2 x 0.26% taker, amortised once
slippage            1 tick per leg, both legs
funding             none (dated, not perpetual)
```

**Fee tiers are NOT assumed.** The lowest published tier is used, because a
research result that depends on volume discounts the account does not have
is not a result. If the answer only works at a better tier, that is a
finding to report, not a parameter to set.

## 8. Gates, fixed now

**Gate A — size.** Net excess over the contemporaneous T-bill, on total
capital committed, **≥ 2.0 percentage points**, full sample.

**Gate B — era sign-consistency.** Net excess **positive in every era**, with
eras defined as three approximately equal thirds of the retrieved window,
declared from the window length before any result is computed. This is the
criterion `DESIGN_BRIEF.md` used to reject fourteen price conditions and
twenty-five indicators, and the one thing the VIX curve passed.

**Gate C — sample.** ≥ 12 quarterly cycles total, ≥ 3 per era.

**Gate D — the collateral buffer.** This is the crypto analogue of the VIX
margin spiral, and it is the gate I expect to do the real damage.

A short dated future loses money immediately when spot rallies, even though
the spot leg gains, and unless the two legs are genuinely cross-margined
that loss must be met with posted collateral or the position is liquidated —
at the worst possible moment, in the one scenario where the strategy is
otherwise fine.

So: compute the **worst observed spot rally within a single cycle** over the
window, size the USD buffer to survive it, and report

```
return on TOTAL capital = (basis - costs) x notional / (notional + buffer)
```

**Gate A is applied to this number, not to the raw basis.** If surviving the
worst observed rally requires a buffer equal to the notional, the headline
basis halves before anything else is charged.

## 9. Kill conditions

- **Gate A fails** → stop. No "but only when the basis exceeds X" — that is
  a filter, a filter is a sweep, and a sweep is how this becomes 2021.
- **Gate B fails** → stop. Including, and especially, if it fails only in
  2022.
- **Gate D requires a buffer that makes the position unsizeable** on a
  stated account → stop, and report it the way `RESULT_VIXCARRY.md` reported
  0.63 contracts.
- **The basis is negative** → stop. The reverse trade (short spot, long
  future) is **not** tested. Shorting spot crypto has entirely different
  borrow costs and availability constraints, and testing the flip after the
  original fails is the sign-flip this project has refused nineteen times.
- **BTC only.** ETH may be reported as a pre-declared secondary. It may
  **not** be used to rescue a BTC failure. Two instruments tested and one
  reported is a two-way sweep.

## 10. What this will not be able to see

- **Exchange failure.** It is priced in the 2-point threshold as a judgement
  and cannot be measured from price data. No amount of clean history tells
  you what the venue does under stress.
- **Withdrawal freezes.** Every failed venue's history looks fine right up
  to the point at which funds stopped moving.
- **Stablecoin risk**, if any leg is denominated in one.
- **Whether quoted depth existed at the quoted price** in the cycles that
  matter most — the same limitation that `RESULT_VIXDAILY.md` recorded for
  the VX roll.
- **Liquidation mechanics in detail.** Gate D uses close-to-close spot moves.
  `RESULT_VIXDAILY.md` established, at some cost, that the worst single day
  in twenty-two years was invisible at monthly resolution; intraday will be
  worse than daily here too, and daily is the best this data will offer.

## 11. Self-test requirements, before the probe runs on real data

Per the standing rule — *a gate that has never been observed to fail has not
been tested* — every gate below must be shown failing on a planted case:

1. a synthetic basis at exactly the threshold must sit on the correct side
   of Gate A, and one just below must **fail**
2. a series positive overall but negative in one era must **fail Gate B**
3. a window that excludes 2022 must be **refused by Phase 0**
4. a spot rally large enough to exhaust the buffer must **fail Gate D**
5. the probe must contain **no measurement function at all** — checked by
   inspecting the module namespace, not by grepping its own source, which
   has produced a self-matching false pass three times in this project
6. the annualisation must be shown wrong-by-construction if `T` is taken
   from the wrong contract — plant a mismatched expiry and assert it is
   caught

## 12. What a pass would mean

If all four gates pass, this is **not** a green light to trade. It is a
green light to price the things this measurement cannot see: exchange risk,
withdrawal risk, and execution depth. `RESULT_VRP.md` produced a
cost-of-information result and `RESULT_VIXCARRY.md` produced a
size-constraint result. A pass here produces a **counterparty-risk** result,
and that is a question about a venue, not about a premium.

## 13. Scoreboard entering this test

**Twenty investigations. Sixteen rejections, one measured-but-unreachable
premium, one headline that dissolved on decomposition, one real premium
whose edge over the index dissolved at daily resolution.**

The only thing that has beaten equity beta in this project so far is equity
beta.
