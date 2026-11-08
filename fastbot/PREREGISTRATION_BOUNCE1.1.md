# PREREGISTRATION BOUNCE1.1: amendment — charge the overnight financing OANDA actually charges

Frozen 2026-10-07, before any BOUNCE1 data exists (the SPY pull has not started). Found by the assumptions audit (AUDIT_ASSUMPTIONS_2026-10-07.md).

I am not a financial adviser. This is a measurement, not a recommendation.

- **BOUNCE1 assumed** a flat 2.0 bp per night for financing.
- **Measured** (`data/oanda_financing.json`, SPX500_USD, live, 2026-09-04): long positions pay 6.15% a year, short positions **receive** 1.15% a year, and Friday nights are charged three days. That equals the US policy rate (about 3.65%) plus 2.5% for longs, and minus 2.5% for shorts.
- **Rule from now on:** financing for a trade opened on day t = days charged (3 on Friday, else 1) / 365 × [long: −(r + 2.5%); short: +(r − 2.5%)], with r = the US policy rate for that month from `data/policy_rates.csv`. In 2020–21 (r ≈ 0.1%) shorts paid about 2.4% a year and longs about 2.6%.
- Spread cost unchanged (1.0 bp). Gates G1–G3 unchanged, with G2/G3 using this cost instead of the flat 2.0 bp.
- Reported as well: the original flat 3.0 bp version, so the effect of the amendment is visible.
