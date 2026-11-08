# PREREGISTRATION v30 — does anyone call it, and does the crowd matter?

```
WRITTEN:  2026-09-25, before any positioning, sentiment or prediction-
          market figure has been fetched. No such data exists in the
          project.
STATUS:   FROZEN
SUBJECT:  Dave: "we are trying to find anyone with key insights that
          continually make good calls" -- measured with the free data
          that can speak to it
CODE:     sentiment_fetch.py 1.0 fetches (on Dave's machine; public data,
          no keys). premarket_sentiment.py 1.0 measures, written after the
          fetch against this document, having seen file FORMATS only.
CHANGES:  nothing in v25.
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.**

---

## 1. Why, and the prior

RESULT_PREANN and RESULT_KUROV found no price drift before CPI or
payrolls. If someone is positioned the right way before these releases,
it has not moved the price. That is the prior: this registration expects
nothing, and says so in section 6. It is run because the one place a
large, informed account could hide from a price test is in POSITIONS,
and positions are published.

## 2. The data, fixed now

```
CFTC Commitments of Traders, futures only (weekly, as of Tuesday,
published Friday)
  TFF      E-mini S&P 500 -> SPX500_USD   E-mini Nasdaq-100 -> NAS100_USD
           DJIA x$5       -> US30_USD      Euro FX           -> EUR_USD
           groups: Leveraged Money, Asset Manager
  Disagg.  Gold (COMEX)   -> XAU_USD       group: Managed Money
  DE30_EUR has no CFTC market and is out of this registration.

AAII weekly survey        bullish minus bearish, %
CBOE                      equity put/call ratio (archive ends 2019),
                          SKEW index (daily close)
Kalshi                    settled CPI and payrolls markets (KXCPI,
                          KXCPICORE, KXPAYROLLS, KXU3): the market's
                          implied call on the print before release
```

**No look-ahead, stated precisely.** A COT report is usable only if its
Friday publication (report date + 3 days) is BEFORE the release date.
AAII: the latest survey published before the release date. SKEW and
put/call: the close of the trading day before. Kalshi: the last price
before 08:30 ET on release day.

GDELT is out: its free search API covers three months, and its history
is terabytes of raw files. Polymarket is out: its CPI and payrolls
markets are too sparse to line up with releases. Both are named here so
their absence is a decision, not an oversight.

## 3. The trade and scale, unchanged

The release-bar move m and the fade at 09:45 exactly as v28 and v29,
sigma = SD of the instrument's prior 24 release-bar moves. Gate 0: every
fade equals v27's gross_H0 to 1e-6 bp, or the run is void. Errors
clustered by date. Samples: S1 CPI + payrolls (gated), S2 claims and S3
control (reported).

## 4. Question A — does anyone call the direction?

```
X  change in the group's net position (long - short) / open interest,
   from the second-latest usable report to the latest usable report --
   what the group DID in the week going into the release
   standardised by the SD of that change over the group's prior 52
   reports, strictly before
Y  m / sigma, the release-bar move in sigma units

model  Y = a + b X, pooled over the five instruments
```

```
G1  Leveraged Money (Managed Money for gold):  b > 0 at t >= 2.4
G2  Asset Managers (the four TFF markets only): b > 0 at t >= 2.4
```

One-sided on purpose: "makes good calls" means the group moved the way
the release then moved. A negative slope would be a group that is
reliably WRONG, which is interesting and is reported, but is not what
this gate asks.

## 5. Question B — does crowding change the bounce?

```
L  the Leveraged Money (gold: Managed Money) net / open interest,
   z-scored against its own prior 52 reports
A  sign(m) x L   positive when the release bar moved WITH the crowd,
                 negative when it moved AGAINST it
model  fade / sigma = a + b A
G3  b != 0 at |t| >= 2.4, two-sided
```

The forced-exit story predicts **b < 0**: a release that goes against a
crowded position forces exits, overshoots, and bounces more.

2.4 is Bonferroni for three gated looks.

## 6. Reported, gating nothing

- **AAII** bull-bear spread, **put/call** (5-day average, to 2019),
  **SKEW**: each against the release-bar direction and against the fade.
- **Kalshi, descriptive only.** From each settled release: the market's
  implied central estimate of the print just before release, whether it
  called the print's direction against the previous print, and whether
  the fade differs when the crowd was wrong. The history starts around
  2021-2023, so n is in the tens. **No verdict can come from it**, and
  the useful thing it does is start a record that the forward test can
  carry on.
- G1 and G2 on claims and control mornings.

## 7. Predictions, registered

- **G1 fails. G2 fails.** Twenty-three years of no pre-release drift say
  nobody is reliably positioned the right way; weekly positions are also
  far too coarse to catch it if they were.
- **G3 fails.** v28 and v29 found that nothing about the size or makeup
  of the move predicts the bounce; crowding is one more thing in that
  family.
- **Kalshi calls the direction of the print better than a coin** --
  well over half the time -- because forecasting a number is what those
  markets are for. Calling the print is not calling the market.
- **AAII, put/call and SKEW show nothing** at |t| >= 2 against direction
  or bounce.

## 8. Kill conditions

- **No other groups, lags or windows.** Dealers, non-reportables, a
  two-week change, a 26-week z-score -- each is a new registration.
- **The measurement script is written after the fetch**, against this
  document, having looked at column names and file layouts and at no
  value joined to a trade. If a source cannot supply a variable as
  defined, that is an amendment hashed BEFORE the measurement runs.
- **No rule changes.** v25 keeps running rule A.
- **The fetch is public data, read only, no keys and no accounts.**

---

**Investigation forty-six.**
