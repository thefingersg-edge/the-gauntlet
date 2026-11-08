# H4 test of the tuned rule: plan, fixed 2026-11-07 ~15:58 before running

Question: is "fade an extreme move" a real liquidity premium, or did the daily tuning fit
noise? H4 bars were never seen by the tuning, so they test the MECHANISM, not the fit.

## Rule, unchanged from arm_g_tuned_FITTED.pine, in H4 bars
L = 6, V = 40, K = 3.0, H = 3 bars (12 hours), no stop, no trend filter, both directions.
All 21 markets. Signal at a bar's close, entry at the next bar's open, exit at the open
H bars after entry. No retuning, no second parameter set.

## Data and costs
pineport/adaptive/data_h4 (make_h4.py, OANDA's 17:00 New York grid, complete 4-bar
blocks only; incomplete blocks are dropped, so a lookback can span a feed gap).
Ends 2026-08-07. Same engine costs: the measured round-trip spread per trade plus 2.5%/yr
per calendar night, nights counted by UTC date boundaries crossed (engine convention).

## Pass rule
PASS (the mechanism holds) = E1, E2 and E3 all positive AND net >= 0.10% per trade.
Anything else = the daily result is treated as fitted noise.
Gates 1-6 are reported for reference. Gate 7 is NOT computed: equity.py charges financing
once per bar, which on H4 would charge it six times a day.
