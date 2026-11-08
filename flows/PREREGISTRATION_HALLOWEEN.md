# PREREGISTRATION FLOWS-12 — "Sell in May": November–April against May–October

```
WRITTEN:   2026-09-28, before any monthly return has been computed for this purpose.
STATUS:    FROZEN at its first commit; halloween.py pins this file's sha256.
SOURCE:    Bouman & Jacobsen (AER 2002); Jacobsen & Zhang, "The Halloween
           indicator: everywhere and all the time" (2018, 300+ years, 114 markets)
VEHICLE:   index level; SPX500_USD CFD for the trading check
```

*Measurement, not a recommendation. Not financial advice.*

## 0. The claim and the power problem

Equity returns are higher from November to April than from May to October.
The effect has the longest out-of-sample record of any calendar effect.
**The CFD history alone (21 years = 21 winters) cannot test it.** The primary
therefore uses the longest free daily index on FRED: the **NASDAQ Composite,
1971–2026**.

## 1. Data (Step 0)

- FRED NASDAQCOM daily closes, 1971-02 → 2026-08 (a price index; dividends
  are omitted, and their seasonality is small next to the claimed effect).
  Month-end closes give monthly log returns.
- SPX500_USD daily mid closes (17:00-NY), 2005-01 → 2026-08.

## 2. Primary

    r_m = a + b·W_m + u       W_m = 1 for Nov–Apr months; Newey-West (6 lags)

The claim predicts **b > 0**.

## 3. Gates

| gate | test | pass |
|---|---|---|
| **G1** | b, NASDAQCOM 1971-03 → 2026-08 | > 0, t ≥ 2.0 |
| **G2** | b in thirds: 1971–1989, 1990–2007, 2008–2026 | > 0 in all three, **last ≥ 0.5 × full** |
| **G3** | b on SPX500 CFD 2005–2026 | > 0 (sign only: 21 years) |
| **G4** | rule on SPX500 CFD, net of long financing: long Nov–Apr, flat May–Oct | Sharpe of the rule > Sharpe of buy-and-hold, both net |

**Kills:** K1 is G1 failing, K2 is G2.

## 4. Power

About 666 months. With a monthly SD near 6%, the standard error of b is
about 0.46%/month, so **t = 2 needs about 0.9%/month**. The published gap is
roughly that, so power is modest.

## 5. Files

    flows/halloween.py   flows/RESULT_HALLOWEEN.md   (data via fetch_longrun.py)
