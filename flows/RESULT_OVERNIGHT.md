# RESULT — FLOWS-3: the overnight drift after a US sell-off

```
RUN:      2026-09-26 20:12:17 UTC, once, on Dave's Mac (pineport/.venv)
SPEC:     PREREGISTRATION_OVERNIGHT.md sha256 2227514a... checked at run time
CODE:     overnight.py as committed in 64fe651; common.py as in 8079914
EVIDENCE: data/overnight_run.log, data/overnight_result.json
VERDICT:  DEAD -- K1, K2 and K3 all fire. As registered expected.
```

*Measurement, not a recommendation. Not financial advice.*

## 1. The replication is exact

Before 2021 the 02:00-03:00 ET window on SPX500 earned **+1.46 bp a day**
(t +5.46, n 4,066) — about **3.7% a year**, the same figure the authors report
for the E-mini. After a bottom-decile US session it earned **+5.32 bp**
(t +3.59, n 363): the conditional drift was real and larger.

## 2. From 2021 it is gone — after sell-offs too

| | 2005 – 2020 | 2021 – 2026-08 |
|---|---|---|
| unconditional | +1.46 bp (t +5.46) | **+0.01 bp** (t +0.03) |
| after a sell-off | +5.32 bp (t +3.59) | **−0.01 bp** (t −0.01, n 133) |
| placebo 20:00-21:00 after a sell-off | | +0.89 bp (t +0.35) |
| net of spread after a sell-off | | −1.13 bp |

Confirmation: NAS100 +1.81 bp (t +0.89), US30 −0.42 bp. DE30 on SPX sell-off
days −0.29 bp. Ratio P2/P1 −0.00. Kill conditions K1 (G1 fails), K2 (placebo
larger than a zero effect) and K3 (net negative) all fire.

## 3. What it means

The registered question was whether the drift survives where it should be
strongest — after large sell-offs, when closing imbalances are still big. It
does not: the conditional effect vanished as completely as the average one.
On this proxy, the market's *response* to a sell-off disappeared, not only the
frequency of large imbalances.

Caveat: the authors measure the closing imbalance directly; this test uses the
US session return as a stand-in, which OANDA data forces. A direct imbalance
measure could still find something. This data cannot.

Registered expectation was that G1 would more likely fail. It did.
