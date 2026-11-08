# PREREGISTRATION v32 — does a bigger surprise mean a bigger bounce?

```
WRITTEN:  2026-09-25, before the claims-surprise figures below exist and
          before any forward event has been recorded with a surprise.
STATUS:   FROZEN
SUBJECT:  the one recurring lead from v29 and v31 -- the bounce looked
          bigger when the release SURPRISED more (CPI naive surprise,
          t +2.15; ADP miss, t +2.90; both without 2020-21, both
          ungated, both on samples already seen) -- while v28 showed it
          does NOT grow with the size of the PRICE move
CODE:     Part A  premarket_surprise.py 1.0
          Part B  forward_surprise.py 1.0, run by forward_tick.sh
CHANGES:  nothing in v25. forward_surprise.py writes its OWN file and a
          failure in it cannot halt or alter the v25 ledger.
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.**

---

## 1. Why this is tradable if it is real

The print is public at 08:30 and rule A enters at 08:45. A surprise
measured FROM THE PRINT is therefore known at entry. A rule that fades
only when the print surprised is implementable -- this is not a
hindsight variable. That is why the lead is worth an honest test.

## 2. Part A — a sample nobody has looked at: weekly claims

Claims-only mornings (S2, 2009-2026) have never been examined for this
question. The claims print is known at 08:30.

```
surprise  s = print - mean(the four weeks published the day before)
          from data/v31/vintages.csv, as published. A "release" whose
          day-of vintage carries no new week is dropped (v31 found 8).
scale     z = s / SD(s over all usable claims releases)
model     fade/sigma = a + b |z|, six instruments pooled, clustered by
          date, sigma and Gate 0 exactly as v28-v31
```

**The pandemic is decided now, not after.** v31 showed that 2020's
claims (millions, against a norm of hundreds of thousands) take over any
scale fitted on the full sample. So:

```
PRIMARY    2020-03-01 .. 2021-12-31 excluded, |z| capped at 3
REPORTED   all dates, uncapped
```

```
GA  b > 0 at t >= 2.0    one look, one-sided: the hypothesis says bigger
```

## 3. Part B — CPI and payrolls, forward only

Those samples are spent for this question. From the first forward event
(payrolls, 2026-10-02) forward_surprise.py records, for each CPI and
payrolls release, beside -- never inside -- the v25 ledger:

```
naive surprise   CPI headline m/m and payrolls change, first print,
                 minus the median of the previous 12 first prints (v29)
crowd surprise   first print minus Kalshi's implied median, from the
                 last hourly price before the market closes at 08:25 ET
                 (v30's method), scaled by that series' median miss over
                 its Kalshi history
```

```
GB  fade (v25 ledger, six instruments) / sigma = a + b |naive z|
    b > 0 at t >= 2.0, the naive surprise PRIMARY, crowd reported
horizon  150 CPI + payrolls release dates recorded, or 2032-09-30
interim  31 January each year, verdict-free, stop only at |t| >= 3.5
```

**How long that takes, said plainly.** The historical hints are a gap of
about 6 bp between big- and small-surprise releases. With the release-day
spread of the fade, telling that from zero at t = 2 needs roughly 150
release dates -- about six years. Part A answers faster because claims
come weekly.

## 4. Predictions, registered

- **GA fails.** The claims-day bounce itself is small (+0.86 bp gross in
  v27), leaving little for a surprise to scale. If it passes, it is the
  first pre-registered positive in the mechanism hunt.
- **GB cannot be called for years.** No prediction on its outcome; the
  prediction is that the first 31 January look (2027) shows nothing
  decisive either way.

## 5. Kill conditions

- **One surprise definition per release**, fixed above. Not the change
  against last week, not a 12-week median, not unemployment instead of
  payrolls.
- **The pandemic rule is fixed above**, both ways reported.
- **Part B never alters the v25 ledger** and is never backfilled.
- **The key stays on Dave's machine.**

---

**Investigation forty-eight.**
