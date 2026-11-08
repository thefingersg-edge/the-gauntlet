#!/usr/bin/env python3
"""Download the Sharadar bulk tables (full history) for the single-stock phase (PEAD1+). RUN LOCALLY on the Mac.
The API key is read from $SHARADAR_API_KEY or ~/.sharadar_key. It is never printed, logged or written anywhere
by this script, and it is stripped from any error message. Read-only GETs. Resumable: finished files are skipped.

    python3 sharadar_pull.py --self-test
    python3 sharadar_pull.py                    # all tables below, years=full
    python3 sharadar_pull.py --tables tickers   # one table

Writes data/sharadar/raw/<table>.<ext> and appends name, bytes and sha256 to data/sharadar/raw/MANIFEST.txt."""
import argparse, hashlib, os, shutil, sys, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data", "sharadar", "raw")
if "--refresh" in sys.argv:            # forward updates: a fresh dated folder, never overwriting the frozen snapshot
    import datetime as _dt
    OUT = os.path.join(HERE, "..", "data", "sharadar_fwd_" + _dt.date.today().strftime("%Y%m%d"), "raw")
BASE = "https://api.sharadar.com/v1.0/data"
TABLES = ("tickers", "stocks", "actions", "events", "daily", "fundamentals", "sp500", "insiders", "metrics", "descriptions")

def load_key():
    k = os.environ.get("SHARADAR_API_KEY", "").strip()
    if not k:
        p = os.path.expanduser("~/.sharadar_key")
        if os.path.exists(p): k = open(p).read().strip()
    if not k: sys.exit("no key: put it in ~/.sharadar_key (chmod 600) or $SHARADAR_API_KEY")
    return k

def build_url(table, key, years="full"):
    return f"{BASE}/{table}?api_key={key}&years={years}"

def redact(text, key): return text.replace(key, "<redacted>") if key else text

def fetch(table, key):
    os.makedirs(OUT, exist_ok=True)
    done = [f for f in os.listdir(OUT) if f.split(".")[0] == table and not f.endswith(".part")]
    if done: print(f"  {table}: already have {done[0]} -- skipped"); return
    req = urllib.request.Request(build_url(table, key), headers={"User-Agent": "fastbot-sharadar-pull"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:               # follows the redirect to the download URL
            final = r.geturl().split("?")[0]; ext = final.rsplit("/", 1)[-1].split(".", 1)[-1] if "." in final.rsplit("/", 1)[-1] else "csv"
            part = os.path.join(OUT, f"{table}.{ext}.part"); h = hashlib.sha256(); n = 0
            with open(part, "wb") as fh:
                while True:
                    b = r.read(1 << 20)
                    if not b: break
                    fh.write(b); h.update(b); n += len(b)
                    if n % (100 << 20) < (1 << 20): print(f"    {table}: {n >> 20} MB", flush=True)
        dest = part[:-5]; shutil.move(part, dest)
        line = f"{os.path.basename(dest)}  {n}  {h.hexdigest()}"
        open(os.path.join(OUT, "MANIFEST.txt"), "a").write(line + "\n"); print(f"  {table}: {line}")
    except urllib.error.HTTPError as e:
        print(f"  {table}: HTTP {e.code} {redact(str(e.reason), key)[:120]}")
    except Exception as e:
        print(f"  {table}: failed -- {redact(str(e), key)[:200]}")

def self_test():
    ok = True
    def check(n, c):
        nonlocal ok; ok &= bool(c); print(f"  [{'PASS' if c else 'FAIL'}] {n}")
    check("redact removes the key from text", "SECRETKEY" not in redact("x?api_key=SECRETKEY&y", "SECRETKEY"))
    check("no print statement takes the key variable directly",
          not any(("print(" in l and "key)" in l and "redact" not in l and "build_url" not in l) for l in open(__file__).read().splitlines()))
    check("full history requested", build_url("stocks", "K").endswith("years=full"))
    print("ALL PASS" if ok else "FAILURES ABOVE"); return 0 if ok else 1

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--tables", nargs="*", default=list(TABLES)); ap.add_argument("--self-test", action="store_true"); ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args()
    if a.self_test: sys.exit(self_test())
    key = load_key()
    for t in a.tables: fetch(t, key)

if __name__ == "__main__":
    main()
