# The cost and margin budget — the premium is real and the trade is out of reach

```
RUN:      2026-08-18
METHOD:   vix_carry_budget.py v1.2 — SIZING ONLY, no strategy simulated
DATA:     VX1! vs VX2!, TradingView, 269 months, 2004-03 to 2026-07
ACCOUNT:  $10,000, 30% maximum drawdown, 2-tick roll, $1.50 per fill
VERDICT:  binding size 0.63 mini contracts. The minimum tradeable position
          is 1. At plausible cash rates the risk-matched return beats
          owning the index by about half a percentage point of account,
          before the risks the measurement cannot see.
```

---

## 1. The answer to the question that was asked

`RESULT_VIXCURVE.md` ended by saying the next honest step was a cost and
margin budget: *"what the roll costs, what margin does in a 2008 or 2020
month, and what position size survives a −24 with the account intact."*

```
gross premium      +0.88 vol pts/month
roll (2 ticks)     -0.10
commission (2x)    -0.03
NET                +0.75 vol pts/month   = 15% of gross eaten by cost
```

Cost is not what kills it. **Size is.**

```
worst drawdown          -47.57 vol pts  = $4,757 per mini contract
size within a 30% budget  0.63 contracts
minimum tradeable         1.00 contracts
```

At $10,000 the smallest position the exchange will sell you already risks
**48% of the account** in a repeat of the worst observed episode. The full-size
VX contract needs roughly $160,000 before it fits.

## 2. And a bigger account does not make it a better trade

This is the part worth being clear about, because it is easy to assume the
problem is just that the account is small.

Premium and drawdown both scale linearly with contracts, so **return on
account at a fixed drawdown budget is size-invariant**:

```
5.6% net per year, at $10,000 or at $10,000,000
```

A larger account does not improve the return. It only makes the contract
granularity workable. What you are buying, at any size, is 5.6% a year on
top of whatever the collateral earns, in exchange for a 30% drawdown budget.

## 3. Against the only benchmark this project accepts

`DESIGN_BRIEF.md` has rejected everything so far on the same test: beat
equity beta or do not bother. Run properly for once — the same window, the
same drawdown budget, both sides as excess returns:

```
SPX 2005-01 to 2026-07    price return 9.0%/yr    worst drawdown -52.5%

  cash    index excess    sized to 30%    VIX carry    winner
   0%          11.0%            6.3%          5.6%     index
   2%           9.0%            5.1%          5.6%     carry
   4%           7.0%            4.0%          5.6%     carry
```

Average 3-month T-bill over this window was roughly 1.7%, so the honest
reading is the middle row: **the carry wins by about half a percentage
point of account.**

That is the entire margin. It has to pay for a futures broker neither
account provides, a minimum position size the account cannot reach, and
three risks below that the measurement cannot see.

## 4. The drawdown is not the shape I assumed

I expected the worst episode to be the two-month 2008-10/2008-11 sequence,
about −37. It is not.

```
    from    trough     depth   to trough   to recover
  2007-01   2008-11   -47.57       22 mo        35 mo
  2019-12   2020-03   -35.30        3 mo        14 mo
  2011-06   2011-09   -22.30        3 mo         7 mo
  2015-07   2015-08   -14.60        1 mo         9 mo
  2018-09   2018-12   -12.70        3 mo        14 mo
```

The worst drawdown **began in January 2007** — fourteen months before the
crisis was visible to anyone — took 22 months to reach its low and 35 months
to get back to even. Peak to peak, that is **four years and nine months.**

**55% of all months were spent below a previous peak.**

`RESULT_VIXCURVE.md` said the premium is positive in all three eras, and
that is still true. It is also compatible with spending most of an era
underwater, and those are very different things to live with. An era being
positive is a statement about its endpoints.

## 5. February 2018 — the oddity, resolved and not reassuring

`RESULT_VIXCURVE.md` flagged that February 2018 does not appear in the worst
months despite XIV losing ~96% that month, and said it needed resolving
before sizing anything.

It does not appear in the worst five **drawdowns** either. The nearest
episode is 2018-09 to 2018-12 at −12.70.

Two reasons, and only one of them is comfortable.

**The comfortable one.** XIV was a daily-rebalanced constant-notional
product. A fixed short futures position is not, and does not compound its
losses the same way. The ETP's mechanics were a large part of the −96%.

**The uncomfortable one.** The measurement is monthly. VIX futures spiked
and substantially retraced *inside* February 2018, and a month-end mark
cannot see a path that round-trips within the month. A margin call is
triggered by the path.

So the monthly series is not evidence that February 2018 was survivable.
It is evidence that a monthly series cannot answer the question.

## 6. What the budget cannot see, stated plainly

- **Margin is an estimate.** $1,100 per mini contract with a 2.5× stress
  multiple. SPAN margin on a volatility product rises with volatility and
  can be raised intraday. This is the documented mechanism by which people
  are closed out at the low rather than riding through.
- **The worst observed drawdown is not a bound.** 2008 and 2020 were not
  the largest possible shocks, and −47.57 is the maximum of 269 draws.
- **The quoted spread is widest in exactly the months that produce the
  worst episodes**, and only 2 ticks are charged here.
- **Monthly marks understate the drawdown.** See §5. This one is now being
  measured rather than assumed — `vix_daily_risk.py`.

## 7. A note on the premium construction, which turns out to be roll-clean

Worth recording because it looked like a bug and is not. The premium is
built as `slope − actual` from a *continuous* front-month series, and a
continuous series jumps at every roll — normally a serious contamination.

But the algebra cancels it:

```
premium = (F2_t - F1_t) - (F1_{t+21} - F1_t) = F2_t - F1_{t+21}
```

and if exactly one roll falls inside those 21 trading days, `F1_{t+21}` is
the very contract that was `F2_t`. So the measure is precisely the P&L of
shorting the second month and closing it as the front month. Correct by
construction.

The caveat is the "exactly one roll" clause. VX cycles average about 21
trading days but are not always 21, so some windows contain none or two,
and those observations reference the wrong contract. The daily
reconstruction does not rely on the coincidence.

## 8. Verdict

**The premium is real and the trade is not reachable.**

Nineteen investigations. This one is not a rejection of the *effect* —
`RESULT_VIXCURVE.md` stands, and it remains the only thing measured across
silver15, pineport and fastbot that keeps its sign through two crises. What
the budget rejects is the *trade at this account size*, on three grounds
that are each sufficient on their own:

1. the minimum position exceeds the risk budget by 60%
2. the risk-matched margin over simply owning the index is ~0.5pp of
   account, size-invariant, and does not improve with capital
3. it needs a futures broker that neither OANDA nor Kraken provides

**What would change the answer:** a materially larger account, or evidence
that the drawdown is smaller than the monthly measure suggests. The second
is cheap to check and is checked next. The first is not a research question.

## 9. Scoreboard

**Nineteen investigations. Fifteen rejections, one measured-but-unreachable
premium, one headline that dissolved on decomposition, one real premium that
survived its crisis eras — and one budget that says the real premium cannot
be traded on this account.**
