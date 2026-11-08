# PREREGISTRATION v24.1 — amendment: Gate A was mis-specified

```
WRITTEN:  2026-09-18, AFTER the v24 run voided and AFTER I had seen the
          hypothesis-gate figures. That disclosure is the reason for the
          restriction in section 3, and it is stated first rather than
          buried.
AMENDS:   PREREGISTRATION_v24 section 5, Gate A only.
CHANGES:  nothing else. Not a threshold, not an offset, not an
          instrument, not a stratum, not the primary statistic.
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.**

---

## 1. What was wrong

v24 Gate A required NAS100_USD and US30_USD each to show the release-fade
base effect at **t ≥ 2.0**, as a positive control. US30_USD returned
**+1.17 bp at t = 0.87** and the run voided.

**A positive control has to be something near-certain.** v22's was
volatility clustering, which returned t = 46.9 — a thing that cannot
plausibly be absent. The release-fade base effect is **t = 2.77 on
SPX500_USD itself**, the instrument it was discovered on. Requiring a
correlated-but-different instrument to clear t = 2.0 for an effect that
marginal means the control fails by chance a large fraction of the time,
whatever the pipeline is doing.

**So Gate A was not testing the pipeline. It was re-testing the
hypothesis under another name, and calling the answer a void.**

## 2. What replaces it

v22's Gate A, which is the right instrument for this job: **does the
event table land on bars that move?**

```
instrument     release |move|   control   ratio       t
NAS100_USD          32.25        9.71     3.32x    12.2
US30_USD            25.12        7.80     3.22x    12.9
EUR_USD             20.85        6.70     3.11x    15.6
XAU_USD             36.22       13.45     2.69x    13.8
DE30_EUR            26.33       11.59     2.27x    10.5
```

```
AMENDED GATE A
PASS   each instrument's release bars show larger |moves| than the same
       08:30 slot on non-release days, t >= 5.0
```

This is near-certain in the way a control must be — a scheduled release
moves the market — and it tests exactly what the void was supposed to
test: that the fetch is right, the timestamps are right, and the code
lines events up with prices. All five pass at t > 10.

**The original Gate A is still computed and still printed.** It is
reported as what it was: a second reading of the hypothesis, not a
control.

## 3. The restriction, which is the whole safeguard

**This amendment may only license reading a NULL.**

```
if Gate B and Gate C FAIL   -> the amendment licenses reporting that
if Gate B or  Gate C PASS   -> the void STANDS. The pass is not a
                               finding, fresh data is required, and
                               this document does not rescue it.
```

I wrote this after seeing the hypothesis-gate numbers. That is a real
contamination and no amount of care removes it. **The asymmetry is what
makes it survivable**: an amendment that can only permit a negative
result cannot manufacture a positive one, and the failure mode
pre-registration exists to prevent — fiddling a gate until a finding
appears — is closed by construction.

The cost of the stricter alternative was a null that my own registered
prediction called in advance, discarded to protect nothing. **The cost
of this one is that a positive result here would be worthless — so it is
declared worthless in advance.**

## 4. What is NOT changed

- **The primary statistic.** C − A, paired within instrument.
- **The thresholds.** Gate B and Gate C still require t ≥ 2.0.
- **The offsets.** A is (1, 1, 5); C is (2, 2, 6). Both hold one hour.
- **The instruments and their groups.** No additions.
- **The strata.** CPI and payrolls; claims still excluded.
- **The 150-event floor.**
- **The prediction in v24 §6**, which stands as written and is scored
  against the result whatever it says.

## 5. One thing the run found that v24 should have anticipated

`verify_pull.py` reports **bid equal to ask for all of 2005-2011 on
NAS100_USD, US30_USD and DE30_EUR** — the same back-filled-index problem
RESULT_PREANN found on SPX500_USD, seven whole years of it.

v24 §7 has an automatic rule for this, but it is written as an
instrument-level test (">50% of bars") and these instruments are around
33% overall, so it does not trip. **The rule should have been per year,
which is how verify_pull.py now reports it.**

Consequence, stated rather than acted on: **cost on the three equity
indices is unmeasurable before 2012** and any cost figure quoted for
them spans a period where a third of the sample has no spread. The
gross figures are unaffected. Gate E is affected and is read with that
in mind. **The sample is NOT trimmed to 2012+ — that would be changing
the spec after seeing the data, and the v24 §7 kill condition says so.**

---

**Investigation forty, amended.** The first time in this project that a
gate failed because I set it badly rather than because the market said
no.
