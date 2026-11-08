# PREREGISTRATION — PROBE1: Andrea Unger's published "market character" probe on our markets

```
STATUS:   frozen before any PROBE1 number is computed (sha in PROVENANCE.md)
WRITTEN:  2026-10-09
SOURCE:   Unger Academy blog "My Trading System" and podcast descriptions (youtube/course1/UNGER_NOTES.md):
          on daily bars, buy a break of the prior day's high and sell a break of the prior day's low, always in the market.
          A rising equity curve means the market trends (build trend-following); a falling one means it mean-reverts (build counter-trend).
DATA:     OANDA 15m bid/ask (struct15 caches): SPX500, NAS100, UK100 (2005->), XAUUSD (2006->), to 2026-09-25.
          WTI/Brent are added as PROBE1-OIL after Saturday's pull, with identical code.
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

## The probe (exactly as published, made mechanical)
- **Trading day:** 17:00 New York to 17:00 New York, the CFD roll. Day d's high and low are the extremes of its 15m mid bars.
- **During day d, the levels are day d−1's high and low.** Positions:
  - go long, or reverse to long, when a bar's high reaches the prior high;
  - go short, or reverse to short, when a bar's low reaches the prior low.
- **Fill price:** the level, or the bar open if the bar opened beyond the level.
- **A bar that touches both levels:** the level nearer the bar open is treated as hit first, then the other.
- **Before the first break:** flat. After that, always in the market (stop and reverse).
- **Daily P&L:** marked to market at the 17:00 New York close, as a fraction of the previous close.
- **Gross:** no costs, as Unger checks the raw edge first.
- **Net:** one full quoted spread per reversal (half on exit, half on entry), plus overnight financing at each 17:00 roll held. Longs pay policy rate + 2.5%; shorts receive policy rate − 2.5%; Friday counts 3 nights. Rates: USD for SPX, NAS and gold; GBP for UK100.

## Questions and gates
**Q1. Character:** is the market's "character" stable?
- The character is the sign of the gross probe return.
- Gates per market:
  - (a) full-sample gross mean daily P&L has |t| ≥ 2 (Newey–West, 5 lags);
  - (b) the same sign in each era 2005–12, 2013–19 and 2020–26.
- A market passing both has a **stable character**: TREND if the sign is positive, MEAN-REVERTING if it is negative.

**Q2. Out of sample:** does the character chosen on early data pay later, after costs?
- **Choose:** on 2005–2015 gross, pick TREND (run the probe) if the mean is > 0, or FADE (run the exact reverse: sell the high break, buy the low break) if it is < 0.
- **Test:** 2016-01-01 → 2026-09-25, **net**.
- **Gate per market:** net mean > 0 and t ≥ 2.50 (Bonferroni over 4 markets, one-sided 0.05/4 ≈ 2.5).
- **Benchmark (reported):** buy-and-hold net of financing over the same period. Sharpe is shown for both.

**Reported, no gates:**
- annual gross and net returns per market;
- number of reversals per year;
- the share of gross P&L lost to spread and to financing;
- the equity curves as CSV, for the episode.

## Self-tests
- **Planted trend:** a steadily rising path must give TREND (positive gross); a zig-zag must give mean-reverting (negative gross).
- **Reversal identity:** probe gross + reverse gross = 0 exactly.
- **No look-ahead:** the levels for day d come only from day d−1.

## What each outcome means
- **Q1 stable everywhere:** Unger's diagnostic is a usable first step for deciding which family to test on each market.
- **Q1 unstable:** on these markets, the "character" his probe reads is era-specific noise.
- **Q2 pass:** a lead for a full pre-registration and a forward record, not money.
- **Q2 fail:** as with every directional test so far, the simple version does not survive costs.
