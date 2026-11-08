# The data

None of the price data is in this repository. This file says exactly what was
used and how to get it, so every result here can be reproduced from source.

## Why it is not included

Two reasons, in order of importance.

1. **Licensing.** The bars come from OANDA's v3 API and from TradingView, under
   terms that permit personal use. Republishing a vendor's market data as a
   public dataset is a different act, and very likely not permitted. Code and
   findings are mine to publish; their price history is not.
2. **Size.** Roughly 18 GB, most of it 1-minute and 5-minute bars. GitHub is
   the wrong place for it even where licensing allows.

Macro series from FRED are public domain and could be included; they are left
out only for consistency, and the fetch scripts are here.

## What was used

### OANDA — 21 instruments, daily and intraday

Fetched with [`pineport/fetch_oanda.py`](pineport/fetch_oanda.py). Mid, bid and
ask are separate pulls; the measured spread table in the gate engine comes from
the bid/ask pair.

```
FX          eurusd gbpusd usdjpy usdcad audusd eurgbp eurjpy
Metals      xauusd xagusd xptusd xcuusd
Indices     spx500usd nas100usd de30eur
Energy      bcousd natgasusd
Rates       usb10yusd de10ybeur
Softs       cornusd wheatusd sugarusd
```

Daily bars run 2005-01-01 to 2026-08-31 for the three-era split used throughout
(E1 2005-01-01→2012-03-31, E2 2012-04-01→2019-06-30, E3 2019-07-01→2026-08-31).

You need a free OANDA practice account for an API token. Every script reads it
from `OANDA_API_TOKEN`; none of them accept it on the command line, and none
log it.

```sh
export OANDA_API_TOKEN='...'
python pineport/fetch_oanda.py --market eurusd --granularity D --price M
```

**One warning that cost me an episode.** OANDA and TradingView stamp a daily
futures bar at the moment the session *opens* — 17:00 America/Chicago on the
previous calendar day. Drop the timezone and keep the date and every bar is
labelled a day early, by an amount that changes with daylight saving. See
[`fastbot/RESULT_VIXDAILY.md`](fastbot/RESULT_VIXDAILY.md). Convert timezones;
never assume a fixed UTC offset.

### TradingView — VIX futures and term structure

`VIX`, `VIX3M`, and the continuous front and second VIX futures contracts,
March 2004 to July 2026. Used by `fastbot/scripts/vix_curve_budget.py`,
`vix_carry_budget.py` and `vix_daily_risk.py`.

### FRED — macro, public domain

`VIXCLS` (VIX close) and `DFF` (effective federal funds rate, monthly, used as
the implied financing benchmark). Refreshed by
`fastbot/scripts/fred_vix_refresh.py`. No key needed for the CSV endpoints.

## Costs, because they decide several of these results

Financing follows OANDA's published convention: a long pays `benchmark +
markup`, a short receives `benchmark − markup`, charged at the 17:00 New York
rollover. The markup is 2.50% on indices and Brent, **1.19% on metals** — a
difference that changed one verdict by a factor of 2.3 when it was corrected.

Brent's implied benchmark runs around −46.1% a year because the futures roll is
carried in the financing line rather than the price. Treating it as an interest
rate gets the sign and magnitude of commodity carry badly wrong; this was found
late, by one of the ep04 arms rather than by me.

Spreads are **measured**, not assumed: the median of `(ask − bid) / mid` over
07:00–21:00 UTC from OANDA's own bid and ask streams, 2024-01 to 2026-11,
doubled for a round trip. See `youtube/ep04/gates/measure_spread.py` and
`youtube/ep04/COST_MODEL.md`. The table it replaced had been copied from one of
the arms' own cost assumptions, which is one contestant pricing the others.

## Reproducing a result

Fetch what the script imports, point it at your data directory, and run it. If
your numbers differ from the result file, that is worth an issue — say which
figure, which script, and what you got.

## What *is* included

Three derived event logs, because episode 1 promises them:

```
pineport/adaptive/b1_events.csv        2,871 chart-pattern detections
pineport/adaptive/b2_events.csv        1,616 reversal detections
pineport/adaptive/l1_candlespace.csv   discovered candle geometry
```

Each row is a detection: date, market, pattern, era, forward return, realised
volatility. These are my own classifications and normalised returns, not price
bars — you cannot reconstruct a vendor's series from them, which is why they
are here and the OHLC is not.
