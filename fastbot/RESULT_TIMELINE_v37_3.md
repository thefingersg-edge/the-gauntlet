# RESULT — v37.3: does training on the post-COVID world predict better? No. More history beats newer history.

```
SPEC:     PREREGISTRATION_v37.3.md  sha 0bb2bd25…
METHOD:   timeline_v37_3.py 1.0   log data/timeline_v37/run_v37_3.log
VERDICT:  A1 PASS (by 0.0001)   A2 FAIL   B FAIL
```

**I am not a financial adviser. This is a measurement, not a recommendation.**

## Part A — trained 2022–24, tested 2024-08-15 → 2026-08-14
```
test direction AUC   NEW (2022-24) 0.536   OLD (2005-12) 0.521   ALL (2005-24) 0.520
A1  NEW vs 20 nulls (max 0.5359)          PASS by 0.0001 -- a coin-edge, not a result
A2  NEW - OLD +0.015, 95% [-0.028, +0.061] FAIL
A3  NEW model trades: 237, net -0.22 bp, t -0.12
```

## Part B — eight eras, RECENT 3 years vs ALL PRIOR history
```
recent    test      RECENT  ALL-PRIOR   gain
2007-09   2010-11   0.487   0.501      -0.014
2009-11   2012-13   0.552   0.503      +0.049
2011-13   2014-15   0.529   0.529      +0.001
2013-15   2016-17   0.545   0.547      -0.001
2015-17   2018-19   0.494   0.537      -0.044
2017-19   2020-21   0.496   0.578      -0.082   (CI excludes 0)
2019-21   2022-23   0.562   0.579      -0.017
2021-23   2024-25   0.522   0.558      -0.036
RECENT wins 2 of 8; mean gain -0.018, t -1.33 -> FAIL
```

## Read it plainly
- **Training on post-COVID data did not improve direction prediction.** The 2022–24 model was slightly better than the 2005–12 model on 2024–26 (+0.015 AUC), but well inside noise. It lost money when traded.
- **Across eight eras, "train on the last 3 years" usually does WORSE than "train on everything so far".** In the COVID period it was clearly worse: 0.496 against 0.578. Whatever the timeline knows about direction, it needs lots of history to learn it. That is the opposite of "the world changed, so old data misleads".
- **One thing worth keeping:** the ALL-PRIOR models score 0.53–0.58 in every window from 2014 on. That is a faint but repeated sign that the full-history timeline carries some direction information. Two cautions:
  - Part B has no permutation null.
  - v37.2's sealed test showed how thin this is in money: an AUC of 0.55 made +1.5 bp a trade, t 1.4.
  It is a lead, not a finding.

## What this means for the living model
- Train on ALL history and retrain as data arrives (expanding window), not on a short recent window.
- Every retest now needs data no model or researcher has seen: forward data, or new instruments.
