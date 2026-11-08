# The buffer was mine, not Kraken's — and the candidate survives

```
RUN:      2026-08-19
METHOD:   kraken_collateral.py v1.2 (Phase 0) + kraken_basis.py v1.1 with
          --buffer 0.0 (Phase 1), PREREGISTRATION_v7
DATA:     the SAME 18 quarterly cycles as v4, 2021-08-27 -> 2026-06-26.
          No returns recomputed. One input corrected.
VERDICT:  PROCEED. Gate A +3.64 pts, Gate B +0.7/+8.2/+2.7, Gate C 18
          cycles. The first pass in twenty-four investigations -- and it
          is a counterparty-risk result, exactly as v4 section 12 fixed
          in advance.
```

---

## 1. What was wrong

`PREREGISTRATION_v4` §8 specified a **USD** collateral buffer sized to
survive the worst observed rally of 73.5%. That multiplied committed
capital by 1.73× and turned +3.75 points of excess into +0.53. It was the
entire rejection, and `RESULT_KRAKENBASIS` recorded at the time that the
assumption might be wrong.

It was wrong. **Kraken still lists inverse dated BTC contracts** —
`FI_XBTUSD_260828`, `260925`, `261225`, all tradeable — and an inverse
future is margined in BTC. The loss and the collateral are the same asset.
There is no conversion, so there is no haircut, and the buffer I imposed
does not exist.

## 2. The arithmetic, because this was decided by it and not by reading

With collateral `M = N/F_entry`:

```
equity   = M - N/F_entry + N/F = N/F
notional = N/F
```

**Equity equals notional at every price.** Liquidation requires
`u < (N/F_entry − M) / (N(1 − mmr))`, whose numerator is zero when fully
collateralised — so no positive price satisfies it:

```
collateral 100% of notional  ->  NEVER liquidated by an upward move
collateral  90% of notional  ->  liquidated at 9.90x entry
collateral  75% of notional  ->  liquidated at 3.96x entry
```

The under-collateralised rows matter as much as the first: a branch that
could only ever return "safe" would not be a test.

## 3. A caveat of mine that had to be retracted

v1.1 of the probe warned that the hedge drifts and needs rebalancing.
**It does not**, and the correction favours the candidate, which is why it
is recorded rather than dropped:

| price | equity BTC | notional BTC | ratio |
|---|---|---|---|
| 12,500 | 4.0000 | 4.0000 | 1.0000 |
| 50,000 | 1.0000 | 1.0000 | 1.0000 |
| 1,000,000 | 0.0500 | 0.0500 | 1.0000 |

The position stays exactly fully collateralised in both directions with no
trades, and the equity's **USD value is constant at N**. That is the
cash-and-carry: BTC converted into synthetic USD, delta-neutral by
construction.

What survives is narrower — mid-life the equity is marked at the *futures*
price, so its spot value moves with F/S until convergence. v4 §1 already
named that.

## 4. The result

```
[PASS] Gate A  net excess over T-bill >= 2.0 pts    +3.64 pts
[PASS] Gate B  positive in EVERY era                +0.7  +8.2  +2.7
[PASS] Gate C  >= 12 cycles, >= 3 per era           18 cycles, 6/6/6
```

Same returns, same window, same costs, same gates. One input.

## 5. And now the parts that should temper it

**Two cycles carry nearly half of it.** The quarters ending 2024-03 and
2024-06 — the spot-ETF launch — returned **+14.8 and +22.2 points**.

```
all 18 cycles                    +3.74 pts
drop those two                   +2.04 pts   -- still passes, barely
median cycle                     +3.40 pts vs a +3.74 mean
```

It survives their removal, which is the honest test, but by four basis
points over the bar. **The premium is real and it is lumpy.**

**Six of eighteen cycles lost to Treasury bills**, two of them by more
than five points.

**Era 1 came in at +0.7 points.** Gate B asks only for a positive sign, as
pre-registered. Held to Gate A's own 2.0-point threshold, the first third
of the sample would not have cleared it.

**Convergence is still not clean.** The largest index-to-future gap at
expiry is 1.41% of spot and the realised column sits above the quoted by
+0.37 points on average — a small tailwind that may be an artefact of the
last daily candle not being the settlement print.

## 6. What this is, stated as v4 fixed it in advance

`PREREGISTRATION_v4` §12, written before any of this:

> If all four gates pass, this is **not** a green light to trade. It is a
> green light to price the things this measurement cannot see… A pass here
> produces a **counterparty-risk result**, and that is a question about a
> venue, not about a premium.

That is precisely where this lands, and the inverse structure **sharpens**
the point rather than softening it. The mechanism that removes the buffer
is that your BTC sits on the exchange *as margin*. The capital efficiency
and the counterparty exposure are the same fact viewed twice.

The 2.0-point bar was set in v4 §2 as one point of insurance against a 1%
annual chance of total loss plus one point of compensation. At +3.64 the
trade pays that insurance and about 2.6 points beyond it. **Whether 1% is
the right number is not measurable from price data and never will be.**
Mt Gox, QuadrigaCX and FTX are the base rate, and auto-deleveraging can
close a profitable short exactly when counterparties are failing.

## 7. Verdict

**The premium is real, the capital requirement I imposed was not, and what
remains is a bet on a venue rather than on a market.**

Twenty-four investigations have produced one candidate that clears its own
pre-registered gates. It clears them on a mechanism that is arithmetically
exact, over a window containing a bear market, with six losing quarters and
a concentration in one extraordinary half-year.

The next honest step is not a bigger backtest. It is the same question
`RESULT_VRP` reached from a different direction: **the remaining risk has a
price that no amount of history can estimate.** A forward-committed rule at
small size would produce evidence that hindsight cannot contaminate, and it
is the only kind of evidence left worth collecting.

## 8. Scoreboard

**Twenty-four investigations. Nineteen rejections, one
measured-but-unreachable premium, one headline that dissolved on
decomposition, one real premium whose edge vanished at daily resolution,
and one — the crypto dated basis — that passed every pre-registered gate
once an assumption of mine was corrected.**

The rejection it replaces was mine, not the market's. That is worth as
much as the pass.
