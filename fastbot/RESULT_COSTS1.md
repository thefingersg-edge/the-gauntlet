# RESULT — COSTS1 (route 1, Databento quotes): the closing auction costs about one-seventh of our EDGE estimate. Opening trades cost MORE than EDGE.

```
SPEC:     PREREGISTRATION_COSTS1.md sha 52b098db… + PREREGISTRATION_COSTS1.1.md sha 1d3b8fb6…
SAMPLE:   data/costs1/sample.csv sha b740ef37… (drawn before any quote; 200 M + 200 S PEAD3 signals, 2018-05 .. 2026-05)
DATA:     Databento XNAS.ITCH / XNYS.PILLAR / XASE.PILLAR, bbo-1s + statistics; pulled 2026-10-03 on Dave's Mac
METHOD:   scripts/databento_costs1.py -> data/costs1/measures.csv; singlestock/costs1_verdict.py; log data/run_costs1.log
RUN:      2026-10-04
DECISION: median closing-auction cost / EDGE = 0.14 (90% CI 0.12–0.15) <= 0.50  ->  ACCEPT the auction cost model
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

```
round-trip cost, median (90% CI)      ALL                 M (mid caps)        S (small caps)
EDGE estimate                         0.81% (0.74–0.86)   0.71% (0.67–0.80)   0.88% (0.81–0.97)
open, quoted spread                   1.18% (1.05–1.31)   0.77% (0.68–0.83)   1.69% (1.56–1.83)
closing auction vs pre-close mid      0.11% (0.10–0.12)   0.07% (0.06–0.08)   0.18% (0.16–0.19)
open / EDGE                           1.43 (1.34–1.60)    1.12 (0.93–1.33)    1.94 (1.63–2.25)
auction / EDGE                        0.14 (0.12–0.15)    0.10 (0.09–0.11)    0.20 (0.19–0.25)
```
## Read it plainly
- **Trading in the closing auction is cheap:** about 0.1% round trip, roughly a seventh of what EDGE assumed. The decision rule is passed by a wide margin.
- **Trading at the open is expensive,** especially in small caps: the quoted spread in the first minute is about twice EDGE. **Every PEAD backtest that entered at the open with EDGE cost was therefore too optimistic about costs at the open**, most of all for small caps, where PEAD3/PEAD5 looked strongest.
- Together: the strategy should be executed in the closing auction, not at the open. The forward portfolio (PORT1) uses the auction model.

## Caveats
- Primary-exchange quotes, not the consolidated NBBO: spreads are the same or wider than NBBO, so costs lean high, not low.
- Auction "cost" = distance of the official close from the last pre-close midpoint. It ignores commission (add 2 × $0.0035/share) and market impact; our order sizes are small relative to closing auctions, but that is an assumption.
- 55 sampled rows were replaced from the reserve: 30 symbols Databento could not resolve (mostly renamed or delisted tickers), 22 with an empty window (20 of them NYSE; 14 had no first-minute quotes), 3 network time-outs. A time-out is not "no data" in the strict sense of COSTS1.1; with 400 rows and CIs this tight it cannot change the decision. NYSE ended at 138 of 400 (sample drew 149).

## What this changes (needs its own pre-registration)
- PEAD3/PEAD5 were judged with open entry and EDGE cost. With measured costs, open entry is worse and auction entry far better. The natural follow-up is **PEAD6: the PEAD3 rule executed close-to-close in the auction with the measured cost (0.07% M / 0.18% S + commission)**. The main window is already seen, so it is a cost re-evaluation, not a fresh discovery; the forward record decides.
