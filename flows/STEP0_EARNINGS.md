# FLOWS-9 (EARNINGS) — Step 0 failed twice. NOT RUN; no price has been joined.

```
STATUS:   VOID at Step 0 (2026-10-02). No return was computed.
EVIDENCE: data/earnings.meta.json, data/earnings_universe.csv (A1 build), data/earnings_frames/
```

The registered universe, "the ten largest public floats in the SEC XBRL frame
CY(y−1)Q2I", cannot be built cleanly from SEC data, for two independent
reasons.

1. **Persistent mis-scaled filers.** Amendment A1 screened out one-off scale
   errors (a value at most $5×10¹², and within ×3 of the previous year). It
   cannot catch firms that mis-scale **every** year: Novanta ($4.8×10¹² in
   2021 and $4.4×10¹² in 2024), Steven Madden and Gentherm still sit in the
   2022–2025 top ten. A firm that makes the same error each year passes a
   year-on-year check by construction.
2. **The frame only holds 30 June float dates.** Apple (float dated in March)
   and Microsoft (December) **never appear** in a CY…Q2I frame. The two
   largest US companies are structurally absent from the universe.

Both were found from company names and reported values alone. A second
amendment would be a third rule laid on an input that does not describe
the object in §0. That is the drift rule 2 warns against. **FLOWS-9 is
void, not failed.**

**To reopen it honestly** would take a fresh pre-registration with a clean
size source fixed in advance: for example, year-end market-cap rankings from
a vendor, or CRSP. It would be written before any price is joined, as
before.
