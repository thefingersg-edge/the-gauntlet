# PREREGISTRATION v12 — their window, verbatim

```
WRITTEN:  2026-09-04, after v11's two arms closed and after reading the
          paper's own window definition, and BEFORE any return on that
          window has been computed
STATUS:   FROZEN
SUBJECT:  the last remaining difference between +44.50 bp and +12.72 bp
          on the same twenty announcements
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.**

---

## 1. Why there is a v12 at all

v11 asked why Kurov's +44.5 bp disagreed with +0.36 bp. Both arms ran
and the question turned out to be built on a mis-statement of mine:

- **Arm 1** — the excluded 45 minutes, T−60m → T−15m: **−2.94 bp**. Not
  the explanation. It makes the gap marginally worse.
- **Arm 2** — the fourteen excluded 2011-2012 events, recovered from a
  sourced Fed press-conference list: **+29.00 bp**, closing 24.6%.
- **Then the paper itself** said the +44.5 was never comparable to what
  v11 compared it with. It is **press-conference announcements only**,
  20 of them, in **E-mini S&P 500 futures**, over a window running
  *"from the stock market open on the day before the announcement to 15
  minutes before the announcement."*

Recomputed on the correct set — the same 20 announcements, all 20
measurable — this project reads **+12.72 bp, SE 11.90**. Theirs sits
**+2.67 SE outside** that. So the disagreement is real and it is not a
subset artifact.

**One difference is left, and it has never been measured here.**

```
theirs   09:30 ET on D-1  ->  T - 15m
mine     T - 24h          ->  T - 1h
```

For a 14:00 release, theirs begins at 09:30 on D−1 and mine at 14:00 on
D−1. **Their window contains four and a half hours of D−1 morning that
mine has never seen.** The tail is already measured and is small. The
head is not.

## 2. Why this is not the sweep v11 forbade

v11 section 6 banned sweeping over window length, and that ban stands.
This is a different act:

**The window here is not chosen. It is transcribed.** It is the one
sentence quoted above, implemented literally. There is exactly one such
window, it was fixed by someone else years ago in a published paper, and
this document is written before it has been run.

The test of whether that distinction is honest is simple: **a sweep has
many candidate windows and reports the best; this has one and reports
it.** If the result is a null, it gets recorded as a null.

## 3. The measurement, frozen

> **WINDOW: from the OPEN of the 09:30 ET bar on D−1 to the CLOSE of the
> bar ending at T − 15 minutes, on M15 bars.**

- **Sample:** the 20 press-conference announcements of 2011-04 to
  2015-12, sourced per year from the Board's own calendars, whose count
  reproduces the paper's own "20 announcements."
- **Secondary:** the same window on the 30 non-press-conference
  announcements of 2011-04 to 2018-12, against their **−0.051%**.
- **Control:** the same clock window on non-event days, ±1 day of any
  event excluded — the construction RESULT_PREANN and v11 both used.
- **D−1** is the previous calendar day. Every announcement in the sample
  falls Tuesday to Thursday, so D−1 is always a trading day; an event
  whose D−1 has no 09:30 ET bar is dropped and counted, not shifted.

## 4. The prediction, registered before it runs

Lucca & Moench located the drift: the market *"rises slightly on the
afternoon of the day before"* and *"drifts sharply higher in the morning
of scheduled FOMC announcements, accumulating the bulk of returns."*
**The D−1 morning is not named in either clause.** It is ordinary
trading, and my window already contains the announcement-day morning
that is.

So:

- **the head is worth under 10 bp**, and
- **implementing their window in full still falls short of +44.5** —
  I expect to land near **+20 bp**, roughly halfway.

**If the head turns out to be worth 30 bp or more, I am wrong about
where the drift lives**, and that is a more interesting outcome than a
confirmation. It would also mean RESULT_PREANN's window was badly
placed, which is a cost worth paying to find out.

**If implementing their window exactly reproduces +44.5, I should be
suspicious rather than satisfied**, because arm 1 already showed the
tail is negative and arm 2 showed the sample correction is only worth
+11 — there would be nowhere left for 32 bp to come from except an
error.

## 5. Kill conditions

- **No bar at or after T−15m.** Checked per event; run void if violated.
- **The head must not silently become the whole window.** The 09:30 ET
  bar on D−1 must exist for every included event, and the bar count is
  reported per event rather than assumed.
- **Above 70 bp** on the primary sample → treated as the window having
  crept past T, per v10 section 6, and investigated before reporting.
- **One run.** If this needs a second window to say something, it is
  abandoned and recorded as abandoned.

## 6. What this can and cannot settle

**It can settle** whether the disagreement is about *when we measure* or
about *what we measure it on*. Those are the only two candidates left,
and after this run only one will be standing.

**It cannot settle the instrument.** E-mini S&P 500 futures are not
OANDA's SPX500_USD CFD, and nothing on this disk can turn one into the
other. If the residual survives a verbatim window on an identical
sample, the instrument is what remains — and that is an honest place to
stop rather than a failure.

**It changes nothing about RESULT_PREANN.** That verdict was FAIL on
Gate E and no window arithmetic touches whether the effect generalises
to CPI and payrolls.

## 7. Scoreboard

**Investigation twenty-eight.** The first to implement someone else's
specification rather than one of our own — and the first written after
discovering that the number being argued with had been misread for two
documents running.
