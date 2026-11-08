# PREREGISTRATION v27 — how far does it run, and is it the release at all?

```
WRITTEN:  2026-09-25, after RESULT_PATHS (v26) and before any mark
          beyond 15:45 ET has been computed on any sample. No overnight
          or multi-day figure for this rule exists anywhere yet.
STATUS:   FROZEN
SUBJECT:  the release fade held for 1 and 2 days, and whether the drift
          after 09:45 is about releases at all
CODE:     premarket_horizon.py 1.0, written against this document
CHANGES:  nothing in v25. The forward test runs rule A, one hour, as
          registered. Claims stays out of the strategy.
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.**

---

## 1. Why, and what is already spent

v26.1 measured the drift after the 09:45 exit on CPI and payrolls:
+4.32 bp more by 15:45 at t = 1.76, against a bar of 2.0 set beforehand.
It failed. The shape table was then read, so **that sample is spent for
horizon questions** -- any horizon chosen on it now is chosen with
hindsight.

Dave asks the obvious next thing: *"can you review it at longer periods,
1 day, 2 days, to see if the bars went in the right direction."*

It is a fair question and it cannot be answered honestly on the same
events. This registration answers it on **two samples that have never
been used for it**, and adds the control that decides whether any of
this has to do with releases.

## 2. The trade, unchanged

```
signal   the 08:30-08:45 ET bar, mid open against mid close
         FADE: close > open -> short, close < open -> long, equal -> none
entry    the open of the 08:45 bar
```

Only the EXIT changes across horizons. Nothing else.

## 3. The three samples, fixed now

```
S1  CPI + payrolls     the v26 sample, 2005-2026.  DESCRIPTIVE ONLY --
                       declared spent above. No gate reads it.
S2  CLAIMS only        845 dates, 2009-2026, weekly, at the same 08:30
                       slot. Dates that also carry CPI or payrolls are
                       excluded (they belong to S1). GATED.
S3  CONTROL mornings   every other trading morning with an 08:30 bar and
                       no CPI, payrolls or claims in the table. GATED.
```

**S3 is not "no news".** PPI, retail sales, GDP and others also print at
08:30 and are not in the event table. S3 means "none of the three
releases this project tracks", and that is exactly what makes it the
right control for the claim *this drift is a release effect*.

Instruments: SPX500_USD, NAS100_USD, US30_USD, DE30_EUR, EUR_USD,
XAU_USD. An instrument with fewer than 150 usable events in a sample is
reported and not pooled.

## 4. The horizons, fixed now. No others are computed.

```
H0   the 09:45 open, same day        rule A's exit, the baseline
H1   the 15:45 open, same day        the last cash-session open
H2   the 15:45 open, +1 trading day
H3   the 15:45 open, +2 trading days
```

"Trading day" means the next dates on which that instrument has a 15:45
ET bar, within 5 calendar days. A holiday or a half day drops that
horizon for that trade and is counted.

## 5. Financing, because H2 and H3 cross the rollover

Dave's standing requirement is profit after costs **and financing**. H0
and H1 pay none. H2 and H3 do, at OANDA's measured rates
(oanda_financing.json, SPX500_USD, live, fetched 2026-09-04):

```
long    -6.15%/yr charged      = -1.685 bp per day charged
short   +1.15%/yr credited     = +0.315 bp per day credited
days    OANDA's own count: Friday counts 3, Saturday and Sunday 0
```

**These are today's rates applied to twenty years, and that is an
assumption, not a measurement.** It is stated here, it is applied
identically to every sample, and **every net figure is also reported at
twice the financing charge** so the reader can see what it would take to
matter.

## 6. What is measured, per sample per horizon

```
gross bp (mid)   share positive   SD   net of spread   net of spread and
                                                       financing
increment vs H0, with standard errors clustered by date
```

Plus two diagnostics that must be reported with any positive result:

```
direction split        share of trades that are long
market move            the mean UNSIGNED move over the same window
```

**A multi-day horizon is exposed to ordinary market drift.** If the fade
is short more often than long, a rising market makes it look worse, and
if it is long more often, better. The split and the market move make
that visible, and S3 tests it directly.

## 7. Gates

```
G1  CLAIMS      increment H0 -> H2 (+1 day) > 0, clustered t >= 2.0,
                same sign in both halves, AND net of spread and
                financing at H2 > 0
G2  CONTROL     the same increment on control mornings, reported with
                its t. This gate decides INTERPRETATION, not pass/fail:
                  positive at t >= 2.0  -> the drift is NOT a release
                                           effect. It is a general
                                           morning pattern, and the whole
                                           event-calendar frame is wrong.
                  flat                  -> the drift, if real, is linked
                                           to the release.
```

G1 is one look at 2.0. **If G1 fails, the 1-day and 2-day hold is
finished as a claim**, whatever S1's descriptive numbers say.

## 8. Predictions, registered

- **G1 fails.** The claims increment to +1 day lands within 3 bp of zero
  at t < 2.
- **S1 (descriptive) is positive to +1 day** -- it would be odd for the
  same-day drift to stop dead at 16:00 -- but smaller per day than the
  intraday leg, and it will not survive financing on the long side.
- **G2's control is positive but small**, under 3 bp, because a
  multi-day window mostly measures the market, not the rule.
- **The share positive stays between 50% and 55% at every horizon.**
  Bigger winners, not more of them: that is what v26 showed intraday and
  I expect it to hold.

My registered predictions in this line have been wrong about half the
time, and the last one was wrong in Dave's favour.

## 9. Kill conditions

- **The horizons are the four in section 4.** No fifth is computed, and
  no best-of is reported. Picking the horizon after the fact is what
  spent S1.
- **S1 decides nothing.** It is printed because Dave asked what the
  numbers look like; a gate that reads it would be a gate on hindsight.
- **Claims does not re-enter the strategy.** v22 measured it at +0.59 bp
  gross against a 1.77 bp spread. It is a sample here, not a trade.
- **Nothing changes in v25.** If G1 passes, the next step is a
  registration of its own and a forward test, not an edit to the running
  one.
- **History is never recomputed.** This run writes its own file.

---

**Investigation forty-three.**
