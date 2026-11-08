# PREREGISTRATION — UNGER2: Unger's published example systems, tested from the day they were published

```
STATUS:   frozen before any UNGER2 number is computed (sha in PROVENANCE.md). The harness (scripts/unger2_run.py) is written and frozen
          separately before the first run. Each part runs ONCE, in the order listed.
WRITTEN:  2026-10-11 (Dave: "yes pre register the whole batch")
CONTEXT:  fastbot/UNGER_PUZZLE.md, "How to break down an edge we can't see". Everything below comes from FREE public sources.
          Nothing comes from paid course material, signals or unauthorised copies.
SOURCES:  A  ProRealCode, "DAX 5 min automated trading by Andrea Unger", posted 2016-06-10. The poster says the code is from a free Unger webinar,
             and Unger commented that the platform developers' version "corresponds nearly completely" to his.
          B  Unger Academy blog, "Breakout Strategy on Hourly Bars: How Does It Work? Example on Gold", 2022-01-13 (coach video).
          C, D  Unger Academy blog, "Trading strategies on crude oil: two trend-following systems that beat volatility", 2025-04-04.
DATA:     OANDA bid/ask: DE30_EUR 5m (data/v38), XAU_USD and WTICO_USD 15m (data/v24 / v51 caches), to 2026-09-30.
          Part F: CME CL.v.0 and GC.v.0 1m from Databento (scripts/fetch_unger2_futures.py, sha e0e975b6…, run on the Mac with a cost check first).
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

## Why this design
- **We have no copy of Unger's real returns, so we test what he PUBLISHED.** Every trade after the publication date is out of sample for him as well as for us.
- **Two systems (C, D) were published with key parts withheld.** We run the bare published core, and compare its average trade with the figure he states. The gap is a measured size for his hidden filters.

## Shared rules
- **Prices and fills:**
  - signals use mid prices; fills pay the quoted half-spread on entry and on exit, from the bar where each happens;
  - a stop or breakout level is filled at the level, or at the bar's open if the bar gaps through it;
  - when one bar touches both an entry and a stop, the stop is assumed hit (the conservative choice).
- **Financing:** a position held over 17:00 New York pays the policy rate + 2.5% if long, and receives the policy rate − 2.5% if short; Friday counts as 3 nights. Rates: EUR for DE30, USD otherwise.
- **Time zones:** each source's stated clock. DAX: Europe/Berlin (the poster used CET). Gold and crude: America/Chicago, the CME exchange clock (the gold video counts bars from the 17:00 exchange-time open).
- **Statistics:**
  - the unit is the net return per trade in bp; t is clustered by day;
  - **family = 4 tests (A, B, C, D)**, so one-sided Bonferroni α = 0.05/4, i.e. **t ≥ 2.24**;
  - D's internal grid of 5 offsets takes a further /5, i.e. t ≥ 2.81.
- **Random-entry placebo (every test):** the same entry times, exits and costs, with a random direction. 1,000 draws, seed 0. The system must beat the placebo's 95th percentile.

---
## A. UNGERDAX1: DAX opening-range breakout (fully specified)
- **Range:** the high (HH) and low (LL) of 08:00–09:00 Berlin; delta = 1 × (HH − LL).
- **Filter:**
  - Dfactor of the previous trading day = |close − open| / (high − low), using that day's 08:00–22:00 Berlin bars, must be < 0.5;
  - no entries on Fridays.
- **Entry, 09:00–10:00 Berlin:**
  - long when a 5m bar closes above HH + delta, entering at the next bar's open ("at market");
  - short when a 5m bar closes below LL − delta;
  - one position at a time; re-entry after a stop is allowed until 10:00 (the code does not forbid it).
- **Exits:** stop at HH for a long and at LL for a short; otherwise flat at 22:00 Berlin. No trailing stop: the poster removed it as buggy and said the backtest was unchanged.
- **Sizing:** one unit; results are in bp of price.
- **Primary window:** 2016-06-10 → 2026-09-30, out of sample since publication.
- **Gates (all must pass):**
  - **G1:** mean net bp per trade > 0 with t ≥ 2.24;
  - **G2:** mean net > 0 in both halves (2016-06-10 → 2021-07-31 and 2021-08-01 → 2026-09-30);
  - **G3:** above the placebo's 95th percentile.
- **Reported:**
  - 2005–2016-06 (the pre-publication record Unger could have seen);
  - a stop-order fill variant (entry at the level itself);
  - trades per year;
  - long and short separately;
  - the Friday and Dfactor filters each removed (how much "context" they add).

## B. UNGERGOLD1: gold hourly breakout with time windows (nearly specified)
- **Bars:** 60m bars built from OANDA XAU 15m, on the Chicago clock. Bar 1 is the bar starting 17:00 CT; the counter resets each session.
- **Long:**
  - in bars 18–22 (10:00–15:00 CT), buy stop at the previous bar's high;
  - exit at the 01:00 CT bar open the next morning (one 17:00 NY financing roll).
- **Short:**
  - in bars 9–12 (01:00–05:00 CT), sell stop at the lowest low of the previous 3 bars ("about 3" in the source; fixed at 3 here);
  - exit at 09:00 CT.
- **Stop:** $17 per ounce from entry (the source's $1,700 on a 100-oz contract).
- **Limits:** at most one long and one short per session, and one position at a time.
- **Primary window:** 2022-01-13 → 2026-09-30.
- **Gates:**
  - **G1:** t ≥ 2.24 with mean > 0;
  - **G2:** both halves positive (2022-01-13 → 2024-05-15 and after);
  - **G3:** above the placebo.
- **Reported:**
  - 2010-01 → 2022-01 (the source's backtest era: "strong 2010–2014, weaker after");
  - the source's stated "~$52 per trade, about 5 ticks" vs ours.

## C. UNGERCL1: crude 15m SMA 30/140 cross, the bare core (filters and session withheld)
- **Rule:** on WTI 15m mid closes, go long when SMA30 crosses above SMA140 and short when it crosses below. Always in the market (stop and reverse). Enter at the next bar's open. All hours.
- **Primary window:** 2010-01-01 → 2026-09-30 (the source's "from 2010 to today").
- **Gates:** G1 t ≥ 2.24 with mean > 0; G2 positive in 2010–2017 and 2018–2026; G3 placebo.
- **Reported (the main point of C):**
  - our average trade in $ per 1,000 bbl (one CL contract) and the win rate, against his stated **$219.66 and 27.69%**;
  - **the gap = what his withheld filters and session window are worth;**
  - the out-of-sample window since publication (2025-04-04 →), descriptive only;
  - the futures route in Part F.

## D. UNGERCL2: crude prior-session breakout entered early (offset withheld)
- **Rule:**
  - each CME session (17:00–16:00 CT), place a buy stop at the prior session's high − k ticks and a sell stop at the prior session's low + k ticks;
  - the first one hit is taken and the other is cancelled;
  - flat at 15:45 CT; no stop (none is stated).
- **Grid, fixed:** k ∈ {0, 5, 10, 20, 40} ticks (1 tick = $0.01). The internal Bonferroni gives t ≥ 2.81 per k.
- **Window:** 2010-01-01 → 2026-09-30.
- **Gates:** for at least one k, G1 at t ≥ 2.81, G2 (both halves of 2010–2026 positive) and G3 (placebo).
- **Reported:** every k, and the source's stated $166.53 per trade vs ours.

## F. Futures route (after the Databento pull; same rules, CME costs)
- **What runs:** B, C and D re-run on CL.v.0 / GC.v.0 1m bars (volume-rolled; days with a roll are excluded from the trade-level stats).
- **Costs:** 1 tick of slippage per side + $2.50 commission per round trip; no financing (futures carry is inside the price).
- **Windows:** the same as the CFD parts, starting from 2010-06-07.
- **Gates:** the same G1–G3 thresholds. This is the fairer test of Unger's own vehicle. CFD and futures verdicts are both reported, and **a PASS on either is a lead for a forward record, never money.**

## Predictions (written before any number)
- **A FAIL.** The forum reported decay soon after publication, and opening-range breakouts on index CFDs failed in our TF1 and SESSION1.
- **B borderline.** It is intraday and short-held, and gold trends (PROBE1). But the source itself said the edge had thinned to about 5 ticks.
- **C FAIL as a bare core.** We expect a large gap to his $219.66, which would say his filters carry most of the result.
- **D FAIL** after the Bonferroni correction.
