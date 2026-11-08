# PREREGISTRATION v23 — does the payrolls reversion reproduce out of sample?

```
WRITTEN:  2026-09-12, before any forward return has been computed on a
          pre-2013 pre-market bar
STATUS:   FROZEN
SUBJECT:  one question. STRATEGY_PREMARKET_FADE section 3 argues the
          payrolls stratum is the maximum of four noise draws. A
          held-out sample decides it.
DESIGN:   confirmation, not discovery. The hypothesis, the sample, the
          statistic and the threshold were all fixed by prior work.
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.**

---

## 1. The single question

v22's registered breakdown produced one positive line:

```
  NFP   n=162   gross +4.55 bp   net +2.78 bp   Sharpe +0.29 +/- 0.27
```

v22 §5 said in advance what that means: **a stratum passing when the
pooled result failed is a finding needing its own confirmation run, and
is not this run's result.** This is that run.

## 2. The held-out sample, and why it is legitimately held out

```
SPX500_USD M15, the 08:30 ET bar, 2003-01-01 .. 2012-12-31
  ~120 payrolls releases, never used for this question
```

v22 started in 2013 because **every bar before 2012 has bid exactly
equal to ask** — so the *cost* axis does not exist there. That is a
reason to exclude those years from a cost measurement. **It is not a
reason to exclude them from a sign measurement**, and RESULT_PREANN set
exactly this precedent: it measured drift across 2003-2026 and
restricted only the cost analysis to 2013+.

The old bars are not flat back-fill. They respond at 08:30:

```
  median release-bar |move|   2003-2012   16.44 bp
                              2013-2026    7.87 bp
```

**No cost is computed in this run and none is claimed.** The output is a
gross figure. If the sign does not reproduce, cost is irrelevant; if it
does, cost has already been measured in the modern sample.

**Two features of this window are named in advance and not excluded.**
It contains 2008, where the median 08:30 move was 50.95 bp, and the
whole decade is a higher-volatility regime. Removing the crisis after
seeing the result would be selection. Gate C handles it by requiring
both halves to agree.

## 3. The construction — identical to v22, deliberately

Same code path, imported rather than retyped:

```
signal bar   the 08:30-08:45 ET bar on a payrolls release date
direction    FADE:  close > open -> short,  close < open -> long
entry        the MID OPEN of the 08:45 bar
exit         the MID CLOSE of the 09:45 bar   (H = 4)
statistic    gross fade return in bp = -cont_bp
```

**Nothing is re-derived.** `cont_bp`, `load_events` and the test
statistics are imported from `premarket_event.py`, which has its own
self-test. A confirmation that reimplements the thing it is confirming
is testing two things at once.

## 4. The gates

**Gate A — the positive control, and it can void the run.**

```
PASS   payrolls bars move further than same-slot non-release bars,
       t >= 5.0
```

Here this does double duty. It is the usual control, and it is the only
check that **the pre-2012 series responds to news at all.** If a
back-filled mid series does not move on payrolls, this is not a sample
and the run is void rather than negative.

**Gate B — the confirmation.**

```
PASS   payrolls gross fade >= +2.0 bp at t >= 2.0
```

The modern estimate is +4.55 bp. A real effect should land in that
neighbourhood; **+2.0 bp is set as the bar because half the modern
estimate is the least that could still be called a reproduction.**

**Gate C — sign stability across the held-out window.**

```
PASS   positive in BOTH halves, 2003-2007 and 2008-2012
```

**Gate D — CPI, reported and not gated.** The modern CPI stratum was
+2.18 bp at t = 1.08. It is carried as context, and it is not a second
chance: **a CPI pass with an NFP failure is not a confirmation of
anything.**

## 5. Prediction, registered before the run

**Gate B fails.** I expect the payrolls gross figure to land between −2
and +2 bp with an unstable sign across the two halves.

The reasoning is the one in STRATEGY §3: payrolls sits at +1.07 of its
own standard error and claims at −1.07, either side of zero, against an
expected extreme of 1.03 for four draws from noise. **If that reading is
right, held-out data has no reason to reproduce it.**

**If payrolls comes back at +4 bp or better on ~120 held-out events, I
am wrong about this being selection**, and the correct response is not
celebration but the second confirmation in STRATEGY §5b — other
instruments, real quotes, fetched fresh.

## 6. Kill conditions

- **One run.** No changing H, the slot, the window or the stratum.
- **No sign flips.** Fade is positive, fixed in §3.
- **The crisis stays in.** So does every other year in the window.
- **A result above 30 bp is a bug until proven otherwise.**
- **Gate A failing voids the run** and means the old series cannot
  answer the question, which is a finding about the data rather than
  about the market.

**Investigation thirty-nine.** The first confirmation run in the
project — every previous investigation asked a new question, and this
one only asks whether the last answer was real.
