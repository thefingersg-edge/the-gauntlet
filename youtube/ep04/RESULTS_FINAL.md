# Episodes 4/5 — final gate results, measured costs

```
RUN:    2026-11-06
DATA:   all 21 markets refreshed from OANDA's own API, common end
        2026-11-06. Hourly refreshed too.
COSTS:  MEASURED from OANDA's bid and ask streams, not assumed.
        Median (ask-bid)/mid over 07:00-21:00 UTC, 2024-01 to 2026-11,
        doubled for a round trip. See COST_MODEL.md.
        This replaces a table copied from ARM B -- one contestant's guess
        used to judge the other five. That flaw is disclosed, not buried.
```

## The scoreboard

| Arm | Cleared | Trades | Mkts | Net/trade | Gross | Cost |
|---|---|---|---|---|---|---|
| **F** part A (dip-buy) | **5 of 7** | 711 | 3 | **+0.523%** | +0.581% | 0.058% |
| **F** full (A + overnight) | **5 of 8** | 8,815 | 3 | +0.061% | +0.092% | 0.031% |
| **C** ORB intraday | **6 of 8** | 6,110 | 2 | **+0.003%** | +0.019% | 0.016% |
| D v3 trend + index MR | 2 of 7 | — | 19 | +0.013% | +0.329% | 0.316% |
| B path continuity | 2 of 7 | — | 21 | −0.091% | +0.212% | 0.303% |
| A Donchian 55/20 | 1 of 7 | — | 21 | −0.119% | +0.303% | 0.422% |
| E twin sleeve | 1 of 7 | — | 21 | −0.091% | +0.532% | 0.624% |

ARM C is scored on its own eight-gate set; the count is not comparable.

## What measuring the spread changed

The borrowed table was wrong in **both** directions:

| | borrowed (ARM B's guess) | measured | |
|---|---|---|---|
| spx500usd | 3.0bp | **1.46bp** | 2.1x too expensive |
| nas100usd | 4.0bp | **1.57bp** | 2.6x too expensive |
| de30eur | 4.0bp | **2.21bp** | 1.8x too expensive |
| de10ybeur | 6.0bp | **2.31bp** | 2.6x too expensive |
| cornusd | 25bp | **46.4bp** | 1.9x too cheap |
| natgasusd | 30bp | **43.5bp** | 1.5x too cheap |
| wheatusd | 25bp | **37.3bp** | 1.5x too cheap |

Index spreads were badly overstated and soft commodities badly understated.
Two results moved.

### ARM F's overnight sleeve is worth something after all

```
                     borrowed cost      measured cost
  gross/trade          +0.0493%           +0.0493%
  cost/trade            0.0497%            0.0285%
  net/trade            +0.0011%           +0.0208%      19x
  on notional            +0.4%/yr           +8.0%/yr
```

On the borrowed table it was 8,000 trades of nothing. Measured, it earns
about 8% a year on notional. Its own figure was "2.5-4% a year", so the
truth sits **above** both our estimate and its own.

ARM F full rises from 4 of 8 to **5 of 8** — the secondary robustness gate
now clears, because the base edge it is measured against is no longer
near-zero. Gate 3 still fails: pooling 711 trades at +0.523% with 8,104 at
+0.021% gives +0.061% against a 0.2% threshold.

### ARM C's edge flips positive, and is still not tradeable

```
                     borrowed cost      measured cost
  net/trade           -0.0158%            +0.0032%
  markets agreeing       0 of 2              2 of 2
```

It now makes money. It makes **0.3 basis points a trade**, and it still
fails two gates:

- **Sign consistency**: +0.026% in era 1, −0.012% in era 2, −0.001% in
  era 3. The effect existed and died.
- **Robustness**: moving the stop from 0.30 to 0.225 ATR turns it negative.

ARM C predicted this about itself, unprompted, in its first sentence:

> "That effect is real but small, and it has weakened in recent years.
> After costs it may be marginal."

It was right on all three counts. The gates confirm an arm's own warning
rather than contradicting it.

## What did not change

ARMS A, B, D and E are unmoved. Measured costs made ARM A and ARM B
slightly *worse* (soft commodities cost more than assumed), and left D and
E where they were. Every one still finds a positive gross edge and loses it
to costs:

```
          gross    cost      net
  ARM A  +0.303%  0.422%  -0.119%
  ARM B  +0.212%  0.303%  -0.091%
  ARM E  +0.532%  0.624%  -0.091%
  ARM D  +0.329%  0.316%  +0.013%
```

## The finding, restated on measured costs

**Six arms, six positive gross edges, and the survivors are the two that
hold positions briefly.** ARM F's dip-buy holds four days and pays 5.8bp.
ARM F's overnight sleeve holds one night and pays 2.9bp. The four trend
arms hold 27-33 nights and pay 30-62bp — more than their entire gross
edge.

Measuring the spread did not change that conclusion. It changed which side
of zero two marginal strategies sit on, and both of those were index
strategies penalised by a guess that was twice the real cost.

**That is the strongest argument in the study for measuring rather than
assuming**, and it cuts against our own earlier result, which is why it
belongs on screen.
