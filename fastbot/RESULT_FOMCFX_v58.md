# RESULT — v58: the FX premium on FOMC days replicates inside the paper's sample and is gone since. FAIL, as predicted.

```
SPEC:     PREREGISTRATION_v58.md  sha 229ba641…  (frozen in commit b0a0d8e)
METHOD:   fomcfx_v58.py 1.0 (sha 3f7a27fb…); OANDA M15 bid/ask, nine G10 currencies vs USD; data/events.csv FOMC rows (deduplicated: 8 a year)
LOG:      data/v58_run.log
RUN:      2026-10-02
VERDICT:  FAIL  (G1 FAIL +3.98 bp t +0.66; G2 PASS; G3 PASS +0.43 bp net)
```

**I am not a financial adviser. This is a measurement, not a recommendation.**

## The registered run
Short USD against the nine-currency basket (DOL), from 15:45 ET on the day before to 15:45 ET on the day.
| window | FOMC days | FOMC-day mean | other days | difference | HC1 t |
|---|---|---|---|---|---|
| **2011–2026 (primary, out of the paper's sample)** | 126 | +3.09 bp | −0.89 | **+3.98 bp** | **+0.66** |
| 2011–2018 | 64 | +2.07 | −1.28 | +3.34 | +0.41 |
| 2019–2026 | 62 | +4.15 | −0.49 | +4.65 | +0.52 |
| *2005–2010 (inside the paper's 1994–2010 sample, reported)* | 48 | +31.36 | −0.37 | **+31.73** | **+2.71** |

- G1 fails. G2 and G3 pass, but only on signs and a +0.43 bp net margin, which mean nothing when G1's t is 0.66.
- **Within-year permutation** (reported): one-sided p 0.143.

## Reported
- **Pre/post split, 2011–2026:** +4.78 bp before the statement, −1.69 bp after. The paper's shape (most of it before the announcement) is still visible, at about a sixth of the size.
- **Per currency, 2011–2026:** all nine positive, none with t above 1.3 (CHF +8.9, t 1.3).
- **AUD+NZD minus JPY+CHF:** −3.62 bp (t −0.61). The paper's high-yield tilt has the wrong sign.
- **FOMC-day volatility:** DOL sd 67.0 bp on FOMC days, 44.1 on others. My budget assumed 40–55 bp, so the real SE is about 6 bp, not 4–5. Even the paper-size +12 bp would have given t ≈ 2.

## How to read it, plainly
- **It replicated, then decayed: the seventh member of PROGRAMME §11's pattern.** In 2005–2010, 48 meetings dominated by the crisis and the start of QE, it was large (+31.7 bp, t 2.7). That is consistent with the paper's finding that the premium is bigger during easing. Since 2011 it has been +4 bp, indistinguishable from zero.
- The positive point estimate in every era and every currency is worth noting, not acting on. At 8 events a year, separating +4 bp from zero at t = 2 would take roughly 35 more years.
- **Closed under Rule 2.** With KUROV, the FOMC premium family is now closed in both equities and FX. PREREGISTRATION_v58 §8 registered no forward ledger for a FAIL, and none is added.
