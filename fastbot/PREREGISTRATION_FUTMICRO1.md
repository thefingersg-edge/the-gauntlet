# PREREGISTRATION — FUTMICRO1: can a $50k account hold the trend sleeve with micro and mini futures?

```
STATUS:   frozen before any FUTMICRO1 number is computed (sha in PROVENANCE.md). The harness is frozen separately before its one run.
WRITTEN:  2026-10-12 (Dave: "pre register everything that we can take forward")
ORIGIN:   FUTPORT1. The trend sleeve made Sharpe +0.44, positive in every era, but whole-contract rounding needs about $1m. Below $100k it barely trades.
DATA:     on disk: data/futport1 (sha-verified). No new pull.
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

## Universe: the 17 markets with a micro or mini contract (fixed)
| root | contract | $ per 1.0 of quoted price | tick value |
|---|---|---|---|
| ES / NQ / YM / RTY | MES / MNQ / MYM / M2K | 5 / 2 / 0.5 / 5 | $1.25 / $0.50 / $0.50 / $0.50 |
| GC / SI / HG | MGC / SIL / MHG | 10 / 1000 / 2500 | $1.00 / $5.00 / $1.25 |
| CL | MCL | 100 | $1.00 |
| 6E / 6A / 6B / 6J / 6C / 6S | M6E / M6A / M6B / MJY / MCD / MSF | 12,500 / 10,000 / 6,250 / 1,250,000 / 10,000 / 12,500 | $1.25 / $1.00 / $0.625 / $1.25 / $1.00 / $1.25 |
| ZC / ZS / ZW | XC / XK / XW (CBOT mini, 1,000 bu) | 10 | $1.25 |

Rates, PL, NG, HO, RB, ZL, ZM, LE and HE are excluded: they have no retail-sized contract.

## Construction
- **Signal:** the trend signal, σ and weights exactly as FUTPORT1, on these 17 markets.
- **Sizing:** the sleeve is scaled to 10% annual volatility (the 3× cap applies). Each market's target $ notional = capital × sleeve weight.
  - Contracts = round(target / (|price| × multiplier)), recomputed daily. Only changes of whole contracts are traded.
- **Costs:** per contract per side, 1 tick + $0.85 commission. Each roll, every held contract pays 2 sides.
- **Capital:** $50,000 primary; $25,000 and $100,000 reported. Fixed capital, not compounded.

## Gates ($50k)
- **G1:** net Sharpe ≥ 0.30 over the live period (the same start as FUTPORT1).
- **G2:** net positive in each era: 2010–15, 2016–20, 2021–26.
- **G3 (holdability):**
  - daily P&L correlates ≥ 0.80 with the same 17-market sleeve held fractionally; AND
  - realised volatility is between 6% and 14%; AND
  - initial margin is ≤ 50% of capital on ≥ 95% of days. The margin proxy is 8% of gross notional, about the CME micro index and FX range.

## Reported (no gates)
- the 17-market fractional sleeve;
- contracts held per day;
- the share of days each market holds 0 contracts;
- turnover;
- the worst drawdown in $.

## Prediction
- Sharpe 0.2–0.4 (fewer markets than FUTPORT1).
- **G3** is likely to pass at $100k and borderline at $50k.
- **G1** borderline.
