# RESULT — the pre-announcement window

```
RUN:      2026-09-03
SPEC:     PREREGISTRATION_v10.1, frozen 2026-08-29 before any price
          was joined to events.csv
CODE:     preann.py v1.2
VERDICT:  FAIL  (Gate E)
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.**

---

## 1. The verdict, as pre-registered

```
event     N   mean bp   ctrl bp   excess      t
--------------------------------------------------
CPI     275      2.47      4.33    -1.86  -0.25
FOMC    168     29.17      4.69    24.48   3.10
NFP     272     -3.15      4.33    -7.48  -1.10

[PASS] Gate A  FOMC excess +24.48 bp, t = 3.10
[PASS] Gate B  eras +52.71  +1.96  +18.78
[PASS] Gate C  168 events (need 120)
[PASS] Gate D  high-VIX minus low-VIX +41.76 bp, t = 2.77 (median VIX 17.1)
[FAIL] Gate E  positive on 1 of 3: FOMC

    FAIL
```

Kill check — bars at or after T: **0 of 1,078**. The timezone conversion
held on both sides of every DST boundary in 23 years.

**Gate E is the verdict and it stands.** Two of the three event types are
negative. §8 of the pre-registration wrote this outcome down in advance:

> **A, B, C pass; E fails** → The FOMC is a special case. Narrower and
> more fragile than the mechanism claims.

That is what happened. The pre-announcement premium is not a general
property of scheduled macro announcements. CPI and payrolls pay nothing
before release; only the FOMC does. Whatever is being compensated, it is
specific to monetary policy, not to scheduled uncertainty as such.

## 2. Gate D passed, and the prediction was registered first

Before the gate ran, on the strength of the by-period table alone, I
wrote:

> The effect is large in the two crisis regimes and near zero in the two
> calm ones. So I expect Gate D to pass, and comfortably. If it doesn't,
> something is wrong with either my VIX join or that reading.

```
median VIX 17.12
  HIGH  n=84  mean +50.05  median +37.23  excess +45.36  positive 59/84
  LOW   n=84  mean  +8.29  median  +2.02  excess  +3.60  positive 48/84
```

The high half earns **fourteen times** the low half. Kurov, Wolfe &
Gilbert's explanation — that the drift did not decay from arbitrage but
from uncertainty falling — reproduces out of their sample, on a
different window, a different instrument and a longer span.

One number is worth pausing on. Lucca & Moench measured **49 bp**,
1994-2011, when average VIX was around 20 — almost entirely the high
half by today's median. The high-VIX half here reads **+50.05 bp**. That
is a closer match than this project has any right to expect, and it was
not aimed at: the window is 23 hours rather than 24, ends an hour early
rather than fifteen minutes, and covers 2003-2026.

## 3. A lookahead bug, found and fixed before the gate ran

`preann.py` v1.1 chose Gate D's VIX like this:

```python
vix.get(d - 1 day) or vix.get(d - 2) or vix.get(d - 3)
```

It preferred **D−1's close**. The window opens at T−24h — 14:00 ET on
D−1 for a 14:00 release. D−1's VIX prints at 16:15 ET. **That close is
two and a quarter hours inside the interval being measured.**

§5 says "the close before the window opens — strictly lagged, no
exceptions"; §6 voids the run on any lookahead. The spec was right and
the code did not implement it.

v1.2 computes the window-open date from each event's own release
timestamp and takes the latest VIX close **strictly before** it —
normally D−2, skipping holidays backwards, never forwards. The run
prints the realised lag distribution as evidence rather than asserting
it:

```
lag D-n: 2d x138  4d x30
```

138 two-day lags (the ordinary case) and 30 four-day (announcements
whose window opens on a Monday, reaching back across the weekend to
Friday). **No one-day lag appears, which is the thing that would mean a
peek.**

The self-test plants the failure. On a fixture where D−1's VIX is 14.0
and D−2's is 13.0, v1.1's rule selects 2015-06-16 — the window-open date
itself — and v1.2 selects 2015-06-15. Checked explicitly, because a gate
that can only fail in one direction has only been half tested:

```
window opens   2015-06-16  (14:00 ET on D-1)
v1.1 selected  2015-06-16 = 14.0   inside window: True
v1.2 selects   2015-06-15 = 13.0   inside window: False
```

**This was fixed before Gate D produced a number**, which is the only
time such a fix is worth anything. CPI, FOMC and NFP reproduce v1.1 to
the last decimal, so the change touched Gate D and nothing else.

Gate D also read `N/A` for a duller reason: there was no VIX file at
`data/VIXCLS.csv`. Two existed in other project folders. They agree on
**all 5,984 overlapping days with zero disagreements**, so they were
merged rather than chosen between — 1990-01-02 to 2026-08-31.

## 4. Is Gate D just the era pattern restated?

The high-VIX events cluster in 2008-2011 and 2020-2023. So the VIX split
and a crisis-era split could be the same fact wearing two hats. Splitting
**within** each four-year period, at that period's own median:

```
period       n   hi n   hi mean   lo mean     hi-lo
2004-2007   25     13     48.17     15.91    +32.27
2008-2011   33     17    133.55     -0.11   +133.66
2012-2015   23     12     -5.17      6.39    -11.56
2016-2019   32     16     20.74     -0.12    +20.86
2020-2023   31     16     71.33      1.43    +69.90
2024-2027   21     11     18.61     -1.97    +20.59
```

**Five of six**, including both calm regimes where the pooled effect
looked dead. 2016-2019 and 2024-2027 each pay about +20 bp to the higher
half of their own quiet distribution. VIX is doing work that a date
cannot do.

**This was not pre-registered.** It is reported as a caveat check, and it
is the kind that could only have weakened the claim — it did not.

## 5. The bid was the ask for nine years

The cost measurement was run at the actual entry and exit bars — buy the
ask at T−24h, sell the bid at T−1h — and returned this:

```
2004-2007  round trip  0.00 bp
2008-2011  round trip  0.00 bp
2012-2015  round trip  2.87 bp
```

A zero spread is not a cheap market. Checking every bar:

```
year       bars   zero-spread        median spread (nonzero)
2003      15274        100.0%              --
...
2011      23588        100.0%              --
2012      23321         15.8%            5.16 bp
2013      22907          0.0%            3.31 bp
...
2026      15699          0.0%            0.76 bp
```

**Every bar from 2003-03-21 to 2011-12-31 has bid exactly equal to ask.**
OANDA's early SPX500_USD history is back-filled index data, not dealt
quotes. Cost there is *unobservable*, not zero.

Two consequences, and the first one flattered the candidate:

- The zero-spread era holds most of the high-VIX events (2008-2011). So
  the first cost run reported high-VIX trading as **cheaper** than
  low-VIX — 0.66 bp against 1.51 — which is backwards for every real
  market and was purely this artifact. **A result that runs toward the
  thing being tested gets checked first.** This is the fifth time in this
  project that a data source has not been what its column names said.
- The single largest contributor to the headline number, 2008-2011 at
  +68.75 bp, comes from the era whose data is demonstrably not quote
  data. The *return* measurement survives that — an index series still
  measures the SPX move — but it cannot support any claim about
  tradeability.

## 6. What it is worth where cost is observable

2013 onward, 107 of 168 FOMC events, gross recomputed on the same
subsample so the comparison is like-for-like:

```
                 n    gross   net of spread   less financing    %/yr   Sharpe
all events     107   +11.07          +9.36            +8.23    +0.64     0.39
high VIX        54   +24.79         +23.46           +22.30    +0.88     0.63
low  VIX        53    -2.91          -5.00            -6.11    -0.24    -0.28
```

**Financing here is measured, not assumed** — updated 2026-09-04 from
OANDA's live `financing.longRate` for SPX500_USD (−6.15%/yr for a long,
+1.15% for a short, so a 3.65% reference with a ±2.50% half-spread),
applied per event at the 3-month bill in force that year rather than a
flat rate. It runs 0.64 bp/event in the ZIRP years to 1.84 bp in
2024-2027, averaging 1.14. The earlier 1.64 bp estimate was
conservative, and correcting it moves the candidate up by 0.02%/yr.

Conditioning is what makes it a strategy rather than a coin flip: it
drops the half that loses money. On the high-VIX half, t = 2.29 against
the control mean, 35 of 54 positive, and — unlike the pooled result —
**the median (+26.32) sits on top of the mean (+26.51)**, so this half is
not tail-carried.

The within-period split holds here too, net of measured spread:

```
2012-2015  hi  -8.02   lo  +3.50   -11.52
2016-2019  hi +18.34   lo  -2.31   +20.65
2020-2023  hi +70.37   lo  +0.59   +69.79
2024-2027  hi +17.91   lo  -2.67   +20.59
```

**And here is the finding that has no precedent in this project: cost did
not kill it.** Spread and financing together come to 2.49 bp against a
24.79 bp gross edge — **10.0% of it**, both sides now measured rather
than estimated. Four of four previous candidates died on access or cost.
This one did not.

What did it die of instead is Gate E: it does not generalise.

## 7. What is still not measured

**Financing has now been measured** (2026-09-04, `oanda_financing.py`),
and the correction was small and in the candidate's favour: 1.14 bp/event
against the 1.64 assumed. Two things came out of doing it properly.

The first is a correction to me. I built the tool around the claim that
**Wednesday** carries the weekend's triple charge — the FX convention —
and wrote that a Thursday announcement would therefore roll over on a
Wednesday and pay three days. OANDA charges the triple on **Friday** for
this instrument. FOMC announcements fall Tuesday to Thursday, so D−1 is
Monday, Tuesday or Wednesday and **never Friday**: all 160 events pay
exactly one day. The guard is correct and reads the table from the API
rather than assuming it, but the mechanism I said was hiding inside a
flat number is not present in this event set at all.

The second is the remaining assumption, and it is now the only one: the
**markup** (+2.28%/yr over the 3-month bill) is measured once, today,
and applied across 2004-2026. The benchmark varies per event; the markup
does not. At ~1 bp/event against a 25 bp gross, no plausible drift in
that markup changes anything here — but it is an assumption and it is
the last one in this table.

**Concentration still bites.** Dropping the five best of 54 events takes
+0.86%/yr to +0.26%/yr and Sharpe 0.62 to 0.26. The two largest are
2020-04-29 (+226 bp) and 2022-03-16 (+203 bp) — the pandemic response and
the first hike of the 2022 cycle. A high-VIX rule holds equity risk into
exactly those meetings, which is the point and also the risk.

**The Kurov discrepancy is unresolved.** He measured +44.5 bp for
2011-2015; the 2012-2015 bucket here reads +0.36. The most likely
explanation is that this window ends a **full hour** before release and
his ends fifteen minutes before, so the last 45 minutes — which is where
a drift into an announcement would concentrate — is excluded by
construction. Going to measure that now, having seen this result, is the
re-specification the whole apparatus exists to prevent. It is available
as a separately pre-registered question and nothing else.

**Sharpe 0.62 on 13.7 years is 2.3σ from zero.** `FINDINGS.md` rule 4
applies to the conclusion as much as to the design: this is at the edge
of what the span can resolve, and it is one instrument, one event type,
one venue.

## 8. Where this leaves the project

| | |
|---|---|
| Pre-registered verdict | **FAIL** — the mechanism does not generalise |
| The FOMC component | real, VIX-conditional, and confirmed within period |
| Cost | **~8% of gross** — the first candidate not killed here |
| Honest expectation | ~0.9%/yr unlevered, Sharpe ~0.6, 4 trades a year |
| Biggest open risk | 54 events, five of which carry half of it |

Dave's question was whether we were too late for any money or only for
the initial profit. The answer this measurement gives: **neither, and
also not much.** The premium is still there, it is still paid, and it is
paid only when uncertainty is high — but on the era where it can honestly
be costed, it is worth under a point a year on an unlevered position, and
it pays that for holding equity risk into the meetings nobody wants to
hold it into.

That is a real thing rather than a signal in a chart, which is what
`FINDINGS.md` rule 3 said would survive. It is also small, and the gate
that was designed to ask "is this general" answered no.

---

**Investigation twenty-six.** The first with a pre-registered clean
result on both sides — a failed generality gate and a passed
conditioning gate — and the first where the killer was not cost.
