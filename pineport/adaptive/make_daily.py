"""
Resample OANDA H1 feeds to daily bars for the adaptive-lookback study.

R4 FIX (2026-09-03) — the previous version used `df.resample("1D")`, i.e. a
UTC-midnight day boundary. The FX/CFD week opens Sunday ~21:00 UTC and closes
Friday 21:00 UTC, so a UTC-midnight day manufactures a Sunday bar out of the
2-3 hours of Sunday evening. It has a real high-low range, so the
`high > low` filter kept it. Measured effect on the old files:

    mean 296.5 bars/yr (range 251.6 - 317.1 across markets)
    -> sqrt(252) annualisation understated every Sharpe by ~8%
    -> len/252 understated every ann_ret and turnover by ~15%
    -> SMA(n) spanned different calendar time on different markets
    -> realised_vol read low, so vol targeting ran over target

The boundary used here is the actual instrument rollover, 17:00 New York:

    td = date(t_ny - 17h) + 1 day    bins [17:00 day N, 17:00 day N+1) -> N+1
    td on Saturday  -> Friday        the Friday post-rollover tail
    td on Sunday    -> Monday        the Sunday early open

DST NOTE (2026-09-03, second pass) — the first version of this fix hardcoded
the boundary at 21:00 *UTC*. OANDA rolls at 17:00 New York, which is 21:00
UTC only under EDT; under EST it is 22:00 UTC. A fixed UTC hour therefore
pushes the 21:00-22:00 UTC hour into the wrong trading day for the whole
winter half of every year. Measured on eurusd: 1,590 hourly bars misassigned
(1.17% of bars) touching 1,572 trading days -- 28.0% of all days -- and 1,564
of those 1,590 were the 21:00 UTC hour exactly as predicted. Because that
hour sits at the very end of the session it lands on the daily CLOSE, which
is the input to every signal in this study. Converting to America/New_York
first makes the boundary track DST automatically.

Verified after both passes: mean 257.2 bars/yr, range 251.5 - 259.7, zero
weekend-dated rows. 257 is correct for FX/CFDs (~260 trading days less a
handful of true global holidays); 252 is the US *equity* convention and was
never the right constant for this feed.
"""
import sys, os, glob
import pandas as pd

SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

ROLLOVER_TZ = "America/New_York"   # OANDA's daily rollover is stamped in NY time
ROLLOVER_HOUR = 17                # 17:00 NY = 21:00 UTC (EDT) / 22:00 UTC (EST)
MIN_BARS = 4                      # hourly observations needed to call it a trading day

# the original 11-market test set; build() takes any instrument name
MARKETS = ["audusd","bcousd","de30eur","eurusd","gbpusd","nas100usd",
           "spx500usd","usdjpy","xagusd","xauusd","xcuusd"]


def trading_date(t: pd.Series) -> pd.Series:
    """Map a tz-aware UTC hourly timestamp to its trading date (UTC-stamped).

    Converts to New York first so the 17:00 boundary tracks DST. `.dt.date`
    rather than `.dt.floor("D")` because flooring a tz-aware series across a
    DST transition is not well defined.
    """
    ny = t.dt.tz_convert(ROLLOVER_TZ) - pd.Timedelta(hours=ROLLOVER_HOUR)
    td = pd.to_datetime(ny.dt.date) + pd.Timedelta(days=1)
    dow = td.dt.dayofweek
    td = td.where(dow != 5, td - pd.Timedelta(days=1))    # Sat -> Fri
    td = td.where(dow != 6, td + pd.Timedelta(days=1))    # Sun -> Mon
    return td.dt.tz_localize("UTC")                       # keep the index tz-aware


def build(mkt: str, min_days: int = 0) -> str:
    p = os.path.join(SRC, f"{mkt}_oanda_h1.csv")
    if not os.path.exists(p):
        return f"{mkt}: MISSING"
    df = pd.read_csv(p, usecols=["time","open","high","low","close","volume"])
    # format="ISO8601" (2026-11-06): the h1 files can contain BOTH
    # "...+00:00" and naive "..." rows, because fetch_oanda --resume
    # appended API rows in a different format from the ones already in
    # the file. Every row is UTC either way; a fixed "%z" format simply
    # refuses the naive ones.
    df["time"] = pd.to_datetime(df["time"], format="ISO8601", utc=True)
    df = df.sort_values("time")
    df["td"] = trading_date(df["time"])

    d = df.groupby("td").agg(open=("open","first"), high=("high","max"),
                             low=("low","min"), close=("close","last"),
                             volume=("volume","sum"), nbar=("close","size"))
    d = d[(d["high"] > d["low"]) & (d["nbar"] >= MIN_BARS)]
    d = d.drop(columns="nbar")
    d.index.name = "time"

    if min_days and len(d) < min_days:
        return f"{mkt}: only {len(d)} days, skipped"

    yrs = (d.index[-1] - d.index[0]).days / 365.25
    d.to_csv(os.path.join(OUT, f"{mkt}_d1.csv"))
    return (f"{mkt}: {len(d)} days {d.index[0].date()} -> {d.index[-1].date()} "
            f"({len(d)/yrs:.1f} bars/yr)")


def all_available() -> list[str]:
    return sorted(os.path.basename(p).replace("_oanda_h1.csv", "")
                  for p in glob.glob(os.path.join(SRC, "*_oanda_h1.csv")))


if __name__ == "__main__":
    todo = sys.argv[1:]
    if todo == ["--all"]:
        todo = all_available()
    elif not todo:
        todo = MARKETS
    for m in todo:
        print(build(m), flush=True)
