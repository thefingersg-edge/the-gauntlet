# RESULT — PEAD1: earnings-reaction drift in US single stocks. The drift is real and has not decayed (+1.1% over 60 days, t 3.9, in every era including 2018–26). But estimated small-cap trading costs of about 1.1% take all of it. FAIL as registered.

```
SPEC:     PREREGISTRATION_PEAD1.md  sha 527d3ce5…  (engine pead_engine.py a9a48da7…, ss_lib.py b6a9594e…)
METHOD:   singlestock/pead1_run.py (staged; final run once); Sharadar full-history bundle (hashes in PROVENANCE.md);
          16,904 US common stocks incl. delisted; 238,800 M+S announcements 2005-2026; log data/run_pead1.log
          post-hoc addendum (labelled): singlestock/pead1_posthoc.py, log data/pead1_posthoc.log
RUN:      2026-10-02
VERDICT:  G1 FAIL  G2 FAIL  G3 FAIL  G4 PASS  G5 FAIL  -> FAIL
```

**I am not a financial adviser. This is a measurement, not a recommendation.**

## Gates (M+S bands, long the top-decile EAR, entry at the open 2 days after the 8-K, held 60 trading days, excess over the band benchmark, net of the EDGE spread and commission; SEs clustered by quarter)
```
G1  net excess +0.03%  t +0.09  n 24,266                                                    FAIL
G2  eras  2005-12 -0.07%  2013-19 -0.02%  2020-26 +0.20%   2018-26 -0.03% (t -0.07)          FAIL
G3  M -0.70% (t -2.37)   S +0.45% (t +1.30)                                                 FAIL
G4  GROSS excess +1.10% vs random-announcement null 95th pct +0.19% (median -0.02%)         PASS
G5  calendar-time excess portfolio 2018+: Sharpe -0.21                                      FAIL
reported: gross M+S +1.10% (t +3.93); median round-trip cost 81 bp (EDGE M 54 bp, S 80 bp)
          L band net +0.24% (t 0.5); X band net -0.52%; 20-day hold net -0.43% (t -2.8)
          with 2 x 0.03% currency conversion: net -0.03%
          ALL M+S announcements, 60-day gross excess: -0.01% (n 238,800) -- the drift is in the top decile, not in "after earnings"
```

## Post-hoc (descriptive only, not gated)
```
gross by era (M+S):  2005-12 +1.04% (t 2.47)   2013-19 +0.87% (t 1.88)   2020-26 +1.42% (t 2.47)   2018-26 +1.12% (t 2.36)
gross by band:       M +0.17% (t 0.58)          S +1.64% (t 4.71)
mean cost per trade: about 0.9-1.2%
if the real cost were 50% of the EDGE estimate:  net +0.56% (t 2.02);  2018+ +0.54% (t 1.17)
if the real cost were 25% of the estimate:       net +0.83% (t 2.98);  2018+ +0.83% (t 1.77)
cheapest third of trades by estimated cost:      net +0.27% (t 0.98)
```

## Read it plainly
- **This is the first real directional effect in the programme.**
  - Stocks with the strongest positive three-day reaction to their results go on to beat similar stocks by about **1.1% over the next 60 trading days**. The t is 3.9, and it comfortably beats picking random announcements.
  - It is positive in all three eras **and on 2018–2026 by itself**. The decay the literature reports has not happened here.
  - It lives in the smaller stocks (S band +1.6%, t 4.7), not in the mid band.
- **It does not survive the costs we assume.** Small stocks' estimated round-trip spread is about 0.8–1.2%, roughly the whole effect. As registered it fails, and nothing here changes that verdict.
- **The decision now turns on one number: the real cost.** The EDGE estimate comes from daily high/low/open/close. It measures the quoted spread a market order pays. A patient trader using limit orders inside the spread pays less.
  - If the real cost were half the estimate, the full sample nets +0.56% (t 2.0), but 2018+ is only t 1.2.
  - So even the optimistic case is marginal in recent years.

## What would move this forward (each needs its own pre-registration)
1. **Measure real costs on small caps:**
   - quote and trade data for a sample of S-band stocks (paid, e.g. Polygon or Databento), or
   - an IBKR paper or small live sample of limit-order fills.
2. **A stronger signal** that is still point-in-time:
   - EAR combined with SUE at the 10-Q date (Brandt et al. found the combination roughly doubled the drift);
   - holding only where the reaction is confirmed on volume.
3. **Fewer, cheaper trades:** restrict to the most liquid part of the S band, accepting fewer events.

## Caveats
- Spreads are estimated, not observed.
- Bands are by dollar volume, not market cap.
- The −30% delisting rule is an assumption; sensitivity has not been run yet.
- The G5 calendar mapping uses an approximate trading-day-to-calendar conversion.
