# RESULT — v45: index rebalancing days. No next-morning reversal of the last-hour move; the fade loses after the spread.

```
SPEC:     PREREGISTRATION_v45.md  sha 69543678…
METHOD:   rebal_v45.py 1.0; SPX500, NAS100 (OANDA 5m, data/, 2005-) and UK100 (5m, data/v38, 2013-); log data/run_v45.log
RUN:      2026-09-27
VERDICT:  PRIMARY FAIL
```

**I am not a financial adviser. This is a measurement, not a recommendation.**

## Interpretations fixed in the harness before the run
- **Rebalance days:** the quarterly third Friday (or the Thursday before it, if the Friday is a holiday).
  - SPX500 and UK100 use all four quarters. NAS100 uses December only, as the spec names it; its March, June and September quarter days are excluded from every group.
- **Controls:** control (a) is the other eight monthly-expiry Fridays; control (b) is all other Fridays.
- **Last hour (LH):** US 14:55 → 15:55 bar close; UK 15:25 → 16:25 bar close.
- **Next morning (NM):** the next session's open → the close of the bar starting 55 minutes later.
- **Self-test:** a planted reversal passes and a planted continuation fails. It passed.

## Numbers (bp; SEs clustered by date)
```
rebalance days: SPX 86, NAS 21, UK 55 (pooled 162);  control-a 456;  control-b 2,152
(i)  NM = a + b*LH on rebalance days     b -0.104   t -0.43        needs t <= -2.0   FAIL
(ii) rebalance slope minus control-a     d -0.317   t -1.23        needs t <= -2.0   FAIL
reported slopes: rebalance -0.10 (t -0.43)   control-a +0.21 (t +2.13)   control-b +0.00
reported mean last hour: rebalance -9.0 bp   control-a +3.6   control-b +2.3
reported fade trade (opposite of LH over NM), net of spread: SPX -1.8  NAS -11.4  UK -1.5;  pooled gross -1.1, net -3.0, hit 48%
```

## Read it plainly
- **No reversal.** The next morning does not undo the last hour on rebalance days (slope −0.10, t −0.4). Fading the move loses money even before the spread.
- **The comparison is weak too.** The rebalance slope is lower than on other expiry Fridays, but not significantly (t −1.2).
  - Other expiry Fridays show mild *continuation* (+0.21, t 2.1). That was reported only and was not a hypothesis.
- **One descriptive oddity:** the last hour on rebalance days averaged **−9 bp**, against +2 to +4 bp on other Fridays. It is not tested here, and there are only 162 days.
- As the pre-registration warned, index-level pressure mostly cancels: funds buy the additions and sell the deletions. The effect lives in constituents, not the index CFD.

## Caveats
- The test has low power: only a reversal of at least about a third of the last-hour move was detectable.
- The special Nasdaq rebalance of July 2023 is excluded.
