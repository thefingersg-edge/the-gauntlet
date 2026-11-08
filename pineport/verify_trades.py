#!/usr/bin/env python3
"""Compare a TradingView trade-list export against the Python port.

Run this after every TradingView export. If the match rate drops, something in
the execution model has drifted apart again and any training done in between is
suspect.

Matching is on ENTRY PRICE + DIRECTION, not timestamp. TradingView exports in
exchange-local time with daylight saving, so timestamps shift by an hour twice
a year and a naive timestamp join understates the match badly (61% vs the real
98%). Entry price is unambiguous.

    python verify_trades.py "path/to/Gold_15m_v6_....csv"
    python verify_trades.py export.csv --data xauusd_oanda_m15.csv \
                                       --config configs/gold_15m_v6.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from broker import BrokerConfig                    # noqa: E402
from data import _normalise, _read_csv             # noqa: E402
from strategy import Params, run_strategy          # noqa: E402
import fetch_fred                                  # noqa: E402

PRICE_TOL = 0.5      # dollars; entry prices agree far tighter than this


def resolve(path: str) -> str:
    """Find the export without demanding a perfect path.

    TradingView drops exports in ~/Downloads and the filenames are long, so
    "file not found" is the normal outcome of typing one by hand. Look in the
    obvious places, and if it is still missing, list what IS there rather than
    just failing.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    cands = [path, os.path.expanduser(path), os.path.join(here, path),
             os.path.join(os.path.expanduser("~/Downloads"), path),
             os.path.join(os.path.expanduser("~"), path)]
    for c in cands:
        if os.path.isfile(c):
            return c
    # Nothing matched: try the basename anywhere obvious, then give up loudly.
    import glob
    base = os.path.basename(path)
    for d in (here, os.path.expanduser("~/Downloads"), os.getcwd()):
        hit = glob.glob(os.path.join(d, base))
        if hit:
            return hit[0]
    found = []
    for d in (here, os.path.expanduser("~/Downloads"), os.getcwd()):
        found += glob.glob(os.path.join(d, "*OANDA*.csv"))
    msg = [f"could not find: {path}", "", "looked in:",
           f"  {here}", "  ~/Downloads", f"  {os.getcwd()}"]
    if found:
        msg += ["", "exports I can see:"] + [f"  {f}" for f in sorted(set(found))[:12]]
    raise SystemExit("\n".join(msg))


def load_export(path: str) -> pd.DataFrame:
    d = pd.read_csv(resolve(path), encoding="utf-8-sig")
    d.columns = [c.strip() for c in d.columns]
    ent = d[d["Type"].str.startswith("Entry")].copy()
    ent["dt"] = pd.to_datetime(ent["Date and time"])
    ent["dir"] = np.where(ent["Type"].str.contains("long"), 1, -1)
    ent = ent.rename(columns={"Price USD": "px", "Size (qty)": "qty"})
    return ent[["dt", "dir", "px", "qty"]].sort_values("dt").reset_index(drop=True)


def match(tv: pd.DataFrame, port: pd.DataFrame) -> tuple[int, list]:
    used: set[int] = set()
    matched, missing = 0, []
    for _, r in tv.iterrows():
        c = port[(port["dir"] == r["dir"])
                 & ((port["px"] - r["px"]).abs() < PRICE_TOL)
                 & (~port.index.isin(used))]
        if len(c):
            matched += 1
            used.add(c.index[0])
        else:
            missing.append(r)
    return matched, missing


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("export")
    ap.add_argument("--data", default="xauusd_oanda_m15.csv")
    ap.add_argument("--config", default=None,
                    help="pin one config; default tries every configs/*.json "
                         "and reports the best match")
    ap.add_argument("--capital", type=float, default=6000.0)
    ap.add_argument("--rates", default="dfii10.csv")
    args = ap.parse_args()

    tv = load_export(args.export)
    df = _normalise(_read_csv(args.data))

    rates = (fetch_fred.load_daily_series(args.rates)
             if os.path.exists(args.rates) else None)

    # The config must match the SCRIPT VERSION that produced the export -- v6
    # uses a dollar ladder and /50 sizing, v7 percent-of-entry rungs and
    # stop-distance sizing, and checking one against the other mismatches for
    # reasons that have nothing to do with the port. Filenames are NOT reliable
    # (a v7 script exporting under a stale shorttitle looks like v6, which is
    # exactly how this bit once already), so try every config and report the
    # best. Deciding by measurement beats guessing from a filename.
    here = os.path.dirname(os.path.abspath(__file__))
    if args.config:
        cfgs = [args.config]
    else:
        cdir = os.path.join(here, "configs")
        cfgs = sorted(os.path.join(cdir, f) for f in os.listdir(cdir)
                      if f.endswith(".json"))

    scored = []
    for path in cfgs:
        try:
            res = run_strategy(df, Params(**json.load(open(path))),
                               BrokerConfig(args.capital, 1.0), rates=rates)
        except Exception as exc:
            scored.append((-1.0, path, None, None, str(exc)[:50]))
            continue
        t = res.trades
        p = pd.DataFrame({"dt": t["entry_time"].dt.tz_localize(None),
                          "dir": t["direction"], "px": t["entry_price"]})
        m, miss = match(tv, p)
        scored.append((100 * m / max(len(tv), 1), path, p, miss, ""))
    scored.sort(key=lambda x: -x[0])

    print("PORT vs TRADINGVIEW  (matched on entry price + direction)")
    print("=" * 72)
    if len(scored) > 1:
        for s, path, p, _m, err in scored:
            note = f"({err})" if err else f"port {len(p)} trades"
            tag = f"{s:5.1f}%" if s >= 0 else "  n/a"
            print(f"    {os.path.basename(path):<32}{tag}   {note}")
        print()
    pct, best, port, missing, _ = scored[0]
    if port is None:
        raise SystemExit("no config could be evaluated")
    matched = round(pct * len(tv) / 100)
    print(f"  best config         : {os.path.basename(best)}")
    print(f"  TradingView entries : {len(tv)}")
    print(f"  port entries        : {len(port)}")
    print(f"  matched             : {matched}  = {pct:.1f}%")

    # Fractional quantities cannot come from math.ceil(); they mean TradingView
    # split or partially liquidated a position, which the port never does.
    frac = tv[(tv["qty"] % 1) != 0]
    if len(frac):
        print(f"\n  !! {len(frac)} FRACTIONAL quantities in the export -- "
              f"TradingView split or margin-called a position.")
        print("     Check margin_long / margin_short are 0.")
        print(frac.to_string(index=False))

    if missing:
        print(f"\n  {len(missing)} TradingView trades with no port counterpart:")
        for r in missing[:15]:
            print(f"    {str(r['dt'])[:16]}  "
                  f"{'long' if r['dir'] == 1 else 'short':<5} @ {r['px']:.2f}")

    print()
    # 97 rather than 98: measured feed noise between vendors on this instrument
    # runs 1-2% of trades, so 97.8% and 98.2% are the same result. A threshold
    # that flags ordinary noise as drift trains you to ignore it.
    if pct >= 97:
        print("  VERDICT: aligned. Training against the port is sound.")
    elif pct >= 90:
        print("  VERDICT: close but drifting. Check the execution-model block "
              "in the .pine header before trusting new results.")
    else:
        print("  VERDICT: NOT ALIGNED. Do not train until this is resolved.")
        sys.exit(1)


if __name__ == "__main__":
    main()
