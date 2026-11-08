# DEFINITION — CYCLES1.1: merging bear-market rallies (amendment to CYCLES1)

```
STATUS:   frozen before CYCLES1.1 is computed (sha in PROVENANCE.md)
WRITTEN:  2026-10-09
WHY:      CYCLES1 split 2007-09 and 1929-32 into bear / short bull / bear, because a 20%+ "bear-market rally" ended the first bear.
          This is the known weakness of the plain 20% rule; Pagan & Sossounov (2003) handle it with an 8-month window on turning points.
          The change was SEEN in the CYCLES1 output, so it is an amendment, logged as such. It uses the published window and is not tuned.
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

## The one added rule
After CYCLES1 dating, a **bull phase lasting less than 8 months** (peak date minus trough date, computed in days on daily data) whose **following bear makes a lower low** than the preceding bear's trough is reclassified as a **bear-market rally**. The bear before it and the bear after it are merged:
- peak = the first peak;
- trough = the lower trough;
- confirmation = the first bear's confirmation.

The rule repeats until no such pattern remains.

**It is not applied the other way round.** Short bears followed by a higher high (1987, 2020) remain bears. That is how they are conventionally recorded, and it avoids erasing fast crashes.

## Everything else
Unchanged from CYCLES1: the 20% thresholds, the confirmation-date definition, the measures and the detectors. Results are reported side by side with CYCLES1. CYCLES2 uses the CYCLES1.1 dates.
