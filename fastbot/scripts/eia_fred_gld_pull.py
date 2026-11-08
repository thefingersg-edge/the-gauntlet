#!/usr/bin/env python3
"""OILGOLD batch data (PREREGISTRATION_OILGOLD_BATCH). RUN ON THE MAC. Public data, read only; places no orders.
Keys are read from ~/.eia_key and ~/.fred_key and never printed.
    python3 eia_fred_gld_pull.py eia     # WTI futures contracts 1-4 (daily) + US crude stocks ex-SPR (weekly)
    python3 eia_fred_gld_pull.py fred    # 10-year TIPS real yield DFII10
    python3 eia_fred_gld_pull.py gld     # SPDR GLD holdings archive (no key)
Writes data/oil/*.csv and data/gold/*.csv with sha256 printed."""
import os, sys, csv, json, hashlib, urllib.request, urllib.parse
HERE = os.path.dirname(os.path.abspath(__file__)); FB = os.path.join(HERE, "..")
def key(name):
    p = os.path.expanduser(f"~/.{name}_key")
    if not os.path.exists(p): sys.exit(f"missing ~/.{name}_key (one line, chmod 600)")
    return open(p).read().strip()
def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "fastbot-oilgold/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r: return r.read()
        except Exception as ex:
            if i == tries - 1: raise
    return None
def save(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as fh: w = csv.writer(fh); w.writerow(header); w.writerows(rows)
    print(f"  {os.path.relpath(path, FB)}: {len(rows)} rows {rows[0][0] if rows else '-'} -> {rows[-1][0] if rows else '-'}  sha256 {hashlib.sha256(open(path,'rb').read()).hexdigest()}")
def eia():
    k = key("eia")
    for sid, fn in (("PET.RCLC1.D", "wti_f1"), ("PET.RCLC2.D", "wti_f2"), ("PET.RCLC3.D", "wti_f3"), ("PET.RCLC4.D", "wti_f4"), ("PET.WCESTUS1.W", "crude_stocks_exspr")):
        rows, off = [], 0
        while True:
            q = urllib.parse.urlencode({"api_key": k, "offset": off, "length": 5000})
            js = json.loads(get(f"https://api.eia.gov/v2/seriesid/{sid}?{q}"))
            data = js.get("response", {}).get("data", [])
            rows += [(d["period"], d["value"]) for d in data if d.get("value") not in (None, "")]
            if len(data) < 5000: break
            off += 5000
        rows.sort(); save(os.path.join(FB, "data", "oil", f"{fn}.csv"), ["date", "value"], rows)
def fred():
    sys.path.insert(0, HERE); from fred_fetch_v31 import call, obs
    o = obs(call("DFII10", key("fred"))); save(os.path.join(FB, "data", "gold", "DFII10.csv"), ["date", "dfii10"], o)
def gld():
    raw = get("https://www.spdrgoldshares.com/assets/dynamic/GLD/GLD_US_archive_EN.csv")
    p = os.path.join(FB, "data", "gold", "GLD_US_archive_EN.csv"); os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "wb").write(raw)
    print(f"  data/gold/GLD_US_archive_EN.csv: {len(raw):,} bytes  sha256 {hashlib.sha256(raw).hexdigest()}")
if __name__ == "__main__":
    {"eia": eia, "fred": fred, "gld": gld}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: print(__doc__))()
