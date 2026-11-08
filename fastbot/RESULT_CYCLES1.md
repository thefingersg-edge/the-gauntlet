# RESULT — CYCLES1: dating bull and bear markets with the 20% rule. The label is real, but it arrives late.

```
SPEC:     DEFINITION_CYCLES1.md  sha fa06a3ff…  (frozen before any phase was dated)
METHOD:   cycles/cycles1_run.py (sha in PROVENANCE; one mechanical self-test fix logged before the run)
DATA:     Shiller S&P Composite monthly 1871-2026 (data/cycles/shiller_monthly.csv); daily cash closes 2005-2026 (SPX, NAS100, UK100, gold)
OUTPUT:   data/cycles/phases_monthly.csv, phases_daily.csv, corrections_monthly.csv, run_cycles1.log
RUN:      2026-10-09        TYPE: descriptive catalogue, no gates
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

## The definition we will use from now on
- **A bear market** runs from a **peak**, the highest close, to the lowest close before price recovers 20%. It exists once price closes 20% below the peak.
- **A bull market** runs from that **trough** to the next peak.
- **Each phase has two dates:**
  - the *peak or trough date*, which can only be known afterwards;
  - the *confirmation date*, the first close through the 20% line, which is the first day anyone could call it.

## Is it called in real time, or only in hindsight? Mostly in hindsight.
S&P 500, 1871–2026: 23 completed bears and 22 completed bulls.

| | median | read it as |
|---|---|---|
| bear depth | −32% | |
| bear length | 18 months | |
| peak → "bear market" confirmed | **10 months** | the peak date is backfilled almost a year later |
| share of the fall already gone at confirmation | **70%** | by the time it is called, most of the damage is done |
| further fall after confirmation | about −10% (but −73% in 1930, −38% in 2008, −32% in 1873) | usually small, occasionally catastrophic |
| bull gain | +83% over 33 months | |
| share of the rise already gone when the bull is confirmed | 36% | bulls are confirmed earlier in their life than bears |

Daily data tells the same story for the recent bears:
- **SPX 2007:** confirmed in July 2008, 9 months after the peak. Only 31% of the fall had gone, and another −40% followed.
- **SPX 2022:** confirmed in June, 161 days after the peak, with 84% of the fall gone.
- **SPX 2020:** confirmed 22 days after the peak, with 74% gone.

**The real-time "early warnings" fire constantly.**
- **Monthly price below its 10-month average:** caught all 23 bears, first signalling a median of 89 days after the peak with only 18% of the fall gone. It also gave 53 false alarms in 105 signals.
- **Daily price below its 200-day average:**
  - SPX: caught 4 of 4 bears, with 57 false alarms in 70 signals.
  - UK100: caught 4 of 4, with 90 false alarms in 120.

So: the labels are mostly retrospective. The tools that do flag bears early also flag about two false alarms for every real one. That is consistent with REGIME1/2: they are better at warning of risk than at calling direction.

## A first look at causes (monthly, 23 bears, descriptive only)
- **Recession:** 16 of 23 bears overlapped an NBER recession. 19 of 30 recessions since 1871 came with a bear.
- **Earnings:** real earnings fell from peak to trough in 16 of 23 bears.
- **Bears without a recession or earnings fall look event- or valuation-driven:** 1917 (war), 1934, 1938–42 (war), 1961–62, 1987 (crash) and 2022 (inflation and rates; CPI +7%, the long rate up 2.5 points).
- **Valuation at the peak varies hugely:** CAPE ranged from 7 (1919) to 43 (2000). The highest readings (1929 at 33, 2000 at 43, 2021 at 38) were all followed by bears, but a high CAPE did not tell you when: CAPE was above 30 for years before 2000 and 2021.

## Known limits of this definition
- **Monthly averages smooth crashes.** In the monthly data the 2020 crash is not a bear at all (the daily fall was −34%), and 1987 shows as −27% (daily −34%). This limit was written into the definition beforehand.
- **The symmetric 20% rule splits some long bears.** A 20%+ bear-market rally ends the bear early:
  - SPX 2007–09 becomes 2007→Nov 2008, then a bull to Jan 2009, then a bear to Mar 2009;
  - 1929 becomes Sep→Nov 1929, a rally, then a bear to 1932.

  The academic fix (Pagan & Sossounov 2003) adds minimum durations, with phases of at least 4 months. That can be added as CYCLES1.1 using the published values, not tuned ones.
- **Daily data starts in 2005,** so the first daily phase of each market begins mid-move.
- **Gold has its own cycles** (2011–15 −45%; 2026 −27% so far), unrelated to equity bears.

## Next: CYCLES2 — what was going on around each bear
FRED pull script: `cycles/fred_cycles_pull.py` (run it on the Mac). It pulls:
- recessions;
- fed funds, T-bill and 10-year rates;
- Baa and Aaa corporate yields (credit spread back to 1919);
- industrial production, unemployment, payrolls and jobless claims;
- CPI and oil;
- M2, financial conditions, sentiment and building permits.

The plan for each bear (and each bull) is to line up what those series were doing 24 months before the peak through to the trough. Then compare that with the same window around random dates, giving a descriptive "fingerprint" of bears, pre-registered before it is computed. With about 15–23 bears this is history, not statistics. It is for understanding, not for a trading rule.
