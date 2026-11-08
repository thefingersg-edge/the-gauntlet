# PREREGISTRATION FORWARD_v36 — registry entry for the NAS100 noise-band forward test

Registry pointer, 2026-09-26. The frozen specification is **FORWARD_v36.md** (sha256
c5eed9075ab841ced934e9e9bbcd07aa5c00b2a55104d62fca432f129e86c490, frozen 2026-09-25).
It is named here so that registry.py lists it as an OPEN pre-registered test. It
has run since 2026-09-28 via forward_tick.sh step 5 (forward_noiseband.py 1.0),
records only, and writes data/forward_noiseband.csv.

It derives from PREREGISTRATION_v36 (rule N), frozen unchanged: NAS100 only, both
sides. There is no performance kill rule before 250 trade-days. Execution-cost
validation is due at 60 trade-days. Confirming +4.35 bp/day needs about 12 years.
v38 and v40 (2026-09-26) both point to US indices at today's spreads as the only
place the edge can pay, which is why this test runs on NAS100.

I am not a financial adviser. This is a measurement, not a recommendation.
