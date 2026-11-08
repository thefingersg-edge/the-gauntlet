# PREREGISTRATION v10 — the pre-announcement window

```
WRITTEN:  2026-08-29, after events.csv passed its coverage gate and
          BEFORE any price series has been joined to it
REVISED:  2026-08-29 (v10.1) -- the window in section 3 was replaced
          after checking WHERE in the published window the returns
          accrue. Still before any price join. See section 9.
STATUS:   FROZEN
SUBJECT:  equity returns in the trading day before scheduled US macro
          announcements, 1994-2026, and whether they track published
          uncertainty
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.**

---

## 1. The table this rests on

`events.csv`, built over five versions and gated against the known
schedule:

```
FOMC   280 events   1994-02-04 -> 2027-12-08
CPI    412 events   1994-01-13 -> 2026-08-29
NFP    400 events   1994-01-07 -> 2026-08-29
```

30 of 34 FOMC years at exactly 8; the four above are 2003, 2008, 2009 and
2010, which genuinely held unscheduled meetings. 2015 reproduces the true
schedule exactly. Minutes contamination 0 of 280, weekend dates 0.

**Every earlier version of that table looked fine in its output and was
wrong** — under-capture, over-capture, a silent six-year gap, a markup
assumption, and a page footer filed as a meeting. That is the moat, and it
is why this document comes now rather than five days ago.

## 2. Why this design, in one line

`FINDINGS.md` rule 4: a continuously held strategy needs 32 years of daily
data to resolve a Sharpe of 0.35. **The same data, read as an event study,
resolves a 14 basis point per-event effect.**

| | N (daily span) | SE of mean | 2σ effect |
|---|---|---|---|
| FOMC | ~264 | 6.8 bp | **13.5 bp** |
| CPI | ~396 | 5.5 bp | 11.1 bp |
| NFP | ~396 | 5.5 bp | 11.1 bp |

Those counts assume the full daily span. **§3 commits the measurement to
intraday bars, so the real N is whatever §9's probe returns** — at the
Gate C floor of 120 FOMC events the 2σ resolution is about 20 bp.

Lucca & Moench measured 49 bp. Kurov et al. measured 44.5 bp for
2011-2015 and 9.2 bp for 2016-2019. So the pre-2016 magnitude is
resolvable at better than 6σ and the post-2016 magnitude sits right at the
edge — which is the reason to condition rather than pool, not an excuse
found later.

## 3. The window, and the fork that had to be settled first

**Daily data cannot cleanly measure the published window.** Lucca &
Moench used 14:00 the day before to 14:00 on announcement day. With daily
bars that window straddles two sessions and, worse, includes the
announcement-day morning — so any daily approximation of it is
contaminated by the reaction it is supposed to precede.

So the primary window is not theirs:

### The first answer, and why it was wrong

v10.0 of this document chose **D−2 close → D−1 close** — the whole trading
day before announcement day — on the grounds that it is entirely
pre-announcement, works on daily bars, and uses one definition for all
three event types.

**That was a mistake, and it was caught before any price was joined.**
Lucca & Moench say where within their window the returns accrue:

> the SPX "rises **slightly** on the afternoon of the day before" but
> "drifts **sharply higher in the morning** of scheduled FOMC
> announcements, **accumulating the bulk of returns**"

The bulk lands between the 09:30 open and the 14:00 announcement. The
day-before window contains **none of it** — only the slight two-hour tail
of D−1, diluted by four and a half hours of ordinary trading.

**A window chosen for cleanliness that cannot see the effect is not a
cheap test. It is a wasted one**, and a null on it would have said nothing
about the phenomenon while looking like a clean negative on 264 events.

No daily window escapes this. `D open → D close` contains the
announcement and its reaction; `D−1 close → D open` is overnight only and
misses the morning. **The measurement requires intraday bars.**

### The frozen window

> **PRIMARY WINDOW: from T − 24 hours to T − 1 hour, where T is the
> release timestamp for that event, on M15 bars.**

- It reproduces the published construction. Lucca & Moench ended theirs
  "about fifteen minutes before the announcement release time"; ending a
  full hour early is **more** conservative and buys robustness against
  exactly the timestamp risk this project has already been wrong about
  five times on simpler things.
- It still contains the sharp morning segment, which is the whole point.
- It works for an 08:30 release as well as a 14:00 one, because OANDA's
  index CFDs trade nearly continuously — so one construction still serves
  all three event types.
- `events.csv` already carries the per-event release time and its quality
  flag, so T is read rather than assumed. **Rows flagged UNCERTAIN are
  excluded from the primary result and reported separately.**

**M15, not H1 — corrected 2026-08-29 after the probe, still before any
price join.** v10.1 specified H1, and H1 cannot express this window for
most of the table:

| release time | events | H1 aligned | M15 aligned |
|---|---|---|---|
| 08:30 (CPI, NFP) | 812 | **no** | yes |
| 14:15 (FOMC pre-2013) | 162 | **no** | yes |
| 14:00 (FOMC post-2013) | 118 | yes | yes |

T − 1 hour lands mid-bar on H1 for **974 of 1,092 events** — 89% of the
table. The window definition is unchanged; only the granularity able to
express it is corrected.

The cost of intraday is history. OANDA serves M1 and M5 from
**2003-03-21**, 23.4 years, so M15 is available at least that far back —
and §9's probe now confirms rather than infers it.

## 4. The prediction, registered in advance

I have read Kurov, Wolfe & Gilbert. Recording what that leads me to expect
**before** seeing any result, so that a match is evidence and a mismatch is
not quietly reinterpreted:

- the pooled effect is positive but **well under 49 bp**
- it is **concentrated before 2016**
- it **scales with VIX**, and the post-2015 decline largely disappears once
  VIX is conditioned on

**A uniform effect across all eras would contradict the published
explanation and should make me more suspicious, not less.** If the number
comes out the same in every era, the most likely cause is a bug in how the
window or the calendar is joined to prices, not a discovery.

## 5. The gates, frozen

**Gate A — is there anything there.**
Mean primary-window return on FOMC event days, **minus** the mean on all
non-event trading days.

```
PASS   t >= 2.0 on the difference
FAIL   otherwise
```

The subtraction is the gate. Equities drift up, so a positive mean on
event days alone means nothing; the control is the whole test.

**Gate B — disjoint eras.**
The span split into three equal, non-overlapping periods.

```
PASS   the excess is positive in ALL THREE
FAIL   otherwise
```

Nested windows are forbidden — `AUDIT.md` established that "positive in
full, 10y, 5y, 3y and 1y" can be one event counted five times.

**Gate C — enough to say anything.**

```
PASS   >= 120 FOMC events with complete H1 bars across the window and a
       time_quality that is not UNCERTAIN
FAIL   -> UNDETERMINED, and the price history is the binding constraint
```

120 rather than 200 because intraday history is shorter than daily, and
the number is set here, before §9's probe reports what the depth is. At
120 events the 2σ resolution is about 20 bp against a published 49 —
enough to see the effect if it is the size the literature says, and not
enough to resolve the 9 bp post-2019 regime. **That limit is accepted in
advance rather than discovered afterwards.**

**Gate D — the conditioning claim.**
Events split at the median VIX **as of the close before the window opens**
— strictly lagged, no exceptions.

```
PASS   high-VIX half exceeds low-VIX half, t >= 1.5 on the difference
FAIL   otherwise
```

1.5 rather than 2.0 because this is a second-order test on half the data
each side, and the threshold is set here rather than after seeing it.

**Gate E — does it generalise.**

```
PASS   at least 2 of {FOMC, CPI, NFP} show a positive excess
FAIL   otherwise
```

One published relationship on one event type is not a finding about
pre-announcement premia. This is the gate that asks whether the mechanism
is general or whether the FOMC is a special case.

## 6. Kill conditions, fixed now

- **Any lookahead.** VIX must be lagged to before the window opens; the
  D−1 return must not touch announcement day. If either is violated the
  run is void, not adjusted.
- **A result materially larger than 49 bp** — say above 70. The window is
  now nearly the published one, so a figure near 49 on the pre-2016 half
  is the expected outcome and not a triumph; a much larger one means the
  window has crept past T and is picking up the reaction. Treated as a bug
  until proven otherwise.
- **The window overlapping T.** If any bar in the window is stamped at or
  after the release time for that event, the run is void. This is the
  failure the whole intraday choice exposes the measurement to, and it is
  checked per event rather than assumed from the construction.
- **A uniform result across eras** (§4) — investigated as a defect before
  it is reported as a finding.
- **Fewer than 200 usable FOMC events** → UNDETERMINED. Not extended to
  more event types until it passes.
- **One run.** No sweeps over window length, no sign flips, no
  re-specification. If a gate needs changing to produce a result, the run
  is abandoned and recorded as abandoned.

## 7. What this cannot answer

**Whether it is tradeable.** Nothing here touches costs, and four of four
previous candidates died there rather than on the premium. A 14 bp effect
across 8 events a year is 1.1 points annually before a single commission,
and `FINDINGS.md` rule 2 says that is where this will most likely end.

**Why the effect exists.** A positive result is consistent with
compensation for holding risk into a scheduled uncertainty event, and also
with something entirely else. Gate D tests one prediction of the
uncertainty explanation; it does not establish it.

**Anything about a specific future announcement.** This is a measurement
of a historical average, and §4 already says the recent magnitude is the
smallest in the sample.

## 8. What each outcome means

| | |
|---|---|
| **A, B, C pass; D and E pass** | A general, state-dependent pre-announcement premium, measured on 1,000+ events. Then, and only then, the cost question. |
| **A, B, C pass; E fails** | The FOMC is a special case. Narrower and more fragile than the mechanism claims. |
| **A, B, C pass; D fails** | The effect exists but does not track VIX. Kurov's explanation would not hold, and an adaptive rule keyed to VIX has no basis. |
| **A fails** | No measurable pre-announcement premium in daily data on this window. Clean negative, on 1,000+ events, worth as much as a pass. |
| **C fails** | UNDETERMINED — the price history is the constraint, not the market. |

## 9. Precondition

**No price series has been joined to this table yet, and none should be
until its depth is probed.**

```
python3 pull_m1.py --probe --granularity H1 --instruments SPX500_USD,US30_USD,NAS100_USD
```

One request per instrument. It settles how far back OANDA serves hourly
bars, and therefore how many of the 280 FOMC events are measurable at all.

Gate C's 120 is written against that answer being **unknown**. If the
probe returns fewer than 120 usable events the result is UNDETERMINED and
the constraint is the data, not the market — which is a real outcome and
not a reason to widen the window until something passes.

### On revising a pre-registration

§3 records that v10.0's window was wrong and was replaced. **That is
legitimate only because no price has been joined yet.** The whole value of
this apparatus is that the specification is fixed before contact with the
data; a change made now costs nothing, and the same change made after
seeing a result would be worthless. Once §9's probe runs and prices are
joined, this document is closed.

## 10. Scoreboard

**Investigation twenty-six.** The first to use a design that escapes the
resolution floor, and the first in this project where a clean negative
would be as informative as a pass.
