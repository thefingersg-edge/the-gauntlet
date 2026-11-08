# Findings — J1, cross-sectional momentum

Pre-registered in `PREREGISTRATION_XSECTION.md`. Run 2026-09-03, 21 markets,
2005-01-03 to 2026-08-07, post-R4 daily bars. Panel reaches full 21-market
width 2007-02-05; 5,574 of 5,609 days have >= 12 live markets.

## Verdict

**FAIL on all three signals. Kill condition MET.**

| signal | Sharpe | eras | vs null | quintile |
|---|---|---|---|---|
| S1 12-1 momentum | **+0.0158** | -0.317 / +0.200 / +0.195 SIGN FLIP | inside null band | +0.020 agrees |
| S2 3-month | **-0.0757** | +0.089 / -0.557 / +0.109 SIGN FLIP | inside null band | -0.051 agrees |
| S3 1-month reversal | **+0.0330** | +0.065 / -0.059 / +0.068 SIGN FLIP | inside null band | +0.134 agrees |

Pass required >= +0.29. Nothing is within an order of magnitude of it.

Every signal also fails era consistency and fails to beat its own
destroyed-timing null. The nulls' bootstrap 95th percentiles (+0.536, +0.340,
+0.506) are an order of magnitude above the live results.

The S1 "plateau" is not a plateau, it is a random walk across neighbouring
formation windows:

    11-1  +0.0633
    12-1  +0.0158
    12-2  -0.0064
     6-1  -0.0630

A real effect does not change sign between 11-1 and 6-1.

## The one result worth keeping

**Realised N_eff came in at 8.79 - 9.88, not the 4.70 - 6.01 measured on the
time-series strategies.** Mean pairwise correlation across the cross-sectional
per-market returns is only 0.056 - 0.069.

This is the theoretical advantage of cross-sectional construction showing up
exactly as advertised: a dollar-neutral portfolio differences out the common
market factor, so 21 names really do behave like ~9-10 independent bets
rather than ~5. The pre-registration warned that a quintile sort on N_eff ~5
would be near-degenerate. That warning was **wrong**, and in the useful
direction — the cross-section is better diversified than the time-series
portfolios this project has been building all along.

Two honest consequences:

1. The pre-registered bar of +0.29 was set from N_eff 5. At the realised
   N_eff of ~9.5 over 21.6 years the noise floor is 1/sqrt(205) = **0.070**,
   so the correct 3-SE bar was **0.21**, not 0.29. This makes no difference
   whatsoever: the best signal scored +0.033.
2. Bloc concentration is fine. Long slots spread fx 29.4%, index 28.5%,
   metals 14.7%, rates 10.4%, ags 10.1%, energy 6.9%. The cross-section is
   not one bloc wearing eight names.

So the construction was sound and the diversification was real. There was
simply no signal to deploy it on.

## The mirror check found something larger than the signals

Ranking on 1/vol alone — the control, with the return term removed entirely —
scores **-0.2594**. Equivalently, ranking on *volatility* scores about +0.26.

That is larger in magnitude than all three momentum signals combined, and it
is the same pattern I1's G3 gate produced, where plain volatility ordered
Sharpe 15x more strongly than tick size did.

**This is not being chased.** A control that outperforms the hypothesis is
information about the data, not a new result. Promoting a mirror check to a
finding after seeing its number is precisely the post-hoc move the kill
conditions exist to stop, and the figure above has had no era test, no null,
no cost sensitivity and no plateau run against it. If a low-volatility /
betting-against-beta effect is wanted, it belongs in a fresh pre-registration
with those gates specified before it runs — the same treatment given to the
Brent contract in K1.

## Kill condition

Pre-registered: "If none of S1/S2/S3 clears criterion 1 in the rank-weighted
specification, the cross-sectional family is closed for this universe. It
would not be reopened with a fourth formation window."

None cleared. **Closed.** The 11-1 / 12-2 / 6-1 windows were run as the
pre-registered plateau check, not as further attempts, and all sit in noise.
