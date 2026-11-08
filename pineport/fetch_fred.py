#!/usr/bin/env python3
"""Fetch daily macro series from FRED (free, no API key) as backtest-ready CSVs.

FRED publishes a plain CSV endpoint that needs no registration:

    https://fred.stlouisfed.org/graph/fredgraph.csv?id=DFII10

Series worth having for gold work:

    DFII10   10-Year Treasury Inflation-Indexed (TIPS) yield -- the real yield.
             The single most-cited gold driver. Daily from 2003-01-02.
    DFII5    5-Year TIPS yield. Shorter duration, more Fed-sensitive.
    T10YIE   10-Year breakeven inflation rate (inflation expectations).
    DGS10    10-Year nominal Treasury yield.
    DTWEXBGS Trade-weighted broad dollar index.

A synthetic real yield is DGS10 - T10YIE, which matches DFII10 closely and is
what TradingView users build when they want it intraday.

    python fetch_fred.py --series DFII10 --out dfii10.csv
    python fetch_fred.py --series DFII10,T10YIE,DTWEXBGS --out-dir .

THE PUBLICATION-LAG TRAP
------------------------
FRED stamps each observation with the date it *describes*, not the date it was
published. The H.15 release carrying DFII10 for a given business day appears
that afternoon, and revisions land later still. Using the value dated D while
trading during D is lookahead -- a subtle one, because the series looks
perfectly well-behaved.

This script writes the raw dated series. The **shift is applied at use**, in
`load_daily_series()`, which lags every observation by one business day by
default. Keeping the raw file honest and the lag explicit at the point of use
means the assumption is visible rather than baked into a file nobody re-reads.
"""

from __future__ import annotations

import argparse
import csv
import io
import os
import sys
import urllib.error
import urllib.request

FRED_CSV = ("https://fred.stlouisfed.org/graph/fredgraph.csv"
            "?id={series}&cosd={start}")
USER_AGENT = "Mozilla/5.0 (compatible; pineport-research/1.0)"

NOTES = {
    "DFII10": "10Y TIPS real yield, % -- the main gold driver",
    "DFII5": "5Y TIPS real yield, %",
    "T10YIE": "10Y breakeven inflation, %",
    "DGS10": "10Y nominal Treasury, %",
    "DTWEXBGS": "Trade-weighted broad USD index",
    "BAMLH0A0HYM2": "ICE BofA US high-yield OAS -- credit spread",
    "NFCI": "Chicago Fed National Financial Conditions Index (weekly)",
    # --- implied-volatility indices, for the sizing work ---
    "VIXCLS": "CBOE VIX -- S&P 500 30-day implied vol",
    "VXNCLS": "CBOE VXN -- Nasdaq 100 implied vol",
    "RVXCLS": "CBOE RVX -- Russell 2000 implied vol",
    "VXDCLS": "CBOE VXD -- Dow Jones implied vol",
    "GVZCLS": "CBOE GVZ -- gold (GLD) implied vol",
    "VXSLVCLS": "CBOE VXSLV -- silver (SLV) implied vol (may be discontinued)",
    "OVXCLS": "CBOE OVX -- crude (USO) implied vol",
    "EVZCLS": "CBOE EVZ -- euro (FXE) implied vol (ends 2025-03)",
}

#: Named groups, so a pull is one flag rather than a comma-separated wall.
SETS = {
    "vol": "VIXCLS,VXNCLS,RVXCLS,VXDCLS,GVZCLS,VXSLVCLS,OVXCLS,EVZCLS",
    "macro": "DFII10,T10YIE,DGS10,DTWEXBGS,BAMLH0A0HYM2,NFCI",
}


def fetch_series(series: str, timeout: float = 60.0,
                 start: str = "1950-01-01") -> list[tuple[str, str]]:
    """Download one FRED series. Returns [(date, value_or_empty), ...].

    `start` becomes FRED's `cosd` parameter. It matters: WITHOUT an explicit
    start date the graph endpoint truncates some series to a few recent years
    and says nothing about it -- BAMLH0A0HYM2 came back with 787 observations
    from 2023 instead of thirty years, which is the kind of silent failure that
    produces a confident, wrong result.
    """
    url = FRED_CSV.format(series=series, start=start)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raise LookupError(f"HTTP {exc.code} -- check the id at "
                          f"https://fred.stlouisfed.org/series/{series}")
    except LookupError:
        raise
    except Exception as exc:                            # noqa: BLE001
        raise LookupError(str(exc))

    rows = list(csv.reader(io.StringIO(raw)))
    if len(rows) < 2:
        raise SystemExit(f"{series}: response was not a CSV table")

    header = [h.strip().lower() for h in rows[0]]
    # FRED has used both "DATE" and "observation_date" as the first column.
    date_i = 0
    val_i = 1 if len(header) > 1 else 0
    out = []
    for row in rows[1:]:
        if len(row) <= val_i or not row[date_i].strip():
            continue
        out.append((row[date_i].strip(), row[val_i].strip()))
    return out


def write_csv(series: str, rows: list[tuple[str, str]], path: str) -> dict:
    """Write date,value with FRED's '.' missing marker dropped."""
    kept = [(d, v) for d, v in rows if v not in (".", "", "NA")]
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date", series.lower()])
        w.writerows(kept)
    vals = [float(v) for _, v in kept]
    return {"rows": len(rows), "kept": len(kept),
            "start": kept[0][0] if kept else "-",
            "end": kept[-1][0] if kept else "-",
            "min": min(vals) if vals else float("nan"),
            "max": max(vals) if vals else float("nan")}


def load_daily_series(path: str, lag_days: int = 1):
    """Load a fetched FRED CSV, applying the publication lag.

    ``lag_days=1`` means the observation dated D is treated as first knowable on
    D+1. That is deliberately conservative: the H.15 release lands in the
    afternoon of D, so a strategy acting on D's close might legitimately have
    it -- but assuming so on 20 years of backtest is how invisible lookahead
    gets in. One day costs almost nothing on a 10-40 day holding period.

    Returns a pandas Series indexed by UTC timestamps, ready to reindex onto
    hourly bars with ffill.
    """
    import pandas as pd

    df = pd.read_csv(path)
    date_col, val_col = df.columns[0], df.columns[1]
    idx = pd.to_datetime(df[date_col], utc=True)
    s = pd.Series(pd.to_numeric(df[val_col], errors="coerce").to_numpy(), index=idx)
    s = s.dropna().sort_index()
    if lag_days:
        s.index = s.index + pd.Timedelta(days=lag_days)
    s.name = val_col
    return s


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--series", default="DFII10",
                    help="comma-separated FRED series ids")
    ap.add_argument("--out", default=None, help="output path (single series only)")
    ap.add_argument("--out-dir", default=".", help="directory for multiple series")
    ap.add_argument("--start", default="1950-01-01",
                    help="earliest observation to request (FRED 'cosd'). Always "
                         "sent -- omitting it lets FRED truncate some series "
                         "silently.")
    ap.add_argument("--set", dest="named_set", choices=sorted(SETS),
                    help=f"fetch a named group instead of --series: "
                         f"{', '.join(sorted(SETS))}")
    ap.add_argument("--timeout", type=float, default=60.0)
    args = ap.parse_args()

    series_arg = SETS[args.named_set] if args.named_set else args.series
    ids = [s.strip().upper() for s in series_arg.split(",") if s.strip()]
    if args.out and len(ids) > 1:
        raise SystemExit("--out takes a single series; use --out-dir for several")

    failed = []
    for sid in ids:
        note = NOTES.get(sid, "")
        print(f"fetching {sid}  {note}")
        try:
            rows = fetch_series(sid, args.timeout, args.start)
        except LookupError as exc:
            # One dead series must not abort a whole set -- several CBOE
            # volatility indices have been discontinued over the years.
            print(f"  !! skipped: {exc}\n")
            failed.append(sid)
            continue
        path = args.out or os.path.join(args.out_dir, f"{sid.lower()}.csv")
        st = write_csv(sid, rows, path)
        print(f"  {st['kept']:,} observations "
              f"({st['rows'] - st['kept']} missing dropped)")
        print(f"  {st['start']} -> {st['end']}   range {st['min']:.3f} to "
              f"{st['max']:.3f}")
        if st["kept"] < 500:
            print(f"  !! only {st['kept']} observations -- check the series id "
                  f"and the --start date before using this")
        print(f"  wrote {path}\n")

    if failed:
        print(f"Skipped {len(failed)}: {', '.join(failed)} "
              f"(discontinued or wrong id -- not fatal)\n")
    print("Note: values are stored on the date they DESCRIBE. The one-business-day")
    print("publication lag is applied at load time by load_daily_series(), not here.")


if __name__ == "__main__":
    main()
