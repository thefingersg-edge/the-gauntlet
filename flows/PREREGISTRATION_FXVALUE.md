# PREREGISTRATION FLOWS-13 — currency value (five-year real exchange-rate reversal)

```
WRITTEN:   2026-09-28, before any exchange-rate or price-level series has been fetched.
STATUS:    FROZEN at its first commit; fxvalue.py pins this file's sha256.
SOURCE:    Asness, Moskowitz & Pedersen, "Value and Momentum Everywhere"
           (JF 2013); Menkhoff, Sarno, Schmeling & Schrimpf, "Currency Value"
           (RFS 2017)
VEHICLE:   G10 currencies against USD (OANDA FX CFDs for the cost check)
```

*Measurement, not a recommendation. Not financial advice.*

## 0. The claim

Currencies whose real exchange rate has risen most over five years
(expensive) underperform those that have fallen most (cheap). This is the
FX expression of value, the one basic factor the programme has never
tested. fastbot tested FX **carry** (FXCARRY, CARRYDISPERSION), which is a
different signal. **Registered expectation:** weak. The published Sharpe is
about 0.3–0.5, and the Fed's 2025 study finds fundamentals rarely beat a
random walk at one month.

## 1. Data (Step 0, FRED, frozen before any return is computed)

- Currencies: EUR (DEM before 1999, spliced at 1.95583), JPY, GBP, CHF, CAD,
  AUD, NZD, SEK and NOK against USD. Month-end spot from FRED daily DEX
  series.
- Price levels: US CPI (CPIAUCSL). Foreign CPIs from OECD MEI on FRED
  (CPALTT01xxM661N; euro area from its euro series, Germany before 1999).
  **Lagged one month** for publication.
- Short rates: US TB3MS; foreign 3-month interbank rates, OECD
  IR3TIB01xxM156N. If one is missing, the call-money rate IRSTCI01 is used.

## 2. Signal and portfolio (monthly)

- Real exchange rate q_i = log S_i(USD per unit of i) + log P_i − log P_US.
- **Value_i = −(q_i,t − q_i,t−60).** A large rise over five years makes the
  currency expensive, which gives a negative value score.
- Each month-end, rank the currencies. Go long the top 3 and short the
  bottom 3, equal weight, USD-neutral, held one month.
- Excess return per currency = spot change + (i_foreign − i_US)/12.
- Sample: portfolio returns 1990-01 → 2026-08. Signal and rate
  availability set the start. The first month with all nine currencies is
  used, and it is recorded.

## 3. Gates

| gate | test | pass |
|---|---|---|
| **G1** | mean monthly long–short excess return | > 0, t ≥ 2.0 (Newey-West 3) |
| **G2** | thirds: 1990–2002, 2003–2014, 2015–2026 | > 0 in all three, **last ≥ 0.5 × full** |
| **G3** | spot-only version (no interest differential) | > 0: value is not just carry in disguise |
| **G4** | net: minus 2 bp per unit of turnover and minus 1%/yr of financing markup across both legs | mean net > 0 |

**Kills:** K1 is G1 failing, K2 is G2, K3 is G4.

## 4. Power

About 440 months. A true Sharpe of 0.35 gives an expected t of about 2.1.
**Roughly a coin-flip chance of passing G1 even if the claim is true.**

## 5. Files

    flows/fetch_longrun.py  flows/fxvalue.py  flows/RESULT_FXVALUE.md
