# The two leads from FLOWS-4 and FLOWS-6: post-hoc diagnostics

```
SCRIPT:   leads_posthoc.py   log data/leads_posthoc_run.log   (2026-09-27)
SAMPLE:   the registered samples only, to 2026-08-31. Nothing after that date is read.
STATUS:   DESCRIPTIVE. Both patterns were found, not predicted. Nothing here is evidence.
```

*Measurement, not a recommendation. Not financial advice.*

## Lead A — release days on low-VIX evenings (FLOWS-4)

| check | result |
|---|---|
| SPX500 low-VIX excess (b1) | +12.0 bp, t 3.23 |
| same on NAS100 / US30 / DE30 | +10.3 (t 2.2) / +9.6 (t 2.8) / +10.9 (t 2.4) |
| high minus low (b3), SPX500 | −12.3 bp, t −1.44: **the split itself is not significant** |
| unconditional release-day excess, SPX500 | +6.4 bp, t 1.55 |
| drop the 10 best days / 10 best and 10 worst | +8.8 (t 2.7) / +13.9 (t 4.8) |
| by type, low VIX | CPI +6.1, NFP +17.6, GDP +9.2, ISM +17.4 |
| by VIX/median tercile, excess over control days | low +15.3, mid +11.7, **high −7.4** |
| trade, ask in / bid out, by era | +11.3 / +5.1 / **+16.3 (t 2.7)** bp; all +10.9 bp, t 3.14, ~25 a year |

**Read.** The pattern is broad: every index, every release type, every era,
and it is not driven by a handful of days. The honest summary is that
release days pay a premium, as the literature says, except when VIX is
already elevated. The difference between low and high VIX is itself not
significant (t −1.4). It is the one lead in this programme that is **larger
in the most recent era**. The four indices are one US equity factor, not four
confirmations.

**Next:** FLOWS-7 (`PREREGISTRATION_LOWVIX.md`) tests it on 1994–2004, which
has never been looked at, and then forward on the CFD.

## Lead B — natural gas on EIA Thursdays (FLOWS-6)

Mean log return by clock segment (ET), report Thursdays against other days:

| segment | Thursday | other days |
|---|---|---|
| 00:00–08:00 | −1.6 | +2.0 |
| **08:00–10:30** | **−20.9** | −0.3 |
| **10:30–11:00** | **−15.5** | −0.7 |
| 11:00–14:30 | −5.7 | −3.7 |
| 14:30–17:00 | +6.7 | +8.9 |

The fall is concentrated in the 2½ hours before the release and the half
hour after it. That points to the report, not to a general Thursday effect.

It is stronger in the winter withdrawal season (−48.6 bp excess, Nov–Mar)
than in the injection season (−36.2 bp).

On Thanksgiving weeks the release moves to Wednesday, and those Wednesdays
gave +80.9 bp (n 21, t 1.1). That is too few days and the wrong sign to
support the EIA reading.

**The decisive check is by era.** Short 08:00 → 11:00 ET on report Thursdays,
mid price:

| era | mid | net of spread | round-trip spread |
|---|---|---|---|
| E1 2005–12 | +77.4 bp (t 5.4) | (no spread on file) | 0.0 |
| E2 2012–19 | +3.4 | −12.8 | 32.4 |
| E3 2019–26 | +15.5 | −8.2 | 47.5 |

**Read.** It is the same shape as FLOWS-1, -2 and -5 again: large in
2005–2012, and small since. The recent residual (about 15 bp) is a third of
the OANDA spread. OANDA quoted no natgas spread before 2013, so every E1 net
figure is really gross.

**Decision: parked.** It would only be worth a pre-registration on a
futures vehicle with a spread of a few bp, and even then the recent edge is
about 15 bp a trade. It is not tested further on the CFD.
