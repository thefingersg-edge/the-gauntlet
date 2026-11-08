#!/usr/bin/env python3
"""fetch_fxvalue_a1.py -- FLOWS-13 amendment A1 Step 0 (RUN ON THE MAC): BIS WS_LONG_CPI
price levels and FRED EXGEUS. Reads nothing into any statistic.
    python3 fetch_fxvalue_a1.py --self-test | (no args)"""
from __future__ import annotations
import csv, datetime as dt, hashlib, io, json, os, sys, urllib.parse
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import fetch_ecb as FE            # noqa: E402
from fetch_fred import load_key   # noqa: E402
D = os.path.join(HERE, "data", "longrun"); META = os.path.join(HERE, "data", "fxvalue_a1.meta.json")
AREAS = ["US", "JP", "GB", "CH", "CA", "AU", "NZ", "SE", "NO", "DE", "XM"]
URLS = ["https://stats.bis.org/api/v1/data/WS_LONG_CPI/{f}.{a}.628/all?format=csv",
        "https://stats.bis.org/api/v2/data/dataflow/BIS/WS_LONG_CPI/1.0/{f}.{a}.628?format=csv"]


def parse(txt: str):
    rows = list(csv.DictReader(io.StringIO(txt)))
    if not rows or "TIME_PERIOD" not in rows[0] or "OBS_VALUE" not in rows[0]:
        return []
    out = [(r["TIME_PERIOD"], r["OBS_VALUE"]) for r in rows if r.get("OBS_VALUE") not in ("", "NaN", None)]
    return sorted(out)


def main():
    os.makedirs(D, exist_ok=True)
    meta = {"built_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "bis": {}, "missing": []}
    for a in AREAS:
        got = None
        for f in ("M", "Q"):
            for u in URLS:
                try:
                    obs = parse(FE.get(u.format(f=f, a=a)))
                except Exception as e:
                    obs = []
                if len(obs) > 40:
                    got = (f, u.format(f=f, a=a), obs); break
            if got:
                break
        if not got:
            meta["missing"].append(a); print(f"  BIS CPI {a}: MISSING"); continue
        f, u, obs = got
        p = os.path.join(D, f"BISCPI_{a}.csv")
        with open(p, "w", newline="") as fh:
            w = csv.writer(fh); w.writerow(["period", "value"]); w.writerows(obs)
        meta["bis"][a] = dict(freq=f, url=u, n=len(obs), first=obs[0][0], last=obs[-1][0],
                              sha256=hashlib.sha256(open(p, "rb").read()).hexdigest())
        print(f"  BIS CPI {a}: {f} {len(obs)} obs {obs[0][0]} .. {obs[-1][0]}")
    key = load_key()
    q = urllib.parse.urlencode(dict(series_id="EXGEUS", api_key=key, file_type="json"))
    try:
        js = json.loads(FE.get("https://api.stlouisfed.org/fred/series/observations?" + q))
        obs = [(o["date"], o["value"]) for o in js["observations"] if o["value"] not in (".", "")]
        p = os.path.join(D, "EXGEUS.csv")
        with open(p, "w", newline="") as fh:
            w = csv.writer(fh); w.writerow(["date", "value"]); w.writerows(obs)
        meta["EXGEUS"] = dict(n=len(obs), first=obs[0][0], last=obs[-1][0]); print(f"  EXGEUS {len(obs)} {obs[0][0]} .. {obs[-1][0]}")
    except Exception as e:
        meta["missing"].append("EXGEUS"); print(f"  EXGEUS: MISSING ({e})")
    json.dump(meta, open(META, "w"), indent=1)
    print("missing:", meta["missing"])
    return 0


def self_test():
    txt = "FREQ,REF_AREA,UNIT_MEASURE,TIME_PERIOD,OBS_VALUE\nM,JP,628,1990-01,80.1\nM,JP,628,1990-02,80.3\n"
    ok = parse(txt) == [("1990-01", "80.1"), ("1990-02", "80.3")] and parse("<html>") == []
    print(f"  {'PASS' if ok else 'FAIL'}  BIS csv parse")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else main())
