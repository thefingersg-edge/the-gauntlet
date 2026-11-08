> **NOT PRE-REGISTERED.** Labelled 2026-10-11. This work was run and written up
> without a pre-registration, which standing rule 1 requires. No kill conditions
> were fixed before the results were known, so the numbers below should be read
> as **exploratory measurement, not as tests that passed or failed a bar set in
> advance.** A registration has deliberately *not* been written after the fact:
> backdating one is precisely what rule 1 exists to prevent, and it would make
> this look stronger than it is. It appears as an unlinked result in
> `REGISTRY.md`'s audit, which is the correct status — see
> `ACCEPTED_UNLINKED.md` in the tree root.

# What this project measured

Gold and NAS100, a Pine v6 strategy with a verified Python port, tested across
five timeframes, three training-history depths, two instruments, and both a
fixed-window and a rolling-retrain protocol.

Every number below is out of sample unless labelled otherwise. Where a result
is fragile I have said so rather than rounding it into a conclusion.

---

## 1. The short version

Nothing tested produced a strategy worth trading.

That is not the same as nothing being learned. The constraints in section 3 are
measured, reproducible, and would have saved most of the work had they been
known at the start. They are the asset here.

The single most useful result: **re-fitting the strategy monthly on trailing
history is statistically indistinguishable from drawing its parameters at
random** (NAS100: +0.07%/mo, t = 0.05, won 50.4% of months, n = 139). The
search is not finding an edge. It is finding noise that happens to fit.

---

## 2. Scoreboard

| what was tested | result |
|---|---|
| 4H gold, fixed window | PF 2.18 in-sample → **0.93 / 1.60** on two unseen windows |
| 4H gold, trained through 2026 | 188% of its 228% total came from 2024-26 alone |
| 15m gold | port/TV agreement 98.2%, but same generalisation failure |
| M5 gold | break-even spread 0.345 vs 0.25 paid — 1.4× margin, thin |
| M1 gold | break-even **0.20 vs 0.25 paid** — below water |
| NAS100 D/H4/H1/M15 | all four: in-sample Sharpe 1.02–1.71 → **0 of 4** clear the bar OOS |
| NAS100 H4 specifically | 1990% net, Sharpe 1.71 in-sample; 0.12 Sharpe on 2012-14 |
| Rolling retrain, 3y/5y/10y × 2 instruments | **0 of 6** beat both frozen and random |
| Buy-and-hold comparison | B&H ahead in **6 of 6**, at every financing rate |
| ~15 indicator / filter / combination ideas | 2 survived; both were bug fixes |
| Volatility targeting | the only thing that never failed — see §3.6 |

---

## 3. The measured constraints

These are the durable findings. Each is a number, not an opinion.

### 3.1 Edge per trade scales with holding period, not bar size

| timeframe | median hold | edge/trade | break-even spread |
|---|---|---|---|
| 15m | 7.1 days | 0.8585% | 5.601 |
| 4H | 2.7 days | 0.2939% | 2.302 |
| M5 | 0.3 days | 0.0515% | 0.345 |
| M1 | **38 minutes** | — | **0.20** |

Sorted by holding period this is monotonic; sorted by bar size it is not (15m
earns more per trade than 4H). The spread is paid per round trip and does not
care how long you hold, so shorter holds mean less edge against a fixed cost.

**Consequence:** any timeframe whose optimiser lands on sub-day holds will fail
on costs. M1 did — its optimiser drove holds to 38 minutes and landed below
break-even. This was predicted before the run and confirmed by it.

### 3.2 Optimisation is dominated by noise

Six search methods on identical data and budget (3 seeds, reversed order,
shuffled order, joint non-grouped search):

```
OOS spread from the SEED ALONE (same algorithm) : sd 0.541  [1.18 to 2.25]
OOS spread across ALL SIX METHODS               : sd 0.377
  ratio 1.44x
```

Re-rolling the random seed moves out-of-sample performance **more than
switching algorithm does**. In-sample PF barely moves with the seed (1.42–1.60,
1.13×) while out-of-sample nearly doubles (1.18–2.25, 1.91×).

The best in-sample variant ranked 5th of 6 out of sample. The variant that
*lost money* in-sample (PF 0.96) ranked 3rd.

**Consequence:** a better optimiser would not have helped. Correlation between
in-sample and out-of-sample quality was −0.18 with a 95% CI of (−0.86, +0.74) —
no detectable relationship, and no basis for claiming a negative one either.

### 3.3 The edge, if any, is non-stationary

Six walk-forward folds, each re-optimised independently:

| param | f1 | f2 | f3 | f4 | f5 | f6 | spread |
|---|---|---|---|---|---|---|---|
| bullish_sma | 16 | 30 | 41 | 47 | 60 | 12 | 5.0× |
| atr_long | 6 | 6 | 4 | 14 | 3 | 3 | 4.7× |
| vol_long | 46 | 108 | 72 | 72 | 89 | 25 | 4.3× |

The optimiser beat random parameters in 5 of 6 folds — so there *is* structure —
but what it selects changes completely each time. There is no stable optimum,
which is why no single backtest range is "best".

### 3.4 Regimes bound the evidence, not bars

Gold has had roughly five or six distinct regimes since 2006. However many bars
you add, that is the number of independent observations of "does this survive a
regime change". This is why:

- more data does not fix the generalisation problem
- a single train/test split is fragile — you are drawing from n≈5
- the 2013–2023 window flattered the strategy because gold went nowhere
  (B&H 1.91%/yr), and 2024–26 flattered it differently (everything worked)

### 3.5 Costs by timeframe, measured not assumed

Gold spread 0.25 pts (1.87 bps). NAS100 measured from OANDA bid/ask: **2.0 pts
(1.12 bps)** — proportionally *cheaper* than gold.

Break-even margins: 4H 9.2×, M5 1.38×, M1 0.8× (underwater). Costs are
irrelevant at 4H and fatal at M1.

### 3.6 The one thing that never failed, and its limits

Volatility targeting on plain buy-and-hold gold. Not a signal — position sizing
by trailing realised volatility.

Original claim: "all six settings beat buy-and-hold on Sharpe." **That was
overcounted.** Target level is a scalar on exposure; it multiplies return and
volatility equally and cancels out of Sharpe. Proof: in 2006–09, `10%/20d`,
`15%/20d` and `20%/20d` all return Sharpe **0.823**, identical to three
decimals. There are two settings, not six.

Tested with 3-year holdouts either side:

| window | 20d vs B&H | 60d vs B&H | 60d beats 20d? |
|---|---|---|---|
| 2006–09 unseen | +0.054 | −0.001 | **0/3 — reversed** |
| 2009–23 reference | +0.001 | +0.083 | 3/3 |
| 2023–26 unseen | +0.562 | +0.581 | 3/3 (gap 0.019 — noise) |

**The plateau claim fails.** The 60d>20d ordering holds only where it was
found. What survives is drawdown reduction: at the 10% target, 60d cut max
drawdown in all three regimes (−30.0→−12.2, −44.9→−34.2, −28.1→−11.6).

It costs return every time. It is a risk tool, not a return tool.

---

## 4. The benchmark question

Buy-and-hold beat every configuration tested, 6 of 6, at every financing rate.
But that comparison needed two corrections, and a third caveat is structural.

**Exposure.** The strategy is in the market 87.4% of the time on gold, 56.4% on
NAS100; buy-and-hold is at 100%. Judging raw returns penalises holding cash.
Corrected by volatility-matching (lever the strategy to the benchmark's risk).

**Carry.** The benchmark was frictionless. Real financing over 2015–2026
averaged **4.59%/yr** (fed funds + 2.5% broker spread), ranging 2.55–7.83%.
Charged to both sides, pro-rata to exposure.

Applied *separately*, gold at 5y/10y beat buy-and-hold on Calmar — the only
positive result in the project. Applied *together* it vanishes: levering 1.25×
finances 1.25× the notional and levers the drawdown too, turning −14.0% into
−36.2%.

| | strategy ann% | DD% | Calmar | B&H ann% | DD% | Calmar |
|---|---|---|---|---|---|---|
| Gold 10y | 4.03 | −36.2 | 0.11 | 6.49 | −27.2 | **0.24** |
| NAS100 10y | 4.44 | −51.6 | 0.09 | 12.26 | −35.2 | **0.35** |

**The structural asymmetry.** Charging buy-and-hold CFD financing is too
generous to the strategy. Nobody holding gold for a decade needs a CFD — an ETF
costs 0.4%. But the strategy *must* use a CFD or futures, because it shorts.

```
gold CFD @ 4.59% financing      6.71%/yr
gold ETF @ 0.40% fee           11.25%/yr
```

The benchmark can avoid a cost the strategy is obliged to pay.

---

## 5. The bug pattern

Three defects in this project caused a reported result to differ from the
measured one. None changed a single trade. All changed what the numbers
appeared to say.

| bug | effect |
|---|---|
| `final = evaluate(cur)` missing slippage | FINAL line was zero-cost against a cost-laden baseline. M1 reported "56.0% net"; the honest figure was 14.4% |
| `emit_pine` ignored `ladder_mode` | printed `markUp = 10000` (disabled) while the scored config had `mark_up_pct = 8.07`. The Pine shown was a different strategy from the one in the results |
| `--rates` loaded but never applied | carry-adjusted table silently ran the fixed sweep; passing real rates changed nothing |

Two more of the same shape: checkpoint keys that omitted the settings
(`search_robustness.py` on `--samples`, `rolling_retrain.py` on
`--train-years`), either of which would have manufactured a "results are
consistent" conclusion from a stale cache.

**The lesson: on a project whose entire value is knowing which results are
real, the reporting layer deserves more scrutiny than the strategy layer.**
Strategy bugs produce obviously wrong numbers. Reporting bugs produce
plausible ones.

Other errors worth recording: a null test using random parameters that produced
*no trades* (comparing against a cash balance and calling it a null); a
train/test boundary leaking one bar per month via inclusive pandas date slicing;
and a `(bar size)^0.29` extrapolation fitted through three non-monotonic points
that produced a confident and meaningless "TRADEABLE" verdict.

---

## 6. What would be worth trying

Ranked by evidence behind them, not by appeal.

1. **The 3–12 month trend horizon.** This project measured trend as
   sign-consistent at 3–12 months and inconsistent at 8 days — then tested
   nothing above a 17-day hold. The one horizon where a signal was actually
   measured has never been traded. Requires Daily bars and
   `--length-scale 25` or higher.

2. **Volatility targeting as an overlay**, accepting it as a risk tool that
   costs return. The drawdown reduction was consistent in sign across three
   regimes, which nothing else here managed.

3. **Anything that does not require shorting**, so the ETF cost structure
   applies instead of CFD financing. That is worth ~4 percentage points a year
   before any signal is involved — larger than any edge measured in this
   project.

Not worth further effort: better optimisers (§3.2), more data (§3.4), faster
timeframes (§3.1), and this entry logic on new instruments (0 of 4 on NAS100).

---

## 7. Method that is worth keeping

Independent of the results, the protocol worked and is reusable:

- holdouts fixed **before** training, on both sides of the window
- nulls attached to every claim — random parameters, frozen parameters, and
  buy-and-hold, not just one
- acceptance criteria written down before the run (`run_window_sweep.sh` and
  `mm15.py` both carry theirs in the docstring)
- checkpoint keys that include the settings, so a cache cannot answer a
  question it was not asked
- costs applied *during* the search, not only in the final table
- scale-free parameters throughout — dollar-denominated constants broke four
  separate times across price regimes

`rolling_retrain.py` is the most honest test in the repo: it simulates what you
would actually do, month by month, with three nulls attached.
