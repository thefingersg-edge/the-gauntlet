# Cost model v2, partial — implemented and re-scored

```
DONE:    2026-11-07, from ARM G's ENGINE_COSTS_v2 spec, implemented by us.
         A subject of the study does not write the code that scores it.
VERDICTS: none changed. Exactly as ARM G predicted.
```

## What was fixed

**1. Futures-based CFDs marked UNPRICED.** The futures roll sits in OANDA's
financing line, not the price. Brent's implied benchmark is −46.1%/yr: a
long **earns** about 43.6%, a short **pays** 48.6%. We were charging a flat
2.5% both ways — wrong by two orders of magnitude and the wrong sign for
longs. With no F1/F2 history available to price it, `bcousd`, `natgasusd`,
`cornusd`, `wheatusd`, `sugarusd` and `xcuusd` are reported but excluded
from any tradeable claim. Brent is measured; the other five are presumed by
analogy and flagged the same way.

**2. Per-instrument markup.** 1.19% on metals, not 2.5% — OANDA prices
metals off the pair's rate differential.

**3. Breadth counted twice** — over everything, and over priced instruments
only. Only the second may be quoted.

## The result: the commodity figures were carrying the breadth count

```
  arm   breadth, all      breadth, priced only
  A     6 of 21           3 of 15
  B     6 of 21           3 of 15
  D     7 of 19           5 of 13
  E     8 of 21           6 of 15
  G     7 of 21           5 of 15
```

**Half of ARM A's positive markets were unpriced commodities.** Its single
best market was `bcousd` at +2.82% per trade on 33-night holds — against an
uncharged roll yield of up to +43.6%/yr on longs. That number was never a
strategy result and is now labelled as such.

No verdict moves: every one of these was failing breadth at 14 of 21 and
fails harder now.

The metals markup correction moved ARM A's net from −0.119% to −0.098% per
trade. Small, and in the direction of making a failure slightly less bad.

## What is still not fixed, and what it needs

The **benchmark half** of the financing charge. OANDA's convention is
`long pays b + m`, `short receives b − m`, where b is the overnight rate of
the instrument's currency. We charge only the markup m, so **longs are
undercharged by b and shorts are under-credited by b**.

At a 4-night hold (ARM F) that is worth 0.02–0.03% per trade. At 27–33
nights (ARMS A, B, E) it is 0.15%+ — comparable to their entire net.

It needs an overnight rate series per currency, 2005–2026. One command on
the Mac gets the USD one, and `FRED:DFF` already validates the
decomposition: it returns **3.88% today, exactly the implied benchmark on
the SPX500 and NAS100 rate cards.** That is validation check 1 of
ENGINE_COSTS_v2 passing.

```bash
cd ~/RStudio/Claude/pineport
python3 fetch_fred.py --series DFF --start 2004-01-01 --out rates_usd_dff.csv
python3 fetch_fred.py --series ECBDFR --start 2004-01-01 --out rates_eur_ecbdfr.csv
```

USD covers spx500usd, nas100usd and the metals. EUR covers de30eur and
de10ybeur. Those five instruments are what ARM F, ARM C and both
mean-reversion sleeves actually trade, so they close the gap for everything
that matters. `ECBDFR` is the ECB deposit facility rate — a proxy for €STR,
which does not exist before 2019; if the script rejects the ID, say so and
we will find the right one rather than guess.

FX financing on the interest differential — ARM G's one genuinely new
claim — is left unimplemented and stated as a known limitation. It needs
six currency series and confirmation on an OANDA FX card, and it changes no
verdict.

## What v2-partial still does not model

Slippage beyond the spread; intrabar paths on stop fills; markups frozen at
2026 values across 2005–2026; metal lease rates; spreads measured 2024–26
and applied to the whole sample. Stated on every result produced on it.

---

# Update — USD benchmark now applied (2026-11-07)

FRED timed out from the Mac, so the series came through the TradingView
connector at monthly resolution: **264 months of Fed funds effective,
2004-12 to 2026-11**. Monthly is adequate — DFF is a policy rate, piecewise
constant between FOMC moves — and it validates: **DFF today is 3.88%,
exactly the implied benchmark on the SPX500 and NAS100 rate cards.**

Financing is now `long pays b + m`, `short is charged m − b`.

**EUR is still not sourced.** No euro overnight series was reachable from
either route. `de30eur` and `de10ybeur` keep markup-only financing and that
is stated wherever their figures appear.

## ARM G's registered re-score predictions — all five correct

It wrote these in `ENGINE_COSTS_v2.md` §6 before the re-score:

| arm | its prediction | actual |
|---|---|---|
| F part A | net falls 0.02-0.06%/trade, stays above +0.40%, verdict unchanged | fell **0.021%** (0.523% → 0.502%), verdict unchanged at 5 of 7 ✓ |
| C | unchanged | unchanged, 6 of 9 ✓ |
| G | FAIL unchanged | 3 of 7 ✓ |
| A, B, E | no verdict passes | 1, 2, 1 of 7 ✓ |
| D | verdict unchanged | 2 of 7 ✓ |

A subject of the study predicted, in advance, what correcting the
apparatus would do to all eight arms including itself, and got every one
right.

## One verdict moved, and I am not banking it

ARM F **full** went from 5 of 8 to 6 of 8. Gate 5 primary flipped from
FAIL to PASS. It did not flip because the strategy improved — part B's net
*fell*, from +0.0208% to +0.0171%, since the overnight sleeve is long and
longs now pay the benchmark.

It flipped because **gate 5 is a ratio, and ARM F full's base edge is
+0.056% per trade.** At a base that small, a tiny absolute change in a
perturbed run moves the ratio across the 80% line. The gate is not
measuring robustness there; it is measuring noise.

```
  ARM F part A   base +0.502%   gate 5 stable, FAIL under every cost model
  ARM F full     base +0.056%   gate 5 flips on a 0.005% change in base
```

**Recorded as unreliable rather than counted.** ARM F full is reported as
5 of 8 with the gate 5 result marked unstable, and the headline arm remains
part A, whose base is ten times larger and whose verdict has not moved
under any cost model we have run.

This is a third weakness in the gate set, found by us rather than by ARM G:
gate 5 already returns "not applicable" for a non-positive base, and it
should do the same below some minimum positive base. That threshold has to
be fixed before a v2 gate set is run, not now.
