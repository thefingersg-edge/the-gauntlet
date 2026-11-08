# PREREGISTRATION FLOWS-11 — Treasury note and bond auctions: the intraday concession

```
WRITTEN:   2026-09-28, before any auction date has been fetched or joined to a price.
STATUS:    FROZEN at its first commit; auctions.py pins this file's sha256.
SOURCE:    Lou, Yan & Zhang, "Anticipated and Repeated Shocks in Liquid
           Markets" (RFS 2013); NY Fed Staff Report 1188 (2026), "Intraday
           Price Pressure and Order Flow around U.S. Treasury Auctions"
VEHICLE:   OANDA CFD USB10Y_USD (USB30Y_USD secondary)
```

*Measurement, not a recommendation. Not financial advice.*

## 0. The claim

Dealers must absorb new supply at each auction, so yields rise in the hours
before the 13:00 ET bid deadline and fall back afterwards: an inverted V.
SR1188 (1991–2024) measures **0.4–0.6 bp of yield up over the 180 minutes
before, and 0.3–0.75 bp down over the 180 minutes after**. On a 10-year note
(duration about 8), 1 bp of yield is about 8 bp of price.

**The paper itself shows decay:** after 2015 the effect is less than half its
earlier size. **Registered expectation: the pattern is present, and too
small to trade by 2019–26.**

**Overlap:** FLOWS-2 tested the quarterly refunding *announcement* (a Friday
drift). Auctions are a different, far more frequent event.

## 1. Step 0 — auction table (Mac, TreasuryDirect, frozen before any price)

- Every Note and Bond auction (5, 7, 10, 20 and 30 years; reopenings
  included; TIPS and FRNs excluded), 2005-01 → 2026-08. Fields: auction date,
  security term and the published closing time for competitive bids.
- Source: the TreasuryDirect auctioned-securities API. Frozen as
  `data/auction_events.csv` with its sha256.
- An **auction day** is a date with at least one such auction. Days with
  more than one auction count once, and the longest tenor is recorded.

## 2. Windows and return (USB10Y_USD M15 mid; ET, DST-aware)

- PRE: 10:00 → 13:00 ET (bars ending at those times). POST: 13:00 → 16:00
  ET.
- In the rare case the competitive close is not 13:00, the windows are
  anchored on the published close time, rounded down to a 15-minute bar end.
- **R = POST − PRE** in price terms. Yields rising then falling means the
  price falls then rises, so the claim predicts **R > 0**.

## 3. Gates

| gate | test | pass |
|---|---|---|
| **G1** | mean R over auction days | > 0, t ≥ 2.0 (Newey-West 5) |
| **G2** | E1, E2, E3 | > 0 in all three, **E3 ≥ 0.5 × full** |
| **G3** | PRE < 0 and POST > 0 separately | both signs right |
| **G4** | trade: short bid at 10:00, cover ask at 13:00; buy ask at 13:00, sell bid at 16:00 | mean net > 0, t ≥ 1.65, **E3 net > 0** |
| **G5** | placebo: same windows on non-auction weekdays | t < 2.0 and mean < mean R |

**Kills:** K1 is G1 failing, K2 is G2, K3 is G4, K4 is G5.

## 4. Secondary

- USB30Y_USD, with the same construction.
- Results by tenor.
- The multi-day concession from Lou et al.: close D−5 → close of the auction
  day D, and D → D+5, on USB10Y.

## 5. Power

About 1,000 auction days. PRE and POST are each about 15–20 bp standard
deviation, so the standard error of R is about 0.8 bp. **Anything above
about 2 bp is detectable.** Two round trips at about 1.5–2 bp each set the
trading bar.

## 6. Files

    flows/fetch_auctions.py  data/auction_events.csv  flows/auctions.py  flows/RESULT_AUCTIONS.md
