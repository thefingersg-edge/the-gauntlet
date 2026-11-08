# RESULT — PROBE1: Unger's "market character" probe. Gold trends steadily, the stock indices have no stable character, and nothing pays after costs out of sample

```
SPEC:     PREREGISTRATION_PROBE1.md  sha 1320a760…  (frozen before any number)
METHOD:   scripts/probe1_run.py (sha in PROVENANCE); OANDA 15m mid bars -> 17:00 New York trading days; spread + financing as registered
LOGS:     data/probe1/run_probe1.log; daily equity series data/probe1/<market>_daily.csv
RUN:      2026-10-09
VERDICT:  Q1 stable character 1 of 4 (gold: TREND)    Q2 out-of-sample net 0 of 4 PASS
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

Self-tests passed:
- a planted trend reads as trend, and a zig-zag reads as mean-reverting;
- probe + reverse = 0 exactly.

## The probe
Buy a break of yesterday's high and sell a break of yesterday's low, always in the market. Unger publishes this as his first look at any market. A rising curve means "build trend-following" and a falling one means "build counter-trend".

## Q1 — does each market have a stable character? (gross, no costs)
```
market   gross bp/day  t       Sharpe   2005-12   2013-19   2020-26   character
SPX500   -1.07         -0.78   -0.15    -1.50     -0.45     -1.18     unstable (weakly mean-reverting every era, not significant)
NAS100   -0.49         -0.30   -0.06    +0.89     -0.77     -1.88     unstable (trend early, mean-reverting since 2013)
UK100    -1.01         -0.70   -0.14    -0.36     +2.45     -5.43     unstable (flips sign every era)
GOLD     +5.19         +3.93   +0.78    +8.69     +1.72     +4.60     TREND (stable)
```
- **Unger's claim that the S&P snaps back is right in sign** in every era here, but too weak to call (t −0.8). It is consistent with REGIME2's snap-back and with our failed breakout tests.
- **Gold trends**, and it does so in every era. This is the cleanest "character" result in the project, and it matches his view that commodities trend.

## Q2 — chosen on 2005–15, traded 2016–26, after costs
```
market   chosen      gross   - spread  - financing  = net bp/day  t       Sharpe    buy & hold Sharpe (net)
SPX500   FADE        +0.91   -0.83     -0.85        -0.77         -0.41   -0.11     +0.51
NAS100   TREND       -1.37   -0.76     -1.05        -3.18         -1.33   -0.37     +0.68
UK100    TREND       -3.39   -1.28     -1.02        -5.69         -3.01   -0.90     +0.13
GOLD     TREND       +2.86   -1.54     -1.00        +0.32         +0.18   +0.05     +0.58
```
**0 of 4 pass.**
- **Indices:** the character picked on old data was wrong or gone by 2016, for NAS (trend turned to mean-reversion) and UK100.
- **Gold:** the trend was still there (+2.9 bp/day gross), but spread and overnight financing ate about 90% of it. Simply holding gold did far better after costs (Sharpe 0.58 against 0.05).
- **Costs:** at about 110–150 reversals a year, the probe pays the spread roughly every other day plus financing every night. That is the same wall our other daily-frequency tests hit.

## Data notes (found during the run, reported honestly)
- **Gold 2006–2013:** the OANDA history has many weekend and partial-session "days" (up to 91 a year). These produce tiny daily ranges and bursts of reversals, up to 47 in one day in Nov 2008.
  - That inflated gold's early reversal count and costs, so the early net figures are not meaningful.
  - **Post-hoc check (not registered):** keeping only full weekday sessions, gold's gross trend character gets *stronger*: +6.35 bp/day, t 4.5, positive in all eras (+11.9 / +2.6 / +4.6), about 111 reversals a year.
  - The Q1 conclusion stands. Q2 uses clean 2016+ data, so it is unaffected.
- **Index spreads before 2012** are missing in the source data (recorded as 0). This affects only the reported annual net figures before 2012, not Q1 (gross) or Q2 (2016+).

## Read it plainly
- **As a diagnostic**, Unger's probe confirms that gold trends steadily. On the stock indices it says "no stable character": their behaviour changed between eras, NAS100 most of all.
- **As a trading rule**, it doesn't survive costs on any of our markets out of sample. That is consistent with his own framing: the probe is where you *start* building a system, not the system itself.
- **What's worth carrying forward:**
  - gold's stable trend character is a reason to test slower, cheaper trend rules on gold (fewer reversals, no overnight CFD financing, e.g. via futures or ETFs);
  - oil gets the identical probe after Saturday's pull (PROBE1-OIL), to check his "crude trends" claim directly.
