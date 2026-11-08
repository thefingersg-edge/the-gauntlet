# PROGRAMME — what the projects found, read together

Written 2026-09-21. Each project keeps its own conclusion; this is the view
across them. It exists because reading one project alone produced a wrong
programme summary twice in two days — once by missing `fastbot/` entirely, and
once by carrying a mis-stated verdict forward without reopening its source.

    pineport/  fastbot/  silver15/  journal/  flows/   79 pre-registrations, 79 results (REGISTRY.md, 2026-09-26)
    Full list, generated: REGISTRY.md             Index for agents: CLAUDE.md

---

## The finding, in one paragraph

Read together, the projects say one thing from three directions. **Predicting
direction failed everywhere it was tried** — twelve pineport families, fastbot's
strategy backtests, silver15's mean-reversion family — and three projects
independently derived that the edge needed to *prove* a directional effect sits
above the effects that exist. **Volatility, by contrast, forecasts**: implied vol
sizes positions to a target far better than trailing realised vol, replicated
out of sample, and candle shapes carry several times more information about
magnitude than about direction. **Risk premia are real** — the variance premium
at 10 sigma, VIX term-structure carry, crypto basis — **and every one died on
access**: the hedge, the venue or the liquidity was not there.

---

## 1. Direction — closed from every side

| project | what was tried | result |
|---|---|---|
| pineport | trend (A), shapes/reversals (B), cross-market agreement (C), real yields (D), VRP as a signal (E), tick size x speed (I), cross-section (J), COT positioning (K), discovered candle geometry (L), realised skew (M), pattern zoo on H1 (N), Kalman trend (O) | 12 families, none cleared its bar |
| fastbot | v1–v3 strategy backtests; open candle; sweep reversal; release-fade variant C; CPI/NFP pre-release | v2: 40 of 40 tests negative. Sweep loses 0.136 R per trade. Wedges **anti-predictive** |
| silver15 | residual mean-reversion vs gold-implied fair value, every speed | family closed — see section 4 |

The most sophisticated construction tested, a two-state Kalman filter, beat a
200-period moving average by +0.123 Sharpe against a 0.153 noise floor. The
failures are informative rather than random: two died on direction, two on era
instability, one lost to a simpler rule, and wedges on SPX lose money
systematically (t −5.02 on 640 trades).

## 2. Volatility — the one thing that forecasts, in every project

- **pineport F — implied vol as the sizing input. PRIMARY PASSED.** The first
  pineport family to pass its pre-registered primary gates, on all of them.
  Realised-vol dispersion of the sized position, IV vs trailing RV: S&P 0.280 vs
  0.399, gold 0.265 vs 0.355, Brent 0.272 vs 0.359, EURUSD 0.242 vs 0.255. Beats a
  750-day destroyed-timing null by 2–4x. 11 of 12 era cells. The flattest plateau
  the project produced (0.2641–0.2674). **Replicated out of sample** on NAS100
  (VXN) and silver (VXSLV), the rule frozen before that data existed. Its
  *secondary* claim — higher Sharpe — was not established, exactly as its
  pre-registration predicted. It is a risk-control result, not a return result.
- **fastbot CANDLEINFO** — candle shape carries real information on 146,037 SPX
  M15 bars, but **7.5x / 5.7x / 3.6x more about magnitude than direction** at
  k = 1 / 2 / 3. The best directional shape is worth 0.355 bp against a 1.8 bp cost.
- **pineport B — converging trendlines.** The only part of the chart-shape
  family consistent across all eleven markets was a volatility finding:
  wedges mark quiet markets that stay quiet. No directional effect.
- **pineport I1, J1, L1, E** — in four families volatility ordered outcomes more
  strongly than the hypothesis did, and had to be controlled to stop it
  masquerading as one. VIX predicts gold better than gold's own vol index: one
  global risk factor, not instrument-specific premiums.

Volatility is forecastable and useful for *risk*. It has not once produced a
directional edge.

## 3. Premia — real, measured, and every one unreachable

| premium | measured | why it could not be taken |
|---|---|---|
| variance risk premium (fastbot) | IV > subsequent RV in 81% of months, **z = 10.0** | unhedged Sharpe +0.32, skew −6.66; 2020-03 was a **10.9 sd** month that erased 9.7 years of average gain. No reachable hedge |
| VIX term-structure carry (fastbot) | ~0.40 Sharpe | worst drawdown −68.2 vol points; edge vanished at daily resolution |
| crypto quarterly basis (fastbot) | every gate passed | the dated contract lost 93.2% of its volume — 4 BTC traded in a month |
| crypto inverse basis (fastbot) | structure exact | zero bid, zero volume |
| crypto cash-and-carry (silver15) | real | +1.46% against T-bills at 3.66% — too small to be worth holding |
| pre-FOMC drift (fastbot) | published drift **replicated to −0.14 SE** | state-dependent on VIX; dead after 2015. FOMC-only — CPI and NFP pay nothing |

fastbot's summary of this table is the most useful sentence in the programme:
*"The bottleneck in this project has never been finding an edge. It has been
reaching one."* Everything that survived measurement was payment for bearing
something unpleasant; nothing that survived was a pattern in prices.

## 4. Three projects derived the same floor

Each project, working alone, found that its detection threshold sits above the
size of the effects on offer:

- **silver15**: required edge = `C / (2·0.75·√H) + k·√H`, convex in hold, with an
  irreducible floor of **4.73 pp** at 17 H4 bars. Measured edge: **3–4 pp**.
  *"This is not 'it didn't work'; it is 'it cannot be tested', which is stronger
  and final."*
- **pineport**: 21.6 years at N_eff ~5 gives a noise floor of 0.096 Sharpe;
  anything below ~0.3 is undetectable whether or not it exists.
- **fastbot**: Rule 4, *more bars is not more evidence* — the error on a Sharpe
  falls with √years, not √bars. Its live forward test states up front that it
  needs ~23 years to confirm a net effect.

Three derivations, three datasets, one conclusion: at retail cost and retail
sample lengths, small directional effects are not provable even if real.

## 5. The apparatus works — and it catches itself

**It finds real effects when they are there.** VRP at 10 sigma. The Kurov drift
replicated to −0.14 SE. The 2008 trend break reproduced three separate ways
(pineport portfolio −84%; slow daily signals +0.41 → +0.03; Kalman's EMA
component +1.21 → +0.08). IV sizing passed and replicated.

**Its errors ran one way.** pineport's adversarial review found 13 material
defects; not one manufactured a rejection. silver15's engine audit found a
barrier-snapping bug that had *manufactured* its only pass (Sharpe +1.51 became a
rejection). fastbot withdrew two of its own PROCEED verdicts on the crypto basis.
pineport's controls caught a VRP shared term and a pattern-zoo control pool that
had produced nine false passes. silver15 put it best: *"every rejection was
robust to a bug that flattered it; the single pass was entirely that bug."*

---

## 6. Where the projects disagree, or were summarised wrongly

- **VRP — resolved.** pineport's verdict "withdrawn" and fastbot's "exists at 10
  sigma" answer different questions: whether the premium predicts *direction*
  (no, 0 of 5 gates) and whether it *exists* (yes). Both correct. Cite both.
- **pineport family F — corrected 2026-09-21.** pineport's `CONCLUSION.md` listed
  it as "no improvement over constant sizing", describing only the secondary
  claim. Its primary passed and replicated. The error was carried from v1 into
  v2 without reopening the source file.
- **Wedges — same sign, mechanism suggested, not tested.** fastbot traded them
  on SPX daily bars with textbook entries and stops: anti-predictive, t −5.02,
  stopped out 64–79% of the time. pineport measured 2,025 wedges across 11 CFDs
  on forward returns without stops: t −0.55 in the predicted direction
  (computed from `b1_events.csv` for this reconciliation). Both negative.
  pineport's *documented* finding explains the difference in size: wedges fire
  in genuinely quiet markets and are followed by *less* volatility expansion
  than a quiet market normally produces. A breakout trade bets on the expansion
  the pattern says will not come — which is what 64–79% stop-outs look like.
  That connects two findings; it is an inference, not a test.
- **silver15 v2–v7** are not linked to results by `registry.py`. Its FINDINGS.md
  closes the family; whether each pre-registration has a matching result is
  worth one read.

## 7. Connections across projects that had not been made

- **The one validated sizing input is not used by the one live strategy.**
  pineport F shows implied vol targets risk far better than trailing measures;
  the journal gold 4h forward test sizes from an ATR stop. The test is frozen and
  must not be changed mid-run — this is a note for any future version, not a fix.
- **`fastbot/data/events.csv`** (1,997 NFP/CPI/FOMC releases, 1994–2026) is usable
  by any pineport test and was never used by one.
- **Two fetchers pull the same OANDA feed** — pineport's `fetch_oanda.py` (mid) and
  fastbot's `pull_m1.py` (bid and ask) — into different directories at different
  vintages. That is the R4 / `resampled_h4` bug class waiting to recur. fastbot's
  bid/ask M15 is also exactly what a spread measurement needs.

## 8. Live

- `journal/` — gold 4h forward test, RULES v2. Was "~2.2 years to a verdict";
  read that against **net +0.210R after carry, not +0.250R gross**, which needs
  roughly 1.4× the sample — see §12b and `journal/FINDINGS_GOLD_4H_CARRY.md`.
- `fastbot/` — v25 release fade, recording only, first event 2026-10-02.
- `fastbot/` — FORWARD_v36 NAS100 noise-band momentum, recording only, from 2026-09-28.
- `fastbot/` — v41 frozen-forest forward record on SPX500 + NAS100, from
  2026-09-28, recorder runs in the Cowork VM about monthly.

These are the only sources of genuinely new information. Everything else
re-reads the same data.

## 9. What it leaves

1. **Let the forward tests run.** Neither can be hurried and both were honest
   about their horizons before they started.
2. **If anything is ever traded, the record points at a premium with a reachable
   hedge, not a signal.** fastbot: *look for something unpleasant you can hold
   that others cannot, not for cleverness in data everyone has.*
3. **IV-based sizing is the one validated tool** and a candidate for the next
   frozen version of any strategy — as risk control, not as a source of return.
4. **Build cross-sectionally** if a premium is ever harvested across instruments:
   pineport J1 measured N_eff 8.8–9.9 against 4.7–6.0 for time-series on the same
   names.
5. **Do not reopen a closed family with a fourth parameter.**

---

## 10. Update 2026-09-26 — fastbot v33–v40: a weak direction signal, confirmed out of market

Everything here is pre-registered in fastbot (REGISTRY.md links each result to its spec). It amends section 1: **direction is closed for every single signal tried, but not for a combination of them.**

| test | question | verdict |
|---|---|---|
| v33 / v34 | VWAP/POC magnets, Rule-of-16 bands (release mornings; every session) | FAIL / FAIL: no pull to any level |
| v35 | shock follow-through; first-30 → last-30 intraday momentum | FAIL: momentum real 2005–12 (t 3.1), gone since |
| v36 | noise-band momentum (Zarattini et al.); VIX-hot last-30 | FAIL net, but **gross +3.4 bp/day (t 3.2)**, the first gross edge |
| v37 / v37.2 | Dave's event timeline: hindsight trade points + 125 time-stamped events → LightGBM + sequence mining | FAIL (sealed 2020–26 +1.5 bp, t 1.4). Two runs voided first: a magnitude label, and a VX look-ahead bug |
| v37.3 | train on post-COVID only vs all history | FAIL: recent-only loses in 6 of 8 eras. **More history beats newer history** |
| v38 | noise-band on UK100/DE30/EU50/JP225/AU200 | gross +1.3 bp/day (t 1.83, all eras +), net −4.1: costs |
| v39 | six model types on the timeline | random forest wins (AUC 0.555, 14/15 years); price-shape matching = null; deep learning adds nothing |
| **v40** | **the frozen forest, trained on SPX only, on five unseen markets** | **G1 PASS: direction AUC 0.512 (95% lower 0.504), 5/5 markets above 0.5.** Trading FAIL (−2 bp/trade, costs) |

**Read it plainly:**
- **The first pre-registered direction PASS in the programme.** A combination of many individually useless events carries a small, real, transferable direction signal. It is too small to trade except on US indices at 2022–26 spreads, where the SPX dev result (+2 to +2.6 bp/trade, t about 2) is post-hoc and awaits forward data.
- **Exits cannot create it.** Tight take-profits and trailing stops were tested on these trades (v39 checks). Wide exits are best, and trailing stops trade return for smoothness.
- **Volatility again dominates.** The strongest thing any timeline model found was magnitude (AUC 0.75, voided v37), consistent with section 2.
- **What it leaves:** FORWARD_v36 (NAS100) is the vehicle. A forward record of the v39 forest on SPX/NAS100 at today's spreads is the next thing worth pre-registering. See fastbot/TIMELINE_LIVING.md for how the timeline is extended and retested.

---

## 11. Update 2026-09-26 (evening) — flows: three forced-flow effects, all replicated, all decayed

| test | replication (paper era) | recent period | verdict |
|---|---|---|---|
| FLOWS-1 month-end rebalancing | b −0.175, t −3.64 (2005–2023-03); DE30/Bund confirms | 2023-04 → 2026-08: b +0.001; 7 trades −84.6 bp | DEAD (K4) |
| FLOWS-2 pre-refunding Treasuries | +9.8 bp, t 2.14; all gates PASS as registered | 2019-07 → 2026: +0.39 bp net per trade | PASS as registered, but decayed to about 0 |
| FLOWS-3 overnight drift after sell-offs | +5.32 bp, t 3.59 (2005–2020) | 2021 → 2026: −0.01 bp | DEAD |

**The pattern across the whole programme now has six members:** pre-FOMC drift, intraday momentum (v35), the overnight drift, month-end rebalancing, pre-refunding gains, and the release fade's lack of drivers. Each is a published effect that replicates on OANDA data in its paper's era and has **decayed to zero since publication or since about 2019–21**. The only effects still alive are **premia paid for bearing risk** (VRP, VIX carry, section 3) and one weak, unpublished-style combination (fastbot v40). That is the strongest single argument for where to go next: see fastbot/REVIEW_NEXT_2026-09-26.md.

Housekeeping: a re-run of flows/pull_all.sh after FLOWS-2 had rebuilt the frozen refunding table and dropped the hand-dated 2015-Q3 row. The committed table (sha 57be5dea…, the one the run used) was restored the same evening. pull_all.sh now refuses to rebuild it unless REBUILD_REFUNDING=1 is set.

**fastbot v42 (2026-09-27), dealer gamma:** with SqueezeMetrics GEX in place of the VIX proxy, last-30-minute momentum appears only on short-gamma days (+7.45 bp against +0.18; difference t 1.98 against a 2.24 bar, positive in all 3 eras). It is a FAIL by a hair, but the textbook mechanism is visible. The noise-band edge is the opposite: it lives on positive-GEX days, so it is not dealer hedging.

## 12. Update 2026-10-10 — SPX500 closed on all three timeframes, and a cost nobody was charging

Two findings, one about the instrument and one about the method. The second is
the more important, because it applies to every strategy in this tree that
holds a position overnight.

### 12a. SPX500 — all three live timeframes failed their holdouts

Pre-registered in `pineport/PREREGISTRATION_SPX500_timeframes.md` (2026-09-27),
scored 2026-10-02, five kill conditions fixed in advance. The 15m arm had
already failed and served as the control.

| arm | stages accepted | conditions fired | note |
|---|---|---|---|
| H4 | 1 of 6 | 1, 4 | positive on *both* holdouts and still fails: 2005–08 Sharpe 0.53 against a 0.8 bar |
| M5 | 2 of 6 | 1, 4, 5 | 2005–08 break-even spread 0.000 — loses money gross |
| H1 | **0 of 6** | 1, 2, 4, 5 | 20 and 6 trades: not a measurement at all |

**Recommendation: stop all three live SPX500 strategies.** Per that
registration's §1 these arms test the *structure*; the live parameter values
were fitted on full history and cannot be validated by anything.

Two corrections came out of it, both mine, both worth recording because they
are failure modes rather than one-off slips:

- **"H4 protects 25× better than the index in a crash" was wrong**, and reached
  a findings document and a recommendation before being checked. Measured
  exposure: 8.6% of bars in 2008, **zero shorts**, 12.2% through the crash
  window with one short trade. The small drawdown was *non-participation*, not
  downside skill. A ratio of two summary statistics is not a measurement of the
  mechanism it appears to describe.
- **A registered prediction was right on the verdict and wrong on the
  mechanism** (carry, below). Writing three independent kill conditions rather
  than the one the reasoning pointed at is what produced the right answer.

### 12b. Spread-only accounting is not adequate for overnight holds

Every backtest in this tree charges the **spread** and nothing else. That is
correct for a strategy that is flat overnight and wrong for one that is not.
Financing was priced for the first time (`pineport/carry_cost.py`, registered
in `PREREGISTRATION_SPX500_H4_CARRY.md`), against DFF with OANDA's published
+2.5% admin fee, shorts credited, /365, accruing per calendar day.

| strategy | carry vs spread charge | effect |
|---|---|---|
| SPX500 H4, 2005–2008 | **6.1×** | decided the verdict |
| SPX500 H4, 2023–2026 | **29.8×** | survived comfortably |
| **gold 4h — LIVE** | **6.6×** *(measured)* | 6.9% of the edge; net +0.233R |

**SPX500 H4 clears the fee and still fails.** Break-even markup is 5.51 points
against OANDA's 2.5 — but the 2005–08 window then earns **+0.39%/yr against a
risk-free 3.78%**. It is *below cash*. Note this is section 3's test applied to
a signal rather than a premium: the crypto cash-and-carry in that section was
already killed as "+1.46% against T-bills at 3.66% — too small to be worth
holding". **The same bar had been applied in one project and nowhere else.**

**The live gold 4h test carries the same unpriced charge**
(`journal/FINDINGS_GOLD_4H_CARRY.md`). `RULES.md` v2 prices the spread at
0.0026R and calls it "genuinely negligible" — correct for a spread — while the
system finances 0.35× equity per trade for a median 6.8 days (max 129, up to
four concurrent positions). Carry was modelled at 0.0404R per trade, 16× the
charge the spec accounts for.

**The gold figure is now MEASURED, and the model was 2.3× too high.** OANDA's
live XAU_USD card: long pays **5.45%**/yr, short **receives 3.07%**/yr —
implying a benchmark of 4.26% and a markup of **1.19%, not the 2.5% published
for index CFDs**. Re-measured over the 201-trade record, carry is
**+0.0172R per trade**: 6.6× the 0.0026R spread, but only **6.9% of the
+0.250R edge**, leaving net **+0.233R**. The verdict needs ~1.07× the sample,
not the 1.4× first claimed. Two errors compounded in the model — the markup,
and crediting shorts at 1.38% instead of 3.07% when 94 of 201 trades are short.
September's observed financing was 7.1% of net P&L against this measurement's
6.9% of edge: independent corroboration.

**The SPX500 verdict is validated on measured rates.** Its card reads
−6.38%/+1.38%, decomposing to benchmark 3.88% + markup 2.50% — *exactly* what
the carry registration assumed. So that result is a measurement, not an
estimate, and it also fires condition 3 at every markup down to zero.

### The rate-card survey — and a commodity problem

Five cards were read (`pineport/FINDINGS_FINANCING_RATES.md`). The markup is a
constant **2.50%** on SPX500, NAS100, UK100 **and Brent**; gold's 1.19% is the
outlier, because OANDA prices metals off the pair's rate differential. The
benchmark follows the **instrument's currency** — UK100 implies 3.73% (GBP),
not 3.88%.

**Brent is not an interest-rate product.** Its implied benchmark is
**−46.10%/yr**, which is the futures curve: steep backwardation, so a long
**earns 43.6%/yr** and a short **pays 48.6%/yr**. That is two orders of
magnitude larger than any effect measured anywhere in this programme.

`BCO_USD` is in the 21-CFD panel, with copper, natural gas, wheat, corn and
sugar. **No verdict is overturned** — all twelve directional families failed,
and an unpriced carry only deepens a failure. The exposure is to the **data**:
a backtest on OANDA commodity price data that ignores financing may not be
measuring a tradeable return at all, and the error has opposite signs for longs
and shorts. Before any commodity result is quoted, establish whether those
price series are rolled front-futures with the roll in the financing line or in
the price. This is standing rule 5 one level out — not what the broker's clock
does, but what the broker's *contract* does.

**Answered for Brent (2026-10-11, `pineport/FINDINGS_BRENT_SERIES.md`):** the
roll is in the **financing, not the price**. `BCO_USD` doesn't jump when the
ICE front month rolls (slope 0.91 ± 0.16 on 34 rolls; a diagnostic, because the
registered procedure's roll calendars were wrong about TradingView's `BRN1!` and
it returned "not identified"), sits about two-thirds of the M1–M2 spread above
the front month, and today's card matches the curve (−35.9% vs −46.1%/yr,
registered check supported). So price-only BCO P&L omits roughly the roll yield:
−8%/yr in 2024, −10% in 2025, −34% in 2026, earned by longs and paid by shorts.
Brent only; the other commodity CFDs are presumed, not measured.

A carry that size is also a premium sitting in plain view, which §3 would
ordinarily want measured. The prior should be that it is a wash by
construction — backwardation compensates for an expected spot decline — and
testing it would need its own pre-registration.

Three process errors are recorded in `journal/FINDINGS_GOLD_4H_CARRY.md` §9
rather than buried, all the same shape — a ratio of real numbers becoming a
confident claim about a mechanism while one unchecked quantity underneath did
the work: the index markup assumed to transfer to a metal; the estimate
asserted **withdrawn** on an unchecked unit; and a supporting check that was
**circular**, inferring equity from RULES' illustrative examples.

**The more consequential finding is not about carry.** Three intervals trading
gold with offsetting positions means **most of September's 13 round trips sit
outside the registered 4h system**, whose own arithmetic expects ~15 trades a
*year*. Per-trade P&L for the frozen system therefore cannot be read off the
account: when a 4h long sits against a 1h short, the account's change is not
that trade's result. The forward test must report the 4h system's own trades
via `rules_met`, not the book.

**The SPX500 result is unaffected**, because SPX500 *is* an index CFD where
benchmark+markup is the published formula, and its verdict rests on being below
cash rather than on the markup. What failed is the assumption that **one asset
class's financing formula transfers to another** — the same class of error as
carrying a percentage stop between instruments instead of an ATR multiple
(`pineport/make_base.py`).

RULES v2 is frozen and is **not** amended either way: carry is a cost of the
vehicle, not a rule of the system.

### 12c. What is and is not exposed

- **Family F is NOT exposed.** Its primary — the claim that passed and
  replicated — is that *implied vol targets realised risk better than trailing
  RV*. That is forecasting accuracy, which financing does not touch, and its
  Sharpe secondary was never established, exactly as pre-registered. **The
  programme's one positive result is untouched by all of this.**
- **The fourteen failed families are not exposed** in any way that matters: an
  uncharged cost only makes a failing strategy fail harder.
- **Still unexamined:** family G (portfolio construction, straddling its gate),
  FLOWS-15, and fastbot's forward records — though event fades held intraday
  should carry little, and futures pay basis and roll rather than CFD
  financing.

This does not overturn anything in sections 1–11. Those conclusions were
overwhelmingly negative, and adding an uncharged cost strengthens them. The
exposure was always to the positives, and it turns out to be narrow.

*Not financial advice. Everything here is measurement, not recommendation.*
