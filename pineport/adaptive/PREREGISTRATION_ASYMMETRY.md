# Pre-registration — M1, volatility asymmetry as a directional signal

Written 2026-09-11, before any signal is computed or joined to a return.

## Why this test exists

F1 established the one thing that survived this project: **implied volatility
forecasts realised volatility better than trailing realised does**, by about
rho = +0.4 beyond persistence, on all four markets with an index.

The obvious next question — can a good volatility forecast tell us which way
price will go — has a structural answer, and it is no. **Volatility is a
second moment; direction is a first moment.** Squaring returns discards the
sign, and no improvement in forecasting sigma puts it back. A better estimate
of the width of a distribution says nothing about where its centre sits.

What can carry direction is the **third moment**: the asymmetry. Not how wide
the distribution is, but whether it leans. This test asks whether the
asymmetry of *realised* variation predicts returns.

## The measure — frozen

Relative Signed Jump Variation, exactly as the published literature defines
it. Within one trading day, from intraday log returns r_i:

    RV+  = sum of r_i^2 over r_i > 0
    RV-  = sum of r_i^2 over r_i < 0
    RV   = RV+ + RV-
    RSJ  = (RV+ - RV-) / RV

RSJ is bounded in [-1, +1], scale-free by construction, and needs no ATR or
vol normalisation — which is deliberate, because normalising by a volatility
is how E2's VRP result turned out to be two formulas sharing a term.

The **trading day is the 17:00 New York boundary** from `make_daily.py`, not a
UTC day. If the intraday aggregation used a different day boundary from the
daily return it is meant to predict, the two would be misaligned by the same
2-3 hours that the R4 defect turned into 296.5 bars a year.

Signal at the decision date = mean RSJ over the trailing month (21 trading
days). Weekly and 6-month formation windows are the pre-registered plateau
check, not separate attempts.

## Data — and the constraint that decides the primary panel

**This is the first test in the project to use intraday data for anything
other than building daily bars.** Coverage was measured before this file was
written:

- **M15 exists for only 11 of 21 markets.** The ten diversifiers pulled for
  Part H are H1-only. Median 92 M15 bars per trading day on the eleven.
- **H1 exists for all 21.** Median 23 bars per trading day; 19 of 21 markets
  have >= 12 bars on >= 90% of days.

That forces a choice, and it is made here rather than after seeing results.
**The primary panel is H1 across 20 markets**, because the published effect is
cross-sectional and the cross-section is the thing that needs breadth: J1
measured realised N_eff at **8.8-9.9** on the 21-market cross-section against
**~3.5** on the original eleven-market cluster. A cross-sectional test run on
those eleven would be close to degenerate, which is precisely the failure the
J1 pre-registration warned about and the 21-market panel escaped.

Twenty-four hourly returns is a coarse realised variance. It is a much less
coarse *ratio*, which is what RSJ is.

**sugarusd is excluded** on a data criterion fixed before any result: median
10 H1 bars per day, and only 18.3% of its days reach 12 bars. xcuusd is
marginal at 89.5% and is kept, with its exclusion as robustness check R4.

A day contributes only if it has **>= 12 intraday bars**. Days below that are
dropped, not filled.

Secondary panel: M15 on the eleven markets that have it, as a precision check
on the same specification. Reported, and scored only if the primary passes.

## Direction — pre-specified

The published sign is **negative**: high RSJ (variance concentrated in upward
moves) predicts **lower** forward returns. Zhao et al., 1993-2013, 19,896 US
stocks: monthly long-short **-0.548%/month, t = -3.82**; weekly **-0.427%,
t = -14.74**; monotone across deciles; surviving controls for size,
book-to-market, realised volatility, realised skewness, realised kurtosis and
past returns.

Fixing the sign in advance makes the test one-sided and removes the escape
hatch this project has seen used elsewhere — B3's pattern direction came out
flat and could have been re-described as a contrarian signal after the fact.
**A positive result here is a FAIL, not a discovery.**

## MEASURED BEFORE FINALISING THIS FILE — and it changed the design

Before committing G1 as a gate, the concern behind it was measured on eurusd,
5,601 trading days, H1 bars:

    corr(daily RSJ, that day's return)   = +0.842
    corr(21d mean RSJ, 21d return)       = +0.848
    corr(RSJ, bars per day)              = -0.016     [G3 clear]

**RSJ is 84% the same object as the trailing return.** That is not a
contaminant to be checked for afterwards; it is most of the signal. Mechanically
obvious in hindsight — a day that closes up necessarily has more of its squared
variation in positive increments — but worth measuring rather than assuming.

Two consequences, both adopted here rather than after seeing a result:

1. **The primary signal is RESIDUALISED RSJ**, not raw RSJ. At each date, RSJ
   is regressed cross-sectionally on the trailing 21-day return and the
   residual is what gets ranked. Raw RSJ is demoted to a reported secondary,
   so that any apparent effect can be attributed to the momentum component or
   to the asymmetry, and not left ambiguous.
2. **The prior drops further.** Testing raw RSJ would be testing one-month
   reversal with extra arithmetic, and J1 already tested that: S3 scored
   **+0.033** against a +0.29 bar, flipped sign across eras and sat inside its
   own null band. At rho = +0.85 the raw version would largely reproduce that.

So the real question this test asks is narrow and worth stating plainly:
**after removing the 85% of RSJ that is simply the recent return, does the
leftover asymmetry predict anything?** That residual is a genuinely new
quantity in this project. It is also, by construction, the small part.

## Prior — low, and for a specific reason

The published effect is US single-name equities across ~20,000 stocks. This
panel is 20 macro CFDs at N_eff ~9.5. The mechanism that story rests on —
cross-sectional dispersion in jump signs across a very wide universe — has
almost no room to operate on twenty instruments. The asset class is different,
the cross-section is three orders of magnitude smaller, and nothing about
FX or commodity futures guarantees the effect transfers.

## Specification

**Primary.** Signal = the cross-sectional residual of RSJ on the trailing
21-day return, ranked. Rank-weighted, dollar-neutral, unit gross, monthly
rebalance — the identical construction to J1, so the two are directly
comparable and neither gets a bespoke portfolio. Returns in each instrument's
own quote convention.

**Secondary, reported alongside.** Raw RSJ, same construction. The gap between
raw and residualised is the momentum component, and reporting both makes it
visible instead of arguable.

**Secondary.** Time-series: position = -sign(RSJ - its own trailing median)
per market. Reported, scored only if the primary passes.

Costs 1bp, with 0 and 3bp as robustness.

## Pass criteria — fixed in advance

1. **Sharpe >= +0.21.** At the realised cross-sectional N_eff of ~9.5 over
   21.6 years the noise floor is 1/sqrt(205) = 0.070, so this is 3 SE. This
   is a *lower* bar than the 0.29 used in J1 and K1, and it is lower because
   J1 measured the cross-section to be better diversified than assumed, not
   because anything is being relaxed to let a result through.
2. Sign consistent across E1 / E2 / E3.
3. Beats its destroyed-timing null (signal lagged 750 bars) at the 95th
   percentile of a stationary block bootstrap.
4. Holds at 3bp.
5. Plateau: weekly, monthly and 6-month formation windows keep the same sign.
6. Sign is **negative**, as pre-specified.

## Gates that can withdraw the result outright

**G1 — is it momentum wearing a new name?** This is the one that matters.
A day with a positive return mechanically has more of its variance in
positive intraday moves, so **RSJ is correlated with the sign of the trailing
return by construction.** If RSJ merely proxies past return, this is
reversal, which the project has already tested and rejected (J1's S3 at
+0.033).

Measured at **+0.842 / +0.848** (above), so this gate is near-certain to
bind, and the design now leads with the residual rather than treating this as
a check that might or might not fire.

Required: the **residualised** signal must clear criterion 1 on its own, AND
raw RSJ must beat `-sign(trailing 21-day return)` on the same panel, same
construction, same costs. If the residual fails, or if raw RSJ cannot beat
plain reversal, **M1 is withdrawn regardless of any Sharpe it reports.** This
is C1's "beat sign(A) at full size" gate — the one that exposed grid agreement
as a direction wearing a sizing costume.

**G2 — is it the low-volatility anomaly?** Mirror check: rank on RV alone,
asymmetry removed. J1's mirror control already scored **-0.259** ranking on
volatility, larger than any momentum signal tested there. If ranking on RV
reproduces M1's result, then what we have found is that parked lead and not
asymmetry, and it must be reported as such rather than as a new finding.

**G3 — is it a bar-count artefact?** RSJ from few bars is noisy and may be
biased. Measured at **-0.016** on eurusd, so this one looks clear already, but
it is checked per market. Require |rho(RSJ, bars-per-day)| < 0.10 and confirm the effect
survives restricting to days with >= 20 bars.

**G4 — is it realised skewness?** RSJ and realised skewness are close
cousins. The published work controls for realised skewness and RSJ survives;
if it does not survive here, the effect is a known one under a new name.

**G5 — destroyed timing.** As criterion 3.

## Robustness

- R1: costs 0 / 1 / 3bp.
- R2: quintile sort instead of rank weighting; must agree in sign.
- R3: M15 panel on the eleven markets that have it.
- R4: drop xcuusd (89.5% bar coverage).
- R5: weekly rebalance.

## Kill condition

If the primary specification fails criterion 1, or fails G1, volatility
asymmetry is closed for this universe. We would not then move to bipower
variation, a jump test, realised skewness, or a different intraday frequency
looking for a version that works.

## What is NOT in this pre-registration

The **low-volatility lead stays separate and unwritten.** J1's mirror scored
-0.259 ranking the cross-section on volatility, and I1's G3 gate found
volatility ordering Sharpe 15x more strongly than tick size. That is a
second-moment risk-premium story, not a third-moment asymmetry story, and
folding it in here would let a control double as a hypothesis — the exact
move the kill conditions exist to prevent. It needs its own file.

## Ceiling, stated in advance

Even a clean pass is a statistical result on 20 CFDs, not a tradeable one. It
would still have to clear the vehicle question (GAUNTLET 4.6) and still be
the first thing in this project to go through a forward test. The honest
ceiling is "worth pre-registering a strategy around".
