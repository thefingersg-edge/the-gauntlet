# RESULT — IMB2: one second late, the 15:50 imbalance still pays on paper, but almost all of it came from 2020

```
SPEC:     PREREGISTRATION_IMB2.md  sha e6344bc1…  (frozen 2026-10-08, before any data)
METHOD:   scripts/imb2_run.py (sha in PROVENANCE)
DATA:     Databento imbalance messages with arrival timestamps (950,438 first messages, 2,098 days, 2018-05 → 2026-09);
          SPY and ES top-of-book at fixed offsets from 15:50:00.000
RUN:      2026-10-11       LOG: data/imb1/run_imb2.log
VERDICT:  G1 PASS (net +1.31 bp, t 3.15, n 487)   G2 PASS (eras +4.63 / +0.10 / +0.27)   -> PASS, as registered
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

## How fast the information arrives
| | value |
|---|---|
| imbalance messages, arrival after 15:50:00 | median 193 ms; 90% within 578 ms; 99% within 879 ms |
| share of imbalance dollars published by 50 / 100 / 250 / 500 / 1,000 ms | 39% / 54% / 74% / 88% / 100% |

SPY mid-price move on signal days (|z| ≥ 1), signed by the signal, measured from 15:50:00.000:
```
50 ms +2.3   100 ms +3.1   250 ms +3.8   500 ms +4.2   1 s +4.2   2 s +4.5   5 s +4.7   15 s +5.3   60 s +6.2 bp
```
- **About two thirds of the one-minute move happens in the first second,** most of it in the first quarter-second, as Nasdaq's 300 ms figure suggested.
- **The move keeps drifting the same way after that:** about +2 bp more from 1 s to 60 s.

## The trade (buy the ask / sell the bid at 15:50:00 + delay, exit at the opposite side at 15:51:00, commission included)
```
delay     SPY net bp (t)      exit 15:50:15 instead   E-mini (Micro fees)
 50 ms    +1.38 (3.02)        +0.62 (1.75)            -0.27
100 ms    +1.56 (3.46)        +0.58 (1.65)            -0.18
250 ms    +1.46 (3.34)        +0.48 (1.48)            -0.27
500 ms    +1.29 (3.00)        +0.37 (1.18)            -0.44
  1 s     +1.31 (3.15)  <- PRIMARY  +0.37 (1.25)      -0.42
  2 s     +1.13 (3.02)        +0.21 (0.81)            -0.62
  5 s     +0.93 (2.96)        +0.01 (0.07)            -0.85
```
**Gates.** The primary test passed both pre-registered gates: G1 (t ≥ 2) and G2 (positive in every era). This is the project's first short-interval directional PASS.

## Post-hoc checks (not registered, read before believing it)
| year | trades | net bp | t |
|---|---|---|---|
| 2019 | 55 | +0.73 | 1.4 |
| **2020** | 69 | **+7.74** | **3.5** |
| 2021 | 63 | +0.41 | 0.6 |
| 2022 | 64 | +0.79 | 0.7 |
| 2023 | 74 | −0.75 | −1.4 |
| 2024 | 65 | +0.35 | 0.4 |
| 2025 | 52 | −0.34 | −0.4 |
| 2026 | 45 | +0.87 | 1.1 |

- **One year carries it.** Remove 2020 and what's left is roughly **+0.3 bp a trade**, positive in 5 of 7 years but not distinguishable from zero. Trimming the 5 best and 5 worst days drops the mean from +1.31 to +0.94.
- **It does beat chance.** Random-direction trades on the same days and prices average **−0.60 bp** (the cost of crossing the spread); 95% of them stay below +0.07.
- **Most of the profit is the slow part.** Exiting at 15:50:15 instead of 15:51 leaves almost nothing. The money comes from the continued drift to 15:51, not from the jump itself.
- **The E-mini route loses at every delay.** Futures reprice faster, and the fee per trade is larger relative to the move.

## Read it plainly
- **A real, measurable effect survives a one-second delay on SPY,** and by the pre-registered rules it passes.
- **Economically it is thin.** Outside 2020, about 0.3 bp a trade on roughly 65 trades a year. It also needs a stock-broker API that can react inside a second at 15:50 every day.
- **Under the project's rules a PASS earns a paper forward record, never money straight away.** The forward record will show whether the post-2020 +0.3 bp is real.

## Episode note ("The 15 Seconds")
The ending changes. The edge *is* mostly gone in a quarter of a second, but a sliver remains for whoever is still there at one second. That sliver mostly lived in one crazy year.
