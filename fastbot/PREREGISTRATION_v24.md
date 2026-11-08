# PREREGISTRATION v24 — does the 30-minute signal bar survive new instruments?

```
WRITTEN:  2026-09-13, BEFORE a single bar of any new instrument has been
          fetched. No data existed when the gates below were fixed.
STATUS:   FROZEN
SUBJECT:  the claim that came out of the timeframe question -- deciding
          the fade at 09:00 instead of 08:45 lifts the Sharpe from 0.34
          to 0.54. Measured on ONE instrument, after looking at four
          variants, on the same 23 years that produced the idea.
DESIGN:   confirmation. The hypothesis, the statistic and the threshold
          are all fixed by prior work; only the data is new.
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.**

---

## 1. The claim, and the exact reason to doubt it

Discovery, on SPX500_USD, 2003-2026:

```
  A  15m signal, 1h hold        net +2.16 bp    Sharpe 0.34
  C  30m signal, 1h hold        net +4.32 bp    Sharpe 0.54
```

**The improvement is +0.20 Sharpe against a standard error of 0.21.**
Paired on the same events, C − A is **+2.69 bp at t = 1.63** — the
improvement itself is not significant, and it was selected as the best
of four variants after the fact.

One standard error is exactly what picking the maximum of four draws
buys you for free. **That is the null this run exists to test**, and the
only way to test it is data that did not exist when the variant was
chosen.

## 2. Why more SPX500 history cannot settle it

There isn't any. 2003-2026 is the whole series, and its held-out decade
was already spent confirming the 15-minute payrolls result in v23.
**A held-out set can only be spent once.** So the new axis is
instruments, not years.

## 3. The instruments, and what each one is for

Five, fetched at M15 with bid and ask, in three groups fixed now:

```
NEAR-CLONES -- an IMPLEMENTATION check, not evidence
  NAS100_USD   US equity index, same 09:30 ET open
  US30_USD     US equity index, same 09:30 ET open

CROSS-MARKET -- a MECHANISM test
  EUR_USD      24h FX, no equity open to correct into
  XAU_USD      24h metal, likewise

OFFSET -- an equity index already mid-session at 08:30 ET
  DE30_EUR     14:30 CET, its own cash market open for hours
```

**The near-clones are roughly 0.9 correlated with SPX500. Finding the
effect there is barely evidence — it is nearly the same data.** They are
carried as a positive control: a pipeline that cannot reproduce a
known-present effect on an almost-identical instrument is broken, and
Gate A says so before anything else is read.

**The cross-market pair is the interesting one**, because it separates
two explanations that fit the SPX result equally well:

```
  "information takes ~30 minutes to be absorbed"    -> should appear in FX and gold
  "the move is corrected when the equity open
   brings real participants at 09:30"               -> should NOT appear there
```

RESULT_PREMARKET §4 localised the SPX reversion to the crossing of the
09:30 open, and RESULT_PREMARKET §8's overshoot story was already
disconfirmed. **EUR_USD and XAU_USD have no 09:30 open.** Whichever way
they come out says something, which is why they are in.

## 4. The construction, frozen

Identical to the discovery run, imported not retyped:

```
releases     CPI and payrolls at 08:30 ET, from events_v2.csv
             CLAIMS EXCLUDED -- a discovery-derived choice, declared:
             claims gross +0.36 bp on variant C against its own cost
signal A     the 08:30-08:45 bar    entry 08:45 open   exit 09:45 open
signal C     the 08:30-09:00 bar    entry 09:00 open   exit 10:00 open
statistic    gross bp from FADING = -sign(close - open) x (exit/entry - 1)
cost         each instrument's OWN round trip, measured from its bid and
             ask at the entry and exit bars. Never assumed, never
             borrowed from SPX500.
```

**Primary statistic: C − A, paired within instrument on the same
events.** Paired because A and C share the release, the day and most of
the window, so the difference is far better measured than either level;
and because the *difference* is precisely the claim.

An instrument needs **150 or more CPI+NFP events** to enter a gate.
Fewer and it is reported, not gated — and that floor is set here, before
the fetch reveals how deep OANDA's history goes.

## 5. The gates

**Gate A — positive control. It voids the run.**

```
PASS   NAS100_USD and US30_USD each show variant A's base effect
       (release fade gross > 0) at t >= 2.0
```

Not evidence. A check that the pipeline reproduces a known-present
effect on a near-identical instrument. **Failing it means the fetch, the
timestamps or the code is wrong, and nothing below is readable.**

**Gate B — the confirmation.**

```
PASS   C - A > 0 at t >= 2.0, paired, pooled across all five
```

**Gate C — the sharpest version of the same question.**

```
PASS   C - A > 0 at t >= 2.0 on the near-clones ALONE
```

The 30-minute-signal story, if true, should transfer most easily to two
instruments that are nearly the same market. **If it fails here it will
not pass anywhere**, and this is the gate I expect to decide the run.

**Gate D — the mechanism, reported and not gated.**

```
EUR_USD and XAU_USD, base effect and C - A, reported whatever they show
```

Registered as a discriminator, not a confirmation. A base effect in FX
and gold favours absorption; its absence favours the equity open.

**Gate E — cost, per instrument.**

```
PASS   variant C's net exceeds zero on the near-clones, using each
       instrument's own measured round trip
```

**Gate F — era. Each instrument split in half; C − A must not flip
sign.** Variant B failed exactly this on SPX500 (+5.44 then +10.97),
which is why B is not in this document.

## 6. Predictions, registered before the data exists

- **Gate A passes.** If it does not, I have a bug, not a finding.
- **Gate B fails.** I expect pooled C − A between −1 and +1.5 bp at
  t < 2.0.
- **Gate C fails**, and this is the one I hold most firmly. The
  improvement was +1 standard error on the sample that chose it.
- **Gate D: I expect the base effect to be present but weaker in FX and
  gold**, and C − A near zero there. Held loosely — my directional
  priors have been wrong in five of the last nine registered
  predictions, including two sign errors.
- **Gate E is not the binding constraint this time.** EUR_USD in
  particular is cheaper than SPX500_USD, so cost is unlikely to be what
  kills this.

**What would change my mind: C − A at +2 bp or better, t >= 2.0, on the
near-clones alone, with the sign holding in both era halves.** That is
the outcome I am registering against, and it is the one worth having.

**If Gate C passes and Gate D shows nothing in FX and gold**, the
correct reading is that the effect is tied to the US equity open rather
than to information absorption — and the next step is more US index
instruments, not a position.

## 7. Kill conditions

- **One run.** No adding instruments after seeing a result, no swapping
  the primary to variant B or D, no moving the 150-event floor.
- **No sign flips.** Fade is positive, fixed in §4.
- **Cost is measured per instrument.** Borrowing SPX500's 1.77 bp would
  be assuming the answer to Gate E.
- **Any instrument whose bid equals ask** — the SPX500 pre-2012 failure —
  has unmeasurable cost and drops to sign-only reporting, automatically
  and not by judgement on the day.
- **A result above 30 bp is a bug until proven otherwise.**
- **The fetch is a separate step from the measurement**, and the
  measurement code is written against this document, not against a first
  look at the data.

## 8. What this cannot settle

**It cannot make the SPX500 result out-of-sample.** That sample is
spent. This asks whether the same rule works elsewhere, which is a
different and weaker question than whether it worked there.

**Five instruments is not five independent tests.** The near-clones are
nearly one, and all five reacted to the same 600-odd US releases on the
same days. The effective number of independent looks is closer to three.

**Investigation forty.** The first to fetch new data for a question that
was already asked, rather than to ask a new one.
