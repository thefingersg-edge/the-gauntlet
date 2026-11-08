# AMENDMENT A1 to PREREGISTRATION FLOWS-4 (ANNOUNCE) — which GDP dates

```
WRITTEN:   2026-09-27, after Step 0 stopped and BEFORE any price has been
           joined to any FLOWS-4 date. The base document is unchanged
           (sha 9705a725…, commit d884bc5). This amendment changes one
           input definition and nothing else.
STATUS:    FROZEN at its first commit; announce.py pins it alongside the base.
```

## What happened

§1 defined GDP days as "every release of ALFRED rid=53" and said "a GDP year
with fewer than 11 or more than 13 releases is a parse failure". The first
Step 0 run (Dave's Mac, 2026-09-27) found 865 rid=53 dates, with 14–16 a year
in 2009, 2013, 2014, 2016, 2017, 2020 and 2021. The extra dates are not GDP
estimates, for example 2009-08-03, 2014-01-10, 2014-09-17, 2017-10-03,
2020-09-16 and 2021-08-06. They are ALFRED vintages of other tables in the
same release, such as annual-update detail and corrections. The guard fired
as intended. The source does not match the event the pre-registration names:
the days BEA publishes a quarterly GDP estimate (advance, second or third).

## The change

**GDP days = the vintage dates of real GDP itself (FRED series GDPC1)**, from
the FRED API `series/vintagedates`, 2005-01-01 to 2026-08-31. A new vintage
of GDPC1 exists exactly when BEA publishes a new GDP estimate.

Checks. A failure STOPS the build, and nothing is written.

- Every GDPC1 vintage date must also be an ALFRED rid=53 date, because the
  two sources describe the same release.
- There must be 10–13 dates a year. 2019 and 2025 may be low because of the
  shutdowns, and each is listed.
- The rid=53 dates that are dropped are written into the meta file so they
  can be audited.

Nothing else changes: the event set, times, VIX state, regression, gates and
kill conditions are exactly as in the base document.

## Why this is not a fourth parameter

It is decided by the definition the base document already states (a GDP
*estimate* release), from metadata alone, before any return exists. Neither
choice of source was available to be compared on results, because no result
exists.
