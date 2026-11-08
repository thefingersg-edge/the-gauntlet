# The variance risk premium — it is real, and that is not the same as tradeable

```
RUN:      2026-08-17
METHOD:   vrp_budget.py — MEASUREMENT ONLY, no strategy simulated
DATA:     VIX 1990-2026 (CBOE); SPX proxy from the OANDA spx500usd M5 file
          already on disk, 2005-2026, 259 non-overlapping monthly observations
VERDICT:  the premium EXISTS at 10 sigma. Unhedged it is worse than equity
          beta. The tradeable version cannot be priced from this data.
```

---

## 1. The first positive result in this project

Fifteen hypotheses have now been rejected. This is not one of them.

```
VRP in vol points   mean +3.60   median +4.50   positive in 81% of months
sign test                        z = 10.0 sigma      209 up months vs 49 down
```

Implied volatility exceeds subsequent realised volatility in four months out
of five, across every era measured, for a stated economic reason: people pay
for crash insurance and someone has to sell it. **The existence of this
premium is not in question** and never was — it is one of the best-documented
effects in finance. Measuring it here confirms the apparatus can find a real
effect when one is present, which after fifteen nulls is worth knowing on its
own.

## 2. And now the number that matters

```
implied Sharpe of selling variance, unhedged, unlevered:   +0.32
skew:                                                      -6.66
worst month:  -0.83046 var points  (2020-03)  =  10.9 standard deviations
```

A symmetric distribution puts its worst-in-260 observation near 3 sd. This one
is at **10.9**.

What that costs, in units of the thing you are accumulating:

| month | IV | RV | payoff | months of average gain destroyed |
|---|---|---|---|---|
| **2020-03** | 33.4 | 97.1 | −0.8313 | **117 months — 9.7 years** |
| 2008-10 | 39.8 | 84.0 | −0.5472 | 77 months — 6.4 years |
| 2008-11 | 53.7 | 75.8 | −0.2862 | 40 months |
| **2025-04** | 21.8 | 48.5 | −0.1877 | 26 months |

March 2020 erased **nearly a decade** of average monthly accumulation in one
month. And note the fourth row: this is not a museum piece. The tail fired
**sixteen months ago**.

### Against the only benchmark that counts

| | Sharpe | skew |
|---|---|---|
| selling variance, unhedged | **+0.32** | **−6.66** |
| equity beta | +0.40 to +0.50 | ~−0.5 |

**More tail risk for less return.** `DESIGN_BRIEF.md` wrote *"Equity beta has
paid ~0.4–0.5 Sharpe for a century with an undisputed mechanism. Eleven
strategies failed to beat it."* Make that sixteen.

## 3. The era table is the most instructive thing here

```
2000-2009    Sharpe +0.10     includes 2008
2010-2017    Sharpe +1.34     no crash
2018-2026    Sharpe +0.21     includes 2018, 2020, 2025-04
full sample  Sharpe +0.32
```

**That +1.34 is the number that sold short volatility to an entire
industry.** Eight years, no crash, a Sharpe most strategies never see. Funds
launched on it, ETPs were built on it, and in February 2018 one of them —
XIV — lost most of its value in a single session.

Anyone measuring this premium in 2017 would have found +1.34 and a smooth
equity curve. The full-sample answer is +0.32. **The difference is not skill,
analysis or timing. It is which decade you happened to sample.** This project
has spent fifteen tests guarding against fitting a strategy to a period; here
is the same failure available to someone who fits a *risk appetite* to one.

## 4. What this measurement cannot see — and it is the whole strategy

The published tradeable version is **not** naked short variance. Quantpedia's
Sharpe 1.16 comes from *"sell the ATM straddle, buy 15% out-of-the-money puts
as insurance against a market crash."* The hedge is what turns an
unacceptable distribution into a business.

**This measurement cannot price that hedge.** VIX gives one number per day. A
15%-OTM put is priced off the volatility *skew*, and the skew is exactly what
steepens when you need the hedge. Estimating the hedged strategy requires the
SPX option surface, which is a genuine data purchase — OptionMetrics, ORATS or
CBOE DataShop, in the thousands, not a free CSV.

> So the honest position: **the premium is measured, the strategy is not.**
> Unhedged it is worse than buying the index. Hedged it may be better, and
> nothing here can say by how much. A premium whose economics depend entirely
> on a hedge you cannot price is not yet a candidate.

## 5. Access, which has not moved

```
OANDA   no listed options, no futures
Kraken  crypto perpetual and dated futures, no equity options
```

Harvesting this needs an options broker that neither account provides. So the
full path is: buy surface data, open a broker, then pre-register. That is a
real commitment of money and time, and it should be made on evidence rather
than on a +1.34 that belonged to 2010–2017.

## 6. What I would conclude

**The premium is real, persistent and economically motivated — and on this
evidence it is not obviously worth harvesting at retail scale.** The unhedged
form loses to the index on both axes. The hedged form is unmeasured and needs
paid data to measure.

That is not a rejection. It is a **cost-of-information** result, which is a
category this project has not produced before: the next honest step has a
price tag, and the measurement says the price is not yet justified.

**Meanwhile the same economic structure — being paid to bear something rather
than to predict — is accessible today on an account already open.** Crypto
basis and funding on Kraken: dated futures trade at a premium to spot for the
same reason implied vol exceeds realised, and silver15 already measured the
funding leg and found it real (+1.46% against T-bills at 3.66% — rejected on
*size*, not existence). Two things have changed since: that measurement was
funding only and never touched the dated-futures basis, and rates have moved.

## 7. Scoreboard

**Sixteen investigations. Fifteen rejections and one measured premium that
cannot yet be reached.**

| | result |
|---|---|
| silver15 ×11, pineport, fastbot v1/v2/v3 | rejected |
| **variance risk premium** | **real at 10σ; unhedged worse than equity; hedged unpriceable without paid data** |

The apparatus found a genuine effect the moment one was actually present.
After fifteen nulls, that is the most reassuring line in this document.
