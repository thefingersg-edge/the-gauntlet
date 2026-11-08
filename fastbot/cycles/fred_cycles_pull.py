#!/usr/bin/env python3
"""CYCLES2 data pull: the long macro series needed to study what was going on around each bull/bear market.
Run on the Mac (Terminal), from fastbot/scripts:   python3 ../cycles/fred_cycles_pull.py
Reads ~/.fred_key (never printed). Read-only. Writes data/cycles/fred/<SERIES>.csv (date,value). Safe to re-run.
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, csv, time
HERE = os.path.dirname(os.path.abspath(__file__)); FB = os.path.join(HERE, ".."); sys.path.insert(0, os.path.join(FB, "scripts"))
from fred_fetch_v31 import call, obs
SERIES = {
    "USREC": "NBER recession indicator (monthly, 1854-)",
    "FEDFUNDS": "effective fed funds rate (1954-)",
    "TB3MS": "3-month T-bill (1934-)",
    "GS10": "10-year Treasury (1953-)",
    "BAA": "Moody's Baa corporate yield (1919-)",
    "AAA": "Moody's Aaa corporate yield (1919-)",
    "INDPRO": "industrial production (1919-)",
    "UNRATE": "unemployment rate (1948-)",
    "PAYEMS": "nonfarm payrolls (1939-)",
    "CPIAUCSL": "CPI all items (1947-)",
    "WTISPLC": "WTI spot oil price (1946-)",
    "M2SL": "M2 money stock (1959-)",
    "NFCI": "Chicago Fed financial conditions (weekly, 1971-)",
    "UMCSENT": "Michigan consumer sentiment (1952-)",
    "PERMIT": "building permits (1960-)",
    "ICSA": "initial jobless claims (weekly, 1967-)",
}


def main():
    p = os.path.expanduser("~/.fred_key")
    if not os.path.exists(p): sys.exit("missing ~/.fred_key")
    key = open(p).read().strip(); out = os.path.join(FB, "data", "cycles", "fred"); os.makedirs(out, exist_ok=True)
    for s, desc in SERIES.items():
        for t in range(3):
            try:
                o = obs(call(s, key)); break
            except Exception as e:
                print(f"  {s}: retry {t + 1} ({type(e).__name__})"); time.sleep(3)
        else:
            print(f"  {s}: FAILED"); continue
        with open(os.path.join(out, f"{s}.csv"), "w", newline="") as fh:
            w = csv.writer(fh); w.writerow(["date", "value"]); w.writerows(o)
        print(f"  {s:<9} {len(o):6,} rows  {o[0][0]} -> {o[-1][0]}   {desc}")
    print("done -- tell Claude it has finished")


if __name__ == "__main__":
    main()
