# PREREGISTRATION v8 — the forward test, and what it is actually for

```
WRITTEN:  2026-08-19, BEFORE a single forward observation exists
STATUS:   FROZEN. This is a protocol, not a backtest. There is nothing to
          fit because there is no history to fit to.
SUBJECT:  the Kraken dated BTC basis, which passed every pre-registered
          gate in v7 and left one class of question unanswered
```

---

## 1. What a forward test cannot do, stated first

The obvious use of a forward test is to confirm the premium. **It is a bad
use, and the arithmetic says so.**

Per-cycle excess across the 18 measured cycles: mean **+3.49 points**,
standard deviation **7.21**. Forward, that gives:

| target | cycles needed | years |
|---|---|---|
| t = 1.0 | 4.3 | 1.1 |
| t = 1.65 | 11.6 | 2.9 |
| **t = 2.0** | **17.0** | **4.3** |
| t = 2.5 | 26.6 | 6.7 |

**Four years to reach 2σ**, on a premium that has already been measured on
eighteen cycles across a bear market. Running a multi-year forward
significance test to re-establish something already established is not
patience, it is waste.

So this protocol is **not** a significance test, and no gate below asks
whether the premium repeated.

## 2. What it is for

Five things that no quantity of history can settle, and that **one cycle**
answers:

1. **Achieved basis versus quoted basis at entry.** Every number in v4 and
   v7 assumes the printed price is obtainable. That has never been tested.
2. **Actual roll cost** against the 0.05% taker plus one tick assumed in
   v4 §7.
3. **Whether equity/notional really holds at 1.0** through a live move.
   v7 proved it algebraically. Algebra is not a margin engine.
4. **Fees and funding actually charged** against the published schedule.
5. **Whether the venue does anything unexpected at all** — margin changes,
   auto-deleveraging, withdrawal delays, contract changes.

Item 3 is the one worth being nervous about. `RESULT_KRAKENBASIS_v7` rests
entirely on an arithmetic identity. If Kraken's risk engine computes
maintenance differently from the published formula — on a mark price, on a
different notional convention, with an added buffer of its own — the
identity holds and the implementation does not.

## 3. Two tracks, and only one needs money

**Track A — observation only, no capital, starts immediately.**
Record daily: front dated contract mid, bid, ask, the settlement index,
days to expiry, and the implied basis. Over one quarter this produces the
realised path of a basis that was previously only ever sampled at entry
and expiry, and it costs nothing but a daily API call.

Track A alone settles item 1 partially — the spread at the moment of
entry, and whether quoted depth is present — and gives the mark-to-market
path the backtest never had.

**Track B — one cycle at minimum size, only if the operator chooses.**
Items 2 through 5 need a real position. Nothing in this document
constitutes advice to take one. **I am not a financial adviser and this is
research tooling, not a recommendation.** If capital is committed, §5 fixes
what gets recorded and §6 fixes what ends it.

## 4. The rule, frozen

```
instrument   FI_XBTUSD_<nearest quarterly>   INVERSE, BTC-margined
position     short N USD of notional, collateral M = N / F_entry BTC
             i.e. exactly fully collateralised, per v7 section 2
entry        the day after the previous contract settles
exit         hold to settlement; no discretionary close
roll         into the next quarterly on the settlement date
size         Track B: the smallest tradeable size. Not a scaled position.
```

**No discretion.** No basis threshold, no timing, no adding, no cutting.
The whole value of a forward record is that it was not steered, and a rule
with a judgement call in it produces evidence about the operator rather
than about the trade.

## 5. What gets recorded, per cycle

| field | why |
|---|---|
| quoted basis at the decision moment | the number v4 assumed |
| achieved entry price and the spread crossed | slippage, item 1 |
| collateral posted, and equity/notional daily | item 3, the identity |
| every fee, funding and adjustment charged | items 2 and 4 |
| realised basis at settlement | against the quoted |
| any venue action, dated | item 5 |

The daily equity/notional ratio is the single most informative series
here, because it is the one thing v7 asserts and cannot demonstrate.

## 6. Kill conditions, fixed now

- **Achieved basis below quoted by more than 0.5 points annualised** →
  the measurement was optimistic and every figure in v4 and v7 needs
  restating with real slippage.
- **Equity/notional departs from 1.0 by more than 2%** in a normal market
  → the v7 mechanism does not describe the venue's risk engine, and the
  buffer question reopens.
- **Any forced action** — margin call, auto-deleverage, forced close →
  record it and stop. That is the counterparty risk becoming observable,
  and one observation of it outweighs the backtest.
- **Withdrawal delay or restriction of any kind** → stop, whatever the
  P&L is doing.
- **The protocol is not modified mid-cycle.** If something looks wrong,
  the cycle completes or is abandoned entirely; it is not adjusted.

## 7. What would make me abandon this line entirely

Stated now, so it is not renegotiated later:

- two consecutive cycles where achieved basis misses quoted by more than
  0.5 points
- any venue event in §6's third or fourth bullet
- the operator finding they cannot follow the rule without discretion,
  which is information about the strategy's practicality and not a
  personal failing

## 8. What this still will not answer

**Counterparty risk remains unpriceable.** A venue that behaves perfectly
for four quarters has told you almost nothing about the fifth. FTX
processed withdrawals normally until it did not. No forward record of any
length converts this into a measured quantity, and the 2.0-point threshold
in v4 §2 remains a judgement rather than an estimate.

That is the honest ceiling of this entire line of work, and it was visible
from `RESULT_VRP` onward: **some risks have a price that no amount of data
can estimate, and the only remaining choice is whether to bear them.**

## 9. Scoreboard

**Twenty-four investigations. Nineteen rejections, one
measured-but-unreachable premium, one headline that dissolved on
decomposition, one real premium whose edge vanished at daily resolution,
and one that passed every pre-registered gate.**

This is the first protocol in the project that produces evidence rather
than consuming it.
