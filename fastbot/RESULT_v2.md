# Result v2 — REJECTED, and the exit structure cannot rescue it

```
RUN:      2026-08-17
SPEC:     PREREGISTRATION_v2.md, unmodified
DATA:     NAS100_USD M5, fit window 2014-2020
VERDICT:  FAIL. 40 of 40 tests negative. Zero advanced.
          Follow-up: no edge exists at ANY horizon for a barrier to capture.
```

---

## 1. The screen

Twenty patterns, two directions, forty tests. **Not one produced a positive
Sharpe.**

```
best:   opening_range long   -0.173     worst:  doji short   -2.569
```

Under a coin-flip null you would expect twenty positive. Forty from forty in
one direction is **p ≈ 9×10⁻¹³**. And the screen returned **fewer** passes than
chance predicted — 0 against ~0.9 expected. These effects are not zero. They
are negative.

## 2. The patterns contribute nothing — it is all execution

Forty tests moving together, on twenty patterns that share no geometry, points
at the one thing they do share: a stop entry on the break of the prior bar's
extreme, held 30 minutes. Run that execution on **random** bars:

```
random long   -0.88bp        random short  -1.58bp
patterns beating their matched benchmark:  20 of 40      <- exactly chance
largest |t| across 40 tests: 2.45          <- exactly what 40 draws produce
```

The 0.70bp gap between the random long and short benchmarks is **index drift**
over a 2014-2020 bull market, not skill. Both are negative because of cost.

**The forty tests measured an execution model plus drift minus cost.
Candlesticks never entered the arithmetic.**

## 3. A measurement error found while building the follow-up

The benchmark in §2 was a single Bernoulli draw for all forty tests. That is
not properly matched, and the reason matters:

```
pure random walk, ZERO edge planted, stop entry on the prior bar's high:
   signal bar was UP     +1.5bp
   signal bar was DOWN   +4.4bp
```

A stop entry is **upward-biased by construction**, and the bias depends on the
bar type. After an up bar the trigger sits at roughly the close and fills
immediately. After a down bar the trigger sits *above* the close, so filling at
all means conditioning on price coming back up — worth +4.4bp at 60 minutes
with nothing there.

Patterns differ in which they fire after, so a single average benchmark
under-credits some and over-credits others. `exit_shape.py` matches on
**trigger-distance decile** instead, which cuts the down-bar bias from +3.59bp
to +0.78bp.

**This does not overturn §1.** All forty were negative *net*, and this bias
pushes results *up* — so 40/40 negative despite an upward bias is a stronger
result than it first appeared. It does mean the 20-of-40 should be read as
"consistent with chance" rather than as a precise figure.

## 4. Is the edge front-loaded? No. There is no edge at any horizon.

The fair objection to a fixed 30-minute hold is that it assumes the edge
accrues uniformly. If a pattern gives direction for five minutes and noise for
twenty-five, the fixed exit dilutes signal with variance and a take-profit
would capture what it throws away.

Measured, pooled across all twenty patterns, as excess over the matched
benchmark — **gross**, so cost cannot hide the shape:

| bars | mins | long | short | both | t |
|---|---|---|---|---|---|
| 1 | 5 | +0.13 | −0.07 | **+0.03** | 0.83 |
| 3 | 15 | +0.05 | −0.05 | 0.00 | 0.02 |
| 6 | 30 | 0.00 | −0.05 | −0.02 | −0.22 |
| 9 | 45 | +0.02 | −0.17 | −0.07 | −0.61 |
| 12 | 60 | −0.23 | −0.20 | −0.22 | −1.56 |

**Flat at zero everywhere.** Peak excess is **+0.03bp**, against a declared
noise floor of 2.5bp and a round-trip cost of 1.74bp. The measurement is
roughly eighty times more precise than the largest number in it. The only
|t| above 1 is negative.

There is no horizon between 5 and 60 minutes at which these patterns give
direction. Not a weak edge eaten by cost — **no edge to eat**.

## 5. The direct answer on stop-loss / take-profit / trailing

A barrier rule interacts with exactly one thing: the excursion distribution.
Here it is, against the matched benchmark:

| | MFE | MAE | ratio |
|---|---|---|---|
| long, pattern | 23.1bp | −24.3bp | **0.95** |
| long, matched random | 22.2bp | −23.3bp | **0.95** |
| short, pattern | 25.2bp | −23.4bp | **1.07** |
| short, matched random | 24.9bp | −23.0bp | **1.09** |

**Identical.** The excursions after a pattern are indistinguishable from the
excursions after a random entry. So any stop, target or ratchet applied to
these patterns produces precisely what it would produce applied to random
entries — and on a distribution with zero mean, that is zero minus cost.

Three things now say the same thing from different directions:

1. **Optional stopping.** For a process with no drift, *every* stopping rule
   has expectation zero before costs. Barriers reshape win rate and average
   win/loss; they never move the mean.
2. **A shallow stop makes cost worse, not better.** silver15's own formula,
   `break-even = 0.5 + C/(2B)`. At a stop of 0.25× the 30-minute dispersion
   the break-even win rate is **64.0%**; at 1.0× it is 53.5%. Asymmetric
   framing does not escape it — at SL 3.9bp / TP 11.7bp you need 32.0% where
   a coin gives 25.0%, i.e. **28% better than random purely to pay the
   spread**, against 7% at a wider stop.
3. **DESIGN_BRIEF already ran this on gold.** *"Never cap winners. Tested four
   ways — take-profits at 1–10% all lost, the ATR ladder lost… MFE analysis
   showed the average trade gives back 75% of its peak and capping still
   lost."*

**The proposed structure would land strictly behind the fixed hold**, because
it pays the spread more often against the same zero-mean distribution.

> The one thing that would have made it worth building is a front-loaded edge,
> and §4 measured that to +0.03bp. This is not an argument against the idea in
> general — it is a measurement of this specific market at this specific
> horizon.

### And a warning that stands regardless

silver15's **only** false PASS in the entire project — v3, Sharpe +1.51 — was
**barrier snapping**. On OHLC bars, when a stop and a target both sit inside
one bar you cannot know which was hit first, and assuming the favourable one
manufactures edge from nothing. `exit_shape.py` simulates no barriers at all,
by design, which is why it cannot have that bug. Any future barrier engine
must assume the **stop** hit first, always, and prove it with a control.

## 6. What is closed

**Bar-pattern breakouts on this venue, as a family.** Not "these twenty shapes
fail" but *"buying the break of the prior bar's extreme on a 5-minute index
CFD loses money regardless of the bar's shape, and no exit structure changes
that."* Two hundred patterns would close as firmly as twenty, because the
patterns were never the operative variable.

**Exit engineering as a rescue.** With the excursion distribution measured
identical to random, barrier design cannot be the missing piece for anything
in this family.

## 7. Scoreboard

**Fifteen hypotheses tested across silver15, pineport and fastbot. Fifteen
rejected.** Three of the last three are *family closures* rather than single
candidates:

| | closed | by |
|---|---|---|
| v1 | intraday shocks revert | measured continuation, 7/7 years |
| v2 | bar-pattern breakouts, and exit structures for them | 40/40 negative; excursions = random |
| v3 | every dealer-quote signal on OANDA | spread is a schedule, not a response |

The apparatus is now producing closures faster than candidates, which is the
efficient direction. What remains unexplored at this horizon is non-price
information — and the published latency figure for that is ~2 minutes from
wire to full incorporation, which is an institutional-feed problem rather than
a retail one.
