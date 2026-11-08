#!/usr/bin/env python3
"""v59 data pull (PREREGISTRATION_v59.md): daily/weekly revision-safe FRED series for the timeline slow-macro family.
Run on the Mac (Terminal):   cd ~/RStudio/Claude/fastbot/scripts && python3 fred_v59_pull.py
Reads ~/.fred_key (never printed). Read-only. Writes data/v59/fred/<SERIES>.csv (date,value). Safe to re-run.
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, csv, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from fred_fetch_v31 import call, obs
SERIES = ["DBAA", "DAAA", "T10Y3M", "DFF", "DCOILWTICO", "NFCI", "ICSA"]

def main():
    p = os.path.expanduser("~/.fred_key")
    if not os.path.exists(p): sys.exit("missing ~/.fred_key")
    key = open(p).read().strip(); out = os.path.join(HERE, "..", "data", "v59", "fred"); os.makedirs(out, exist_ok=True)
    for s in SERIES:
        for t in range(3):
            try: o = obs(call(s, key)); break
            except Exception as e: print(f"  {s}: retry {t + 1} ({type(e).__name__})"); time.sleep(3)
        else: print(f"  {s}: FAILED"); continue
        with open(os.path.join(out, f"{s}.csv"), "w", newline="") as fh:
            w = csv.writer(fh); w.writerow(["date", "value"]); w.writerows(o)
        print(f"  {s:<11} {len(o):6,} rows  {o[0][0]} -> {o[-1][0]}")
    print("done -- tell Claude 'v59 fred done'")

if __name__ == "__main__":
    main()
