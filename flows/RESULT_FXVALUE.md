# RESULT — FLOWS-13: currency value (five-year real-rate reversal). DEAD (K2): real, then gone.

```
SPEC:     PREREGISTRATION_FXVALUE.md (sha d36d1a8b…) + A1 (07f96982…: BIS CPI, FRED EXGEUS, spliced rates)
METHOD:   fxvalue.py   log data/fxvalue_run.log   result data/fxvalue_result.json
DATA:     FRED spot + OECD short rates (data/longrun), BIS WS_LONG_CPI (data/fxvalue_a1.meta.json)
          all nine currencies from 1985-07; portfolio 1990-02 .. 2026-08 (438 months);
          7 EUR rate months carried forward (A1 §3)
RUN:      2026-10-02, once
VERDICT:  G1 PASS  G2 FAIL  G3 PASS  G4 PASS  ->  DEAD (K2)
```

*Measurement, not a recommendation. Not financial advice.*

| | result | gate |
|---|---|---|
| long 3 cheapest / short 3 dearest, excess return | **+0.247%/month (3.0%/yr), t 2.56, Sharpe 0.43** | G1 PASS |
| thirds | **1990–2002 +0.545% (t 3.0)**, 2003–14 +0.096%, **2015–26 +0.073%** | G2 FAIL (last third 30% of full) |
| spot only, without the interest differential | +0.283%, t 2.93 | G3 PASS: value is not carry |
| net of turnover and 1%/yr financing | +0.153%/month, t 1.58 | G4 PASS |

## Read it plainly

- **The published currency-value premium replicates** at the published size
  (Sharpe 0.43 against the literature's 0.3–0.5), and it comes from exchange
  rates reverting, not from carry.
- **Almost all of it was earned in 1990–2002.** Since 2003 it has been about
  1% a year and not significant: thirteen and twelve years with nothing to
  show. The recent-era floor exists for exactly this, and it fails.
- It is a slow monthly strategy. Under the programme's own power floor, a
  premium of the size seen since 2003 cannot be told apart from zero in any
  sample we have.
