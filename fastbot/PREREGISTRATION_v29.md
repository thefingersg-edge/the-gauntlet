# PREREGISTRATION v29 — who showed up, and what did the release say?

```
WRITTEN:  2026-09-25, before any tick-volume figure or any release
          content (actual values, internals, surprises) has been
          computed or fetched for this project.
STATUS:   FROZEN
SUBJECT:  the two inputs 44 investigations never used -- participation
          in the release bar, and the content of the release
CODE:     Part 1  premarket_participation.py 1.0 (runs on data on disk)
          Part 2  release_content.py 1.0 fetches, premarket_content.py
                  1.0 measures. The content data does not exist yet.
CHANGES:  nothing in v25. Mechanism tests, not rule changes.
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.**

---

## 1. Why these two

v28 left a description with no explanation: a scheduled release moves
six markets and over the next hour a **roughly constant** amount comes
back -- `fade = +2.59 bp + 0.057 x |move|`, slope t 1.14 -- on release
mornings only. Five explanations are dead. Every one of them was tested
with price and a calendar. A bounce that ignores how far price went
might depend on **who traded** or on **what the number said**, and
neither has ever been measured.

## 2. Common to both parts

```
trade      rule A: fade the 08:30-08:45 ET bar, in at the 08:45 open,
           mid P&L at the 09:45 open (v22). Identical to v27's gross_H0.
samples    S1 CPI+payrolls  S2 claims only  S3 control mornings, as v27
instr.     the six. Before 2026-09-18 only: the forward sample is unseen.
sigma      SD of the instrument's prior 24 release-bar moves, same class,
           strictly before the morning (v28). No prior sigma -> dropped.
errors     clustered by date
Gate 0     every trade's fade must equal v27's gross_H0 to 1e-6 bp
           (v28.1's form). Any mismatch voids the run.
threshold  |t| >= 2.4 for every gate: Bonferroni for three gated looks
```

## 3. Part 1 — participation

```
V     tick count of the 08:30 bar (OANDA's volume column, bid file)
P     V / median(V of the instrument's prior 24 same-class events)
      strictly prior -- tick counts drift up over twenty years and
      this removes the drift without looking ahead
model fade/sigma = a + b x ln(P), per sample, six instruments pooled
```

```
G1  S1 CPI+payrolls   b != 0 at |t| >= 2.4  (two-sided -- see below)
G2  S2 claims         replication: SAME sign as G1's b, t >= 2.4 in that
                      direction. Evaluated only if G1 passes.
S3  control           reported with its t, interpretation only
```

**Two-sided because the stories disagree on the sign.** A bounce that
comes from quotes going stale in a thin book predicts b < 0 (fewer
participants, bigger bounce). A bounce from crowded, one-way flow that
unwinds predicts b > 0. The gate asks whether participation matters at
all; the sign says which.

**Reported, gating nothing:** thirds of P with mean fade in bp; the same
model in raw bp with instrument fixed effects (v28's ratio-bias
concern does not apply here -- P and sigma are different quantities --
but the raw form is shown so nobody has to take that on trust).

## 4. Part 2 — the content of the release

**Data, fixed now.** FRED/ALFRED real-time data, fetched by
`release_content.py` on Dave's machine: for each CPI and payrolls date
in events_v2.csv, the series **exactly as published on that day**
(realtime_start = realtime_end = the release date), last two
observations kept.

```
payrolls  PAYEMS (level)  UNRATE
CPI       CPIAUCSL (headline index, SA)  CPILFESL (core index, SA)
```

A release is **dropped and counted** if the latest observation in that
day's vintage is not the month the release reports (the month before
the release month). That check is what catches a vintage date that is
not a release date -- the 2026-09-12 Saturday row taught this project
that ALFRED dates and BLS dates are different claims.

**Definitions, fixed now.** "Surprise" here is a naive one: the print
against the median of that measure's previous 12 first prints. Real
consensus is not available; this proxy is weaker, which makes a PASS
harder, not easier.

```
payrolls  h = change in PAYEMS (first print) - median(prior 12 first-
              print changes)
          u = change in UNRATE as published that day
          MIXED  when the headline and unemployment tell opposite
                 stories: h > 0 and u > 0, or h < 0 and u < 0
          CLEAN  when they agree; either exactly zero -> neither
CPI       hh = headline m/m - median(prior 12 first-print headline m/m)
          cc = core m/m     - median(prior 12 first-print core m/m)
          MIXED  when hh and cc have opposite signs
          CLEAN  when they share a sign; either zero -> neither
```

**The hypothesis is digestion**: the first move reacts to the headline,
and when the internals say otherwise the market walks part of it back.

```
G3  S1: mean fade on MIXED releases - mean fade on CLEAN releases > 0
        at clustered t >= 2.4, six instruments pooled
```

**Reported, gating nothing:** payrolls and CPI separately; the fade
against |h| and |hh| (does it scale with the SURPRISE, when v28 says it
does not scale with the MOVE); the count dropped by the vintage check.

## 5. Predictions, registered

- **G1 fails.** Participation is a second-order property and v28 showed
  first-order ones do not move the bounce. If it passes, **b < 0**:
  thin books bounce more.
- **G2 is not reached.**
- **G3 passes, weakly.** Of everything left, digestion is the story the
  held-out data has been kindest to: the effect is release-specific,
  scales across release TYPES, and ignores the size of the move -- all
  things a headline-versus-internals disagreement would produce. I put
  this at better than even and not much better.
- **The dropped count in Part 2 is under 5%** of CPI and payrolls dates.

My registered predictions in this line: right about half the time, and
the last mechanism prediction was wrong.

## 6. Kill conditions

- **Part 2's definitions are frozen before any value is fetched.** If
  the fetch reveals that a series cannot supply them, that is an
  amendment written and hashed BEFORE the measurement runs, restricted
  so it cannot loosen G3.
- **No other internals.** Wages, revisions, participation rate, shelter,
  energy -- all tempting, all a new registration. Choosing the internal
  that works after seeing several is the fishing this line exists to
  avoid.
- **No rule changes.** A pass is a candidate for its own registration
  and an out-of-sample test. v25 keeps running rule A.
- **Keys stay on Dave's machine.** release_content.py reads a FRED API
  key from `$FRED_API_KEY` or `~/.fred_key`, never prints it, and the
  key is never pasted into chat or committed.

---

**Investigation forty-five.**
