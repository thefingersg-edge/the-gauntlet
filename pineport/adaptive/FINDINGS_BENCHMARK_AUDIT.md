# Benchmark audit — what everything in this project was measured against

Run 2026-08-27, prompted by the right question: if no signal works, someone
would have noticed. **They have.** And separately, the benchmark that beat
everything here was wrong.

---

## Part 1 — the external record agrees with the null results

The findings in this project are not anomalous. They are what the replication
literature reports.

**Time-series momentum.** Huang, Li, Wang and Zhou (2018) re-ran Moskowitz, Ooi
and Pedersen's canonical 2012 paper with bootstrapped critical values. The
original t-statistic of **4.48 fails the corrected 95% threshold of 4.96**, and
out-of-sample R² across their tests is "generally negative, with seldom
exceptions". Their conclusion: the evidence for TSM "is quite weak, especially
for the large cross section of assets". That is the same result Part A reached
independently — signals that look strong in-sample and vanish out of it.

**Chart patterns.** The Cambridge study of automated head-and-shoulders trading
on eight years of GBP/USD tick data found slippage-adjusted profits
**consistently negative at every frequency tested** — −31 pips daily, −37 pips
at one minute, on 2,099 trades. Filters improved 69% of cases and still "rarely
to the extent that the loss-making strategy becomes profitable." Part B2 and B3
reached the same verdict across 32 constructions.

**So the honest answer to "surely someone would have noticed" is that they did,
and this project independently reproduced their conclusions.**

## The strongest evidence on the other side, and why it does not contradict this

AQR's *A Century of Evidence on Trend-Following Investing* builds a time-series
momentum strategy back to **1880** — roughly 110 years — across nearly all
equity index, fixed income and commodity futures and currency forwards, and
reports it "consistently profitable" over that span.

That is not in conflict with anything measured here. It is the noise-floor
argument restated:

| | market-years | smallest resolvable Sharpe |
|---|---|---|
| **this project** | **147** | **0.165** |
| AQR's century study | ~7,000+ | roughly 0.02 |

**Their sample can resolve effects fifty times smaller than mine can.** The
correct conclusion from this work was never "trend following does not work". It
is "an effect of the size trend following plausibly has is invisible in 21 years
of 21 correlated markets" — which is exactly what 19 null results look like.

---

## Part 2 — the benchmark was wrong, and it flatters itself

Every comparison in Parts C, H and I used **"buy and hold an equal-weight basket
of 21 CFDs, held long"**. Three things are wrong with that.

### It is gross of financing

A long CFD position pays overnight funding. The fed funds rate averaged
**1.86%** over 2005–2026.

| | Sharpe | annual return |
|---|---|---|
| buy and hold, as measured | +0.582 | +4.51% |
| …charging funding only | **+0.365** | **+2.67%** |
| …funding + a 2% retail CFD spread | **+0.120** | **+0.65%** |

The benchmark that "beat everything" returns 0.65% a year once it is paid for.

### Seven of the twenty-one are FX pairs held long, arbitrarily

FX pairs have no expected drift, and the choice to hold EURUSD long rather than
short is a coin flip I made by construction. Those seven return **+0.24%** a
year. Excluding them lifts the benchmark to +6.33% gross — so the basket is
simultaneously padded with directionless positions *and* understated by them.

### It is concentrated in three markets

| | annualised |
|---|---|
| Nasdaq, DAX, gold | **+9.56%** |
| the other eighteen | **+2.10%** |

"Buy and hold the basket" is, in substance, *own equities and gold* with
eighteen markets of noise attached. Natural gas returns −2.56% before any roll
cost, and a real long position in it would be far worse.

---

## Part 3 — what this does to the conclusions

Re-running the Part I ladder with funding charged on net exposure:

| rung | gross | + funding | + funding & 2% spread |
|---|---|---|---|
| 0 · buy and hold | +0.582 | **+0.365** | +0.120 |
| 1 · + trailing-vol sizing | +0.635 | **+0.115** | −0.413 |
| 2 · + implied-vol sizing | +0.649 | **+0.120** | −0.416 |
| 3 · + sign(A) direction | +0.281 | +0.199 | +0.140 |
| 4 · + real-yield overlay | +0.257 | +0.175 | +0.116 |

**Part I's result reverses.** Rung 2 beat buy-and-hold gross, +0.649 to +0.582;
charged for funding it loses, +0.120 to +0.365.

The reason is straightforward and I should have seen it: **volatility targeting
to 10% against a basket whose natural volatility is 8.16% requires leverage, and
leverage costs money.** The matched-volatility comparison in Part I — levering
rung 2 by 2.29× to reach the benchmark's volatility — quietly assumed 2.29× of
borrowed exposure at no cost. At 1.86% funding that is **4.3% a year of drag
against a 5.09% return.** The drawdown improvement was real; the return
comparison alongside it was not.

The long/short rungs (3 and 4) hold up better under funding because their net
exposure is small and two-sided, which is the one thing the audit says in their
favour.

### What survives the audit unchanged

**The calibration result.** F/G measured how closely realised volatility tracks
a target — a forecasting question, not a return question. Funding costs do not
enter it. Dispersion falls 22%, the bootstrap excludes zero in 3 of 4 markets,
and it replicated. That claim is untouched.

Which sharpens the summary rather than changing it: the project's one durable
finding is a **volatility forecasting** result, and it was never a return result
in the first place.

---

## What was actually being measured, stated plainly

**Spot and CFD price series that embed neither funding nor roll yield.**
Everything in this project is gross of carry. Real implementations differ:

- **Futures** returns are already excess returns — funding is in the price — so a
  futures implementation would look different again, and better for the long/short
  rules than this audit suggests.
- **CFDs** charge funding on long notional and pay a lower rate on shorts, which
  is roughly what the table above models.
- **Commodity longs** pay roll costs the spot series never shows. Natural gas is
  the extreme case and it is in the basket.

**The implementation vehicle was never specified, and it turns out to matter more
than most of the signals tested.** That belongs in the gauntlet.
