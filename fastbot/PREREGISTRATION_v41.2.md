# PREREGISTRATION v41.2: amendment — stamp the broad dollar index at its real weekly release

Frozen 2026-10-04, after RESULT_AUDIT_INDEX and before the v41 forward ledger has any row.

I am not a financial adviser. This is a measurement, not a recommendation.

- **Problem (RESULT_AUDIT_INDEX):** `tl_build2.macro_events` stamps each daily value of the Nominal Broad Dollar Index (FRED DTWEXBGS, Federal Reserve H.10) at 18:00 on its own date. The Fed publishes H.10 weekly, on the Monday after the week it covers, so the `usd_chg5` state and the `usd_up1`/`usd_dn1` events were available up to a week before they really were.
- **Fix (forward recorder only, `forward_forest.py` 1.2):** every usd value and usd event is restamped at 16:15 ET on the Monday strictly after its observation date, and the completeness guard uses the same rule. Monday holidays (release on Tuesday) are not modelled.
- **Unchanged:** `tl_build2.py`, the frozen forest (`forest_v41.pkl`, `freeze_v41.json`), thresholds, entries, exits and the decision rules.
- **Consequence stated:** the frozen forest was trained with the early stamps, so live it sees dollar information later than in training. Any loss of performance from that is part of what the forward record now measures honestly. v39/v40 conclusions carry this caveat.
