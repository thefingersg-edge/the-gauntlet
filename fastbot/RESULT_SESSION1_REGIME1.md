# RESULT — SESSION1 and REGIME1: restricting to cash hours changes nothing, and moving-average "overall direction" filters don't tell direction

```
SPEC:     PREREGISTRATION_SESSION1.md  sha 11bb4e0a…   PREREGISTRATION_REGIME1.md  sha b3a1b70b…  (both frozen before any number)
METHOD:   scripts/session1_run.py, scripts/regime1_run.py (shas in PROVENANCE); OANDA 15m bid/ask to 2026-09-25; daily cash closes (daily_close.py)
LOGS:     data/run_session1_verdict.log, data/run_regime1_q1.log, data/run_regime1_q2.log; trade-level data/session1/*.json
RUN:      2026-10-09
VERDICT:  SESSION1  Part A CHoCH FAIL, BOS FAIL;  Part B 0 of 84 PASS        -> objection "you ran it on 24 hours" answered
          REGIME1   Q1 0 of 10 filters tell direction;  Q2 0 of 86 patterns pass when taken with the trend
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

## SESSION1 — cash session only
**Part A, v51 break of structure / change of character, 15m.** SPX/NAS 09:30–16:00 New York, UK100 08:00–16:30 London, gold 08:30–13:30 New York. All positions are flat by the close.
```
                   k=3 net bp (t)     24-hour v51       vs random in-session entries    gates
CHoCH              -1.90 (t -4.5)     -2.75 (t -12.6)   -0.42 (t -1.0)                  all 5 FAIL
BOS                -0.51 (t -1.0)     -2.62 (t -8.6)    +0.70 (t +1.7)                  G2 pass, rest FAIL
BOS gross k=4/5    +1.7 bp (t 3.0)  -> the spread (~1.6 bp) takes all of it; only 2005-12 positive; UK100 and gold negative
A2 (structure drawn on session-only bars, reported): CHoCH -0.59, BOS -0.76
```
**Part B, TF1 30m and 1h, 09:00–16:00 New York, 3-hour hold.** **0 of 84 pass.** The best tests:
- 30m marubozu long: +3.1 bp, t 1.9.
- 1h key reversal long: +18.5 bp on just 18 trades.

Structure loses on both timeframes; CHoCH 30m is −4.6 bp (t −5.2).

**Read it plainly:**
- Taking out the overnight hours makes the losses smaller, because spreads are tighter in the cash session.
- It does not turn anything positive enough to pass.
- The objection was fair to raise, and it is now answered. One faint lead, worth one sentence and no more: 15m BOS with wider swings (k = 4–5) is slightly positive *before* costs in the cash session. It disappears after the spread, it was only positive in 2005–12, and this is the version we saw second.

## REGIME1 Q1 — does a moving average tell you the overall direction?
The question is whether average returns are higher in the "up" state than in the "down" state, for the next day and the next week. Four markets, 2005–2026.
```
filter                     next day b (t)    next week b (t)    up-state share   vol up / down (daily bp)
F1 close > SMA200          -2.8 (-0.8)       -12.8 (-0.9)       74%              96 / 174
F2 golden cross 50/200     +0.6 (+0.2)       +2.1 (+0.2)        74%              106 / 158
F3 EMA20 > EMA50           -4.9 (-1.6)       -21.3 (-1.7)       68%              96 / 161
F4 12-month return > 0     -3.1 (-0.9)       -8.1 (-0.5)        76%              105 / 165
F5 SMA200 rising           -2.0 (-0.6)       -2.7 (-0.2)        75%              108 / 157
hit rate: every filter is *below* simply calling "up" every day (e.g. F1 52.6% vs 53.9%)
```
**0 of 10 pass.** Four of the five point the wrong way: average returns were slightly *higher* below the moving average, because the sharpest rallies happen inside bear markets. The golden cross is the only one with the right sign, and it is +0.6 bp, which is noise.

**What the moving average really measures is volatility.** Below the 200-day line, daily swings are about 1.8× larger. That is why v52 found the 200-day MA halves drawdowns while adding no return: it moves you out of the rough periods, not out of the falling ones.

## REGIME1 Q2 — do candle patterns and structure work when taken *with* the trend?
Each SESSION1 trade was kept only if it went the same way as the 200-day filter. Its random-entry partners were filtered the same way.

**0 of 86 pass.** The median "lift" from the filter, after taking out what the filter gives random entries, is +0.7 bp. It is positive in 56% of tests, which is a coin flip. Structure stays negative with the trend: CHoCH −2.9 bp at 15m and −3.7 at 30m. Some aligned shorts show large averages, such as 1h marubozu short +21 bp, but on only 81 trades. They are below every gate, and the golden cross shows the same scatter.

## What this means for "find the direction first, then the pattern"
- On these markets, a moving average, crossover, 12-month trend or 200-day slope does not tell next-day or next-week direction better than "indices usually go up".
- Where it helps, it is risk control: it lowers exposure when volatility is high (v52, v50, vol targeting). It does not pick direction.
- Adding it to candle patterns or structure breaks does not create an edge. The patterns had none to begin with, and the filter does not add one.
- Things not tested here, which remain open:
  - **Higher-timeframe structure as the bias:** a 4h or daily BOS state as the filter. The 4h structure trades lose on their own (TF1), so this is unlikely to help.
  - **Slower holding periods:** trend following over weeks or months. TSMOM1 gave t 1.7, real but too weak to bet on.
  - **ADX and other "trend strength" filters:** these measure strength, not direction. This could be a REGIME2 if wanted.

## Caveats
- The filters use cash closes and the CFD, as in v52; futures closes would differ slightly.
- Q2 uses the F1 state from the previous close, so trades never use the same day's close.
