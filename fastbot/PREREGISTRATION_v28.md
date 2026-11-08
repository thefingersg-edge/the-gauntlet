# PREREGISTRATION v28 — which PART of the release move comes back?

```
WRITTEN:  2026-09-25, before any decomposition of a release move has
          been computed. No cross-instrument factor, residual, or
          regression of the fade on anything exists in this project.
STATUS:   FROZEN
SUBJECT:  the mechanism. Is the fade paid for absorbing an idiosyncratic
          move, or for correcting the market's reading of the data?
CODE:     premarket_factor.py 1.0, written against this document
CHANGES:  nothing in v25. This is a mechanism test, not a rule change.
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.**

---

## 1. Why this question and not another variant

Three explanations for the release fade have died: overshoot-and-correct
(the reversion does not scale with the size of the move), noise-plus-
selection (held-out data reproduced it), and the 09:30 open doing the
correcting (gold and EUR_USD have no equity open and show it anyway).

What the measurements have fixed since:

```
not a risk premium     v27: it stops dead overnight. A premium accrues.
release-specific       v27: +3.61 bp on release mornings, +0.19 bp on
                       23,521 ordinary ones
scales across TYPES    claims is a quarter of CPI/payrolls
not within a type      the quintile test on move size was non-monotonic
```

Everything so far has been measured from one instrument's price and a
calendar. **Direction cannot be explained by a variable that only
encodes direction.** Six instruments react to the same release on the
same morning, and that is information this project has never used.

## 2. The decomposition, defined before it is computed

For instrument i on morning d:

```
m        the 08:30-08:45 bar move, mid close against mid open, in bp
sigma    the standard deviation of that instrument's LAST 24 release-bar
         moves, strictly BEFORE d, same event class. Fewer than 24 prior
         events -> the morning is dropped.
z        m / sigma
common   the MEDIAN of the other three equity indices' z on that morning,
         rescaled: c = sigma_i x median(z_j), j != i
resid    e = m - c
C        c x sign(m)      how much of this move was the pack
E        e x sign(m)      how much was this instrument alone
                          identity: C + E = |m|
```

**The primary group is the four equity indices** -- SPX500_USD,
NAS100_USD, US30_USD, DE30_EUR -- four measurements of one underlying
reaction, so a median of the other three is a meaningful pack. A morning
where any of the four is missing is dropped and counted.

**EUR_USD and XAU_USD are reported separately and gate nothing.** Their
loading on a US macro surprise is not fixed -- a growth surprise and a
rates surprise move them differently against equities -- and this
registration does not estimate loadings.

## 3. The statistic

The fade P&L y is rule A's own window, 08:45 to 09:45, mid, signed in
the fade's direction, exactly as v22 defined it. Everything is
standardised by the same trailing sigma, so the regression is unitless
and one instrument's scale cannot dominate:

```
y/sigma  =  a  +  bC x (C/sigma)  +  bE x (E/sigma)  +  error
```

Standard errors clustered by release date. The two readings:

```
bE > 0, bC ~ 0     the fade is paid for ABSORPTION -- the part of the
                   move that was this instrument alone comes back
bC > 0, bE ~ 0     the fade is paid for the market MISREADING the data
                   -- the shared, informational part comes back
```

## 4. Gates

```
Gate 0  positive control. Rule A's mean fade on the CPI/payrolls
        equity sample must land within 0.30 bp of v27's +3.61 bp on
        the same window, or the run is VOID as a pipeline failure.

G1      CPI + payrolls:  bE - bC > 0 at clustered t >= 2.24
G2      CLAIMS, replication: the same contrast, same sign, t >= 2.24
G3      CONTROL mornings: interpretation, not pass/fail --
          positive on release AND control mornings -> general absorption;
            releases merely supply bigger idiosyncratic moves
          positive on release mornings only -> release-specific absorption
          positive nowhere -> the decomposition explains nothing and the
            absorption story is dead with the other three
```

2.24 is Bonferroni for two gated looks at 5%.

## 5. Reported, and deciding nothing

- **bE and bC separately**, with their t, per sample and per instrument.
- **A tertile table**: mean fade P&L by thirds of the idiosyncratic
  share |E| / (|E| + |C|), because a coefficient is not a picture.
- **The same regression at 15:45** -- DESCRIPTIVE ONLY. Every sample here
  is spent for horizon questions (v26.1 spent CPI/payrolls, v27 spent
  claims and the control), so no gate may read a horizon again on them.
- EUR_USD and XAU_USD, as section 2 says.

## 6. Predictions, registered

- **G1 passes: bE > 0, bC within 0.05 of zero.** This is the absorption
  story and I have said so out loud before running it.
- **G2 is a coin flip.** I expect the same sign on claims; I would not be
  surprised by t < 2.24 on a release a quarter the size.
- **G3: the control shows a positive contrast about half the size.**
  Liquidity errors happen on ordinary mornings too; releases just make
  them bigger.
- **At 15:45 the contrast is weaker than at 09:45**, because absorption
  is a fast process. If it is STRONGER, the absorption story is wrong
  and the 15:45 drift is something else.

My registered predictions in this line have been wrong about half the
time, and I am more confident here than that record earns.

## 7. Kill conditions

- **No loadings are fitted.** The pack is a median of the other three,
  fixed above. A regression that estimates betas per instrument is a
  different registration.
- **No horizon is gated.** Section 5.
- **No variant follows automatically.** If G1 passes, the rule does not
  change: a rule that fades only the residual is a NEW registration with
  its own out-of-sample requirement, and v25 keeps running rule A
  either way.
- **sigma uses only prior events.** A trailing window that includes the
  morning being measured is look-ahead, and it would flatter exactly the
  coefficient this run is about.
- **History is never recomputed.** This run writes its own file.

---

**Investigation forty-four.** The first one that asks WHY rather than
WHETHER.
