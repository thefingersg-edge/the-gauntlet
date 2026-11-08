# v39 checks (2026-09-26): forest plateau, and do tighter exits help? DESCRIPTIVE, post-hoc; nothing here is a test.

```
SPEC:     none -- DESCRIPTIVE checks on the PREREGISTRATION_v39 winner; they gate nothing and fed PREREGISTRATION_v40
METHOD:   v39_plateau.py, v39_exits.py, v39_trail.py (post-hoc, seen data); logs data/v39/
RUN:      2026-09-26
VERDICT:  descriptive -- forest AUC plateau 0.554-0.559; tight exits worse; trailing stops add no return
```

**I am not a financial adviser. This is a measurement, not a recommendation.**
Scripts: v39_plateau.py (data/v39/plateau.csv), v39_exits.py (data/v39/exits.log). The frozen v39 FOREST is unchanged.

## 1. Plateau: 12 forest settings, yearly walk-forward 2012–2026
```
min leaf   depth 6   depth 10   unlimited      years > 0.5
   50      0.5584    0.5571     0.5564         15/15 each
  100      0.5581    0.5581     0.5588         15,15,14
  200      0.5579    0.5560     0.5553 (v39)   15,14,14
  500      0.5559    0.5544     0.5543         15/15 each
```
- **A flat plateau (0.554–0.559).** The direction signal does not depend on the settings, which is good evidence it is not a tuning accident.
- **Going deeper or shallower does not help.** The frozen setting is typical, not lucky.
- Every setting is stronger in 2019–26 (about 0.57) than in 2012–18 (about 0.54).

## 2. Exits on the forest's trades (2,722 trades, 2013–2026; stop 1σ, 2h maximum)
```
exit                     win %   avg win  avg loss  gross   NET    control net  signal adds
take profit 0.25σ        72.5%    +6.71   -23.73    +0.23  -1.66      -2.14       +0.48
take profit 0.50σ        58.2%   +14.26   -22.10    +0.96  -0.93      -2.13       +1.21
take profit 0.75σ        51.8%   +19.72   -21.71    +1.64  -0.25      -1.99       +1.74
take profit 1.00σ (v37)  48.6%   +22.33   -21.54    +1.66  -0.23      -1.88       +1.65
1σ + lock b/e at 0.5σ    40.2%   +23.29   -16.02    +1.68  -0.21      -1.83       +1.62
no target, 2h            46.2%   +24.78   -21.53    +1.74  -0.15      -1.69       +1.55
```
The median 1σ(2h) is 30 bp. "Control" = every decision point traded both ways, with no signal.

- **The "bouncing" is real.**
  - 55% of trades time out.
  - Of trades that were +0.5σ up at some point, 53% never reached the 1σ target, and 11% went on to hit the stop.
- **But banking profit early makes it worse, not better.**
  - A 0.5σ target wins 58% of the time instead of 49%, but the average win halves while the average loss stays about the same.
  - Net falls from −0.23 to −0.93 bp.
  - What the signal adds over no-signal trading shrinks from +1.65 to +1.21 bp.
  - The forest is right about direction over the whole 2 hours; a tight target cuts off exactly the trades where it is right.
- **Break-even locks** shrink losses and wins about equally, so they are neutral.
- **The widest exit is best:** no target, 2h, net −0.15.

## 3. Costs decide it (by era, net per trade)
```
                 2013-17 (spread 3.0)   2018-21 (1.6)   2022-26 (0.7)
TP 1σ (v37)          -2.22                 +0.04            +1.84  (t 1.85)
no target, 2h        -2.49                 -0.16            +2.59  (t 2.20)
```
- At today's spreads, the forest's direction signal nets about +2 to +2.6 bp a trade on SPX.
- **This is post-hoc, on seen data.** The exit and the era were both picked after looking. It is a reason to run v40 and a forward test, not a result.

## 4. "Don't quit while you're ahead": trailing and tightening stops, held to the close (v39_trail.py, data/v39/trail.log)
The forest's first signal each day, 1,870 trades 2013–26 (one a day so that holds to the close cannot overlap).
```
exit                                   win%   avg win  avg loss   NET    t     2022-26 NET   t     adds vs no-signal
fixed 2h, stop 1σ                      48.3   +26.6    -23.0    +0.99  1.25     +3.79     2.47      +2.64
to close, stop 1σ, no trail            44.8   +38.9    -29.3    +1.24  1.16     +4.27     2.10      +2.49
to close, trail 1.0σ                   41.1   +32.5    -20.8    +1.09  1.27     +2.57     1.62      +2.43
to close, trail 0.75σ                  39.4   +26.2    -16.3    +0.47  0.68     +2.54     1.94      +1.65
to close, trail 0.5σ                   36.2   +19.3    -11.7    -0.48 -0.98     +2.26     2.35      +0.82
to close, tightening 1σ -> 0.3σ        46.7   +22.9    -18.9    +0.63  0.97     +3.17     2.59      +2.18
tightening + break-even after 0.5σ     44.8   +23.2    -17.4    +0.74  1.16     +3.57     2.94      +2.37
```
- **Following winners with a trailing or tightening stop does not add return.**
  - Wide or no trail: about the same as a fixed exit.
  - Tight trail (0.5σ): clearly worse, because intraday noise stops the trade out before it runs.
- **Why:**
  - The best point a trade reaches before the close has a median of 0.93σ (90th percentile 2.6σ).
  - But by the close the median trade stands at only +0.12σ, giving back 1.18σ on average.
  - Intraday runs mostly retrace, and a trail cannot tell a pause from a reversal until after the fact.
- **The tightening + break-even stop is the smoothest** (highest t in 2022–26: 2.94, with smaller average losses). It trades a little return for steadier results. It is a risk choice, not an edge.
- Post-hoc and on seen data. The one-per-day entry set also differs from section 2, so compare within the table only.
