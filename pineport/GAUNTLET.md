# The gauntlet

Every check below is here because something in this project failed it, and the
measurement that revealed the failure is named. Nothing is included on
principle. Run them in the order given — cheap rejections first.

**The rule that governs all of them:** a criterion agreed after seeing a result
is not a criterion. Write the pre-registration, then run.

---

## 0. Before any data is touched

| # | check | what earned it |
|---|---|---|
| 0.1 | **A stated reason to work that does not reference a backtest.** Written down first. | 57 parameters on one market, produced by screening scripts that backtested well on someone else's data |
| 0.2 | **A sign map, per market, written in advance** — including at least one market whose predicted sign is *opposite*. A signal that works on everything is a common factor, not a mechanism. | the real-yield study: 7/9 signs matched, but USDJPY failed to flip, which is what the map was for |
| 0.3 | **Primary and secondary claims stated separately.** Direction and size are different claims. | the VRP study nearly re-described a direction failure as a sizing success |
| 0.5 | **Edge before diversification.** A market added to raise the effective sample size must ALSO show edge of the same sign. N_eff is necessary, never sufficient — diversification multiplies edge, it does not create it. | same-sign edge in the added markets, checked before the portfolio test | ten uncorrelated markets took N_eff from 3.6 to 6.0 and **halved** the portfolio Sharpe, because the rule has no edge on nine of them. The gate as pre-registered let a doomed test through |
| 0.4 | **A budget of three to five candidates, fixed in advance.** Not fifty. | twelve tested, two survived, both bug fixes |

## 1. Structural checks — no statistics needed

| # | check | threshold | what earned it |
|---|---|---|---|
| 1.1 | **Shared terms.** Does the predictor share a variable with the target, or with the target's denominator? Re-run with it removed. | must survive | `VRP = IV − RV` against `\|move\| ÷ RV` gave +0.24; removing RV from the target gave −0.05 |
| 1.2 | **Built-in null.** Every parameterised rule must collapse to its control at some parameter value. | must exist | the vol-scaled adaptive MA at γ = 0 *is* the fixed rule — which is where it peaked |
| 1.3 | **Scale-invariant parameters.** ATR multiples, percentages, standard deviations — never dollars. | no exceptions | `markUp`, `longVal`, `rangeL`: three separate dollar-denominated bugs, each making the strategy silently untestable outside its fitted price level |
| 1.4 | **Comparisons at matched scale.** Two sizing rules on different scales differ in average exposure, not timing. Normalise causally (expanding window). | required | implied vol sits systematically above realised vol — that *is* the premium |
| 1.6 | **Stale inputs.** A discontinued series forward-filled to the end of the price data is invented data. Cap the fill at a few bars and check every input's last *changing* observation against the end of the bars. | fill ≤ 5 bars; gap reported | VXSLV stopped 2022-02 and was carried to 2026 — **29% of the sample frozen** — which turned a passing market into a failing one. EVZ did the same for 7.5% of EURUSD |
| 1.5 | **No conjunctions you don't need.** Fragility multiplies: three conditions at 84% agreement give 60% joint. | minimise | the short leg needed three simultaneous crossunders and produced zero reproducible trades |

## 2. Robustness of the measurement itself

| # | check | threshold | what earned it |
|---|---|---|---|
| 2.1 | **Sampling-grid robustness.** Re-compute at every possible start of the non-overlapping grid and average. | sign stable in ≥ 80% of starts | at a 252-day horizon ρ swung from −0.51 to +0.53 purely on where the grid began |
| 2.2 | **Bar alignment**, for any timeframe above 1H. Four offsets plus the platform native; the spread is the error bar. | report the spread | shifting the 4H boundary by one hour moved the out-of-sample percentile from 48.0 to 99.7 |
| 2.3 | **Feed robustness.** Two vendors, trade-list overlap. | ≥ 80% | 61.3% on gold — Sharpe 1.14 on one feed, 0.77 on the other, same code, same twenty years |
| 2.4 | **Rare-event caution.** Triggers defined by tail excursions reproduce at ~68% across feeds; slow common states at ~99%. | prefer common states | the wedge detector kept 41% of detections when the pivot window moved by one bar |
| 2.5 | **Lookahead audit.** Delay every position one extra bar. A large drop means the edge lives in the fill bar. | small decay only | standard on every run since |

## 3. Statistical checks

| # | check | threshold | what earned it |
|---|---|---|---|
| 3.1 | **Era sign-consistency.** Same sign in every era, or reject. | 3 of 3 | zero of fourteen price-derived conditions held their sign at an 8-day horizon |
| 3.2 | **Effective sample size.** N_eff = N / (1 + (N−1)·ρ̄) on the *strategy* returns, not the assets. | state it | eleven markets, mean pairwise ρ 0.21 → **N_eff = 3.5**, and the ceiling for this basket is 4.8 however many you add |
| 3.3 | **Trade / observation count.** | ≥ 30 per window, ≥ 10 per fitted parameter | 7 trades a year on gold; 166 trades against 57 parameters |
| 3.4 | **Random-entry null at matched exposure.** | must beat it | gold 99.5th percentile, 0 of 7 other markets |
| 3.5 | **Destroyed-timing null.** Same signal distribution, timing broken by a long lag. Isolates timing from exposure profile. | must beat it | shuffled vol-target leverage landed exactly on the untargeted rule, +0.252 vs +0.267 |
| 3.6 | **Plateau, not spike.** Sweep every parameter; label PLATEAU or SPIKE. | plateau | vol targeting spans +0.343 to +0.382 across twenty settings. Both earlier sweeps came back SPIKE, and neither held |
| 3.7 | **Walk-forward, parameters chosen out of sample only.** | 3.6 applies inside it too | a 7-parameter search went 4/6 windows, then 2/6 on re-run |
| 3.8 | **Multi-market, pre-registered.** | ≥ 6 of 7 unseen instruments | 0 of 7 |

## 4. Economic checks

| # | check | threshold | what earned it |
|---|---|---|---|
| 4.1 | **Costs.** Realistic spread and slippage, plus a higher sensitivity run. | survives both | everything in the adaptive study loses roughly a third of its Sharpe from 1bp to 5bp |
| 4.2 | **Concentration.** | top 10 trades < ~40% of profit | 92% from 10 trades |
| 4.3 | **Exposure.** Edge × exposure is what pays. | report average \|position\| | the gold entry beat random entry 2.2× and still lost, at 27% invested |
| 4.4 | **Beat buy-and-hold, or state the risk case explicitly.** | one or the other, in writing | the best pre-registered rule so far: Sharpe 0.382 against the basket's 0.571 — a drawdown case, not a return case |
| 4.6 | **Name the implementation vehicle before measuring.** Spot and CFD price series embed neither funding nor roll yield. Charge the carry the chosen vehicle actually pays, on the exposure the rule actually runs. | funding + spread modelled | buy-and-hold fell from Sharpe +0.582 to +0.120 once funding was charged, and the vol-targeted rungs — which need leverage to hit their target — fell further, **reversing Part I's ranking** |
| 4.5 | **Never cap winners.** | no take-profits | tested four ways; the average trade gives back 75% of its peak and capping still lost |

## 5. After a rejection

| # | rule |
|---|---|
| 5.1 | A rejected candidate is rejected. Re-running it on new markets or a longer history is **fishing**, unless pre-registered as a replication of a specific stated claim at the same thresholds. |
| 5.2 | Distinguish *untested* from *tested and failed*. The credit-spread candidate came back with truncated data — that is untested, and it is still available. |
| 5.3 | More data of the same kind does not rescue a structural failure. Ask first which category the failure was: negative-and-precise, structural, or genuinely underpowered. Only the third is a data problem. |
| 5.4 | Record the failure with the number attached. The value of this project is the list of tests that reliably say no. |
