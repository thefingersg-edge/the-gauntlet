#!/usr/bin/env python3
"""PREREGISTRATION_v53 -- fetch credit spreads and the 10y yield from FRED. RUN LOCALLY on Dave's Mac.
The key is read from $FRED_API_KEY or ~/.fred_key (release_content.load_key) and is never printed.
Public data, read only. Writes data/v53/raw/<SERIES>.csv and prints each file's sha256.
    python3 fred_fetch_v53.py"""
import csv, hashlib, os, sys, time
from fred_fetch_v31 import call, obs
from release_content import load_key

SERIES = ("BAA10Y", "DGS10", "BAMLH0A0HYM2")   # BAA10Y primary; HY OAS reported only (history may be truncated)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "v53", "raw")

def main():
    key = load_key(); os.makedirs(OUT, exist_ok=True)
    for s in SERIES:
        o = obs(call(s, key))
        p = os.path.join(OUT, f"{s}.csv")
        with open(p, "w", newline="") as fh:
            w = csv.writer(fh); w.writerow(["date", s.lower()]); w.writerows(o)
        print(f"  {s}: {len(o)} obs {o[0][0] if o else '-'} -> {o[-1][0] if o else '-'}   sha256 {hashlib.sha256(open(p,'rb').read()).hexdigest()}")
        time.sleep(0.6)

if __name__ == "__main__":
    main()
