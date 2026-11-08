# Findings — M1, volatility asymmetry as a directional signal

Pre-registered in `PREREGISTRATION_ASYMMETRY.md`. Run 2026-09-12. 20 markets
on H1 bars, 2005-01-03 to 2026-08-07, sugarusd excluded on a data criterion
fixed in advance.

The first test in this project to use intraday data for anything other than
building daily bars.

## Verdict

**FAIL, in the pre-registered wrong direction. Kill condition MET.**

| | result | required |
|---|---|---|
| primary, residualised RSJ | **-0.1178** | >= +0.21 |
| eras | -0.47 / -0.43 / +0.50 | consistent |
| vs destroyed-timing null | -0.118 vs p95 **+0.2063** | beat p95 |
| 3bp | -0.1650 | >= +0.21 |
| plateau 5 / 21 / 126d | -0.076 / -0.118 / -0.024 | same sign |
| sign | **positive effect** | negative |

The sign matters. The signal was built as `-RSJ`, so a positive Sharpe would
mean the published direction (high RSJ -> lower returns) holds. It came back
**negative**, i.e. the data leans the opposite way to the literature. The
pre-registration stated in advance that *"a positive result here is a FAIL, not
a discovery"*, so this fails on direction as well as on size — and it sits
inside its own null band regardless.

## G1 is the result

**Plain reversal beats RSJ by 0.23 Sharpe.**

    raw RSJ                      -0.1005
    -sign(trailing 21d return)   +0.1283

RSJ is a worse version of one-month reversal. Under the pre-registered gate
that withdraws M1 regardless of anything else it reports, and it is the
cleanest possible answer to the question the test was built to ask.

Note what *is* the best number in the table: plain reversal at +0.1283. It
still does not clear the +0.21 bar, and its eras still flip (+0.07 / -0.05 /
+0.27). J1's S3 scored +0.033 on the vol-normalised version of the same idea.
Reversal remains the same weak, unstable thing measured from a third angle.

## The gates that passed, and one honest correction

- **G2 clear.** Ranking on RV alone gives +0.0425, smaller in magnitude than
  the primary. This is *not* the parked low-volatility lead resurfacing.
- **G3 clear.** Max |rho(RSJ, bars-per-day)| across 20 markets = **0.035**,
  against a 0.10 threshold. Not a bar-count artefact. The intraday
  construction is sound even at 23 bars a day.
- **G4 informative.** Realised skewness scores -0.0755 with the same era
  pattern (-0.40 / -0.28 / +0.34) as RSJ's -0.1178 (-0.47 / -0.43 / +0.50).
  The two behave as the close cousins they are, and neither works.

**The correction.** The design was changed before running because RSJ measured
rho = **+0.842** against the same day's return. That number is a *time-series*
correlation, within a market across dates. The residualisation is
*cross-sectional*, across markets within a date. Those are different
quantities, and the difference shows: residualising moved the Sharpe by only
**+0.0173** (raw -0.1005 to residual -0.1178).

So the +0.842 headline over-predicted how much the momentum contamination
would matter to a cross-sectional test. Residualising was still the right
call — it asks the cleaner question — but the stated justification for it was
measured in the wrong dimension, and saying so is more useful than leaving it
to look prescient.

## Why it may not transfer, stated in the pre-registration

The published effect (Zhao et al., -0.548%/month, t = -3.82) is US
single-name equities across **19,896 stocks**. This panel is 20 macro CFDs at
N_eff ~9.5. A mechanism resting on cross-sectional dispersion in jump signs
across ~20,000 names has almost nothing to work with on twenty instruments.
That was written down before the run, and it remains the most likely
explanation — which is not the same as the effect being absent in equities.

## Kill condition

Met. No bipower variation, no jump test, no different intraday frequency, no
substituting realised skewness — G4 already shows that cousin behaving
identically. Volatility asymmetry is closed for this universe.

## What this settles about the original question

The question was: *if volatility prediction works, what do we need to predict
direction from it?* The structural answer was the third moment, and the only
third-moment measure computable from data in hand has now been tested and
failed.

That leaves the answer standing but unreachable: the asymmetry that would
carry direction is the **implied** one — the 25-delta risk reversal, the tilt
of the option surface rather than its width. Every volatility index this
project has used (VIX, GVZ, OVX, EVZ, VXN, VXSLV) is at-the-money. We have
been holding the width and asking it for the tilt. Getting the tilt needs a
strike-level surface, which is a paid feed and a different project.
