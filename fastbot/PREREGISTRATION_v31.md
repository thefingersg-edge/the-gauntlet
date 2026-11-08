# PREREGISTRATION v31 — can public data call the market move before 08:30?

```
WRITTEN:  2026-09-25, before any petrol, ADP, claims or market-backdrop
          series has been fetched for this project.
STATUS:   FROZEN
SUBJECT:  Dave: petrol is known before CPI -- "could we use that as a
          pre-empt to CPI direction? ... any other pieces of data that
          would help with the other events?" Free data only, by his
          decision: no paid sources.
CODE:     fred_fetch_v31.py 1.0 fetches (Dave's machine, his FRED key,
          never printed). premarket_public.py 1.0 measures, written after
          the fetch against this document, having seen FORMATS only.
CHANGES:  nothing in v25.
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.**

---

## 1. The distinction this registration is built on

Calling the PRINT and calling the MARKET are different targets. Kalshi
called the direction of headline CPI 35 times out of 36 (v30), which
means the market already knows what petrol says. The 08:30 move is the
reaction to what it did NOT know. A public predictor can only be traded
if the market UNDER-USES it -- which has been documented for economists'
consensus forecasts, and has to be measured here, not assumed.

So every predictor gets the same three questions:

```
Q1  does it call the PRINT?          a positive control -- it should
Q2  does it call the 08:30 MOVE?     the only one that could pay. GATED.
Q3  does it change the bounce?       reported
```

## 2. The predictors, fixed now

**CPI -- petrol.** EIA weekly US regular retail petrol (FRED GASREGW),
current vintage; it is a market price and is not materially revised.
For a CPI release reporting month M:

```
g(M)  ln(mean petrol in M) - ln(mean petrol in M-1)
P     g(M) - g(M-1)       the ACCELERATION: what petrol says about this
                          month's headline m/m against last month's
```

Q1 target: headline m/m(M) - m/m(M-1), first prints (release_content.csv
from v29). The m/m is from seasonally adjusted CPI and petrol is not
seasonally adjusted; using the acceleration removes most of that, not
all of it, and the positive control will show how much is left.

**Payrolls -- ADP.** ADP private payrolls (FRED NPPTTL), **as published
the day before the payrolls release** (realtime = release date - 1).

```
A     ADP change for month M - median(the previous 12 as-published changes)
```

If NPPTTL has no real-time vintages, **Q2 for payrolls is reported as
not measurable.** It is NOT replaced with revised data: ADP's history
was rebuilt in 2022, and the revised series knows things the market
did not.

Q1 target: the payrolls headline surprise h from v29.

**Claims -- their own trend.** Initial claims (FRED ICSA), as published
the day before each claims release:

```
C     last published week - mean of the four weeks before it
```

Q1 target: the release's own print minus the last published week, first
print, from the same fetch on the release day.

## 3. The trade and the scale, unchanged

m (the 08:30-08:45 move), the fade at 09:45, sigma = SD of the prior 24
release-bar moves, exactly as v28-v30. Gate 0: every fade equals v27's
gross_H0 to 1e-6 bp. Six instruments, clustered by date, forward sample
excluded. Predictors are z-scored against their own full-sample SD --
scaling does not change a t.

## 4. Gates

```
G1  CPI:      move/sigma = a + b P        pooled six instruments
G2  payrolls: move/sigma = a + b A        pooled six instruments
G3  claims:   move/sigma = a + b C        pooled six instruments
each: b != 0 at |t| >= 2.4, two-sided
```

**Two-sided because the sign of the market's reaction has flipped
across these twenty years.** Hot inflation was harmless to equities in
2010-2019 and brutal in 2022; good jobs news has been good news and bad
news. A gate that fixed the sign would be a gate on one regime.

2.4 is Bonferroni for three gated looks.

## 5. Reported, gating nothing

- Q1 for each predictor, with its t -- the positive controls.
- Q3: fade/sigma on |predictor|.
- Q2 per instrument, and split 2005-2015 / 2016-2026, **because a
  two-sided pass whose sign flips between halves is a regime, not an
  edge**, and it will be read that way.
- **Market backdrop, against direction and bounce on all three release
  types:** VIX close the day before (VIXCLS, on disk), the 2-year yield's
  change over the 5 days before (DGS2), the broad dollar's change over
  the 5 days before (DTWEXBGS, from 2006), and the instrument's own
  return over the day before (from our bars).

## 6. Predictions, registered

- **Q1 passes for CPI** (petrol calls the print) and **is weak for
  payrolls and claims** -- ADP is a poor guide to payrolls, and claims
  trend but noisily.
- **G1, G2 and G3 all fail.** The information is public and the market
  has it. v30's Kalshi number is the evidence: the crowd already knows
  what petrol says.
- **No backdrop variable clears |t| = 2.** Pre-release drift and the VIX
  regime were already tested in v10-v13 and found nothing for CPI and
  payrolls.

## 7. Kill conditions

- **No other transformations.** Not the level of petrol instead of its
  acceleration, not a three-month change, not oil instead of petrol --
  each is a new registration.
- **Revised data never stands in for as-published data.**
- **The measurement script is written after the fetch**, having seen
  column names and layouts, and no value joined to a trade.
- **No rule changes.** v25 keeps running rule A.
- **The key stays on Dave's machine.**

---

**Investigation forty-seven.**
