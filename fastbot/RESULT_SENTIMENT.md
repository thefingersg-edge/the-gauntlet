# RESULT — v30: does anyone call it, and does the crowd matter? No.

```
RUN:      2026-09-25   SPEC: PREREGISTRATION_v30 (sha256 checked)
CODE:     sentiment_fetch.py 1.1 (Dave's machine, public data)
          premarket_sentiment.py 1.0
DATA:     CFTC positions 2006-2026 (5,290 weekly rows, five markets),
          AAII 1987-2026, CBOE SKEW 1990-2026, put/call 2006-2019,
          Kalshi 2021-2026 (1,932 settled markets, 219 releases)
VERDICT:  G1, G2 and G3 all FAIL, as predicted. Nobody visible in the
          public positioning data calls these releases.
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.** Inputs and caveats: PROVENANCE.md.

Gate 0: 31,178 trades matched v27's file, max difference 5e-07 bp.

## 1. Does anyone call the direction? No.

What each group DID in the week into the release, against which way the
release bar then went (sigma units, clustered by date):

```
                                   n        b       t
Leveraged money (gold: MM)  S1  2343   -0.003   -0.11   G1 FAIL
                            S2  4021   +0.023   +1.05
                            S3 17346   -0.003   -0.36
Asset managers              S1  1872   +0.024   +0.62   G2 FAIL
                            S2  3209   -0.039   -1.27
                            S3 13824   +0.003   +0.23
```

**Hedge funds, CTAs and asset managers, as a group, are positioned no
better than a coin before CPI and payrolls** -- and no better before
claims or on ordinary mornings. This is the positions-side twin of
RESULT_PREANN's price-side finding. Weekly positions are coarse, and a
single well-informed account inside a group would be invisible here;
what this rules out is a GROUP that reliably gets it right.

## 2. Does crowding change the bounce? No.

```
fade/sigma on sign(move) x crowding   S1 b -0.013 t -0.66   G3 FAIL
                                      S2 b -0.057 t -1.66
                                      S3 b -0.014 t -0.87
```

A release going against a crowded position does not bounce more. The
sign is the one the forced-exit story predicts, everywhere, and nowhere
near the bar.

## 3. Sentiment going in — reported, gating nothing

```
                          vs direction   b      t    vs bounce   b      t
AAII bull-bear                 2981   +0.086  +1.96          -0.055  -1.52
put/call 5d (to 2019)          1885   -0.020  -0.40          +0.023  +0.59
SKEW                           2981   +0.075  +1.81          -0.006  -0.20
```

Nothing clears |t| = 2. AAII at 1.96 is the closest, and it points the
way a naive reading would expect (bullish retail, release bar up) -- it
is ungated, one of six numbers in this table, and the kind of cell that
sits just under 2 by chance about once in twenty.

## 4. Kalshi — the crowd's call on the print. Descriptive.

```
series        n    called the direction vs the previous print
KXCPI        36    35 of 36 = 97%
KXCPICORE    22    17 of 22 = 77%
KXPAYROLLS   36    21 of 36 = 58%
KXU3         33    19 of 33 = 58%
```

**The crowd is very good at headline CPI and barely better than a coin
at jobs.** That pattern is what you would expect: headline CPI's month-
to-month change is driven by petrol prices that are visible every day
before the release, and nowcasts are known to be good at it; payrolls
has no such tell. Calling the print is still not calling the market,
and nothing here connects the crowd's call to the bounce -- see below.

**A number from the run that should NOT be quoted.** The script printed
the fade on days the crowd "missed by more than the median" as -0.29 bp
against +8.35 bp on days it missed by less. That split used a miss
measured RELATIVE to the size of the crowd's estimate, which explodes
when the estimate is near zero (CPI at 0.1%) and mixes units across
series. Rebuilt properly -- each series' miss scaled by its own median
miss -- the difference is **+0.49 bp at t 0.11** (CPI days -0.01, t
0.00; payrolls days +4.65, t 0.80). There is nothing there. The first
version was a bad metric, caught on review before it was written up.

## 5. Predictions, scored

```
G1 fails                                         RIGHT
G2 fails                                         RIGHT
G3 fails                                         RIGHT
Kalshi calls the print well over half the time   RIGHT (CPI), MARGINAL (jobs)
AAII, put/call, SKEW nothing at |t| >= 2         RIGHT, with AAII at 1.96
```

## 6. Where this leaves Dave's question

"Is there anyone with key insights who continually makes good calls?"
In everything public and free: **no one visible.** Not in price before
the release (v10-v13), not in the positions of the groups that trade
these futures (this run), not in retail sentiment, options skew or the
put/call ratio. Prediction markets forecast the NUMBER -- very well for
headline CPI -- and that forecast says nothing about the bounce.

What is left needs data this project does not have: order-by-order
futures data, to look for an account the weekly aggregates would hide.

---

**Investigation forty-six.**
