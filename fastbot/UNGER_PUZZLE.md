# UNGER PUZZLE: a running project to rebuild a champion's method from public pieces

```
OPENED:   2026-10-09 (Dave: "keep this as a moving project to see if we can find the missing pieces")
STATUS:   LIVE. Update this file after every related test or new public source. Newest entries go at the top of the log.
RULES:    1. Public sources only: his free videos, blog, podcasts, interviews, and books bought legitimately.
             Never unauthorised copies of paid courses (course-dump or resale sites). COURSE1 searches surfaced such listings for
             OTHER educators' courses; none were opened, and none is used for anyone.
             No scraping or reselling of his paid signals.
          2. Every rebuilt piece is pre-registered and frozen before it is run, exactly like everything else in fastbot.
          3. The aim is to test the IDEAS on our markets and costs. It is not to clone or publish his product.
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

## What we know (public, sourced: youtube/course1/UNGER_NOTES.md)
| Piece | Source | Status |
|---|---|---|
| Contest wins 2008/09/10 (+672/115/240%) | WCTC Hall of Fame | verified |
| Contest returns used deliberately extreme "turbo" risk | Armchair Trader 2021 | his own statement; **TURBO1: with zero edge at 100% vol, the best of 200 makes about +615%** |
| Step 1: daily prior-high/low breakout "probe" decides trend vs counter-trend per market | Unger blog *My Trading System* | **tested: PROBE1** |
| Simple core idea, then "context" rules rather than optimised parameters | Algorithmic Advantage #038 | **tested: CONTEXT1, 0/6 generic filters** |
| Several system types per market (trend, mean reversion, breakout, volatility) | Algorithmic Advantage #038 | **tested: MULTI1, FAIL (low correlation, but mostly negative parts)** |
| ~30–40 liquid futures; 5–15 min to daily bars; short bars only to time entries | Algorithmic Advantage #038 | partly (we have 4 CFDs; oil Saturday) |
| Robustness: in/out of sample, parameter nudges, perturbed prices; no walk-forward | Algorithmic Advantage #038, BST ep.16 | our method already covers most of this |
| About 1% risk per trade, fixed-fractional; drawdown sets leverage | Algorithmic Advantage #038 | not yet tested |
| Monthly rotation of strategies by recent performance (his "Titan/Zeus" tools) | Algorithmic Advantage #038 | **tested: ROTATE1, FAIL (no strategy momentum)** |
| Longer timeframe used to filter shorter-timeframe trades | BST ep.16 show notes | partly (REGIME1/2 used daily filters: no help on indices) |

## What is missing (the actual rules he sells)
- The specific "context" filters added to each core idea.
- The exits: stops, targets, time exits.
- Which markets he trades with which system type today.
- How the rotation tool scores strategies.

## Results so far
| Date | Test | Finding |
|---|---|---|
| 2026-10-09 | PROBE1 | Gold has a stable TREND character (t 3.9, every era). The indices have none: SPX weakly mean-reverting, NAS flipped after 2013, UK100 flips each era. The raw probe after costs out of sample: 0/4. On gold, costs ate about 90% of the edge. |

| 2026-10-11 | GOLDTREND1, CONTEXT1, MULTI1, ROTATE1, TURBO1 | All gated tests FAIL. Slower gold rules cut spreads, but CFD financing (rate + 2.5%) eats the trend; the futures route is only Sharpe 0.2. Context filters remove trades, not losers (best: inside day, OOS t 1.79). Multi-system: correlation +0.03, but 9 of 12 parts negative, so the portfolio is Sharpe -0.68. No strategy momentum. TURBO1: a zero-edge winner of a 200-entrant contest makes a median +615%; mix in 10 real edges and a zero-edge trader still wins 58%. Three wins in a row is the real evidence. See RESULT_UNGER_BATCH.md. |
| 2026-10-12 | UNGER2 (his published examples, from their publication dates) | 0/4 pass on CFD or futures. DAX opening-range: +27 bp/trade (t 4.4) in the 11 years BEFORE the 2016 webinar, -0.8 bp after. Gold hourly on CME futures: +2.7 bp (t 3.3) 2010-22, +0.04 bp since the 2022 video. Bare crude 30/140 core: $20-72 gross per contract vs his stated $219.66, so the withheld filters would have to add ~$200/trade. Published systems stop working once shown. See RESULT_UNGER2.md. |
| 2026-10-10 | PROBE1-OIL | WTI has a stable TREND character (t 2.5, every era), confirming "crude trends". Brent is unstable (2013-19 mean-reverting). Out of sample after costs: 0/2 (WTI net +4.4 bp/day, t 0.9; buy-and-hold better). |

## How to break down an edge we can't see (plan, 2026-10-11)
**What is still missing:**
- **His live return series.** It is not public: the contest gives yearly figures only, and Unger Academy posts are hand-picked winners.
- **Real futures data and futures costs.** We tested on CFDs, where the policy rate + 2.5% financing kills slow, multi-day rules. He trades futures.

**Approach: test his PUBLISHED examples from the date he published them.**
- Anything after the publication date is true out-of-sample for him as well as for us.
- Run each "core idea" without his withheld filters. The gap between his stated average trade and ours measures what the hidden context adds, without seeing it.
- Where a monthly return series exists, attribute it to known premia (trend, carry, index beta, leverage). What is left over is the real secret.

**Public, specified pieces found (all from free sources; nothing from paid material):**
| piece | source / date | specified? | our data |
|---|---|---|---|
| DAX opening-range breakout: 08:00-09:00 CET range, entry at range ± 1x range until 10:00, previous day's \|close-open\|/range < 0.5, no Fridays, stop at the other side of the range, flat by 22:00 | Unger free webinar, coded on ProRealCode 2016-06-10; Unger commented the developers' version matches his "nearly completely" | fully | OANDA DE30 15m (5m needs a pull). **10 years out-of-sample since publication.** Forum users reported decay after Aug 2016 |
| Gold 60m breakout: bar counter from 17:00 NY; longs on bars 18-22 when price breaks the prior bar's high, exit 01:00; shorts on bars 9-12 below the 3-bar low, exit 09:00; $1,700 stop | Unger Academy coach video, 2022-01-13 | nearly (short lookback "about 3") | OANDA XAU 15m -> 60m. **Intraday, so no CFD financing.** 4.7 years out-of-sample |
| Crude 15m SMA 30/140 cross, stop-and-reverse; "proprietary filters" and session window withheld; stated average trade $219.66, win rate 27.7% | Unger Academy, 2025-04-04 | core only | OANDA WTI 15m; CL futures via Databento. Measures what the filters add |
| Crude intraday: entry a set number of ticks inside the prior session's high/low, flat at end of day | Unger Academy, 2025-04-04 | offset withheld | testable as a small, pre-fixed grid with a Bonferroni correction |
| Crude 15m MA trend (launched about 2017; stated average trade $156) and 5m "strength" system ($213) | Unger Academy (crude oil $49k post) | vague | descriptive only |

**UNGER2: pre-registered and frozen 2026-10-11 (PREREGISTRATION_UNGER2.md, sha ead63712...):** UNGERDAX1, UNGERGOLD1, UNGERCL1 (core with no filters; comparison with his stated average trade). Optional Databento pull: CL and GC 1m from 2010, to repeat all three on futures costs.

## Test queue: all pre-registered 2026-10-09 in PREREGISTRATION_UNGER_BATCH.md; run in this order
1. **PROBE1-OIL** (on the Saturday list): the same probe on WTI and Brent. It checks his "crude trends" claim.
2. **GOLDTREND1**: gold's stable trend with a *slower, cheaper* rule, to cut the reversal and financing costs that killed PROBE1. Examples: the probe on weekly bars, or only trading breaks that close beyond the level. Compare a CFD route with a futures/ETF cost route.
3. **CONTEXT1**: his "core idea + context" step, tested honestly. Fix a small menu of *published, generic* context filters in advance, apply each to the gold probe, and Bonferroni-correct across the menu: volatility regime (ATR percentile), day of week, inside-day / narrow-range day (NR4/NR7), gap vs no gap. Does any context filter survive out of sample?
4. **MULTI1**: several system types per market (trend + mean reversion + breakout), combined. Does mixing uncorrelated simple systems create a positive whole when each part is marginal?
5. **ROTATE1**: monthly rotation by recent performance. Across a fixed library of simple systems, does switching to recent winners beat holding all of them equally? This is "strategy momentum", and it is testable without his tools.
6. **TURBO1**: an episode simulation. Take a modest edge (e.g. gold trend at Sharpe 0.5) and show what "turbo" leverage does: the chance of a +600% year against the chance of ruin. This explains how a contest is won, and why the 99% blow up trying.

## Sources to mine next (public)
- His books, bought legitimately if Dave wants them: *Trattato di Money Management* (Hoepli) and his English-language titles.
- Better System Trader episode 16, full audio. The show notes mention "a proposed solution" to the drawbacks of trend following.
- His free YouTube webinars and the Unger Academy blog: look for named example systems he has published in full.
- Interviews from 2008–2012 (around the wins): Traders' magazine, MoneyShow, Italian financial press (Milano Finanza, Il Sole 24 Ore).

## Log
- 2026-10-12: UNGER2 run (Databento CL/GC futures pulled, $41.25). Pattern: edges existed before publication and vanished after. Working conclusion: any real edge is in his continuously refreshed portfolio (rotation, retiring systems), not in a fixed rule set, which is the Teacher's Paradox in data.
- 2026-10-11: UNGER2 pre-registered: A DAX opening-range breakout (out of sample since 2016), B gold hourly breakout (since 2022), C crude SMA 30/140 bare core (gap to his $219.66 per trade), D crude early breakout (grid, Bonferroni), F futures re-run after the Databento CL/GC pull.
- 2026-10-11: found 4 public, specified Unger examples (DAX ORB 2016; gold 60m breakout 2022; crude SMA 30/140 2025; crude prior-session breakout). Plan: test each from its publication date, and measure the hidden filters as the gap to his stated average trade.
- 2026-10-11: tests 2-6 run (unger_batch.py, frozen e31a29d2...). The generic public principles fail on our CFD markets and costs. Remaining missing piece: his specific rules, plus futures-level carry costs. Leads (fresh spec needed): futures-route gold channel, inside-day context, oil trend.
- 2026-10-10: PROBE1-OIL run. Commodities trend and indices don't, which matches Unger's split.
- 2026-10-09: tests 1-6 pre-registered and frozen (PREREGISTRATION_UNGER_BATCH.md). The new clean-day rule drops weekend and partial sessions.
- 2026-10-09: project opened. PROBE1 run. Unger interview notes collected (youtube/course1/UNGER_NOTES.md). PROBE1-OIL added to the Saturday task.
