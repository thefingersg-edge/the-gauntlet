# Is any of it tradable?

```
WRITTEN: 2026-11-06, after the measured-cost run.
I am not a financial adviser and this is not advice. What follows is what
the measurements support and what they do not.
```

## Short answer

**One candidate, not disqualified, not proven: ARM F part A.** Everything
else is out on the evidence we have.

## The five that are out

```
  ARM A  Donchian trend      net -0.119%/trade   fails 6 of 7
  ARM B  path continuity     net -0.091%/trade   fails 5 of 7
  ARM E  twin sleeve         net -0.091%/trade   fails 6 of 7
  ARM D  v3 trend + MR       net +0.013%/trade   fails 5 of 7
  ARM C  ORB intraday        net +0.003%/trade   fails 2 of 8
```

A and B and E lose money per trade after measured costs. D makes 1.3 basis
points and fails sign consistency and the matched control. C makes 0.3
basis points, fails sign consistency, and goes negative if the stop moves
by a quarter.

None of these is a close call.

## The one candidate

**ARM F part A** — buy a sharp pullback (RSI2 < 20) in an uptrend
(close > SMA200) on spx500usd, nas100usd and de30eur, hold about four days.

```
  cleared                5 of 7
  net per trade          +0.523% after measured costs
  trades                 711 over 20.8 years
  sign consistency       +0.58% / +0.52% / +0.46% across the three eras
  matched control        +0.44% per trade over matched days
  sized at 2% risk       8.4%/yr, 10.2% max drawdown at daily resolution
```

### What is genuinely in its favour

**It cleared the matched control.** That is the gate that killed most of
episodes 1 to 3, and it is the one that matters most here. The control
compares each trade against same-market, same-era bars in the same
prior-return and volatility decile, held the same number of bars, charged
the same costs. So the +0.44% is not "indices went up for twenty years" —
a matched long hold is exactly what it is measured against.

**It is positive in all three eras and decays gently** (+0.58%, +0.52%,
+0.46%) rather than flipping, which is what every trend arm did after 2012.

**Its own author's figures reproduce independently.** Our engine, written
from the specification without reference to its results, matched its trade
count to within one and its returns and drawdown to within 1-2%.

**Its holding period is why it survives.** Four days costs 5.8bp. The trend
arms hold 27-33 nights and pay 30-62bp.

### What is against it, and none of this is small

**It failed robustness, and the failure is specific.** Move the RSI entry
from 20 to 25 and 78% of the edge survives; move the exit from 70 to 52 and
72% survives. The bar is 80%. The trend filter, ATR period, stop multiple,
limit offset and holding period are all stable at 87-106%. So the edge sits
in the RSI thresholds specifically — how deep the dip is and how far the
bounce runs. That is a narrow place for an edge to live.

**It is one idea in three instruments that move together.** 54% of entries
fire on the same day as another. The breadth failure is not a technicality;
it means a single adverse regime in equity indices hits all of it at once.

**It is long-only in markets that rose for twenty years.** The matched
control addresses this but cannot fully remove it.

**It is not a discovery.** RSI2 mean reversion above a long moving average
is a published, widely known retail strategy. That cuts both ways: better
odds it is real, worse odds it is uncrowded.

**The first unseen data was discouraging.** Ten weeks, 13 trades, +0.020%
per trade — about 4% of the backtested edge. Thirteen trades proves
nothing, but it is not encouraging either.

### What would make it tradable

Not another backtest. The twelve-month forward test registered in
`FORWARD_REGISTRATION.md`, run on paper, judged by the rule fixed before it
started. If it clears that with its edge intact, it has earned a small
live allocation and not before.

A reasonable bar, in my view: forward Sharpe above 0.5 and the per-trade
edge above 0.2% after costs, over at least 150 forward trades. At 34 trades
a year across three markets that is four years, not one — which is itself
the honest answer about how long it takes to know.

## The uncomfortable part

The strategy with the best gate result is also the one that was built by
the only arm that could see the data, searched about 280 configurations,
and produced an in-sample Sharpe that rose 0.82 -> 1.08 -> 1.23 while its
out-of-sample Sharpe sat still at 0.61 -> 0.60 -> 0.67.

By Wiecki's own finding, that search is exactly what should make its
forward performance disappoint. Our gates are a stricter test than its own
holdout, and it passed five of seven — but it is still the most heavily
searched object in the study, and the 10-week read came in at 4% of
backtest.

**The honest position: it is the only thing worth forward-testing, and the
reason it looks best is also the reason to distrust it.**
