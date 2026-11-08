# RESULT — FLOWS-5: the 20-day DE30 drift after ECB decisions. DEAD (K1, K2, K3).

```
SPEC:     PREREGISTRATION_ECBDRIFT.md (sha 32e7cd47…)
METHOD:   ecbdrift.py   log data/ecbdrift_run.log   result data/ecbdrift_result.json
DATA:     DE30_EUR, DE10YB_EUR M15 bid+ask; ecb_events.csv 1b5b4968… (213 scheduled
          decisions 2005-01 .. 2026-07; the commit 703c446 message says 241 -- that was a typo)
RUN:      2026-09-27, once, in the Cowork VM
VERDICT:  G1 FAIL  G2 FAIL  G3 FAIL  G4 PASS  G5 PASS  ->  DEAD
```

*Measurement, not a recommendation. Not financial advice.*

## The registered test

| | estimate | t | gate |
|---|---|---|---|
| mean signed 20-day drift, 211 decisions (2 had a zero reaction) | **+55.8 bp** | +1.64 | G1 FAIL (needs t ≥ 2) |
| by era | E1 **+131.6**, E2 **−26.3**, E3 +40.6 | +2.38 / −0.54 / +0.58 | G2 FAIL (E2 negative) |
| trade, net of spread and 20 days' financing | +35.4 bp | +1.04 | G3 FAIL |
| placebo, the Thursday a week before | +3.5 bp | +0.09 | G4 PASS |

## Read it plainly

- **The direction is right, the size is roughly the paper's, and the evidence
  is too thin.** +56 bp against the ~90 bp that t = 2 needed. This is the
  power problem stated in §0 of the pre-registration, not a surprise.
- **It all comes from 2005–2012.** E1 has +132 bp, t 2.4. E2 (2012–19) is
  negative. E3 is positive but a third of E1. That is the same shape as
  FLOWS-1 and FLOWS-2: the effect sits in the crisis years.
- **The placebo is clean** (+3.5 bp). Whatever there is, it is tied to ECB
  days, not to a general DAX 20-day momentum.
- **Financing costs about 19 bp a trade** (gross fills +54.6, net +35.4).
- **Not the paper's split:** monetary shocks +73.9 bp (t 1.7), information
  shocks +32.5 bp (t 0.5). Valentin found information shocks larger.
- **Positive shocks drive it:** unsigned R20 is +164 bp after positive
  reactions and +41 bp after negative ones. After a negative reaction the
  DAX still rose, just less. So "step aside after a negative shock" barely
  helps: the paper's long-or-flat rule makes +5.40%/yr against +5.28% for
  buy-and-hold, both net of financing.

## What this closes

Post-ECB 20-day drift in DE30 on CFDs: dead as registered. It has no
tradable edge after financing and no recent-era support.
