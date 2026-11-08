#!/usr/bin/env python3
"""fetch_aiind.py -- data for the AIIND batch (PREREGISTRATION_AIIND.md). Run on the Mac. Read-only, places no order.
    python3 fetch_aiind.py binance     BTCUSDT 5m klines 2017-08 -> 2026-10-16 from data.binance.vision (free, no key)
    python3 fetch_aiind.py futures     ES.v.0 / NQ.v.0 ohlcv-1m 2026-09-01 -> 2026-10-17 from Databento (refuses over $2)
Outputs: data/aiind/binance/BTCUSDT-5m-*.zip (as downloaded, never edited), data/aiind/{ES,NQ}_topup.csv, data/aiind/pull_log.jsonl
The Databento key is read from ~/.databento_key and never printed. Stdlib only.
I am not a financial adviser. This is a measurement, not a recommendation."""
import datetime as dt, hashlib, json, os, subprocess, sys, time, urllib.parse, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(HERE, "..", "data", "aiind"); B = os.path.join(D, "binance")
LOG = os.path.join(D, "pull_log.jsonl"); BASE = "https://data.binance.vision/data/spot"
END = dt.date(2026, 10, 16); MAXUSD = 2.00


def log(**k):
    os.makedirs(D, exist_ok=True)
    with open(LOG, "a") as f: f.write(json.dumps(dict(utc=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), **k)) + "\n")


def get(url, tries=4):
    for a in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "fastbot-research/1.0"})
            with urllib.request.urlopen(req, timeout=120) as r: return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404: return None
            time.sleep(3 * (a + 1))
        except Exception:
            time.sleep(3 * (a + 1))
    raise RuntimeError(f"failed: {url}")


def binance():
    os.makedirs(B, exist_ok=True); n = 0; miss = []
    months = []; y, m = 2017, 8
    while (y, m) <= (2026, 9):
        months.append(f"{y}-{m:02d}"); m += 1
        if m == 13: y, m = y + 1, 1
    days = [(dt.date(2026, 10, 1) + dt.timedelta(d)).isoformat() for d in range((END - dt.date(2026, 10, 1)).days + 1)]
    jobs = [(f"{BASE}/monthly/klines/BTCUSDT/5m/BTCUSDT-5m-{p}.zip", p) for p in months] + \
           [(f"{BASE}/daily/klines/BTCUSDT/5m/BTCUSDT-5m-{p}.zip", p) for p in days]
    for url, p in jobs:
        out = os.path.join(B, f"BTCUSDT-5m-{p}.zip")
        if os.path.exists(out) and os.path.getsize(out) > 0: continue
        blob = get(url)
        if blob is None: miss.append(p); continue
        open(out, "wb").write(blob); n += 1
        log(source="binance", file=os.path.basename(out), bytes=len(blob), sha256=hashlib.sha256(blob).hexdigest())
    print(f"binance: {n} new files, {len(jobs) - len(miss)} of {len(jobs)} present" + (f"; missing {miss}" if miss else ""))


def key():
    k = os.environ.get("DATABENTO_API_KEY", "").strip(); p = os.path.expanduser("~/.databento_key")
    if not k and os.path.exists(p): k = open(p).read().strip()
    if not k: sys.exit("no Databento key in ~/.databento_key")
    return k


def api(endpoint, params, k):
    url = "https://hist.databento.com/v0/" + endpoint + "?" + urllib.parse.urlencode(params)
    r = subprocess.run(["curl", "-sS", "--fail-with-body", "-u", f"{k}:", "--max-time", "600", url], capture_output=True, text=True)
    if r.returncode != 0: raise RuntimeError(f"{endpoint}: {(r.stdout or r.stderr).strip()[:300]}")
    return r.stdout


def futures():
    k = key(); end = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=9)).date()
    end = min(end, END + dt.timedelta(days=1)).isoformat()
    qs = {s: dict(dataset="GLBX.MDP3", symbols=f"{s}.v.0", stype_in="continuous", schema="ohlcv-1m", start="2026-09-01", end=end) for s in ("ES", "NQ")}
    cost = sum(float(api("metadata.get_cost", q, k)) for q in qs.values())
    log(source="databento", end=end, est_usd=cost)
    if cost > MAXUSD: sys.exit(f"REFUSING: estimated ${cost:.2f} > ${MAXUSD:.2f}")
    for s, q in qs.items():
        txt = api("timeseries.get_range", dict(q, encoding="csv", pretty_px="true", pretty_ts="true", map_symbols="true"), k)
        p = os.path.join(D, f"{s}_topup.csv"); open(p, "w").write(txt)
        log(source="databento", file=os.path.basename(p), rows=txt.count("\n") - 1, sha256=hashlib.sha256(txt.encode()).hexdigest())
        print(f"{s}: {txt.count(chr(10)) - 1} rows -> data/aiind/{s}_topup.csv")
    print(f"futures done (est ${cost:.3f})")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a == ["binance"]: binance()
    elif a == ["futures"]: futures()
    else: print(__doc__)
