# "95% of traders lose money": where the real number sits, and how big our haystack is

```
WRITTEN:  2026-10-09        TYPE: literature review + our own registry count (no new test)
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

## Short answer
"95%" is folklore. No single study produced it, and the number changes a lot depending on what "lose" means and over what period. The real figures sit either side of it:

| question | best evidence | number |
|---|---|---|
| What share of retail CFD/FX accounts lose money over a year? | ESMA (2018), summarising national regulators | **74–89%** |
| …at OANDA specifically? | OANDA's mandatory risk warning (entity not stated on the page) | **73.5%** |
| What share of day traders are profitable in a given period? | Barber, Lee, Liu & Odean, Taiwan 1992–2006 | **about 5%** (and >75% quit within 2 years) |
| What share can *predictably* profit year after year, net of fees? | Barber, Lee, Liu & Odean (2014), *Journal of Financial Markets* | **<1%** |
| Of people who day-trade persistently (≥300 days)? | Chague, De-Losso & Giovannetti (2019), Brazil mini-index futures | **97% lost money; 0.4% earned more than a bank teller** |
| Of prop-firm challenge buyers? | The Funded Trader (Mar 2025); FPFX Tech (300k accounts) | 5–10% pass; about 20% of those get a payout; **1–2% ever paid** (FPFX: 7%) |
| Professionals: active US large-cap funds trailing the S&P 500 | SPIVA (S&P Dow Jones), year-end 2024 | **84% over 10 years, 90% over 15, 92% over 20** (79% in 2025 alone) |

**How to read it:**
- **Over any single year, 70–90% of retail leveraged accounts lose.** The minority who win in a given year are mostly lucky. When the same people are followed over time, the winners don't stay winners.
- **The meaningful number is the bottom row of the retail evidence:** fewer than 1 in 100 show *repeatable* skill after costs, and fewer than 1 in 200 persistent day traders earn a modest wage from it.
- **Even full-time professionals with research teams mostly fail to beat simply holding the index** over long horizons.

So the honest replacement for "95% lose" is: **most lose in any year; about 99% fail over several years; the persistent winners are a fraction of 1%.**

## Why so many lose (the mechanics, all of which we have measured ourselves)
1. **Costs come first, and they are certain.** Spread plus financing is a guaranteed loss on every trade, while any edge is uncertain. Our 1–15-minute tests (v1, v2, TF1) mostly lost *before* costs and always after.
2. **Direction calls are close to coin flips.** REGIME1/2 and CYCLES1 show that even the "obvious" tools (moving averages, ADX, the bull/bear label itself) don't tell next-day or next-week direction. The bear-market label arrives about 10 months late, with 70% of the fall already done.
3. **Leverage turns a small negative edge into a fast blow-up.**
4. **Survivorship in what people see.** Winners post; losers quit quietly (>75% quit within two years in Taiwan).

## Our own haystack
| | count |
|---|---|
| pre-registered studies with a written result (fastbot 92, flows 13, silver15 7) | **about 112** |
| individual hypotheses tested inside them (patterns × sides × timeframes, gates, eras) | **roughly 1,000** |
| short-interval directional signals that passed and survived re-checks | **0** |
| ideas that passed and look real | **about 4**, all *risk premia / carry*, not prediction: VIX futures carry (~0.4 Sharpe, every era), the variance risk premium (real, needs hedging), crypto basis carry (PROCEED), the Treasury-refunding flow (flows, all gates passed) |
| ideas that worked in old data and died once known | gold fix, spin-offs, PEAD (pre-2013), Kurov drift (dead after 2015) |

**What the haystack says:**
- At a 5% false-positive rate, ~1,000 hypotheses would produce **about 50 false "winners"** if we didn't correct for multiple testing. That is exactly how most backtested systems sold online are made. Our strict gates (Bonferroni, beating random entries, every era) exist so that we don't fool ourselves the same way.
- Our pass rate for genuine directional prediction at short intervals is **0 in roughly 1,000**. That matches the academic <1%: the needle, if it exists for retail, is not in bar patterns, structure or trend indicators.
- The ideas that survive are **getting paid for carrying a risk other people want to offload** (volatility, basis, funding). They are not about knowing where price goes next. That is where the remaining search effort is best spent.

## Sources
- ESMA press release, 27 Mar 2018: retail CFD losses 74–89%. https://www.esma.europa.eu/pl/node/84933
- OANDA risk warning (73.5%), via ForexBrokers.com review. https://ForexBrokers.com/reviews/oanda
- Barber, Lee, Liu, Odean (2014), "The cross-section of speculator skill: Evidence from day trading", *J. Financial Markets* 18:1–24. https://ideas.repec.org/a/eee/finmar/v18y2014icp1-24.html
- Barber, Lee, Liu, Odean, "Do Day Traders Rationally Learn About Their Ability?" (Taiwan 1992–2006). https://faculty.haas.berkeley.edu/odean/papers/day%20traders/day%20trading%20and%20learning%20110217.pdf
- Chague, De-Losso, Giovannetti (2019), "Day Trading for a Living?" https://ideas.repec.org/p/fgv/eesptd/525.html
- Finance Magnates (18 Mar 2025), prop-firm pass and payout rates. https://www.financemagnates.com/forex/only-1-in-20-traders-pass-prop-firm-challenges-reports-the-funded-trader/
- SPIVA U.S. Year-End 2025 (S&P Dow Jones Indices). https://www.spglobal.com/spdji/en/spiva/article/spiva-us-year-end-2025/ ; long-horizon figures (YE2024) via https://walnutinvest.com/stats/active-fund-underperformance-spiva
