# PREREGISTRATION FLOWS-9 — the index on mega-cap earnings announcements

```
WRITTEN:   2026-09-28, before any earnings date has been fetched or joined to a price.
STATUS:    FROZEN at its first commit; earnings.py pins this file's sha256.
SOURCE:    Savor & Wilson, "Earnings Announcements and Systematic Risk",
           Journal of Finance 71(1), 2016. Firms earn a premium around their
           earnings announcements, and the premium is linked to market risk.
VEHICLE:   OANDA CFD SPX500_USD (NAS100_USD secondary)
```

*Measurement, not a recommendation. Not financial advice.*

## 0. The claim, and why the index

US indices are now concentrated in a handful of firms. The earnings release
of a top-ten firm is therefore a market-level event, scheduled weeks ahead.
If announcement risk is priced, **holding the index across these releases
should earn more than holding it across other 24-hour windows**. No test in
the programme has used company earnings.

**Registered expectation:** low. A firm premium is diluted by its index
weight. At about 5% weight, even a 50 bp firm premium is about 2.5 bp on
the index.

## 1. Step 0 — the event table, built before any price is read

- **Universe, fixed ex ante each year.** For events from 1 April of year y
  to 31 March of year y+1, the universe is the **ten SEC registrants with the
  largest `dei:EntityPublicFloat` for the instant CY(y−1)Q2I**, from the SEC
  XBRL frames API. That is public float at 30 June y−1, as reported in
  10-Ks filed by early y. The first year used is the first frame with at
  least 500 filers. The universe table is frozen with its sha256.
- **Events.** Every 8-K filed by a universe firm with Item 2.02 (Results of
  Operations), with its EDGAR `acceptanceDateTime` converted to ET. Source:
  data.sec.gov/submissions (including the paged history files).
- **Window.** The anchor is the last 15:45 ET before acceptance, on an NYSE
  trading day. The window runs from that anchor to 15:45 ET on the next
  NYSE trading day. When several events fall in the same window, the window
  counts once.

## 2. Data and return

- SPX500_USD M15 bid/ask (fastbot/data/v24). r = mid close of the bar ending
  15:45 on the next trading day, over the mid close of the bar ending at the
  anchor, minus 1.
- **Controls:** every other consecutive 15:45 → 15:45 window in the sample.
- Sample: from the first universe year to 2026-08-31.

## 3. Primary

    r_w = a + b·EARN_w + g·MON_w + u          Newey-West (5 lags)

MON_w = 1 for windows spanning a weekend. The claim predicts **b > 0**.

## 4. Gates

| gate | test | pass |
|---|---|---|
| **G1** | b | > 0, t ≥ 2.0 |
| **G2** | b in E2 and E3 (E1 is only partly covered) | both > 0, **E3 ≥ 0.5 × full** |
| **G3** | trade: buy ask 15:45, sell bid 15:45 next day, one rollover of financing (Friday = 3 days) | mean net > 0, t ≥ 1.65, **E3 net > 0** |
| **G4** | size | ≥ 300 event windows |

**Kills:** K1 is G1 failing, K2 is G2, K3 is G3.

## 5. Secondary

- NAS100_USD, with the same construction.
- Pre-open announcers (acceptance before 09:30) compared with after-close
  ones (after 16:00).
- b by the firm's rank in the universe (top 3 against 4–10).

## 6. Power

About 600 windows. With a 24-hour standard deviation near 1.1%, the standard
error is about 4.5 bp, so **t = 2 needs about 9 bp**. The dilution argument
suggests the true figure is smaller.

## 7. Files

    flows/fetch_earnings.py  data/earnings_universe.csv  data/earnings_events.csv
    flows/earnings.py        flows/RESULT_EARNINGS.md
