# AMENDMENT A1 to PREREGISTRATION FLOWS-9 (EARNINGS) — screening mis-scaled public-float filings

```
WRITTEN:   2026-09-28, after the Step 0 universe was built and inspected, and BEFORE
           any price has been joined to any earnings date. Base unchanged (sha 4df6d4ae…).
STATUS:    FROZEN at its first commit; earnings.py pins it alongside the base.
```

## What happened

The universe rule in §1 was "the ten registrants with the largest
`dei:EntityPublicFloat`". Applied literally to the SEC frames, it selects
**unit errors**, not the largest companies. Filers that tagged their float in
the wrong scale report values up to $3×10¹⁶. For example, the 2022 list is
topped by Zimmer Biomet at "$33 quadrillion", and the 2018 list by IQVIA. Only
2–4 of each year's ten are genuine mega-caps. The resulting table does not
measure what §0 describes.

## The change

A frame value counts only if it is plausible by two checks that use **no
price and no later information**:

1. It is at most **$5 × 10¹²**. No US company's public float reached that at
   any instant in the sample.
2. The same CIK reported a float in the **previous** year's frame
   (CY(y−2)Q2I), and the ratio of the two values lies between **1/3 and 3**. A
   one-off scale error is a factor of 1,000.

The universe for year y is the ten largest values that pass both checks.
Filers whose previous-year value is missing are excluded, so the first
universe year moves one year later. The unfiltered and filtered lists are
both written to the meta file for audit. Everything else is unchanged
(events, windows, return, gates).

## Why this is not a fourth parameter

It corrects the input so that it matches the object the pre-registration
names ("mega-cap" firms whose announcements are market events). It was decided
by inspecting company names and reported values only. No return exists yet.
