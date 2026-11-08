# PREREGISTRATION v22 — does volatility whose cause is KNOWN carry a sign?

```
WRITTEN:  2026-09-12, after an availability-and-cost precondition check
          and BEFORE any forward return has been computed on a
          pre-market bar
STATUS:   FROZEN
SUBJECT:  RESULT_VOLCAUSE section 5. v21 asked whether the cause of
          volatility carries a sign and answered with proxies, because
          the one cell where the cause is KNOWN held 108 observations.
          This is that cell, properly populated.
ORIGIN:   the named follow-up of a null, not a new idea
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.**

---

## 1. Why v21 could not answer its own question

v21 split volatility by spread and tick volume and found nothing: every
cell of its 2×2 within 0.42 bp, |t| ≤ 1.6, on 84,163 bars. Its positive
control fired at t = 46.9, so the null was readable.

But spread and volume are **proxies for the cause**. The event table is
the only **instrument** — a bar where information provably arrived. v21
had 108 such bars, because it sampled RTH only and **CPI, payrolls and
claims all release at 08:30 ET, an hour before the 09:30 open.** Only
FOMC at 14:00 landed inside the window.

```
v21 event cell      n =   108      cont +1.19 bp   t +0.20
this arm            n = 1,059      -- the same question, 10x the sample
```

## 2. Precondition check — availability and cost only

Counts, bar availability and unconditional spread. **No forward return,
and deliberately not the positive control's own statistic**: looking at
volatility-on-event-days before the spec is frozen is how a one-shot run
stops being one.

**Pre-market bars exist and carry real quotes.**

```
SPX500_USD M15, 2013+          bars    med spread   p90    bid==ask   med vol
  08:00                        3,523      1.66 bp   3.07      0.0%       259
  08:30   <- the release bar    3,523      1.66 bp   3.05      0.0%       406
  08:45   <- the entry bar      3,524      1.66 bp   3.03      0.0%       299
  09:30   <- the RTH open       3,521      1.64 bp   2.95      0.0%     1,804
  11:00                        3,521      1.63 bp   2.91      0.0%       797
```

**The finding that changes the prediction: cost does not widen
pre-market.**

```
RTH   median spread 1.63 bp   n = 90,152
PRE   median spread 1.67 bp   n = 77,449      ratio 1.02x
```

I expected the pre-market spread to be the obvious killer and wrote as
much before measuring it. **It is 2% wider than midday, not 200%.**
Activity is genuinely thinner — 406 ticks against 1,804 at the open —
but OANDA does not charge for it in the spread. So for the first time in
this project the cost gate is not stacked against the candidate before
the run starts, and a continuation of ~3.3 bp would clear it.

Two consequences, both registered now:

- **This is the strongest-positioned candidate so far**, and I should be
  correspondingly more suspicious of a positive result, not less.
- **It weakens v21 retrospectively.** v21 read `corr(spread, range) =
  +0.001` as "the liquidity axis is orthogonal to the volatility axis".
  A spread that barely moves across the day correlates with nothing by
  construction. The honest reading is that OANDA's spread is a **coarse
  and largely dealer-set instrument**, which makes v21's null weaker
  evidence than RESULT_VOLCAUSE claimed. That belongs in the record
  whatever this run returns.

**The sample.**

```
SPX500_USD M15, 2013-01-01 .. 2026-08-28
  08:30 ET slot, 3,523 days
  of which 1,059 carry a scheduled release    CLAIMS 715  CPI 175  NFP 169
  control: the same slot on the remaining 2,464 days
  separate stratum: FOMC 14:00, 118 events (RTH -- v21's cell)
```

2013 is the hard floor for the same reason as v21: **every bar before
2012 has bid exactly equal to ask** (RESULT_PREANN), so the cost axis
does not exist there.

The event times come from `events_v2.csv`, built 2026-09-12 by
`event_table.py` v1.8 and verified by v1.9. For a 2013+ sample
`events.csv` and `events_v2.csv` are identical — the 14 recovered FOMC
rows are all 2011-2012.

## 3. The construction, frozen

```
signal bar   the 15-minute bar containing the release (08:30-08:45 ET)
entry        the MID OPEN of the NEXT bar (08:45)   never the signal close
exit         the MID CLOSE of bar t+H
cont_bp      +sign(close_sig - open_sig) x (exit/entry - 1) x 1e4
```

Positive is **continuation**, negative is **reversion**, fixed now.

`H = 4` primary (08:45 → 09:45 ET, crossing the open). `H = 1` and
`H = 12` pre-specified as robustness, reported together, never
substituted. Same horizons as v21 so the two are comparable — that
comparability is most of the point.

**Entry is the next bar's open and this matters more here than
anywhere.** The signal bar's close is exactly the price you would want
and exactly the one you cannot have; and the spread quoted *during* the
sixty seconds after 08:30 is certainly wider than the close-of-bar
snapshot this data carries. Entering 15 minutes later sits outside the
worst of it. **Gate E therefore understates cost, and is a floor rather
than an estimate.**

## 4. The gates

**Gate A — the positive control, and it can void the run.**

```
PASS   release bars show larger |moves| than same-slot non-release bars,
       t >= 5.0
```

A release moves the market; a method that cannot see that cannot be
trusted to report absence of anything else. **This gate also tests the
event table itself** — 1,059 timestamps built from ALFRED and the Fed,
never before checked against a price. If the times were wrong, Gate A is
where it shows, and the run is void rather than quietly diluted.

**Gate B — do known-cause moves continue.**

```
PASS   release bars show cont_bp > 0 at t >= 2.0
```

**Gate C — is the KNOWN CAUSE doing the work.**

```
PASS   release-bar continuation MINUS same-slot non-release continuation,
       t >= 2.0
```

**This difference is the entire hypothesis**, and it is v21's Gate C with
an instrument in place of a proxy.

**Gate D — the placebo, which is the one most likely to kill it.**

```
PASS   the 08:30 bar on the DAY BEFORE each release shows no such effect
FAIL   -> whatever was found is a property of the 08:30 slot, not of
          information arriving in it
```

**Gate E — cost.**

```
PASS   the Gate C difference exceeds 2.0x the spread ACTUALLY PAID on the
       event bars  (~3.3 bp at the measured 1.66 bp median)
```

**Gate F — present in all three disjoint eras.**

**Gate G — the mechanism, pre-specified as a contrast and not a search.**

```
PASS   continuation to 09:45 (H=4, crossing the open) EXCEEDS
       continuation within pre-market alone (H=1), t >= 2.0
```

The reasoning: the release lands 60 minutes before the real market
opens, into a venue carrying a quarter of the open's activity. **If the
pre-market repricing is incomplete because the participants who set the
price are not there yet, the move should finish at the open.** That is a
mechanism with a direction, and it is the one form of this effect that
would survive arbitrage — collecting it requires holding through the
thinnest hour of the session.

Gate G is reported whether or not B and C pass.

## 5. The stratification, fixed in advance

Primary is **all 08:30 releases pooled**. The three are reported
separately as a registered breakdown, **not as a menu**: if the pooled
result fails and one stratum passes, that is a finding about that
stratum requiring its own confirmation run, and it is not this run's
result.

```
CLAIMS  715   weekly, low-profile, and nobody builds infrastructure for it
CPI     175   every desk on the street trades this
NFP     169   likewise
FOMC    118   14:00, RTH -- v21's original cell, carried for comparison
```

## 6. Predictions, registered before the run

- **Gate A passes overwhelmingly.** If it does not, the event table's
  times are wrong and nothing else in this document matters.
- **Gate B fails.** I expect pooled continuation between −1 and +2 bp.
  With n ≈ 1,059 the standard error is roughly 0.5 bp, so 2 bp would
  reach t ≈ 4. This is a real prediction, not a hedge: **post-
  announcement drift at 15-minute scale on a liquid index has been
  hunted for thirty years.**
- **Gate C fails**, |difference| < 2 bp.
- **Gate D passes** — the placebo shows nothing.
- **Gate E is the one I am least sure of, and I was wrong about it
  yesterday.** I wrote that pre-market spread would kill this before
  measuring it. It will not. If C passes at all, E is now winnable.
- **Gate G is the live one.** This is where I would put the run's only
  real chance, and I put it at perhaps one in four.
- **Of the four strata, CLAIMS is the one to watch** — 715 events, the
  lowest profile, and the least-crowded trade. Dave's standing question
  is what nobody has the time or effort to explore; claims at 08:30 is
  a candidate answer. **Registered as a prior, not as a licence to go
  looking there after the pooled result fails.**

**If Gate C passes above 10 bp I should suspect the event timestamps
before celebrating**, because a 10 bp free continuation an hour before
the open, at a cost of 3.3 bp, would not have survived this long.

## 7. Kill conditions

- **The signal bar's close is never an entry price.**
- **No lookahead.** The control set is defined by the calendar, not by
  any price.
- **A result above 30 bp at H=4 is a bug until proven otherwise.**
- **One run.** No moving H, the slot, the strata or the control.
- **No sign flips.** Continuation is positive, fixed in section 3.
- **Gate A failing voids the run**, and does so loudly, because it would
  mean the table rather than the market is what was measured.

## 8. What this cannot do

**It cannot say the cause is the release.** It can say a bar containing
a documented information arrival behaves differently from one that does
not, at the same minute of the same instrument. That is far stronger
than spread-and-volume proxies and it is still not causation.

**The spread it measures is a close-of-bar snapshot.** The quote during
the release itself is not in this data and is certainly worse.

**OANDA's volume is tick count at one venue.** The pre-market thinness
this whole argument rests on — 406 ticks against 1,804 — is thinness *on
Dave's platform*, which is the right thing for tradeability and is not
the same as market-wide participation.

**Investigation thirty-eight.** The first with a known instrument rather
than a proxy, and the first whose cost gate is not stacked against it
before the run begins.
