# ARM G-mem (spec 2): gated, diagnosed, one disciplined improvement search

Run 2026-11-07 on gates/engine.py, same costs and gates as every arm, via the scripts
in this folder (arm_gmem.py, common.py, run_spec2.py, diag.py, search.py).
Side test, memory open, unregistered. Not an arm. Gate window ends 2026-08-31;
trades after that are reported as unseen. engine.DATA is re-pointed to
~/mnt/RStudio/Claude/... in arm_gmem.py; engine.py itself is untouched.

## Spec 2 as written: 4 of 7
```
[FAIL] 1 sign        E1 +0.352%  E2 -0.266%  E3 +0.132%
[PASS] 2 breadth     14 of 21 (exactly at the bar)
[FAIL] 3 effect      net +0.082% (gross +0.260%, cost 0.178%), t +0.67
[PASS] 4 sample      964
[FAIL] 5 robustness  K=1.5 -> -0.039% (-47% of base); L=3 30%, T=150 40%
[PASS] 6 control     +0.294%, 99% coverage
[PASS] 7 daily risk  VACUOUS: spec 2 claimed no drawdown. Measured 29.7%.
equity 10,000 -> 8,989, CAGR -0.5%.  Unseen after 2026-08-31: 6 trades.
```
Its own abandon conditions: (a) fires. (b) FIRES: ex-index net -0.004% on 799 trades,
so it is ARM F in disguise, as it warned it might be. (c) FIRES: E3 +0.132% is below
half of E1 +0.352% (0.176%). Three of its four abandon conditions fire; (d) is forward.

## Where the money is
- Indices: net +0.50%, t +2.28. Everything else: about zero. This is ARM F's effect.
- E2 loses on both sides; metals, energy, rates and softs all flip at 2012, like the
  trend arms.
- Removing the trend filter (G3) turns it to -0.25% per trade. The positive part comes
  from being on the trend's side, not from the reversal. Same finding as spec 1.
- |z| buckets rise monotonically (2.0-2.25: -0.24%; 3.0+: +1.10%). A real pattern in
  sample, but it is also exactly what makes Gate 5 fail: lowering K by 25% always
  dilutes a monotone effect by more than 20%.
- 38 stopped trades lose 5.7% each, about 0.22% per trade across the book.

## The search (plan fixed in SEARCH_PLAN.md before running)
```
id  change                 E1+E2   E1      E2      brd12  E3      full
G0  none                   +0.054  +0.352  -0.266  10     +0.132  +0.082
G1  K 2.5                  +0.291  +0.743  -0.363  13     +0.678  +0.431
G2  K 3.0                  +0.350  +0.693  -0.146  12     +0.936  +0.603
G3  no trend filter        -0.245  -0.164  -0.313   4     -0.128  -0.204
G4  no filter, K 2.5       -0.289  -0.324  -0.256   4     +0.084  -0.146
G5  trend at t-L, K 2.5    -0.173  +0.151  -0.505  10     +0.164  -0.043
G6  K 2.5, no stop         +0.377  +0.899  -0.380  14     +0.684  +0.488
G7  K 2.5, H 3             +0.055  +0.333  -0.345   8     -0.164  -0.024
(net % per trade)
```
Eligible under the rule (E1>0, E2>0, 14+ markets on E1+E2): NONE. Every variant loses
in E2, so every variant also fails Gate 1 on the full sample. Not improved.

## The trap, stated so it is not walked into later
G1, G2 and G6 show +0.43% to +0.60% full-sample and E3 +0.68% to +0.94%. Quoted
alone, those look like a fix. They are not: E2 is negative in all three, the threshold
was raised after seeing the |z| buckets, and E3 had already been seen. That is a fork
through the same data, which is what PROGRAMME.md section 9.5 says not to do.

## Verdict
The family is closed for this specification as well. Two independent specs of the
same idea (spec 1, spec 2) both put every position on the trend's side and both break
at 2012. The only part that works is the index dip-buy that ARM F already found.
