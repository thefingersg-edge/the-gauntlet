# silver15 — findings

> **ENGINE AUDIT (2026-08-10). All three backtest engines now pass synthetic
> controls. Two real bugs found; both conclusions survive.**
>
> `audit.py` feeds each engine inputs whose correct answer is known in advance
> — driftless walks (must return 0), planted edges (must be recovered),
> reversed signals (must mirror), cost scaling (must be linear).
>
> **Bug 1 — barrier snapping.** On a breach, P&L was recorded as *exactly* the
> barrier level. The breaching bar actually closes past it, so every breach was
> mis-stated. **This cancels for symmetric barriers and does not for asymmetric
> ones**, because the near barrier is hit more often and its error dominates:
>
> | engine | barriers | bias on a driftless walk |
> |---|---|---|
> | v1 prereg | 2.0 / 2.0 | none (symmetric) |
> | v2 pairs | 3.0 / 3.0 | none (symmetric) |
> | hedged | tp 1.0 / sl 1.5 | **−0.057** (near barrier is the TP) |
> | v3 directional | sl 2.9 / tp 8.71 | **+0.278** (near barrier is the SL) |
>
> The v3 bias *manufactured* a pass — Sharpe +1.51, both criteria met. The
> hedged bias ran the other way and *suppressed* results silently. That is the
> dangerous direction, and it was found only because the audit looked for it.
>
> **Bug 2 — in the audit itself.** The first version fed the hedged engine an
> always-long signal and then asked it to recover a mean-reversion edge. It
> reported a FAIL that was my harness's fault. An audit producing spurious
> failures is as useless as one missing real ones; fixed and re-verified.
>
> **Effect on conclusions:** none reverse. v1 and v2 were never affected. The
> hedged numbers shift slightly *up* (15m zero-cost mean −0.0126 → **+0.0602**)
> but the null test is a comparison between variants that shared the bias, so
> **+3.32 sd stands unchanged**. v3's pass becomes a rejection (mean +0.2846 →
> **−0.0791**).
>
> **The asymmetry worth keeping:** every rejection was robust to a bug that
> flattered it; the single pass was entirely that bug.

> **FINAL RESULT (2026-08-10): the signal family is closed, and we can say why
> in one line of algebra.**
>
> For a residual mean-reversion strategy with fixed round-trip cost `C`,
> barriers `B`, and hold `H`, the true edge needed to *prove* profitability is
>
> ```
>     required(H) = C / (2 · 0.75 · √H)   +   k · √H
>                   \___ break-even ___/       \_ detectability _/
> ```
>
> The first term falls with hold (a bigger barrier dilutes a fixed cost); the
> second rises (fewer independent trades). The sum is convex, so there is an
> **irreducible floor** at `2·√(a·k)`:
>
> | hold (H4 bars) | required edge |
> |---|---|
> | 4 | 6.02pp |
> | 8 | 5.07pp |
> | **17 (optimum)** | **4.73pp** |
> | 40 | 5.18pp |
> | 80 | 6.24pp |
>
> **No signal speed gets below 4.7pp.** Measured evidence puts the real edge at
> 3–4pp. The floor sits above the effect, so no configuration of this family —
> fast or slow, metals or indices or FX — can be shown profitable on retail
> data. This is not "it didn't work"; it is "it cannot be tested", which is
> stronger and final.
>
> Going faster makes it worse, not better: from a 30-bar to a 2-bar signal you
> gain 3.7× the sample (saving 1.3pp of detectability) but pay 4.8pp in
> break-even. A bad exchange rate in every direction.
>
> **What would change it**, since `floor = 2√(a·k)`, `a ∝ cost`, `k ∝ 1/√data`:
>
> | to reach | costs | or data |
> |---|---|---|
> | 3.5pp | 45% cheaper | ×3.3 |
> | 3.0pp | 60% cheaper | ×6.2 |
>
> 45% below retail is institutional pricing. ×3.3 data means ~80 mechanism
> pairs or ~60 years of history. Neither is available.

> **PROJECT CONCLUSION (2026-08-10, corrected).**
>
> **Every one of ten metal pairs is unprofitable after measured retail
> spreads.** Pooled across 9 pairs and 20 years: 5,641 non-overlapping trades,
> win rate **47.95%** against a **54.3%** break-even, mean P&L **−0.2035**
> spread-vol units, bootstrap 95% CI **[−0.2579, −0.1478]**. Every pair's
> t-statistic is negative, spanning −7.44 to −1.19.
>
> **CORRECTION to the 2026-08-09 conclusion.** That version claimed the signal
> carried "real directional information of 1.8–4pp" at H4. It was wrong. A
> beta clip inherited from `silver_mr.py` — `clip(0.5, 4.0)`, sized for
> silver/gold's natural beta of 1.43 — bound **84–98%** of the time on every
> cross-metal pair, whose natural betas are 0.11–0.54. Those pairs were never
> hedged; the "residual" was a fixed blend, over-hedged by up to 5×.
>
> With the hedge corrected, the directional diagnostic falls from **+2.69 sd
> to +0.67 sd**. At H4 there is essentially no directional information, and
> what looked like a signal was an artefact of the broken hedge.
>
> **What survives the correction:** the 15-minute silver/gold hedged result
> (+3.32 sd on independent trades). Silver/gold's beta sits inside the old
> bounds — the clip binds 0.3% of the time there — so that finding is
> untouched. Fast reversion at 15 minutes is real; by 1.3 days it is gone.
>
> **What the bug did NOT do:** rescue anything. Correcting it made every
> result worse, not better, and made the rejection cleaner.
>
> Four strategies tested, four correctly rejected.

---



Date: 2026-08-09
Data: OANDA M15 mid, XAG/XAU/EUR, 2016-01 → 2026-08, ~250k bars each,
cross-checked against an independent Dukascopy BID pull.

---

## Summary

The data layer is sound. The primary signal, as currently specified, has
**no detectable edge**. The effect it is trying to capture is real and has the
right sign, but it is roughly **4× too small to pay the spread at 15 minutes**.

No meta-model should be fitted on top of this signal until the specification
changes. A logistic P(win) trained on a signal with no edge can only fit noise,
and purged walk-forward CV will not save it — it will just produce a plausible
number.

---

## 1. The cost model was masking everything

The first full run reported a mean P&L of **−1.91 ATR per trade against a
−1.5 ATR stop**. You cannot lose more than your stop; that number is
structurally impossible and was the thread worth pulling.

Cause: `spread_usd = 0.08` is large relative to 15-minute silver ATR.

| year | 15m ATR ($) | median price | half-spread in ATR |
|------|------------|--------------|--------------------|
| 2016 | 0.0346 | 17.10 | 1.15 |
| 2017 | 0.0248 | 17.02 | 1.61 |
| 2018 | 0.0191 | 16.08 | 2.09 |
| 2019 | 0.0204 | 15.85 | 1.97 |
| 2020 | 0.0593 | 18.38 | 0.67 |
| 2024 | 0.0656 | 29.09 | 0.61 |
| 2026 | 0.3739 | 75.49 | 0.11 |

The take-profit sits at **+1.0 ATR**. Wherever that last column exceeds 1.00,
a trade that *hit its take-profit* was still booked as a loss. That covers
2016–2019 entirely.

This also explains the apparent "improvement" over time — win rate rose from
7.9% (2016) to 50% (2026). Nothing about the strategy improved. The spread is
fixed in dollars while ATR scales with price, and silver went from $17 to $75.
**A monotonic improvement that tracks the price level is a cost artefact, not
a finding.**

Sensitivity:

| spread_usd | win rate | mean pnl_atr |
|-----------|----------|--------------|
| 0.080 (assumed) | 20.28% | −1.9134 |
| 0.040 | 36.68% | −1.0125 |
| **0.019 (measured)** | **48.39%** | **−0.4882** |
| 0.010 | 52.97% | −0.2683 |
| 0.000 | 58.18% | −0.0219 |

0.019 is the measured OANDA round-trip (2 × the 0.0095 mid−bid half-spread
from `oanda_intraday.py --sides`). **Set `spread_usd = 0.019`** — but see below,
because it does not rescue the strategy.

---

## 2. The signal fails a null test

With barriers tp=1.0 / sl=1.5, a driftless random walk wins **60%** of the
time by geometry alone. That, not 50%, is the bar to clear.

At **zero cost**:

| variant | win rate | mean pnl_atr |
|---------|----------|--------------|
| REAL signal | 58.18% | −0.0219 |
| REVERSED signal | 57.25% | −0.0448 |
| RANDOM side (10 seeds) | 57.74% ± 0.65pp | −0.0327 |

The real signal beats a random coin flip by **0.44pp against a 0.65pp standard
deviation** — well inside noise. All three sit *below* the 60% geometric
baseline. Even frictionless, the signal adds nothing.

This is the single most important result in this document. Everything
downstream was built on the assumption that the residual carries direction.
It does not, as specified.

---

## 3. But the effect is real — just too small, and contaminated by drift

Forward return in ATR units, in-session bars, vs `resid_z`:

| horizon | corr(z, fwd) | mean fwd given z ≤ −2 | mean fwd given z ≥ +2 |
|---------|-------------|----------------------|----------------------|
| 4 | −0.0095 | +0.0446 | −0.0127 |
| 12 | −0.0061 | +0.0534 | −0.0301 |
| 24 | −0.0080 | +0.2241 | +0.0420 |
| 48 | −0.0114 | +0.4461 | +0.1741 |
| 96 | −0.0011 | +0.4626 | +0.6475 |
| 384 | +0.0073 | +1.2838 | +1.9850 |

Two things to read here.

**At short horizons the sign is correct.** At h=12 (the current `max_hold`),
cheap silver returns +0.053 ATR and rich silver returns −0.030 ATR. Mean
reversion is present. It is just tiny — you need ~**0.21 ATR** to cover the
measured round-trip, and you are getting ~0.05.

**At longer horizons the drift takes over.** By h=24 the short side has already
flipped positive (+0.042), and by h=96 both sides are strongly positive. That
is not reversion, it is silver's secular uptrend. Lengthening `max_hold` will
therefore not fix this — it replaces a small real signal with a large fake one.

---

## 4. The signals are not independent

`resid_z` autocorrelation: +0.96 (1 bar), +0.87 (4), +0.66 (12), +0.44 (24),
+0.11 (48), −0.44 (96).

`cum_resid` is a 96-bar rolling sum, so it is smooth by construction. When
`|z| ≥ 2` fires it stays fired for many consecutive bars. The 8,236 "trades"
are clusters, not independent draws — **the effective sample size is far
smaller than the trade count**, and the ±0.65pp null spread above is
correspondingly optimistic.

The −0.44 at lag 96 is a rolling-window artefact (the sum drops the same bars
it added), not evidence of a 24-hour reversion cycle. It should not be traded.

---

## 5. The specification has an internal inconsistency

The signal measures a **gold-implied residual** — "silver is cheap *relative to
gold*". The trade taken is **outright silver**. So the position carries the full
common precious-metals factor, which is exactly the drift contaminating
section 3.

This is the most promising thing to fix. Hedging the position with
`beta × gold` would isolate the quantity the signal actually measures. It also
removes the secular drift that currently swamps the residual at every horizon
beyond ~12 bars.

---

## Recommended next steps, in order

1. **Set `spread_usd = 0.019`** (measured, not assumed). Re-check any earlier
   result that was produced under 0.08.
2. **Trade the spread, not the outright.** Hedge with `beta × XAU`. This is a
   structural change to `triple_barrier` — P&L becomes the hedged pair — but it
   aligns the trade with the signal and removes the drift. Test before anything
   else.
3. **Re-run the null test after every change.** Real vs reversed vs random
   side, at zero cost. If the real signal does not clear random by several
   standard deviations frictionlessly, stop and re-specify. This should gate
   the meta-model permanently.
4. **Consider a longer bar.** Cost in ATR units falls as the bar grows. At H1,
   ATR is roughly double the M15 ATR, halving the cost hurdle. The `pineport`
   project already has H1 and H4 OANDA data for the same instruments.
5. **Only then fit the meta-model.** It is a filter on an existing edge, not a
   source of one.

---

## 6. The hedge diagnosis was right — and it is still not enough

Section 5 predicted that hedging with `beta × gold` would isolate the quantity
the signal measures. It does. But two corrections had to be made first.

### 6a. Overlapping trades were inflating every significance number

`resid_z` autocorrelates at +0.96, so `|z| ≥ 2` stays true for many consecutive
bars and the 8,236 "trades" are repeated views of ~2,064 episodes. Enforcing
one trade per `max_hold` window (`--no-overlap`) changes the verdict entirely:

| variant | overlapping | independent |
|---------|------------|-------------|
| unhedged, zero cost | +2.56 sd | **+0.12 sd** |
| hedged, zero cost | +4.04 sd | **+3.32 sd** |

The unhedged signal was never significant. It only looked so because the
sample size was a fiction. **Any result computed on overlapping trades in this
project should be recomputed.**

### 6b. Hedged, on independent trades, the signal is real

At zero cost, 2,064 independent trades:

| barriers | REAL | REVERSED | RANDOM | vs random | mean pnl_sig |
|----------|------|----------|--------|-----------|--------------|
| tp1.0/sl1.5 | 59.11% | 52.08% | 55.97% ±0.95 | **+3.32 sd** | −0.0126 |
| tp1.0/sl1.0 | 53.39% | 46.61% | 50.36% ±1.01 | **+3.02 sd** | **+0.0657** |

The real/reversed separation is clean and consistently signed in every
configuration tested — 59.1/52.1, 53.4/46.6, 60.9/53.1, 54.7/45.3. That is not
noise. **Hedged, the signal carries genuine directional information of roughly
3–4 percentage points over a coin flip.**

With symmetric barriers the break-even is 50% rather than 60%, and zero-cost
expectancy turns **positive** for the first time (+0.0657 spread-vol units).

### 6c. Costs are larger than the entire profit target

| config | zero cost | with measured cost |
|--------|-----------|--------------------|
| 15m, tp1.0/sl1.0 | +0.0657 | **−1.3233** |
| 1h, tp1.0/sl1.0 | +0.0911 | −0.6911 |
| 1h, tp1.0/sl1.5 | +0.0327 | −0.7495 |

Round-trip cost at 15m is ≈ **1.39 spread-vol units against a take-profit of
1.0**. You pay more to open and close than the trade can possibly make.

The hedge causes part of this — you now cross gold's spread too, scaled by
beta — but it is not the main driver. The driver is that the hedged spread's
volatility over a 3-hour horizon is simply smaller than two retail round-trips.

Moving to 1h halves the relative cost, exactly as predicted, and is still
nowhere near enough. Cost falls as `1/√horizon`, so covering a 1.4-unit cost
needs roughly **50× the holding period** — about six days, not three hours.

### 6d. Conclusion

The intraday premise, not the signal, is what fails. A ~3–4pp directional edge
is real but is 20–40× too small to pay two retail spreads at 15 minutes.

**The signal deserves to be retested as a multi-day gold/silver convergence
trade**, where the residual has room to move relative to a fixed cost. That is
a different strategy from the one this project set out to build, and it should
be pre-registered as such rather than reached by tuning until something passes.

Caveat on 1h: only 512 independent trades, so the null-test standard deviation
doubles and it fails on sample size (+1.43 sd) despite a similar effect size.
Longer horizons will always be sample-starved on 10 years of data — which is
itself an argument for pre-registration over search.

---

## What is now trustworthy

- Day-index bug in the Dukascopy fetcher found and fixed (exact price match).
- OANDA and Dukascopy agree: silver return corr 0.9878, gold 0.9961,
  euro 0.9971, with disagreement confined to the 21h UTC rollover — which the
  `sessions = [(7, 16)]` gate already excludes.
- `oanda_intraday.py --audit` verifies feed provenance from file bytes, after
  three separate incidents of a file not being what its name claimed.
- **Pine/Python parity confirmed at the data layer.** A TradingView OANDA
  XAGUSD 15m export (653 bars, 2026-07-29 → 2026-08-07) matches
  `data/xagusd_mid_15m.csv` on open, high, low and close at **100.00% exact**
  (volume 99.85%, one bar off by a single tick). Bar boundaries and timestamps
  are identical — no offset, no drift. TradingView draws **mid**, not bid, so
  `--price M` is correct. Fixture kept at
  `parity/tradingview_xagusd_15m_2026-08.csv`.
- All diagnostics reproduce identically on pandas 3.0.5 / numpy 2.4.6 (Dave's
  stack) and pandas 2.3.3 / numpy 2.2.6.

---

## Small-cap / low-float: closed on cost, without buying data (2026-08-11)

The Kellogg line — change the MARKET rather than the signal, on the reasoning
that eight families failed while holding market, data and edge type constant.
Measured with `smallcap_budget.py`, 40 screener names, Polygon free tier,
Abdi & Ranaldo (2017) effective spreads from daily H/L/C. **No returns
computed.**

The thesis that kept it alive was confirmed: **in-play volatility is 17%
median against the 7.2% published average**, so the stocks are far more
volatile on the days a momentum strategy would engage. But spreads widen
alongside, and the ratio does not improve.

| scenario | cost/vol | required edge/trade |
|---|---|---|
| average day, incl. failures | 0.38 | 0.42 |
| average day, excl. failures | 0.57 | 0.61 |
| **in play, incl. failures** | **0.41** | **0.45** |
| **in play, excl. failures** | **1.12** | **1.16** |

against 0.071 for FX H4 directional and 0.146 for residual mean-reversion.

**The bar term is 0.040 of that.** Unlike every other family in this project,
sample size is irrelevant here — the constraint is cost, not history. That is
why no amount of paid data changes the answer, and why the line was closed
*before* spending anything.

### The estimator failure rate is itself a finding

31% of all-day and **41% of in-play** spread estimates came back clamped to
exactly zero — the covariance went negative and there was no root to take. A
clamped zero is a FAILED estimate, not a measurement of a free-to-trade stock,
and the first version of the script fed them into the median as data. That
reported 0.45 when the honest answer is a range of 0.45–1.16.

Neither treatment is unbiased: including the zeros biases spread down,
excluding them biases it up, because the estimator fails more often when the
true spread is small. A high failure rate on microcaps is expected — they
halt, gap and trade thinly, violating the estimator's assumption of continuous
trading around a random walk.

### What this does and does not establish

It does **not** show that discretionary low-float traders lose money. It shows
that the **systematic, testable version needs 0.45–1.16 volatility units of
edge per trade — 16× to 40× the only edge this project has ever measured**
(hedged 15m silver/gold, +3.32 sd over 13,013 trades = 0.029).

At 17% in-play volatility, 0.45 vol units means every trade must average ~7.6%
gross before costs, and the honest end means ~20%. A discretionary trader
selecting a handful of setups a day might plausibly clear the low end. **A
rule that can be written down, backtested and verified cannot** — an effect
that large would be visible to everyone.

So the honest conclusion is narrower and more useful than "it doesn't work":
if the edge is real, it lives in discretion we cannot backtest from historical
bars, which puts it outside what this project can validate.

### Method note

Both free sources failed and neither was worked around: **Stooq** serves a
JavaScript bot check, **Yahoo** returns HTTP 429. Polygon's free tier (5
calls/min, 2 years, delisted included) resolved 39 of 40 symbols. Bot
protection was treated as a stop signal, not an obstacle.

---

## Crypto perpetual funding: closed below cash (2026-08-11)

The tenth family, and the one with the most concrete mechanism in the project.
A perpetual has no expiry, so the exchange forces convergence to spot by making
levered longs pay shorts. Long spot + short perp is market-neutral **by
construction** — which is precisely the quantity v6's budget was silent on.

Measured with `funding_budget.py` from Kraken's public funding history. **No
price returns computed**; funding is a published cash flow.

| symbol | events | span | every | gross/yr | % positive |
|---|---|---|---|---|---|
| PF_XBTUSD | 8,781 | 1.0y | 1h | +3.58% | 72% |
| PF_ETHUSD | 8,781 | 1.0y | 1h | +3.19% | 69% |
| PF_SOLUSD | 8,782 | 1.0y | 1h | **−0.12%** | 55% |
| PF_XRPUSD | 8,782 | 1.0y | 1h | +0.97% | 54% |

Fees are one-off (four fills: buy spot, sell perp, unwind both) and therefore
amortise over the hold — **the only family here where holding longer reduces
cost per unit time** instead of raising it.

| hold | fee/yr | net/yr | vs 3-month T-bill |
|---|---|---|---|
| 30d | 7.55% | −5.47% | −9.13% |
| 90d | 2.52% | −0.44% | −4.10% |
| 180d | 1.26% | +0.82% | −2.84% |
| **365d** | **0.62%** | **+1.46%** | **−2.20%** |

**Closed on the risk premium, not on the arithmetic.** The trade is genuinely
profitable at a long hold. It just pays less than cash: +1.46% against a
Treasury bill at 3.66%. BTC alone, the strongest leg, nets 2.96% on a one-year
hold and still lands 0.70% below cash. You would accept basis risk, margin
calls on the short leg and exchange counterparty risk to earn a negative
premium. FTX went to zero with customer funds inside it.

Funding historically ran 10–15% annualised in bull markets. It now prints 3.6%
on BTC and **negative** on SOL. Capital arrived and competed it away, which is
what should happen to a well-known, mechanically harvestable premium.

### A wrong number I printed, and why it mattered

v1.0 divided net funding by the volatility of the funding *stream* (0.17%/yr)
and reported a Sharpe of **+8.48** at a one-year hold. The denominator was
wrong by orders of magnitude: funding varying is not the risk in this trade —
funding is a contractual payment. The risk is basis at entry and exit, margin,
and the exchange, none of which are in the funding series.

No denominator computable from that file was the right one, so v1.1 reports
**no Sharpe at all** and benchmarks against cash instead. A large flattering
number invites belief; omitting it is the safer failure.

### A different kind of uncertainty

Kraken publishes ~1 year of history, giving a nominal 2σ bar of 2.00 — but
that framing does not apply here. Funding is contractual, so no statistical
significance is needed to know it was received. The risk is that the regime
does not persist, and one year says almost nothing about that.
