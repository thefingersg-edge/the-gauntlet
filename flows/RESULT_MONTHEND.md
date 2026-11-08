# RESULT — FLOWS-1: month-end rebalancing

```
RUN:      2026-09-26 19:35 UTC, once, in the Cowork VM (python 3.10, pandas 2.3.3)
SPEC:     PREREGISTRATION_MONTHEND.md, sha256 e8cb9ac5... checked at run time
CODE:     monthend.py + common.py exactly as committed in 64fe651
EVIDENCE: data/monthend_run.log, data/monthend_result.json,
          data/monthend_trades.csv, data/roll_flags_usb10y.csv (sha256 06ff6df8...)
VERDICT:  DEAD under kill condition K4 -- and not for the reason registered.
```

*Measurement, not a recommendation. Not financial advice.*

A run started on the Mac at 19:34:55 stopped inside the input grid check,
before any return was computed (a pandas-resolution bug in the check, fixed
afterwards in its own commit). This VM run is the only outcome.

## 1. The answer in one line

**From 2005 to early 2023 the rebalancing reversal is on the OANDA vehicle,
clearly and robustly. In the 41 months after the paper's sample it is not
there at all, and the seven trades the rule took in that period lost.**

## 2. The gates, as registered

| gate | result | |
|---|---|---|
| G1 replication, 2005-01 – 2023-03 | b −0.175, t −3.64, n 215, q 0.001 | PASS |
| G2 eras | E1 −0.234 (t −3.13), E2 −0.104 (t −1.82), E3 −0.100 (t −2.43) | PASS |
| **G3 holdout**, 2023-04 – 2026-08 | **b +0.001, t +0.01, n 41** | **FAIL** |
| G4 mechanism | b1 −0.151 (t −2.86), b2 +0.257 (t +2.47) | PASS |
| G5 placebo, days 6-10 | b −0.118, t −1.43 | PASS as registered — see §4 |
| G6 reversal next month (support) | +0.082, t +1.76 | consistent |
| **G7 trading rule, net** | 70 trades: full +51.7 bp (t +1.56); **holdout 7 trades −84.6 bp** | **FAIL** |
| G8 DE30 vs Bund (confirmatory) | b −0.178, t −2.84 | consistent |

Kill conditions: K1 no, K2 no, K3 no, **K4 yes** (G7). Registered verdict: **DEAD.**

b is the slope of the last-five-day equity-minus-bond return on the
month-to-date equity-minus-bond return: −0.16 means that after equities beat
bonds by 5% over the month, the last five days take back about 0.8%.

## 3. What held

- **The replication is strong.** t −3.64 over 215 months, surviving
  Benjamini-Hochberg at q 0.001, negative in all three eras.
- **It is rebalancing, not momentum.** G4 is the shared-term check against the
  rejected time-series momentum: the month's equity winner is sold (b1 < 0)
  and its bond loser bought (b2 > 0). Momentum would show the opposite.
- **It is not a vehicle artefact.** Excluding roll-flagged months (primary,
  3 of 259), including them (R2 −0.185, t −3.17) and replacing the bond CFD
  with a DGS10 duration proxy (R3 −0.163, t −3.68) give the same answer.
  Vol-scaling the legs weakens it (R1 −0.072, t −2.03) but keeps the sign.
- **It replicates on an independent pair.** DE30 against the Bund, a different
  pension system and a different CFD, gives −0.178 (t −2.84).
- **Costs were not the problem.** Across the 70 trades, spread cost averaged
  2.4 bp and financing −7.1 bp a trade, against a gross edge of +61 bp.

## 4. What did not, and a caveat on a gate that passed

**The holdout is empty.** After March 2023 the slope is +0.001 — not weak,
absent. The rule's seven trades in that period were all "short equity / long
bond" after strong equity months, and five of seven lost (−305, −198, −106,
−82 bp against +81, +27, +17). With n = 41 months and 7 trades this cannot
distinguish decay from bad luck, which is exactly why the pre-registration
made the holdout a sign check rather than a significance test — and the sign
failed.

**G5 passed, but the placebo is not zero.** Days 6-10 of the month show a
slope of −0.118 (t −1.43), about 72% of the primary's size. It meets the
registered criterion (t > −2 and smaller than the primary), but it suggests
part of what G1 measures is a general short-horizon reversal of the
equity-bond spread rather than something specific to month-end. That makes
the month-end mechanism less certain than G1 alone suggests.

## 5. Against the registered expectation

Registered: G1 more likely than not to pass; the holdout too short for more
than a sign; G7 the most likely failure. G1 passed. G7 failed, as expected —
but on the holdout, not on costs.

## 6. What this means

Per the pre-registration: stop. The pattern the literature describes existed
on this vehicle for eighteen years and has not been visible since the paper's
sample ended. Whether that is decay, crowding after wide attention, or noise
in 41 months is not answerable from this data.

The only honest way to learn more is to watch it forward without trading,
under a new pre-registration — the same design as fastbot's v25. That would
be a new decision, not a continuation of this test.
