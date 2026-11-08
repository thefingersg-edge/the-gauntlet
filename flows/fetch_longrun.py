#!/usr/bin/env python3
"""
fetch_longrun.py -- Step 0 for FLOWS-10 (secondary), -12, -13 and -14. RUN ON THE MAC.
FRED (API key as fetch_fred.py; never printed) and Shiller's ie_data.xls.
Reads nothing into any statistic; writes raw series + data/longrun.meta.json.
Series that FRED does not serve are RECORDED as missing, not guessed.
    python3 fetch_longrun.py --self-test | (no args)
"""
from __future__ import annotations
import csv, datetime as dt, hashlib, json, os, sys, urllib.parse
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import fetch_ecb as FE             # noqa: E402  verified-TLS get
from fetch_fred import load_key    # noqa: E402
D = os.path.join(HERE, "data", "longrun"); META = os.path.join(HERE, "data", "longrun.meta.json")
API = "https://api.stlouisfed.org/fred/series/observations?"
SHILLER = "http://www.econ.yale.edu/~shiller/data/ie_data.xls"
CCY = ["EU", "GE", "JP", "UK", "SZ", "CA", "AL", "NZ", "SD", "NO"]
DEX = {"EU": "DEXUSEU", "GE": "DEXGEUS", "JP": "DEXJPUS", "UK": "DEXUSUK", "SZ": "DEXSZUS",
       "CA": "DEXCAUS", "AL": "DEXUSAL", "NZ": "DEXUSNZ", "SD": "DEXSDUS", "NO": "DEXNOUS"}
ISO = {"EU": "EZ", "GE": "DE", "JP": "JP", "UK": "GB", "SZ": "CH", "CA": "CA", "AL": "AU", "NZ": "NZ", "SD": "SE", "NO": "NO"}
SERIES = (["NASDAQCOM", "TB3MS", "BAA", "AAA", "GS10", "CPIAUCSL"] + list(DEX.values())
          + [f"CPALTT01{ISO[c]}M661N" for c in CCY] + [f"CPALTT01{ISO[c]}Q661N" for c in ("AL", "NZ")]
          + ["CP0000EZ19M086NEST"]
          + [f"IR3TIB01{ISO[c]}M156N" for c in CCY] + [f"IRSTCI01{ISO[c]}M156N" for c in CCY])
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()


def fred(key, s):
    q = urllib.parse.urlencode(dict(series_id=s, api_key=key, file_type="json", observation_start="1900-01-01",
                                    observation_end="2026-08-31"))
    js = json.loads(FE.get(API + q))
    return [(o["date"], o["value"]) for o in js.get("observations", []) if o["value"] not in (".", "")]


def main():
    key = load_key()
    if not key:
        raise SystemExit("STOP: needs the FRED key")
    os.makedirs(D, exist_ok=True)
    meta = {"built_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "fred": {}, "missing": []}
    for s in SERIES:
        try:
            obs = fred(key, s)
        except Exception as e:
            obs = []; print(f"  {s}: {e}")
        if not obs:
            meta["missing"].append(s); print(f"  {s}: MISSING"); continue
        p = os.path.join(D, f"{s}.csv")
        with open(p, "w", newline="") as f:
            w = csv.writer(f); w.writerow(["date", "value"]); w.writerows(obs)
        meta["fred"][s] = dict(n=len(obs), first=obs[0][0], last=obs[-1][0], sha256=sha(p))
        print(f"  {s:22s} {len(obs):6d}  {obs[0][0]} .. {obs[-1][0]}")
    # NASDAQCOM also where preholiday.py / halloween.py look for it
    if "NASDAQCOM" in meta["fred"]:
        src = os.path.join(D, "NASDAQCOM.csv"); dst = os.path.join(HERE, "data", "fred_nasdaqcom_long.csv")
        rows = list(csv.reader(open(src)))[1:]
        with open(dst, "w", newline="") as f:
            w = csv.writer(f); w.writerow(["date", "close"]); w.writerows(rows)
    try:
        import subprocess
        raw = subprocess.run(["curl", "-sS", "--fail", "-L", "--max-time", "60", SHILLER], capture_output=True)
        if raw.returncode != 0 or len(raw.stdout) < 100000:
            raise RuntimeError(raw.stderr.decode()[:200] or f"{len(raw.stdout)} bytes")
        p = os.path.join(D, "ie_data.xls"); open(p, "wb").write(raw.stdout)
        meta["shiller"] = dict(url=SHILLER, bytes=len(raw.stdout), sha256=sha(p)); print(f"  Shiller ie_data.xls {len(raw.stdout)} bytes")
    except Exception as e:
        meta["missing"].append("shiller"); print(f"  Shiller: MISSING ({e})")
    json.dump(meta, open(META, "w"), indent=1)
    print(f"missing: {meta['missing']}")
    return 0


def self_test():
    ok = len(SERIES) == len(set(SERIES)) and "NASDAQCOM" in SERIES and "IR3TIB01JPM156N" in SERIES
    print(f"  {'PASS' if ok else 'FAIL'}  series list well-formed ({len(SERIES)} series)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else main())
