# RESULT — UNGER2: Unger's published examples worked BEFORE they were published and stopped afterwards

```
SPEC:     PREREGISTRATION_UNGER2.md  sha ead63712…  (frozen 2026-10-11, before any data)
METHOD:   scripts/unger2_run.py  sha afaa7aef…  (frozen 2026-10-12 before any run; 8 planted self-tests pass)
DATA:     OANDA DE30 5m, XAU and WTI 15m bid/ask; CME CL.v.0 and GC.v.0 1m from Databento (Dave's pull, $41.25), built to 15m
RUN:      2026-10-12, each part once.   LOGS: data/unger2/run_unger2_{A,B,C,D,F}.log
VERDICT:  0 of 4 published systems pass on either the CFD or the futures route
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

| system | published | BEFORE publication (reported) | AFTER publication (gated) | verdict |
|---|---|---|---|---|
| **A** DAX opening-range breakout | 2016-06-10 | **+27.4 bp/trade, t 4.39**, both halves positive | **−0.8 bp, t −0.28** (406 trades) | FAIL |
| **B** gold hourly breakout, CFD | 2022-01-13 | +0.1 bp, t 0.13 | −0.9 bp, t −0.69 | FAIL |
| **B** gold hourly breakout, **CME futures** | 2022-01-13 | **+2.7 bp, t 3.34** (2010–22) | **+0.04 bp, t 0.03** | FAIL |
| **C** crude SMA 30/140, bare core, CFD | 2025-04-04 | 2010–26: +5.8 bp, t 1.38 | (since publication +16.6 bp, t 0.97, descriptive) | FAIL (G1) |
| **C** same, CME futures | | 2010–26: +3.2 bp, t 0.69 | | FAIL |
| **D** crude early breakout, 5 offsets | 2025-04-04 | best: futures k = 10, +1.9 bp, t 0.55 | | FAIL |

## The headline: the edges were real in the past and vanished on publication
- **The DAX system is the clearest case we have ever measured.**
  - Over the eleven years before the 2016 webinar code, it made **+27 bp a trade after spreads (t 4.4)**.
  - In the ten years since, it made **nothing** (−0.8 bp).
  - The forum users who reported it "doesn't seem to have performed" after August 2016 were right.
- **Gold tells the same story on futures.** The hourly breakout earned **+2.7 bp a trade net (t 3.3) on CME futures in 2010–2022.** That matches the source's "strong 2010–2014, weaker after". Since the Jan-2022 video it made **+0.04 bp.**
- **Three explanations, and the data can't separate them:**
  1. The systems were **fitted to the history** that existed when they were presented. That is a selection effect: examples are chosen because their past looks good.
  2. The edges **decayed** as markets changed.
  3. **Publication itself** crowded them out.
- **All three lead to the same practical rule:** a published system's backtest says almost nothing about its future.

## What his hidden filters would have to be worth (test C)
- **The bare 30/140 cross makes $20–72 a CL contract gross and −$2 to +$25 net,** depending on the route and on how rolls are handled. Win rate is 33%, against his 27.7%.
- **His stated figure is $219.66 a trade,** so the withheld filters and session window would have to add **about $195–222 per trade.** That is roughly 3–10× the core's gross edge.
- **Two readings of that gap:**
  - his filters carry almost all of the result; or
  - his figure is an in-sample number.
- **Either way, the public core is not the edge.**

## Other findings
- **CFD vs futures matters for gold,** so the futures pull was worth doing. On CFDs the 2010–22 gold edge (+4.4 bp gross) is eaten by spreads; on futures it survived (+2.7 bp net).
- **Gold since 2022: longs held up, shorts didn't.** Longs made +1.3 bp (CFD) and +3.7 bp (futures); shorts made −3.9 bp and −2.5 bp. This is post hoc: a long-only version would need its own pre-registration and a correction for having seen this.
- **The random-direction placebo beat the real DAX and gold systems after publication.** Their direction calls added nothing.
- **Disclosures:**
  - the futures C excludes 196 trades that spanned a contract roll;
  - DAX spreads before 2012 are imputed (this affects only the "before" column);
  - the DAX 5m cache (51 MB) stays in the session workspace and is rebuilt by `unger2_build.py dax`.

## What it does to the puzzle
- **The pattern across PROBE1, the Unger batch and UNGER2 is consistent.** Public pieces describe how he works and which markets trend. **The specific systems he has shown publicly stopped working once shown.**
- **Most likely, whatever edge he has lives in a continuously refreshed portfolio,** maintained by "monthly rotation" and "retire broken systems". It does not live in any fixed rule set. A static copy of his rules would decay just as these did.
- **That is the Teacher's Paradox in data:** what he teaches has already stopped working by the time it is taught.

## Independent replication: TradingView (added 2026-10-12)
- **Setup:** Dave ran `pine/ungerdax1.pine` (the same rules) in TradingView on OANDA:DE30EUR 5m, using TradingView's own data and fill engine. The trade list is saved as data/unger2/tv_trades_ungerdax1.csv (sha 243fe0924218…).

| | TradingView | fastbot harness |
|---|---|---|
| before publication (2006-06 → 2016-06-09) | **+27.2 bp/trade net, t 3.39** (227 trades) | +27.4 bp, t 4.39 (375) |
| after publication (2016-06-10 → 2026-09) | **−1.3 bp, t −0.41** (363 trades) | −0.8 bp, t −0.28 (406) |

- **Day by day:**
  - on days both engines traded (522), the direction agreed 99.8% of the time;
  - the entry prices differ by a median of 0.3 points;
  - per-trade returns correlate at 0.97.
- **The engines differ mainly before 2019.** There, TradingView skips about 40% of our trading days. That is consistent with its older 5m history having gaps in the 08:00–09:00 range. From 2019 they are nearly identical.
- The TradingView export times are one hour off UTC in summer (the chart's time zone). This has no effect on the results.
- **Conclusion: the 2016 break is not an artefact of our pipeline.** Two independent engines on two independent histories give the same before and after.
