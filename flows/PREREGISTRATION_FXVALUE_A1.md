# AMENDMENT A1 to PREREGISTRATION FLOWS-13 (FXVALUE) — data sources that FRED no longer serves

```
WRITTEN:   2026-09-28, after Step 0 and BEFORE any FX, price-level or rate series
           has been joined into any return. Base unchanged (sha d36d1a8b…).
STATUS:    FROZEN at its first commit; fxvalue.py pins it alongside the base.
```

## What happened

The Mac pull (2026-09-28) found that FRED answers HTTP 400 for **every OECD CPI
series named in §1** (CPALTT01xx…) and for **DEXGEUS** (the daily mark rate).
FRED has withdrawn them. Without price levels the real exchange rate, and so
the signal, cannot be built as registered.

## The changes (inputs only; signal, portfolio, gates unchanged)

1. **Price levels** come from the **BIS long consumer price series**
   (`WS_LONG_CPI`, index), monthly where the BIS publishes monthly data and
   quarterly otherwise. Quarterly values follow §1's lag rule: a quarter's
   value is used from the second month after the quarter ends. Monthly values
   keep the one-month lag. The countries are the US, JP, GB, CH, CA, AU, NZ,
   SE and NO, with DE up to 1998-12 and the euro area (XM) from 1999-01,
   chained on growth as the base's implementation note says.
2. **The mark before 1999** comes from **FRED EXGEUS** (monthly average, DEM
   per USD). It is used only for the five-year look-back of the pre-1999 EUR
   signal. EXGEUS is a monthly average, not a month-end rate: that is a small
   timing blur, only in the look-back, and it is stated here.
3. **Short rates.** Some OECD 3-month series start late or end early (JP from
   2002, CH from 1999, EZ and GB end 2026-01). Each currency's rate is the
   3-month interbank rate where published, filled by the call-money rate
   (IRSTCI01) where not. After both end, the last value is carried forward at
   most 8 months. Every month filled this way is counted in the result.
4. The sample still begins at the first month with all nine currencies after
   1990-01, and it is recorded.

Nothing else changes. If the BIS series cannot be fetched either, FLOWS-13 is
**void for want of data**, not failed.
