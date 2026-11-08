# RESULT — v56: weak S&P breadth is followed by a stronger S&P month. PASS as registered, against my prediction. The pass is narrow and depends on the standard-error method.

```
SPEC:     PREREGISTRATION_v56.md  sha 2fa66403…  (frozen in commit f4a4c25)
METHOD:   breadth_v56.py 1.0 (sha 9219d57f…); data/tv_20261001 (MANIFEST b287eb00…); OANDA SPX500 15m bid/ask (data/v24)
LOGS:     data/v56_run.log (the registered run); data/v56_checks.log (post-hoc checks, descriptive)
RUN:      2026-10-02
VERDICT:  PASS  (G1 PASS t -2.06, G2 PASS, G3 PASS t +2.13), narrowly; see the checks before relying on it
```

**I am not a financial adviser. This is a measurement, not a recommendation.**

## The registered run
```
h=20  n 4,896   slope per 10pp of S5FI  -23.87 bp   NW t -2.06          G1 PASS
      eras  2007-12 -4.81 (t -0.24)   2013-19 -29.54 (t -2.12)   2020-26 -46.07 (t -2.42)   G2 PASS
      S5FI < 20 (326 days) minus the rest  +229.6 bp  NW t +2.13
      low-breadth mean +292.6 bp vs all days +78.3 bp; median entry spread 1.33 bp      G3 PASS
h=5   slope -6.64 (t -1.64); low minus rest +56.9 bp (t +1.25)     reported
```
- **The prediction was wrong.** I wrote that the sign would be right but t would fall short of −2, and that one era would break. Neither happened: all three eras have the predicted sign, and the effect is larger in recent years, not smaller.
- That runs against the pattern of the six published timing effects that decayed (PROGRAMME §11).

## Reported (not gated)
- S5TH (above the 200-day): slope −11.90 bp (t −0.77).
- ADD z-score: −1.15 bp (t −0.15).
- **Breadth measured over 50 days carries it; 200-day breadth and one-day A/D do not.**
- **Zweig thrusts (9 since 2007):** every one had a positive r20, ranging from +154 to +731 bp. Eight of the nine had a positive r60. Nine events is an anecdote, not evidence.
- **First washouts (S5FI < 10, 14 since 2007):** r20 positive in 9 of 14, including −2,568 bp (2008-09-29) and −920 bp (2020-02-27).

## Checks run AFTER the verdict (data/v56_checks.log). They change nothing, but they are how to read it
| check | slope t | low-breadth t | reading |
|---|---|---|---|
| registered (Newey–West, Bartlett lag 20) | −2.06 | +2.13 | pass |
| Hansen–Hodrick (equal weights to lag 19, the textbook choice for overlapping returns) | −1.82 | +1.93 | **would not pass** |
| non-overlapping months, 20 offsets (245 obs each) | median −1.40 (−3.10 … −0.49) | median +1.44 (+0.23 … +2.50) | same sign every offset, weak alone |
| excluding 2008-09 → 2009-06 and Feb → Jun 2020 | −3.54 | +3.97 | **stronger without the crash rebounds** |

- The effect is a **regime**, not an entry signal. There are 26 independent low-breadth episodes, and the r20 from their FIRST day averages only +57 bp (15 of 26 positive). The premium comes from being long through the weak stretch, not from catching the turn.
- **Cost:** a long SPX CFD held 20 sessions pays about 54 bp of financing plus the 1.3 bp spread. The low-breadth mean nets about +238 bp, against about +23 bp for the plain long over the same period.

## How to read it, plainly
- Registered gates passed, so this is a PASS. It joins a very short list of pre-registered direction passes: v40 (the timeline, out of market) and FLOWS-2 (pre-refunding Treasuries, since decayed). It is the only one from a published indicator that is stronger in recent years.
- It sits **on the knife-edge of the standard-error choice**, rests on about 26 independent episodes, and uses TradingView's breadth series. That series' constituent handling (survivorship) cannot be checked from here.
- The shape (higher returns after the market has been broadly weak, stronger outside crashes) is what a **premium for holding through fear** looks like, not a timing pattern. That fits the programme's finding that what survives is being paid to bear something unpleasant. That is an interpretation, not a test.
- **What this does not justify:** trading it. 26 episodes cannot separate +230 bp from luck at the stricter standard errors.

## What follows
- **Proposed, not yet registered:** a forward record of the S5FI < 20 regime (recording only, like v41), and a replication on breadth rebuilt from a constituent history that is free of survivorship bias, if one can be sourced. Each needs its own pre-registration.
