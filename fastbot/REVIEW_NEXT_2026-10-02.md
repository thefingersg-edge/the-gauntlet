# Where next: review after v57/v58 (2026-10-02, written while Dave is away)

I am not a financial adviser. This is a research plan, not a recommendation.

## What ran today
| item | result |
|---|---|
| AUDIT_v54_v56 | **v56 code correct.** No look-ahead (S5FI moves with the S&P on t, corr 0.76, not t+1). **The inference is borderline:** rotation null p 0.048 / 0.057, and the NW t ran about 1/6 too high. **v54:** nothing that could flip its FAIL. |
| v57 breadth beyond VIX | **NOT SHOWN** (t −1.73, rotation p 0.075). VIX did not absorb it. Breadth, VIX and the 50-day fall share one weak post-decline effect, and 26 episodes can't tell which carries it. **Breadth timing is closed.** |
| v58 FX on FOMC days (Mueller–Tahbaz-Salehi–Vedolin 2017) | **FAIL.** In the paper's era (2005–10) +31.7 bp, t 2.71. Since 2011 +4.0 bp, t 0.66. **The seventh published effect to replicate and then decay** (PROGRAMME §11). The FOMC premium family is closed in equities and FX. |

## Method lesson, proposed for GAUNTLET.md (not edited; Dave's checklist)
- For any regression on **overlapping horizons with a persistent regressor**, register a **rotation (circular-shift) null** beside Newey–West.
- In v56 and v57 the NW t's null sd was 1.17–1.19, not 1.0. A gate at |t| ≥ 2 was really about |t| ≥ 1.7.

## Queue, ranked
| rank | item | needs | prior |
|---|---|---|---|
| 1 | **v43: hedged VRP on SPX options** (already pre-registered) | Dave buys ORATS data (v43 §budget: one month of the delayed API, $199) and runs orats_pull.py on the Mac | Highest. A premium measured at z = 10, and the hedge is the missing piece |
| 2 | FLOWS-15: v36 noise-band on ES/NQ futures costs | Databento account ($125 free credit covers the bars) | Medium. Decides whether the one live intraday edge has a cheaper vehicle than CFDs |
| 3 | FOMC-cycle even weeks (Cieslak–Morse–Vissing-Jorgensen, JF 2019), **weeks 2/4/6 only** | nothing new. Week 0 overlaps KUROV and must be excluded | Low: published timing, sample ends 2013. Expect a v58 shape |
| 4 | Overnight/intraday "tug of war" on index trend signals (UNEXPLORED A3) | nothing new | **Not recommended.** The 12-month sign flips only ~10–15 times on four correlated indices, so N_eff is too small to gate |

## The pattern, updated
- Seven published timing effects have now replicated in their paper's era and decayed after it. They are pre-FOMC drift, intraday momentum, the overnight drift, month-end rebalancing, pre-refunding gains, the release-fade drivers and the FOMC-day FX premium.
- Today's two results reinforce the programme conclusion rather than change it. **Free timing tests have stopped being informative.** The next informative thing costs money, and that is Dave's decision (rank 1).
