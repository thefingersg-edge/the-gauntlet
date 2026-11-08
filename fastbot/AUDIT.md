# Audit — what could have skewed 21 investigations, and what was never asked

```
WRITTEN:  2026-08-19, after RESULT_KRAKENBASIS
PURPOSE:  find the errors that would have produced a wrong REJECTION, the
          framing that ran through every test unexamined, and the gaps
```

---

## 1. One concrete error that biased against a candidate

**`RESULT_VIXDAILY.md` compared a daily drawdown to a monthly one.**

The VIX carry's drawdown was measured at **daily** resolution (−68.20 vol
points) — that was the entire point of the file. The equity benchmark it
was compared against was measured from **month-end** closes (−52.5%), by
`risk_matched()` in `vix_carry_budget.py`, which resamples SPX to `ME`
before computing the drawdown.

So the candidate was held to a stricter standard than its benchmark, in
exactly the dimension the file existed to sharpen. Equity's daily-close
drawdown over the same window is roughly −57% rather than −52.5%, so the
index should be sized about 8% smaller:

```
                            as published    corrected
index sized to 30%, 2% cash      5.1%          ~4.7%
VIX carry, daily drawdown     3.4 - 4.0%    3.4 - 4.0%
margin to the index            1.1 - 1.7      0.7 - 1.3
```

**The verdict survives — the index still wins at every cash rate — but the
margin narrows by about a third.** The published number overstated the
case against the carry. This should be recomputed from the SPX file on
disk rather than from a remembered index level.

## 2. One assumption that decided a rejection, fixed in advance

`RESULT_KRAKENBASIS.md` already records this and it belongs in the list.
Gate D specified a **USD** collateral buffer, and the buffer is the entire
rejection: without it, both Gate A and Gate B pass. If the short leg is
BTC-collateralised — which is what the inverse `FI_` contracts exist for —
a rally lifts the collateral at the same rate as the futures loss and most
of the buffer disappears.

It was frozen before the data was pulled, so the run is honest. But the
single most consequential parameter in that test was chosen by me, in
advance, on an assumption about margin mechanics I did not verify with the
venue.

## 3. The framing that ran through all 21 tests without being examined

**Every investigation asked "does this beat equity beta standalone?"**

For something you would *add* to a portfolio, that is the wrong test. A
0.3-Sharpe stream uncorrelated with equities improves a portfolio more
than a 0.5-Sharpe stream that moves with them. The right measure is
marginal contribution, not standalone comparison.

Two qualifications, so this is not overstated:

- It cannot rescue most of the record. Fifteen results were at or below
  zero; a diversification argument does not save a strategy with no
  return.
- It matters for exactly the two that measured positive — the VIX carry
  and the crypto basis — and **both are short-volatility carry, which
  correlates with equities precisely in crises.** So the marginal framing
  probably does not rescue them either.

But "probably" is doing work there that a measurement should be doing.
Neither correlation was ever computed.

## 4. The resolution floor, never quantified

The detectability bar used throughout is `k_sigma / sqrt(years)`. At 2σ
over seven years that is **~0.76 Sharpe** — which is why
`PREREGISTRATION_v1` set Gate A at exactly 0.76.

That is a very large edge. **Any real effect between 0.2 and 0.7 Sharpe —
which includes most documented risk premia, including equity beta itself
at 0.4–0.5 — was below the resolution of the strategy backtests.**

This does *not* mean the nulls were marginal misses. v1 came back at −1.09
net and −0.725 gross, pointing the wrong way. The 40 pattern tests were
all negative at p ≈ 9e-13, and `exit_shape.py` found MFE/MAE
indistinguishable from random at every horizon. Those are strong nulls.

But it does explain a pattern worth naming:

> **Measuring a premium directly found real effects. Backtesting a
> strategy found nothing.**

| approach | result |
|---|---|
| VRP measured directly | real at **10σ** |
| VIX term structure, by regression | carry ~0.40 Sharpe, era-consistent |
| crypto basis measured directly | **+4.15 pts** over the bill |
| 15 strategy backtests | nothing |

Strategy P&L is a noisy estimator of an underlying effect — it adds entry
timing, exit timing, sizing and cost noise on top of the thing you want to
measure. Direct measurement of the premium has far more power. The three
real effects in this project were all found the second way.

## 5. Smaller items

**Taker fills everywhere.** Kraken maker fees are roughly 40% below taker
on both legs. It would not have changed the crypto verdict — the buffer
dwarfs it — but no test has ever assumed passive execution.

**Everything is single-instrument time series.** Nothing cross-sectional
has been tested anywhere in silver15, pineport or fastbot. Cross-sectional
tests give many times the observations for the same calendar span, which
is the cheapest available way to lower the resolution floor in §4.

**The intraday work priced one venue's spread.** `RESULT_v3` established
OANDA's CFD spread is a schedule rather than a response. The gross results
were null too, so the conclusion does not depend on the cost model — but
"no edge in bar patterns" is established for OANDA's cost regime and
tested nowhere else.

## 6. What has never been tested at all

`ASSESSMENT.md` §5 listed six unexplored areas. Three have since been
done — VRP, futures term structure, crypto — and all three found a real
premium. Three remain untouched:

**Volatility targeting as the strategy, not an overlay.** `DESIGN_BRIEF`
found this was the *one* thing that worked: all six settings beat
buy-and-hold on Sharpe, with a **plateau rather than a spike** — the
signature of a real effect rather than a fitted parameter. It was noted
and never built on. It applies to equity beta, which is the only thing
that has beaten equity beta.

**Event-driven with known timestamps.** Releases have publication times
known in advance, which removes the latency race in `ASSESSMENT` §1.

**Cross-sectional factors.** Breadth rather than speed. See §5.

And one that was on nobody's list:

**FX carry on OANDA, and how much of it the broker keeps.** Carry is a
forty-year documented premium. OANDA pays and charges daily financing on
every position, publishes those rates, and the account is already open.
The decisive question is this project's own speciality: *the retail
financing spread against the true interest differential.* If OANDA keeps
most of the carry, that is a clean rejection with a number attached, and
it is measurable without a new venue, new data purchase, or new broker.
It is the largest accessible gap in the entire record.

## 7. On stacking

The honest answer to "what combinations would give an advantage":

**Diversification across genuinely uncorrelated return streams is the only
free lunch in the subject.** But every premium this project has found —
variance, VIX term structure, crypto basis, FX carry — is a carry or
short-volatility premium. Those look diversified in calm periods and
behave like a single position in a crisis. Stacking them is the documented
failure mode of "carry everywhere" portfolios, not an escape from it.

Two combinations do have evidence behind them, from inside this project:

1. **Equity beta plus volatility targeting.** The only thing that has won,
   plus the only overlay that improved it across every setting tested.
2. **Capital efficiency as the objective.** Two candidates have now died
   on required capital rather than on premium size. If anything is
   stacked, the thing to optimise is return per unit of *total* capital
   including buffers — and to prefer positions whose buffer requirements
   do **not** coincide.

The second is the more interesting reframe, because it is the lesson the
last two investigations actually taught, and no test has yet been designed
around it.
