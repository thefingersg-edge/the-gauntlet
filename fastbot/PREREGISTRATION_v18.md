# PREREGISTRATION v18 — the opening-range liquidity sweep

```
WRITTEN:  2026-09-11, BEFORE any sweep has been located or any outcome
          computed
STATUS:   FROZEN
SUBJECT:  does a failed breakout of the opening range -- sweep, then
          close back inside -- predict a move to the other side of that
          range, beyond what the trade's own geometry already implies
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.**

---

## 1. This is not what v17 tested

v17 tested *"the opening candle is large, therefore reverse"*. Size was
the trigger. **Size does not appear in this rule at all.**

This is a three-step sequence: the first bar sets a range, price later
trades **outside** it, then a bar **closes back inside**. Entry on that
confirmation close, stop beyond the sweep extreme, target the far side
of the range. They share only the opening bar.

RESULT_OPENCANDLE stands as the answer to the size claim — it fires on
54.8% of openings and returns −0.00 bp. It says nothing about this.

## 2. The null is not zero return — it is the trade's own geometry

A bracket with a stop at −1R and a target at +kR, on a driftless price,
has **expected value exactly zero** by optional stopping, whatever k is,
and whatever stopping time ends it. That is what makes this testable
without a P&L curve:

```
primary metric   mean R per trade
null             0.00 R
```

A time-stopped trade is not an awkward third case — a martingale stopped
at *any* stopping time still has expectation zero, so closing at 16:00
is handled by the same null.

For intuition the **hit rate against its own geometric break-even** is
reported alongside: for each trade, `p* = stop / (stop + target)`.
Beating `p*` is the same claim as mean R > 0, stated the way a trader
would state it.

**Drift is the loophole.** Equities drift up, so long trades inherit a
little and shorts give a little back. §4's control removes it.

## 3. The six free parameters, fixed now

The write-up leaves these open. Each is set to the **least-parameterised
reading**, not the most flattering one.

| | choice | why this one |
|---|---|---|
| timeframe | **15m**, first bar 09:30-09:45 ET | chosen by Dave; 5,842 sessions, and directly comparable to v17 |
| sweep deadline | **11:00 ET** | chosen by Dave |
| time stop | **16:00 ET session close** | chosen by Dave |
| what counts as a sweep | **any trade outside the range — no minimum excursion** | "aggressively spike" is unmeasurable; a threshold would be a free parameter, so there is none |
| confirmation | **the first bar, at or after the sweep bar, that closes back inside** | includes the single-bar wick-and-reject case without a separate rule |
| how many per day | **one — the first qualifying setup**, either side | one observation per session; no overlapping trades to compound |
| stop placement | **exactly at the sweep extreme**, no buffer | "safely beyond" is a free parameter. A tighter stop means MORE stop-outs, so this runs against the strategy |

**Every one of these choices that is arguable is arguable in the
direction of making the rule harder to pass.** That is deliberate and it
is stated before the run.

### Entry price — measured both ways, on purpose

The rule says *enter on the close of the confirmation candle*. v17 found
that using a signal bar's own close as the entry manufactures
microstructure. So:

```
PRIMARY     the mid OPEN of the next bar      (tradeable)
REPORTED    the mid CLOSE of the confirmation  (the rule as written)
```

**If those two differ materially, the difference is the microstructure,
not the strategy** — and that is a result worth having either way.

## 4. The control, which is the real test

**Matched-geometry control.** For every actual trade, the identical
bracket — same direction, same stop distance in bp, same target distance
in bp, same entry time of day — is applied to a randomly chosen *other*
session's price path. Seed fixed at **20260911**, declared here.

This absorbs equity drift, time-of-day effects and the bracket geometry
itself. What survives it is the signal.

**Time-of-day control.** The entire construction is repeated with the
**11:00-11:15 ET** bar defining the range and a 12:30 sweep deadline. If
a midday range sweeps and reverts exactly as often, the "opening
liquidity" story is decoration — the same question v17 asked and the one
Dave asked first.

## 5. The gates, frozen

```
Gate A   mean R > 0, t >= 2.0, NET of measured spread        is it there
Gate B   beats the matched-geometry control, t >= 2.0        is it signal
Gate C   opening range beats the 11:00 range, t >= 2.0       is it the OPEN
Gate D   mean R positive in all three disjoint eras          is it stable
Gate E   hit rate exceeds its own geometric break-even       consistency
```

Gate E must agree with Gate A by construction; if they disagree there is
an arithmetic error and the run is void rather than reported.

Costs are **measured, not assumed**: the actual bid-ask at the entry and
exit bars, as in RESULT_PREANN, which put SPX500_USD at 0.76-3.31 bp
round trip by era.

## 6. Predictions, registered before the run

- **Gate A: FAIL.** Mean R between −0.10 and +0.05 before cost,
  negative after. Pattern claims are 0 for 16 in this project.
- **Gate C: FAIL**, and specifically the 11:00 range will behave the
  same as the 09:30 one within noise.
- **The entry-price diagnostic will bite.** Confirmation-close entry
  will look better than next-bar-open entry, and the gap will be about
  one spread. That is the most likely way this rule appears to work on a
  chart and fails in an account.
- **If Gate A passes and Gate B fails**, the bracket geometry is doing
  the work, not the sweep.

**If everything passes I should be suspicious, not pleased.** This is a
widely published retail setup; a large, stable edge in it would need
explaining, not celebrating.

## 7. Kill conditions

- **No lookahead.** The opening range uses only the first bar. The sweep
  and confirmation are located in forward time order. The stop and
  target are fixed at entry and never moved.
- **Intrabar ambiguity.** When a bar's high reaches the target and its
  low reaches the stop, the outcome is **scored as the stop** — the
  pessimistic assumption. Without tick data the order is unknowable, and
  assuming the favourable one is how backtests lie.
- **A mean above +0.50 R** is treated as a bug until proven otherwise.
- **One run.** No moving the deadline, the stop buffer, or the entry
  convention to find a pass.

## 8. What this cannot settle

**Whether a discretionary trader does better.** "Sharply reject" and
"aggressively spike" are judgements this cannot encode, and a human
filtering setups by eye is not what is being measured.

**Targets other than the far side of the range.** The rule also mentions
"internal liquidity pools", which is not a defined price. Only the
stated target is tested.

**Investigation thirty-four.**
