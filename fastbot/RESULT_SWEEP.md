# RESULT — the opening-range liquidity sweep

```
RUN:      2026-09-11
SPEC:     PREREGISTRATION_v18, frozen before any sweep was located
CODE:     sweep_reversal.py 1.2  (1.0 and 1.1 each carried a bug; both
          are documented in section 4 with the direction each ran)
SAMPLE:   SPX500_USD M15, 5,842 RTH sessions, 4,160 setups, 2003-2026
VERDICT:  FAIL. The setup loses 0.136 R per trade and is WORSE than a
          random bracket of the same geometry.
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.**

---

## 1. The result

```
                      n      mean R      t     hit    break-even
open, next_open    4160     -0.136   -6.61   47.4%       48.2%
open, conf_close   4172     -0.129   -6.31   47.3%       48.4%
11:00, next_open   4170     -0.215   -9.62   45.8%       47.9%
matched control    4160     -0.065
```

```
[FAIL] Gate A  mean -0.136 R, t = -6.61          is it there
[FAIL] Gate B  vs matched control -0.072, t=-2.15  is it signal
[PASS] Gate C  open vs 11:00 +0.079, t = 2.60      is it the OPEN
[FAIL] Gate D  eras -0.040  -0.246  -0.123        is it stable
[FAIL] Gate E  hit 47.4% vs break-even 48.2%      consistency

    FAIL
```

The setup fires on **71.2% of sessions**, so this is not a rare pattern
being tested on thin data — it is most days, for 23 years.

## 2. The one gate that passed says something worth reading carefully

Gate C passed: the opening range beats an 11:00 range by +0.079 R,
t = 2.60. **Both lose money.** The opening range is *less bad* than a
midday range, which is not a strategy.

That is the whole content of the "opening liquidity" claim as measured:
the open is different, and the difference is that you lose 0.136 R there
instead of 0.215 R.

## 3. Worse than random, which is the sharpest finding

Gate B is the one that matters. The **matched-geometry control** — the
identical bracket, same direction, same stop and target distances in bp,
started at a random time on a randomly chosen other session — loses
0.065 R. The actual setup loses **0.136 R**, and the difference is
significant at t = −2.15.

**Waiting for the sweep and the rejection made the trade worse than
entering at random with the same stop and target.**

The mechanism is not mysterious. The stop sits at the sweep extreme,
which by construction is close to the entry — a fast counter-move is
exactly what defines the setup. A tight stop placed just beyond a level
price has already visited is a stop that gets hit. 52% of trades stopped
out; 47% reached target.

## 4. Two bugs, and they ran in opposite directions

**v1.0 — the cost lookup was keyed by time of day only.** It built
`{slot: spread}`, overwritten once per session, so every trade was
charged the *last* session's spread in absolute points — 2026's
point-spread against 2003's index level, where the same points are eight
times the fraction. It reported 0.190 R of cost against a 21.9 bp stop,
implying ~4 bp of spread on an instrument RESULT_PREANN measured at
0.76-3.31 bp. **That overstated cost, so it ran against the candidate**,
and fixing it moved the headline from −0.043 R to +0.032 R.

**v1.1 — the entry bar carried no risk.** For the `next_open` entry I
passed the forward path starting *after* the entry bar, so a trade
entering at a bar's open could not be stopped out during that bar. **A
free bar with no stop exposure, running toward the candidate.**

That second one is the classic way a backtest lies, and it is worth
naming precisely because of what it produced: with the free bar,
`next_open` read **+0.032 R** and appeared to beat `conf_close` by
0.160 R, which I was about to report as a microstructure finding. With
the bar restored, `next_open` reads **−0.136 R** and the gap to
`conf_close` is **+0.008 R** — nothing.

**The entire apparent entry-convention effect was my own bug.**

## 5. Predictions

| | predicted | measured | |
|---|---|---|---|
| Gate A | fail; −0.10 to +0.05 R gross | fail; **−0.021 R gross** | **held** |
| Gate C | fail — 11:00 same as open | **pass**, t = 2.60 | **missed** |
| entry diagnostic | conf_close better by ~a spread | **+0.008 R, nothing** | **missed** |
| "suspicious if all pass" | — | nothing passed | n/a |

One of three. The Gate C miss is the interesting one: I expected the
open to be indistinguishable from midday and it is not — it is
reliably, measurably less bad. That is a real time-of-day effect and it
is not enough to trade.

## 6. What this does and does not settle

**It settles the mechanism as specified.** Sweep the opening range,
close back inside, enter the reversal with a stop at the sweep extreme
and a target at the far side — on 4,160 setups over 23 years that loses
money, loses to its own geometry, loses to a random bracket, and loses
in all three eras.

**It cannot test discretion.** "Aggressively spike" and "sharply reject"
are judgements no encoding captures. A human filtering these by eye is
not what was measured — though it is worth noting that the filter would
have to convert a −0.136 R average into a positive one, which is a lot
to ask of eyeballs.

**It does not test other targets.** The rule also mentions "internal
liquidity pools", which is not a defined price. Only the stated target —
the far side of the opening range — was tested.

**Six parameters were fixed by me**, each at the least-parameterised
reading and each declared in v18 §3 before the run: any excursion counts
as a sweep, the first qualifying setup per day only, the stop exactly at
the sweep extreme with no buffer. That last one makes stops tighter than
"safely beyond" implies, and therefore makes the rule harder to pass. A
generous buffer would widen R and reduce stop-outs — but it would also
be a parameter chosen after seeing this result, which is the thing the
pre-registration exists to prevent. **If you want it tested with a
buffer, that is a new pre-registration with the buffer fixed in
advance.**

---

**Investigation thirty-four.** Pattern claims now 0 for 17.
