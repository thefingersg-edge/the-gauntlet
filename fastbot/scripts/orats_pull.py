#!/usr/bin/env python3
"""v43 -- pull ONLY the SPX option chains v43 needs from the ORATS Data API
(hist/strikes), on Dave's Mac. Standard library only (the Mac python3 has no pandas).

The token is read from $ORATS_TOKEN or ~/.orats_token and is NEVER printed,
logged or written anywhere. Nothing here trades.

    python3 orats_pull.py --self-test      offline: expiry/entry calendar
    python3 orats_pull.py --probe          1 request: prints the field names and row count
    python3 orats_pull.py --pull           ~460 requests, resumable; writes data/orats/
"""
import argparse, csv, datetime as dt, hashlib, io, json, os, sys, time, urllib.parse, urllib.request

VERSION = "1.0"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data", "orats")
URL = "https://api.orats.io/datav2/hist/strikes"
FIRST, LAST = dt.date(2007, 1, 1), dt.date(2026, 9, 18)


def token():
    t = os.environ.get("ORATS_TOKEN", "").strip()
    if not t and os.path.exists(os.path.expanduser("~/.orats_token")):
        t = open(os.path.expanduser("~/.orats_token")).read().strip()
    if not t:
        sys.exit("No ORATS token: put it in ~/.orats_token (one line) or $ORATS_TOKEN.")
    return t


def third_friday(y, m):
    d = dt.date(y, m, 15)
    return d + dt.timedelta(days=(4 - d.weekday()) % 7)


def monthly_expiries():
    out, y, m = [], FIRST.year, FIRST.month
    while True:
        f = third_friday(y, m)
        if f > LAST + dt.timedelta(days=40):
            return out
        out.append(f)
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def get(tok, day, retries=4):
    q = urllib.parse.urlencode({"token": tok, "ticker": "SPX", "tradeDate": day.isoformat()})
    for k in range(retries):
        try:
            with urllib.request.urlopen(URL + "?" + q, timeout=90) as r:
                body = r.read().decode()
            data = json.loads(body).get("data", [])
            return data
        except Exception as e:                       # never print the URL: it holds the token
            msg = str(e).replace(tok, "***")
            if k == retries - 1:
                raise SystemExit(f"request for {day} failed: {msg[:120]}")
            time.sleep(3 * (k + 1))


def first_trading_day(tok, start, step, limit=5):
    d = start
    for _ in range(limit):
        rows = get(tok, d)
        if rows:
            return d, rows
        d += dt.timedelta(days=step)
    return None, []


def keep_expiry(rows, target):
    """Rows for the standard monthly contract: expirDate within a day of the third
    Friday (before Feb 2015 SPX monthlies carried a Saturday date)."""
    out = []
    for r in rows:
        try:
            e = dt.date.fromisoformat(str(r.get("expirDate"))[:10])
        except ValueError:
            continue
        if abs((e - target).days) <= 1:
            out.append(r)
    return out


def self_test():
    ok = True
    def check(n, c):
        nonlocal ok; ok &= bool(c); print(f"  [{'PASS' if c else 'FAIL'}] {n}")
    print(f"orats_pull.py v{VERSION} self-test\n")
    check("third Friday of Sept 2026 is the 18th", third_friday(2026, 9) == dt.date(2026, 9, 18))
    check("third Friday of Mar 2008 is the 21st (Good Friday -- fetch falls back a day)", third_friday(2008, 3) == dt.date(2008, 3, 21))
    ex = monthly_expiries()
    check("about 230 monthly cycles 2007 -> 2026", 225 <= len(ex) <= 240)
    rows = [{"expirDate": "2014-01-18"}, {"expirDate": "2014-01-17"}, {"expirDate": "2014-01-24"}]
    check("a Saturday-dated pre-2015 monthly is kept, a weekly a week later is not",
          len(keep_expiry(rows, dt.date(2014, 1, 17))) == 2)
    lines = [l for l in open(os.path.abspath(__file__)) if "print(" in l and "check(" not in l]
    check("no print statement references the token", not any("tok" in l.split("print(", 1)[1] for l in lines))
    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE")); return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(); g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--self-test", action="store_true"); g.add_argument("--probe", action="store_true"); g.add_argument("--pull", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())
    tok = token(); os.makedirs(OUT, exist_ok=True)
    if a.probe:
        rows = get(tok, dt.date(2020, 3, 16))
        print(f"2020-03-16: {len(rows)} rows; fields:\n  " + ", ".join(sorted(rows[0].keys())) if rows else "no rows returned")
        return
    ex = monthly_expiries()
    man = os.path.join(OUT, "manifest.csv")
    done = {r["file"] for r in csv.DictReader(open(man))} if os.path.exists(man) else set()
    fresh = not os.path.exists(man)
    with open(man, "a", newline="") as mf:
        mw = csv.writer(mf)
        if fresh: mw.writerow(["cycle", "kind", "trade_date", "target_expiry", "rows", "file", "sha256"])
        for prev, nxt in zip(ex, ex[1:]):
            if nxt > LAST + dt.timedelta(days=1):
                break
            for kind, start, step, target in (("entry", prev + dt.timedelta(days=1), 1, nxt),
                                              ("expiry", nxt, -1, nxt)):
                fn = f"spx_{kind}_{nxt.isoformat()}.csv"
                if fn in done:
                    continue
                day, rows = first_trading_day(tok, start, step)
                if kind == "entry":
                    rows = keep_expiry(rows, target)
                else:
                    rows = rows[:1]                     # only the underlying price is needed
                if not rows:
                    print(f"  {nxt} {kind}: NO DATA -- recorded, check by hand"); mw.writerow([nxt, kind, "", nxt, 0, fn, ""]); continue
                buf = io.StringIO(); w = csv.DictWriter(buf, fieldnames=sorted(rows[0].keys())); w.writeheader(); w.writerows(rows)
                b = buf.getvalue().encode(); open(os.path.join(OUT, fn), "wb").write(b)
                mw.writerow([nxt, kind, day, nxt, len(rows), fn, hashlib.sha256(b).hexdigest()]); mf.flush()
                print(f"  {nxt} {kind:<6} {day}  {len(rows):>5} rows")
                time.sleep(0.4)
    print("done -- tell Claude the pull has finished")


if __name__ == "__main__":
    main()
