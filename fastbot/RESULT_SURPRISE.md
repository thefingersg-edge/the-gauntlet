# RESULT — v32: does a bigger surprise mean a bigger bounce?

```
RUN:      2026-09-25   SPEC: PREREGISTRATION_v32 (sha256 checked)
PART A:   premarket_surprise.py 1.0 -- weekly claims, never looked at for
          this question. GA FAILS.
PART B:   forward_surprise.py 1.0, hooked into forward_tick.sh (non-fatal).
          Records from payrolls on 2026-10-02. Verdict at 150 release
          dates or 2032-09-30.
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.** Inputs and caveats: PROVENANCE.md.

## Part A — claims

Gate 0: 4,820 claims-morning trades matched v27, max difference 5e-07 bp.
836 claims releases with a usable surprise (91 in the pandemic window).

```
PRIMARY  pandemic out, |z| capped at 3    n 4246 on 745 releases
         b +0.103  t +1.31   halves +0.100 (t +1.13) / +0.075 (t +0.49)
         fade: bigger-surprise half +0.81 bp, smaller half +1.37 bp
REPORTED all dates, uncapped               b -0.206  t -1.55
         fade: bigger-surprise half +0.23 bp, smaller half +0.84 bp

[FAIL] GA  b +0.103  t +1.31  (needed t >= 2.0)
```

**On the one sample that had never been looked at, the lead does not
reproduce.** The slope is small and not significant, and the plain split
points the other way: bigger claims surprises bounced LESS. Prediction
(GA fails): right.

This does not kill the idea for CPI and payrolls -- claims' own bounce is
small (+0.86 bp), so there was little for a surprise to scale -- but the
two historical hints (t 2.15, t 2.90) now have no independent support,
and it is fair to read them as the shape this project has been fooled by
before.

## Part B — forward

Each CPI and payrolls release from 2026-10-02 gets a row in
`data/forward_surprise.csv`: the first print, the naive surprise, and
Kalshi's call just before 08:25 with the crowd surprise. It never
touches the v25 ledger, and a failure only logs a line. The answer
arrives in years, not months.

---

**Investigation forty-eight.**
