# PREREGISTRATION FLOWS-8 — the dollar around the Tokyo and London fixes

```
WRITTEN:   2026-09-28, before any FX bar has been read for this purpose. Only
           EUR/USD is on disk (fastbot v24); the other eight pairs are not.
STATUS:    FROZEN at its first commit; fixes.py pins this file's sha256.
SOURCE:    Krohn, Mueller & Whelan, "Foreign Exchange Fixings and Returns
           around the Clock", Journal of Finance 79(1), 2024
VEHICLE:   OANDA FX CFDs, nine USD pairs
```

*Measurement, not a recommendation. Not financial advice.*

## 0. The claim

Across the nine most-traded currencies over 21 years, the dollar **rises into
the major fixes and falls back afterwards**, a W-shape around the clock. The
paper finds the reversals "pervasive and highly statistically significant",
and consistent with dealers managing inventory from predictable dollar demand
at the fixes.

**Overlap:** fastbot v47 tested the London *gold* fix, which decayed after
the 2015 reform. FLOWS-1 tested month-end rebalancing, which included the
FX fix on month-end days. **Nothing has tested the everyday FX fix.**

**Registered expectation:** the gross pattern is likely to be there. Whether
it pays four spread crossings a fix is the real question.

## 1. Data (Step 0, frozen before any return is computed)

- OANDA M15 bid/ask, 2005-01 → 2026-08, for EUR_USD (fastbot/data/v24),
  USD_JPY, GBP_USD, AUD_USD, USD_CAD, USD_CHF, NZD_USD, USD_NOK and USD_SEK
  (flows/data, pulled with pull_m1.py).
- **USD return** on each pair is the pair's return, signed so that + means
  the dollar rose. The **basket** is the equal-weight mean across the pairs
  with bars in the window.

## 2. Windows (15-minute bars; stamps are bar starts)

- **Tokyo fix (09:55 JST; Japan has no DST).** The 15-minute grid cannot
  split 09:55, so the fix bar is the one ending 10:00 JST. PRE runs from
  08:00 to 10:00 JST, POST from 10:00 to 12:00 JST.
- **London WM/R fix (16:00 London, DST-aware).** PRE runs from 14:00 to 16:00
  London, POST from 16:00 to 18:00 London.
- Each leg is the mid close at its end over the mid close at its start
  (bars ending at those times), minus 1. Weekdays only. A day missing any
  window bar for a pair drops that pair from the basket that day.

## 3. Primary

For each day d and each fix f: **R = PRE_USD − POST_USD** on the basket. The
W-shape predicts R > 0. The daily statistic sums R over the two fixes. Its
mean is tested with Newey-West t (5 lags).

## 4. Gates

| gate | test | pass |
|---|---|---|
| **G1** | mean daily R, 2005-01 → 2026-08 | > 0, t ≥ 2.0 |
| **G2** | mean R in E1, E2, E3 | > 0 in all three, **E3 ≥ 0.5 × full** |
| **G3** | Tokyo and London separately | both > 0 |
| **G4** | trade, net | mean net > 0 with t ≥ 1.65, **and E3 net > 0** |
| **G5** | size | ≥ 3,000 days |

**G4 trade.** For each pair and each fix: buy USD at the start of PRE,
close at the fix, sell USD at the fix, and close at the end of POST. Every
fill is at the quoted bid or ask of the bar at that time. The basket's net
return is the equal-weight mean across the pairs. No rollover is crossed
(both fixes fall inside one trading date), so there is no financing.

**Kills:** K1 is G1 failing, K2 is G2, K3 is G4.

## 5. Secondary (descriptive)

- PRE and POST separately, per fix and per pair.
- The ECB reference rate (14:15 CET), using the same construction.
- The London fix on month-end days compared with other days (FLOWS-1
  overlap).

## 6. Power

About 5,400 days. The two-hour basket moves are about 10 bp standard
deviation, so the standard error of mean R is under 0.3 bp. **Any real
pattern will be seen. The spreads decide the trade.**

## 7. Files

    flows/fixes.py   flows/RESULT_FIXES.md   (pulls via pull_more.sh)
