# ARM G: trend-side liquidity reversal. Frozen specification

Written 2026-11-07, from EP04_BRIEF.md, PROGRAMME.md and REGISTRY.md only. No price data
was looked at. `ARM_G.md`, `ARM_G_SCORED.md` and `PREREGISTRATION.md` in this folder were
deliberately not opened.

## 1. Instruments
All 21: eurusd gbpusd usdjpy usdcad audusd eurgbp eurjpy xauusd xagusd xptusd xcuusd
spx500usd nas100usd de30eur bcousd natgasusd usb10yusd de10ybeur cornusd wheatusd sugarusd.
Each market is traded independently, with at most one position per market.

## 2. Timeframe
Daily bars, as supplied in the gate dataset. Every "bar" below is a daily trading bar of that
instrument. Signals are computed on bar t's close. Orders fill at bar t+1's open.

## 3. Signal (computed at the close of bar t)
- r_i = ln(C_i / C_{i-1}), the daily log return
- sigma_t = population standard deviation (divide by V) of r over the V = 60 bars ending at t,
  including r_t
- R_t = ln(C_t / C_{t-L}) with L = 4
- z_t = R_t / (sigma_t * sqrt(L))
- S_t = simple mean of the T = 200 closes ending at t, including C_t
- LONG signal:  z_t <= -2.0 AND C_t > S_t
- SHORT signal: z_t >= +2.0 AND C_t < S_t
- A signal is acted on only if the market is flat at bar t's close, after any stop fill that
  bar. Signals during an open position are ignored, never queued. A signal needs complete V,
  L and T windows inside the dataset; no signals before that.

## 4. Entry and exit
- Entry: at the open of bar E = t+1, in the signal's direction.
- Disaster stop, fixed at signal time from C_t and live from the open of bar E:
  long  stop = C_t * (1 - 3.0 * sigma_t * sqrt(5))
  short stop = C_t * (1 + 3.0 * sigma_t * sqrt(5))
  It triggers when a bar's low (long) or high (short) reaches the level. It fills at the stop
  level, or at the bar's open if the bar opens beyond it.
- Time exit: at the open of bar E+5, so five full bars are held, unless stopped first.
- No profit target and no trailing stop. A stop on the same bar as the time exit is
  impossible, because the time exit fills at that bar's open.

## 5. Sizing on a $10,000 account
- Equity Q is the account's marked-to-market equity at bar t's close. Starting value: $10,000.
- Target USD notional: N = min(0.0020 * Q / sigma_t, 1.0 * Q). That is about 0.20% of equity
  in daily volatility per position, capped at 1x equity.
- Units = N / (USD value of one unit at C_t), rounded down to the broker's minimum unit
  increment (OANDA tradeUnitsPrecision). If that gives zero, trade one minimum increment if
  its notional is <= 1.0 * Q; otherwise skip the trade.
- Portfolio cap: total open gross notional <= 4.0 * Q. If entries on the same day would
  breach it, take them in descending |z_t| (ties in the instrument order of section 1). Skip
  any entry that would itself breach the cap.
- Scope: Gates 1-6 are scored on the uncapped per-market trade list, as percentage returns
  per trade, so sizing does not affect them. Gate 7 is scored on the $10,000 account with
  this section's sizing and cap.

## 6. Every parameter
L = 4, V = 60, T = 200, K = 2.0, H = 5, M = 3.0, B = 0.20% of equity per day,
per-position cap = 1.0x equity, portfolio cap = 4.0x equity.
The Gate 5 perturbations of +/-25% are exact for L (3/5), V (45/75), T (150/250),
K (1.5/2.5) and M (2.25/3.75). H rounds to 4/6.

## 7. Costs (as the brief prescribes)
Each trade is charged the brief's measured round-trip spread for its instrument, plus
2.5%/yr of notional per calendar night held, in either direction.

## 8. Pre-registered expectations and kill conditions
- Probability of clearing all seven gates, stated before scoring: about 10%.
- Most likely failures, in order: Gate 2 (FX and rates sign), Gate 3 (effect size outside
  the indices and high-volatility commodities), Gate 5 (K moved to 1.5).
- Gate 6 assumption: the matched control matches on a prior-return window but not on the
  200-day trend state. If it matches on both, the strategy is close to null by construction,
  and a Gate 6 failure should be read as that.
- Abandon, with no re-tuning and no added filter, if any of these hold:
  (a) any gate fails;
  (b) net per trade outside spx500usd, nas100usd and de30eur is <= 0, because then this is
      ARM F part A in disguise;
  (c) era 3 net is below half of era 1 net (the decay pattern of section 11);
  (d) forward: after 200 forward trades, net mean <= 0, or the lower 95% bound is below
      -0.10%.
- Brent caveat: price-only bcousd P&L omits the roll yield (PROGRAMME section 12b). Any Brent
  number under this cost model is not a tradeable return.
