# RESULT — OILIMP1: the oil carry is holdable on a $10k CFD account on paper; Micro futures at $10k are too lumpy

```
SPEC:     PREREGISTRATION_OILIMP1.md  sha 923437de…  (frozen 2026-10-11, before any number)
METHOD:   scripts/oilimp1_run.py  sha 54fa0e18…  (self-test reproduces the roll-fixed OILCARRY1 Sharpe +0.54)
DATA:     EIA WTI futures 1-3, 1986 -> 2024-04-05; OANDA WTICO spreads (median 5.6 bp at 10:00 NY, 2013-24, used where missing)
RUN:      2026-10-11, once.   LOG: data/run_oilimp1.log
VERDICT:  route C (OANDA CFD) PASS;  route M (Micro WTI futures, $10k) FAIL on G2 and G3
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

| $10,000 account, 1987 → 2024-04 | Sharpe (× √37 yrs) | per year | worst drawdown | eras 1987–04 / 05–14 / 15–24 | verdict |
|---|---|---|---|---|---|
| **C: OANDA CFD**, admin fee 2.5% | **+0.49 (2.97)** | +5.5% | −$2,516 | +$13,587 / **+$928** / +$5,896 | **PASS** (G1–G4) |
| C at fee 1.5% / 3.5% | +0.51 / +0.46 (2.82) | +5.8% / +5.2% | | | G4 holds at 3.5% |
| M: Micro WTI (MCL), whole contracts | +0.40 (2.43) | +5.9% | **−$4,569** | +$14,351 / **−$1,800** / +$9,234 | FAIL (G2, G3) |
| M at $25k / $50k | +0.53 / +0.46 | +6.0% / +5.4% | −$6,412 / −$12,334 | all eras positive | reported |
| E: CRUD ETC long or flat | +0.48 | +3.0% | −$2,734 | +$9,432 / +$148 / +$1,441 | reported |

## Read it plainly
- **Lumpy contracts hurt the futures route at $10k.**
  - One MCL is about $6–8k of oil, so the $10k account held 0 contracts in 36% of months and 1–3 in the rest.
  - Rounding pushed the drawdown to −$4.6k and turned 2005–14 negative.
  - At **$25k** the rounding problem mostly disappears: Sharpe 0.53, every era positive, 0-contract months only 5%.
- **The CFD route can size exactly**, so it keeps the premium: Sharpe 0.49 at a 2.5% admin fee and 0.46 at 3.5%.
- **The weak spot is 2005–14:** +$928 over ten years on $10k. Most of the money came from 1987–2004 and 2015–24.
- **April 2020** (the negative-price month) added +$3,008 to the CFD route. Its worst month was Nov 2014 (−$865).

## The big caveat
- The CFD route assumes OANDA's daily commodity financing **exactly offsets the futures basis** and adds a flat admin fee, as OANDA describes it.
- If that offset is imperfect, the CFD return differs from the futures carry. **We have never measured it.** The forward record will show it.
- **Before any money, a second check is needed:** record OANDA's actual WTICO financing (read-only, `oanda_financing.py`) next to the futures curve for a few months, and compare.

## What runs now (paper only)
- **forward_oilcarry.py**, step 9 of the Mac tick:
  - a monthly signal from 2026-10-30, plus daily paper marks for MCL ($10k/$25k/$50k) and the CFD;
  - it needs a one-off `--seed` pull from Databento.
- **`oilimp1_run.py oos`** runs once after the seed. It checks Databento's CL against EIA for 2010–24, then reports the 2024-04 → 2026-09 stub. That stub has not been seen yet.
- **Review at 24 months (2028-10):** KEEP only if the forward Sharpe is above the 5th percentile of the backtest's 24-month blocks.
