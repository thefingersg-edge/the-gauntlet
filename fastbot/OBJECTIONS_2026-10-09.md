# How people will try to dismiss the findings — and where each one stands (2026-10-09)

**I am not a financial adviser. This is a measurement, not a recommendation.**

Purpose: an honest "steel-man" list for the channel and for the research. ✅ = already answered by a test or audit; 🟡 = partly answered; ❌ = open (testable).

## A. Market hours (Dave's question)
| Test family | Hours used | Status |
|---|---|---|
| v1, v2 (bar patterns), v36 noise band, reactive, levels/VWAP, timeline ML, PAIRS1, TF1 1-minute | **US cash session only** (09:00/09:30–16:00 New York) | ✅ |
| Opening candle / sweep, UK open (v49), calendar tests, imbalance/bounce, single stocks | defined around the open, close or a scheduled time | ✅ |
| **v51 break of structure / CHoCH (15m and 1h)** | **all 24 hours** of the CFD session, including Asian hours with thin liquidity and wider spreads | ✅ *answered by SESSION1 (2026-10-09): cash-session-only re-run still FAILS (CHoCH −1.9 bp, BOS −0.5 bp)* |
| **TF1 30m / 1h / 4h** | 24 hours by design (TF1.1 — a 6-bar hold could not fit in one session) | ✅ *SESSION1: 30m/1h cash-session-only 0 of 84 pass; 4h cannot fit a session* |

## B. "Your costs are wrong"
- *"Spreads are lower than that" / "you used broker quotes"* — ✅ spreads validated against Dave's real OANDA fills (within ~0.1 bp); US stock auction costs measured on 400 real trades (COSTS1/2).
- *"You forgot financing"* — ✅ measured and charged where positions are held overnight (and it halves trend following through CFDs).
- *"With a better broker it would work"* — 🟡 most failures are negative **before** costs (patterns, structure, pairs); cost can't rescue a negative gross. Futures were costed (not cheaper than OANDA today).

## C. "Your data is wrong"
- *"CFD data isn't the real market"* — 🟡 index CFDs track the futures within the spread; key results replicated on Sharadar exchange prices and Databento exchange quotes. A futures re-run of the bar tests has not been done.
- *"Survivorship bias"* — ✅ delisted stocks included; S&P breadth rebuilt point-in-time (BREADTH2).
- *"Look-ahead"* — ✅ two audits; the one real case (PEAD3–8) was found and voided by us.

## D. "You tested it wrong"
- *"You didn't optimise the settings"* — ✅ deliberate: settings come from the literature or the published rule, because tuning on the same data manufactures false passes. Exit/hold variations were tested (PEAD8, v2 barrier analysis, v39 checks) and did not rescue anything.
- *"Patterns work in context / with confluence, not alone"* — 🟡 v39/v41 ML combined dozens of features and context (AUC 0.55, failed); STRAT1 combined triggers (failed). A specific "confluence" recipe from a named source could still be tested. ❌
- *"Bonferroni is too strict"* — ✅ nothing failed only because of the correction: the best tests are also no better than random entries, which is a separate gate.
- *"The random benchmark is unfair"* — ✅ it uses the identical entry/exit mechanics and the same time-of-day and year mix; it isolates what the pattern itself adds.
- *"You only tested longs"* — ✅ both directions in every pattern/structure test.
- *"Wrong timeframe"* — ✅ 1m, 5m, 15m, 30m, 1h, 4h, daily all tested now.
- *"Wrong market"* — 🟡 SPX, NAS, US30, gold, UK100, DE30, JP225, AU200, EU50, EURUSD, US single stocks, crypto basis. **Oil not yet** (Saturday). ❌

## E. "Markets changed" / "it works now"
- ✅ Recent-regime policy: anything consistent since 2013 goes to a forward record (v36, small-cap drift, breadth).
- ✅ Several famous edges were shown to have died (gold fix after 2015, spin-offs after 2013, leveraged-ETF front-running after 2011) — the record supports "markets change", in the direction of edges disappearing.

## F. "Professionals make money, so it must be possible"
- ✅ The 15-second imbalance result shows exactly where: real effects exist but are captured within milliseconds by firms with direct feeds and co-location; access, not existence, is the barrier (Rule 2).

## G. "Small edges compound with leverage"
- ✅ Leverage scales the edge and the cost equally; a net-negative edge compounds into a faster loss. Positive-but-insignificant edges (e.g. trend following t 1.7) cannot be told apart from luck, so leveraging them is a bet on noise.

## H. "Discretion / experience beats rules"
- 🟡 Out of scope for backtesting by definition; Dave's own fills audit (no per-trade edge after costs, financing ≈ trading profit) is the honest discretionary data point.

## Open items worth testing (from this list)
1. ~~**SESSION1**~~ DONE 2026-10-09 (RESULT_SESSION1_REGIME1.md) — re-run v51 structure and TF1 30m/1h patterns/structure on the US cash session only (data in hand, cheap). Pre-register as a robustness check of the hours assumption.
2. **Oil** (already scheduled, Saturday).
3. A named "confluence" strategy (e.g. a published ICT/SMC or price-action recipe with exact rules) — needs a specific source to test faithfully.
4. Bar tests on exchange futures data (Databento CME 1m) — only if 1 shows something.


## Added 2026-10-09: "you didn't find the trend first"
REGIME1: five moving-average / trend filters (price vs SMA200, 50/200 cross, EMA20/50, 12-month return, SMA200 slope) do not tell next-day or next-week direction (0 of 10; four of five point the wrong way). Patterns and structure taken only with the 200-day trend: 0 of 86 pass; the filter's lift beyond what it gives random entries is +0.7 bp median, positive in 56% of tests. ✅

REGIME2 (ADX trend strength): direction on trending days 0/6 (the trend direction pointed the WRONG way: strong trends snapped back); setups matched to trending/ranging regime 0/86; 15m-ADX structure 0/2. ✅
