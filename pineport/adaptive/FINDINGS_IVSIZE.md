# Implied volatility as the sizing input — the primary claim passes

Run 2026-08-27 against `PREREGISTRATION_IVSIZE.md`, written first, and held to
`../GAUNTLET.md`. Reproduce with `python3 f1_ivsize.py`,
`python3 f2_verify_ivsize.py` and `python3 f3_replicate.py`.

> ## CORRECTION — the first version of this file had a bug, and it changed a verdict
>
> `iv_on()` forward-filled each volatility index onto bar dates without a limit.
> That is right for weekends and holidays and **catastrophic for a discontinued
> series**. EVZ stops in March 2025 and was being carried forward to August 2026:
> **513 days, 7.5% of the EURUSD sample, of frozen implied volatility.** VXSLV
> stops in February 2022 and was carried to 2026 — **1,636 days, 29% of the
> silver sample.**
>
> Both of the markets that "failed" were the two with stale tails. The failure
> was the loader.
>
> With the fill capped at five bars and post-series bars dropped:
>
> | | before | after |
> |---|---|---|
> | dispersion gate | 3 of 4 | **4 of 4** |
> | frozen-forecast error gate | 3 of 4 | **4 of 4** |
> | era cells won | 10 of 12 | **11 of 12** |
> | silver replication | FAIL | **PASS** |
>
> The corrected result is stronger than the one first reported, which is not a
> reason to trust it more. Every number below is post-fix, and the check is now
> GAUNTLET 1.6.

**This is the first candidate in this project to pass its pre-registered primary
gates. It is also a narrow claim, and the pre-registration said in advance which
half of it would not survive.**

---

## PRIMARY — calibration. Passes.

Direction is held fixed at `sign(A)`; only the denominator changes. Implied vol
is rescaled by an expanding causal ratio so both rules carry the same average
exposure and differ only in timing. Realised volatility of the sized position,
on non-overlapping 21-day blocks against a 10% target:

| market | RV bias | **IV bias** | RV dispersion | **IV dispersion** | null dispersion |
|---|---|---|---|---|---|
| S&P 500 | 0.0300 | **0.0241** | 0.399 | **0.280** | 1.127 |
| gold | 0.0251 | **0.0194** | 0.355 | **0.265** | 0.660 |
| Brent | 0.0263 | **0.0203** | 0.359 | **0.272** | 0.860 |
| EURUSD | **0.0191** | 0.0196 | 0.255 | **0.242** | 0.494 |

| gate | threshold | observed | |
|---|---|---|---|
| 1 · dispersion lower | ≥ 3/4 | **4/4** | ✓ |
| 2 · bias lower | ≥ 3/4 | **3/4** (EURUSD by 0.0005) | ✓ |
| 3 · holds in every era | 3/3 | **11 of 12 market-era cells**; the only miss is EURUSD in 2005–12 | ✓ |
| 4 · beats destroyed-timing null | ≥ 3/4 | **4/4**, and not close | ✓ |
| 5 · plateau | plateau | **16 settings span 0.2641–0.2674** | ✓ |
| 7 · shared-term / frozen forecast | must survive | **4/4** on error, 3/4 on correlation | ✓ |

**Gate 4** makes it a forecast rather than an exposure profile: the same series
lagged 750 days — identical distribution, timing destroyed — gives dispersion of
0.49 to 1.13, two to four times worse than either real rule.

**Gate 5** is the flattest plateau this project has produced. Across four
rescaling windows and four leverage caps the dispersion moves by 0.0032 on a
value of 0.265 — about one percent. The leverage cap is nearly irrelevant,
because a well-sized position rarely reaches it.

**Gate 7** is the one the VRP study bought at full price. In the main run the
position re-sizes daily, so by day k of a block the trailing-realised forecast
already contains k−1 bars of the block it is scored on — which helps the RV rule.
Freezing both forecasts at the block boundary, so neither sees a bar of what it
predicts:

| market | RV rank corr | **IV rank corr** | RV error | **IV error** |
|---|---|---|---|---|
| S&P 500 | 0.437 | **0.468** | 0.530 | **0.497** |
| gold | 0.368 | **0.502** | 0.403 | **0.347** |
| Brent | 0.479 | **0.561** | 0.455 | **0.392** |
| EURUSD | **0.6677** | 0.6666 | 0.313 | **0.303** |

EURUSD is a tie on correlation (0.0011 apart) and a win on error. It remains the
weakest market in the set — it is the one where trailing realised volatility is
already the best forecaster available — but after the loader fix it is no longer
a failure, it is a near-tie. A 50/50 blend beats implied vol alone on 1 of 4, so
implied vol **replaces** trailing realised rather than merely adding to it.

---

## SECONDARY — Sharpe. Not established, exactly as pre-registered.

| market | RV Sharpe | IV Sharpe | at 5bp |
|---|---|---|---|
| S&P 500 | +0.300 | +0.328 | +0.250 → +0.255 |
| gold | +0.455 | +0.384 | +0.391 → +0.303 |
| Brent | +0.187 | +0.165 | +0.156 → +0.125 |
| EURUSD | +0.158 | +0.179 | +0.058 → +0.051 |

**2 of 4 at 1bp, 1 of 4 at 5bp. No Sharpe claim.** The pre-registration stated
before the run that a better volatility forecast implies better-calibrated
exposure and *not* a higher return, that only the first follows from the
mechanism, and that at an effective sample size near two the return test is
underpowered whatever it shows. None of that is revised now.

Part of the reason is measurable: implied-vol sizing costs **+4.7 turnover units
a year**, roughly a third more, because implied vol moves faster than a 60-day
average. At 5bp that is about 24bp a year against a rule returning around 2%.

---

## Where the value actually is

Not in the mean. In the tail of the exposure distribution:

| against a 10% target | RV sizing | IV sizing |
|---|---|---|
| 95th-percentile realised block vol | 16.1% | **14.0%** |
| worst block, S&P 500 | 26.1% | **21.8%** |
| worst block, Brent | 30.8% | **26.8%** |
| worst block, gold | 28.2% | **27.2%** |

A vol target exists to stop exposure running away. The implied-vol forecast cuts
the overshoot in the worst months by roughly a fifth at unchanged average
exposure. Whether that is worth a third more turnover is a risk decision, not a
backtest result.

---

## Replication — see `FINDINGS_IVSIZE_REPLICATION.md`

Both available replication pairs pass: **VXN → NAS100** and **VXSLV → silver**.
Under the replication pre-registration, neither adds evidence — they are
0.927 and 0.801 correlated with markets already in the set, and the effective
sample size does not move. They were run because a failure would have been
informative. Neither failed.

## Caveats, stated plainly

- **Four markets, effective sample size 2.42**, and it stays there with the two
  replications added. The calibration claim rests on ~1,000 non-overlapping
  block observations, which is where the power is; the return claim rests on
  four correlated markets, which is why it was pre-registered as secondary.
- **Coverage.** Six markets now have a usable volatility index; five of the
  eleven do not, and silver's ends in 2022. There is no version of this for the
  FX crosses or the DAX.
- **It is a calibration result.** It buys exposure control, not return.
- **A day's implementation lag** costs the direction component but barely touches
  calibration — dispersion moves from 0.265 to 0.28–0.30.
- **The result got better when a bug was fixed.** That is the right direction for
  a bug fix to move a result, and it is also exactly how a bug that *flattered*
  a result would look if it were still there. The loader is now checked; nothing
  else in the chain has been.
