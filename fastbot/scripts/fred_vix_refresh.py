#!/usr/bin/env python3
"""Append new VIX closes (FRED VIXCLS) to data/VIXCLS.csv. APPEND-ONLY: existing rows are never changed, so every past test
that used VIXCLS 'to 2026-08-31' still sees identical values. A frozen copy of the original is kept the first time.
Key: ~/.fred_key (never printed). Public data, read only.   python3 fred_vix_refresh.py"""
import os, csv, shutil, datetime as dt
from fred_fetch_v31 import call, obs
from release_content import load_key
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"); P = os.path.join(D, "VIXCLS.csv")
FROZEN = os.path.join(D, "VIXCLS_frozen_to_20260831.csv")
def main():
    key = load_key()
    if not key: raise SystemExit("no FRED key in ~/.fred_key")
    if not os.path.exists(FROZEN): shutil.copy2(P, FROZEN)
    rows = list(csv.reader(open(P))); last = rows[-1][0]
    start = (dt.date.fromisoformat(last) + dt.timedelta(days=1)).isoformat()
    new = [(d, v) for d, v in obs(call("VIXCLS", key, observation_start=start)) if d > last]
    with open(P, "a", newline="") as fh: csv.writer(fh).writerows(new)
    print(f"VIXCLS: +{len(new)} rows, now to {new[-1][0] if new else last}")
if __name__ == "__main__": main()
