# Replication — implied-vol sizing on markets it was not fitted to

Run 2026-08-27 against `PREREGISTRATION_IVSIZE_REPLICATION.md`, written **before
the data existed**. The rule was frozen; nothing was tuned. Reproduce with
`python3 f3_replicate.py`.

## What the pull returned

| series | obs | span | usable |
|---|---|---|---|
| **VXNCLS** (Nasdaq) | 6,430 | 2001-02 → 2026-08 | yes |
| **VXSLVCLS** (silver) | 2,748 | 2011-03 → **2022-02** | yes, to 2022 |
| RVXCLS (Russell 2000) | 5,697 | 2004-01 → 2026-08 | needs `US2000_USD` |
| VXDCLS (Dow) | 7,269 | 1997-10 → 2026-08 | needs `US30_USD` |
| BAMLH0A0HYM2 | **787** | **2023-08** → 2026-08 | **still truncated** |

## Results — each pair scored on its own

| pair | RV disp | **IV disp** | RV bias | **IV bias** | null | frozen-forecast ρ | verdict |
|---|---|---|---|---|---|---|---|
| **VXN → NAS100** | 0.353 | **0.266** | 0.0269 | **0.0210** | 0.827 | 0.403 → **0.461** | **PASS** |
| **VXSLV → silver** | 0.362 | **0.270** | 0.0242 | **0.0236** | 0.741 | 0.488 → **0.573** | **PASS** |

Per era, dispersion:

| pair | 2005–12 | 2012–19 | 2019–26 |
|---|---|---|---|
| NAS100, RV → IV | 0.321 → **0.267** | 0.363 → **0.250** | 0.372 → **0.283** |
| silver, RV → IV | — | 0.311 → **0.241** | 0.494 → **0.346** |

Silver has no 2005–12 window because VXSLV starts in 2011, and its 2019–26
window ends in February 2022.

## What this does and does not mean — as written in advance

**It does not add evidence.** NAS100 is 0.927 correlated with the S&P and silver
is 0.801 correlated with gold. Measured before the run: effective sample size of
the tested set is 2.42, and adding both takes it to **2.39** — it goes down.
These are the same two observations again. The pre-registration says a pass is
reported as *consistent with* and nothing more, and that is what this is.

**It was worth running because a failure would have been informative.** A rule
that calibrates the S&P well and the Nasdaq badly would not be doing what the
mechanism claims. Neither pair failed.

## The correction that came out of running it

The first run of this replication returned **silver: FAIL**, on four gates at
once. That was wrong, and finding out why changed the original result too.

`iv_on()` forward-filled without a limit. VXSLV stops in February 2022; it was
being carried forward to August 2026 — **1,636 days, 29% of the silver sample,
of frozen implied volatility**, which is what a "failing" calibration looks like.
The same bug was inventing 513 days for EURUSD in the original study, which is
the market that failed there.

With the fill capped at five bars, silver passes and EURUSD improves from a
failure to a near-tie. The check is now GAUNTLET 1.6, and `iv_on()` prints a
warning whenever a series ends more than 30 days before the price data.

**The replication's most useful output was not the replication.** It was a stale
series in a market nobody had looked at closely, which exposed a loader bug that
had been quietly degrading a result already published.

## Still outstanding

- **The credit-spread candidate is still untested.** `&cosd=` fixed every other
  series — DGS10 came back from 1962, VXD from 1997 — but BAMLH0A0HYM2 still
  returns 787 observations from 2023-08. It is a per-series quirk of the graph
  endpoint, not the fix failing. FRED's `/data/BAMLH0A0HYM2.txt` endpoint is
  worth trying as a fallback.
- **RVX and VXD are in hand** but need `US2000_USD` and `US30_USD` from OANDA.
  Both are more correlated with the S&P than the Nasdaq is, so both are worth
  less than the replication just run — which was worth nothing in evidence
  terms. Pull them only if the aim is more falsification surface, not more
  confirmation.
