# RSI Boll Squeeze — post-mortem

Everything learned, consolidated. Detail lives in `QUIRKS.md` (what the original
code does), `FINDINGS.md` (results), `TUNING.md` (which parameters matter),
`PREREGISTRATION.md` (the pre-committed tests).

**Data:** 124,450 hourly XAUUSD bars, 2006-01 → 2026-07, Dukascopy, plus 124,236
XAGUSD bars, EURUSD for the gold-in-EUR cross, and DFII10 (10Y TIPS) from FRED.
**Verification:** the Python port matches TradingView on 1,341/1,341 bars of
position state and to 4 decimal places on per-trade P&L.

---

## 1. The bottom line

The strategy does not have a robust edge. Its twenty-year record is best
explained as a combination of a weak genuine timing effect and fitting to gold's
particular history.

| | strategy | gold buy & hold |
|---|---|---|
| CAGR (20.6y) | 5.02% | **10.52%** |
| Sharpe | **0.93** | 0.64 |
| max drawdown | **−12.35%** | −45.25% |
| Calmar | **0.41** | 0.23 |
| time in market | 27–51% | 100% |

Half the return at a quarter of the drawdown. As a **risk-managed exposure** that
is defensible. As a way to **beat gold on return** — the stated goal — twenty
years of evidence says no.

Three findings drive that conclusion:

1. **Ten trades are 92% of the profit.** The other 271 net roughly zero. All ten
   are long, all from 2024 onward.
2. **Out of sample (2006–2022, 17 years) it returned 1.2–1.4% CAGR** against
   gold's 7.71%.
3. **It does not generalise to silver** — 70–76th percentile against random
   entry once volatility-adjusted, against 99.5th on gold.

---

## 2. What the strategy actually is

Stripped of decoration, the seven-condition entry is one condition:

> Buy when price crosses up through a 15-period VWMA Bollinger lower band, while
> a Keltner squeeze is on and momentum is positive. Exit on a ratcheting
> percentage trailing stop.

A mean-reversion entry with a trend-following exit. Leave-one-out on the entry:

| removed | full sample | out-of-sample |
|---|---|---|
| **BB lower crossover** | **−0.190** | **−0.159** |
| squeeze (sqzUp) | −0.039 | −0.015 |
| volatility gate | −0.003 | −0.074 |
| macro 4H filter | +0.048 | +0.051 |
| sma(1) × sma(2) | **0.000** | **0.000** |
| ADX > 23 | **0.000** | **0.000** |
| RSI(1) crossover 29 | **0.000** | **0.000** |

Three of seven components are *exactly* redundant — removing all three leaves the
trade list unchanged to the last trade. The lower-band crossover already implies
the other two triggers.

---

## 3. Bugs found in the original

| # | bug | effect |
|---|---|---|
| 1 | **Keltner built from `high`, not `ta.tr`** | channel sat at −1,997/+4,665 around a price of 1,331, so `sqzOn` was true on **100%** of bars. Repaired: 41%. **The single most valuable fix.** |
| 2 | Long stop read `price_stop_long` on the current bar, freshly reset to 0.0 | collapsed to `close × 0.995`. Short side used `[1]` correctly. |
| 3 | `mult` (BB MultFactor) declared, never used | that input does nothing |
| 4 | RSI(1) crossing 29 ≡ sma(1) × sma(2) | two of three triggers are one condition; `Over Sold` at any value 5–80 gives an identical trade list |
| 5 | Take-profit displaced ±10000 | every exit is a stop exit |
| 6 | Ladder rungs in absolute dollars | +190 was 22× ATR in 2024 but 63× ATR in 2006 — unreachable in early history |
| 7 | Short leg not a mirror of the long leg | see §5 — it cannot fire at all |

Fix 1 alone: Sharpe 0.93 → 1.13, drawdown −12.35% → −10.33%, profit factor
2.19 → 4.18, exposure halved. **Repairing one line of code was worth more than
every optimisation attempted.**

---

## 4. Everything tested

| # | test | method | verdict |
|---|---|---|---|
| 1 | Keltner range repair | ablation, both sample halves | ✅ **real** — improves on 3 independent statistics |
| 2 | Stop loss 2–3% vs 6% | pre-specified sweep, 6 windows | ✅ **real** — plateau, beat 6% in **5/6** |
| 3 | Real-yield filter (DFII10) | pre-registered, 6 windows | ⚠️ **modest** — 5/6, but a tie on the full sample |
| 4 | Take-profit, 1%–10% | counterfactual on 231 real trades | ❌ every level loses |
| 5 | ATR-normalised ladder | walk-forward | ❌ worse in both halves |
| 6 | Parameter search, 7 params | walk-forward, 2 nulls | ❌ 4/6 |
| 7 | Parameter search, 2 params | same | ❌ 2/6 — **combined 6/12 = chance** |
| 8 | Gold-in-EUR confirmation | pre-registered, 6 windows | ❌ 2/6 rejected |
| 9 | **Silver generalisation** | pre-registered, null test | ❌ **70–76th vs gold's 99.5th** |
| 10 | **Mirrored short side** | symmetry, no free parameters | ❌ **33rd percentile vs random shorts** |
| 11 | Sleeve structure (participation) | multi-market | ⚠️ better concentration, no extra return |
| 12 | **Vol-scaled, 7 unseen markets** | pre-registered, null test | ❌ **0 of 7 — decisive** |

Two real improvements, two modest, eight rejected. **Everything that survived
came from reading the code or a pre-registered test. Nothing came from
searching.**

---

## 5. The short side (investigated in detail)

**The original short leg cannot fire.** Over 124,450 bars:

| condition | fires |
|---|---|
| `crossunder(RSI(5), 20)` | 3,413 |
| `crossunder(close, BBupper)` | 2,432 |
| `crossunder(sma2, sma26)` | 4,556 |
| RSI **and** band | **32** |
| all three | **19** |
| all three **and** `sqzDown` | **0** |

The upper Bollinger band is where price is extended *upward*; RSI(5) below 20
means a sharp 5-bar *selloff*. The script demands both at the same instant. At
the 2,432 bars where price crosses down through the upper band, RSI(5) has a
median of 46.8 and is below 20 on 32 of them.

It is also not a mirror of the long leg — different band parameters, RSI length
1 vs 5, sma(1)×sma(2) vs sma(2)×sma(26), a 76-bar linreg vs a 942-bar one, and
no macro/ADX/volatility filters at all.

**Building a true mirror** (same band parameters, same SMA pair, linreg sign
flipped, same three filters with macro inverted — no free parameters) makes it
fire 171 times. It does not help:

| config | trades | L/S | CAGR | Sharpe | max DD | Calmar |
|---|---|---|---|---|---|---|
| long only | 138 | 138/0 | **4.83%** | **1.13** | **−10.33%** | **0.467** |
| original shorts (dead) | 138 | 138/0 | 4.83% | 1.13 | −10.33% | 0.467 |
| **mirrored shorts** | 294 | 160/134 | 1.21% | 0.35 | −12.93% | 0.093 |
| mirrored, shorts only | 124 | 0/124 | −1.23% | −0.40 | −28.45% | −0.043 |

By regime, the shorts do exactly what directional beta predicts:

| period | gold move | trades | PF | net/unit |
|---|---|---|---|---|
| 2006–2011 bull | +203% | 50 | 0.61 | −30.8% |
| 2011–2015 **bear** | −42% | 21 | **1.41** | **+9.7%** |
| 2016–2019 flat | +43% | 16 | 0.76 | −5.6% |
| 2020–2022 choppy | +20% | 14 | **1.56** | **+8.1%** |
| 2023–2026 bull | +121% | 19 | 0.42 | −20.2% |

They make money when gold falls and lose when it rises. That is beta, not skill —
and the decisive test confirms it:

| | vs random **short** entry, matched exposure |
|---|---|
| shorts, full sample | **33.4th percentile** |
| shorts, 2011–15 bear only | 60.4th percentile |
| *longs, full sample* | *99.5th percentile* |

**Conclusion: the short side is not blocked by a fixable bug.** The bug is real
and worth knowing about, but repairing it reveals there was no edge behind it.
Even in the bear market where shorts should excel, they beat only 60% of random
short entries. Over a sample in which gold rose 980%, short exposure is a
structural drag with nothing to offset it.

**Recommendation: delete the short side.** It contributes nothing when broken and
costs you when fixed.

---

## 6. Why it doesn't work

Not because the signal is worthless. The long entry beats random entry at
matched exposure **99.5th percentile** on the full sample and **86.7th**
out-of-sample — it more than doubles random-entry returns in 2006–2022.

The problems are structural:

1. **Under-deployment.** 2.2× random return on 26% exposure still loses to 100%
   exposure. The lever is participation, not selectivity.
2. **Concentration.** Ten trades carry it, so every ratio is a restatement of
   what those ten did, and no amount of cross-validation fixes a sample of ten.
3. **Instrument specificity.** Silver says most of the gold performance was
   gold's history, not a market behaviour.

---

## 7. Building from the findings: the sleeve structure

The strongest structural finding was that `pyramiding = 0` discards 19 of every
24 signals, so participation — not selectivity — is the constraint. `sleeves.py`
runs the verified single-position engine K times, sleeve *k* taking signals that
fired while sleeves 1..*k*−1 were busy. Exactly equivalent to K concurrent
positions, each with its own trailing stop, with no broker rewrite.

**Gold:**

| sleeves | trades | Sharpe | Calmar | max DD | top 10 = % of profit |
|---|---|---|---|---|---|
| 1 | 138 | **1.13** | 0.467 | −10.33% | **93%** |
| **2** | 200 | 1.04 | **0.502** | **−8.39%** | **66%** |
| 3 | 219 | 1.01 | 0.473 | −9.42% | 61% |
| 6 | 243 | 0.85 | 0.343 | −12.35% | 62% |

**K=2 genuinely helps the risk profile** — best Calmar, lowest drawdown, and
concentration falls from 93% to 66%. That last number matters: "ten trades are
92% of the profit" was one of the three central weaknesses, and this is the only
change that moved it.

**But it does not raise return, and the reason is instructive.** Splitting
capital K ways means sleeve 1 now trades 1/K of the account. Average capital
deployed *falls* (27.8% at K=1 to 8.2% at K=6) rather than rising. The structure
diversifies; it does not lever. To actually increase exposure each sleeve would
need full size — and that is leverage, which could be applied to K=1 just as
easily. **Deployment and leverage are separate decisions, and only the second
closes a return gap.**

The per-sleeve diagnostics also confirmed an anticipated failure mode: sleeves
1–3 average +1.16%, +1.05%, +1.47% per trade, sleeves 4–6 average +0.14%,
−2.18%, −2.43%. The extra signals really are worse, which is why K beyond 2–3
degrades everything. Sleeve returns correlate at 0.283, so the diversification
is real rather than the same trade held twice.

**Across markets, tested simultaneously this time:**

| | K=1 Sharpe | K=2 Sharpe | verdict |
|---|---|---|---|
| XAUUSD | 1.13 | 1.04 | works, modest risk gain at K=2 |
| XAGUSD | **−0.19** | **−0.18** | negative at every K |
| EURUSD | **−0.05** | **−0.12** | negative at every K, PF < 1 |

The sleeve structure cannot rescue a signal that is not there. Silver and
EURUSD are negative at every K, consistent with §1's finding that the edge is
gold-specific. Testing all three at once cost one command and settled it
immediately — the lesson from having discovered the silver problem last time.

---

## 7b. The final test: ten markets, decisive

Late in the project an inconsistency in my own method surfaced — silver had been
volatility-scaled before testing, EURUSD had not. Correcting it put EURUSD at
the 89th percentile against random entry **on an instrument with zero drift**,
which appeared to rule out "this is just buy-the-dip in a rising asset".

That looked like the most promising finding of the whole project. It was also
derived post-hoc from data already used many times, so it was pre-registered and
tested on seven markets never previously examined.

| never-tested market | trades | **percentile** | drift |
|---|---|---|---|
| GBPUSD | 135 | 79.3 | −1.19% |
| BRENT | 70 | 79.2 | −1.25% |
| AUDUSD | 119 | 58.7 | −0.20% |
| COPPER | 89 | 46.3 | 3.61% |
| USDJPY | 129 | 37.1 | 1.42% |
| DAX | 81 | 19.8 | 8.93% |
| S&P500 | 71 | 11.2 | 12.73% |

**Zero of seven cleared the 80th percentile.** All had 70+ trades, so none is
inconclusive. Strategy returns correlated at −0.058 across markets, so these
were close to independent tests.

The verdict fixed in advance applies: **the volatility scaling was fitted to
gold and EURUSD.** Two markets clearing out of nine examined is chance.

Two details worth remembering:

**GBPUSD (79.3) and BRENT (79.2) missed by a tenth of a point.** Had the
threshold been 75 the headline would read "2 of 7" and this section would be
about a promising partial result worth pursuing. Setting the bar in advance is
the only thing that prevented that reinterpretation.

**The equity indices are the most damning result in the project.** S&P500 and
DAX have the strongest upward drift of anything tested — 12.7% and 8.9% CAGR —
and the strategy was beaten by *random entry at matched exposure* in both
(11.2th and 19.8th percentile). If the logic were even a crude "buy dips in a
rising market", those are the two places it should have worked.

---

## 7c. Confirmed on the better feed

The multi-market test was re-run on OANDA data — the feed the charts use, with
21.6 years of index and commodity history rather than Dukascopy's 12.8–14.6.

**1 of 7 never-tested markets cleared the 80th percentile** (Brent, 84.9),
against 0 of 7 on Dukascopy. The criterion required 6 of 7. **Rejected on both
feeds.**

The instructive part is the instability:

| market | OANDA | Dukascopy | swing |
|---|---|---|---|
| GOLD *(known)* | 85.2 | 99.4 | −14 |
| COPPER | 51.3 | 86.9 | −36 |
| GBPUSD | 51.5 | 79.3 | −28 |
| BRENT | **84.9** | 79.2 | +6 |
| SILVER *(known)* | 80.7 | 70.7 | +10 |

Individual percentiles move by up to 36 points on a change of vendor. Only the
aggregate verdict is stable — 0 of 7 and 1 of 7, both far from the bar.

**Gold's 99.4th percentile was substantially a feed artefact.** It was the most
encouraging number in the project and the reason the multi-market work was
undertaken at all. On the feed that matches the charts it is 85.2 — still
positive, no longer remarkable.

What survives unchanged on both feeds: **S&P 500 at 11.7 and DAX at 17.3**, over
21.6 years, in the two markets with the strongest upward drift tested. A
long-only dip-buying rule losing to random entry there is not a vendor artefact.

---

## 8. What's reusable

The strategy is a dead end; the toolkit is not.

| file | what it does |
|---|---|
| `pine_ta.py` | Pine-exact `ta.*` — `rma` seeded with SMA, population `stdev`, `dmi` with `fixnan` |
| `broker.py` | TradingView's execution model: next-bar fills, `pyramiding=0`, intrabar stops |
| `verify.py` | bar-by-bar diff against a TradingView chart export; finds the first diverging bar |
| `null_test.py` | **random entry at matched exposure** — separates timing skill from being long a rising market |
| `optimise.py` | walk-forward with a trade-count floor and two nulls |
| `dukascopy.py` | free hourly history back to ~2003, any instrument |
| `fetch_fred.py` | macro series with the publication lag handled |
| `generalisation_test.py` | apply a fitted config to an untouched instrument |
| `sleeves.py` | raise participation without rewriting the broker |

`null_test.py` is the one I would carry to any future project. Comparing a
long-only strategy to buy-and-hold conflates timing skill with market exposure;
this separates them, and it is what revealed both that the gold signal is real
and that the short signal is not.

---

## 9. If you continue

**Working on this strategy:** apply `fix_keltner_range=True`, set the stop to
2.0–2.7%, delete the short side, the ADX filter, the duplicate RSI trigger and
the SMA crossover. That is the best version of it — and it still returns half of
gold's CAGR.

**Starting fresh:** the methodology transfers unchanged. Pre-register the
hypothesis, fix the success criterion before looking, test against random entry
at matched exposure, validate on an untouched instrument. On this project that
process rejected seven ideas out of ten — including several that looked
excellent in-sample.

**The most transferable lesson:** the biggest single gain came from reading the
code closely enough to notice a Keltner channel built from price levels instead
of ranges. No optimiser would have found that, because no optimiser questions
whether the indicator is computing what its name says.
