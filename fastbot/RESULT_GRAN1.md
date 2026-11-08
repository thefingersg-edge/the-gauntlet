# RESULT — GRAN1: single-stock data holds no tradeable information about SPX500 or NAS100 direction or volatility. FAIL on all three. No sealed run was triggered.

```
SPEC:     PREREGISTRATION_GRAN1.md  sha 67e1d50d…;  table gran_daily.csv sha 6377d9b2…
METHOD:   singlestock/gran1_run.py main (sha in PROVENANCE.md); OANDA SPX500/NAS100 daily cash closes, 5m regular-session RV, VIXCLS; sample to 2023-06-30 (sealed after); log data/run_gran1.log
RUN:      2026-10-03
VERDICT:  H1 FAIL   H2 FAIL   H3 FAIL   (sealed window 2023-07 -> 2026-09 untouched)
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

```
H1  insiders buying vs selling (30-day ratio) -> SPX next 20 days: +23.8 bp per sd, t 0.86; eras +44 / -10 / +41          FAIL
H2  large-cap earnings reactions (28-day mean) -> SPX next 20 days: +49.2 bp per sd, t 1.43; eras +82 / -36 / +78        FAIL
H3  cross-stock dispersion -> next-day SPX volatility beyond HAR+VIX: -0.5% per sd, t -0.39;
    eras +0.35 (t 5.7) / +0.04 / -0.36 (t -4.3);  out-of-sample DM t -1.40                                               FAIL
reported: NAS100 H1 t 0.76, H2 +79.8 bp/sd (t 2.22), H3 t 1.16 (DM -0.58);  H1 at 60 days t 1.32
          timing on signal > 0: H1 +86 vs +81 bp (no difference); H2 +92 vs +57 bp
```

## Read it plainly
- **The granular data does not add to what the index already shows.**
  - Insiders as a group: weak and inconsistent.
  - The earnings season's mood: right sign in two eras of three, short of the bar. NAS100 reaches t 2.2, but that was reported only, and one era is the wrong way round.
  - Cross-stock dispersion does carry volatility information, but it flips sign between eras once VIX is in the model. Out of sample it makes forecasts worse.
- **This matches v57 (breadth not beyond VIX) and v50 (news not beyond VIX).** The index price, VIX and recent volatility already contain what the constituents say.
- **The single-stock data's value is in trading the stocks themselves (PEAD3), not in timing the index.**
- The sealed 2023-07 → 2026-09 window remains unused and available for future survivors.
