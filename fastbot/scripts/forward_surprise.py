#!/usr/bin/env python3
"""PREREGISTRATION_v32 Part B -- record the surprise for each FORWARD CPI
and payrolls release, beside (never inside) the v25 ledger.

Run by forward_tick.sh after the ledger. Idempotent: a release is written
once, when both its first print and the Kalshi call are available; until
then it is retried on the next tick. A failure here is logged and cannot
halt or alter the v25 tick. Public data, read only; the FRED key is never
printed. Nothing here trades.

    python3 forward_surprise.py --self-test
    python3 forward_surprise.py
"""
from __future__ import annotations

import argparse, csv, datetime as dt, json, os, re, statistics as st, sys, time
import urllib.parse

from release_content import load_key, fetch, last_two, expected_month
from sentiment_fetch import get, KALSHI_BASES
from premarket_sentiment import implied_median

VERSION = "1.0"
START = dt.date(2026, 9, 18)                     # v25 START_DATE
OUT = "../data/forward_surprise.csv"
HIST = "../data/release_content.csv"
SPEC = {"CPI": ("CPIAUCSL", "KXCPI"), "NFP": ("PAYEMS", "KXPAYROLLS")}
MON = "JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split()
PRIOR = 12
_FORBIDDEN = re.compile(r"order|execute|submit|position", re.I)


def headline(rel, prev, last):
    """CPI m/m in % (Kalshi's units) or payrolls change in jobs."""
    return round((last / prev - 1) * 100, 1) if rel == "CPI" else (last - prev) * 1000


def event_ticker(series, release_date):
    y, m = map(int, expected_month(release_date).split("-")[:2])
    return f"{series}-{y % 100:02d}{MON[m - 1]}"


def kalshi_call(series, evt):
    """Kalshi's implied median just before close, or None."""
    for base in KALSHI_BASES:
        for path in ("/markets", "/historical/markets"):
            try:
                js = json.loads(get(f"{base}{path}?" + urllib.parse.urlencode(
                    {"event_ticker": evt, "limit": 200}), timeout=30)[0])
            except Exception:                                    # noqa: BLE001
                continue
            pairs = []
            for m in js.get("markets", []):
                if m.get("floor_strike") is None or m.get("cap_strike") is not None \
                        or m.get("strike_type") not in ("greater", None):
                    continue
                ct = dt.datetime.fromisoformat(m["close_time"].replace("Z", "+00:00"))
                q = urllib.parse.urlencode({"start_ts": int(ct.timestamp()) - 3 * 86400,
                                            "end_ts": int(ct.timestamp()), "period_interval": 60})
                cs = None
                for cp in (f"/series/{series}/markets/{m['ticker']}/candlesticks",
                           f"/historical/markets/{m['ticker']}/candlesticks"):
                    try:
                        cs = json.loads(get(f"{base}{cp}?{q}", timeout=30)[0]).get("candlesticks", [])
                        break
                    except Exception:                            # noqa: BLE001
                        continue
                cs = [c for c in (cs or []) if c["end_period_ts"] <= ct.timestamp()]
                if not cs:
                    continue
                def v(side):
                    x = cs[-1].get(side) or {}
                    y = x.get("close", x.get("close_dollars"))
                    return None if y in (None, "") else float(y)
                b_, a_ = v("yes_bid"), v("yes_ask")
                if b_ is not None and a_ is not None:
                    pairs.append((float(m["floor_strike"]), (b_ + a_) / 2))
                time.sleep(0.2)
            if pairs:
                return implied_median(pairs)
    return None


def _guard(names):
    bad = [n for n in names if _FORBIDDEN.search(n)]
    if bad:
        raise SystemExit(f"namespace guard: {bad}")


_guard(list(globals()))


def self_test():
    ok = True
    def check(n, c):
        nonlocal ok; ok &= bool(c); print(f"  [{'PASS' if c else 'FAIL'}] {n}")
    print(f"forward_surprise.py v{VERSION} self-test\n")
    check("CPI in Kalshi's units: % m/m to one decimal",
          headline("CPI", 300.0, 300.9) == 0.3)
    check("payrolls in jobs", headline("NFP", 159000.0, 159150.0) == 150000.0)
    check("an October CPI release is the September event",
          event_ticker("KXCPI", dt.date(2026, 10, 14)) == "KXCPI-26SEP")
    check("a January payrolls release is the December event",
          event_ticker("KXPAYROLLS", dt.date(2027, 1, 8)) == "KXPAYROLLS-26DEC")
    check("forward only, from v25's start", START == dt.date(2026, 9, 18))
    check("no order, execute, submit or position name in this file",
          not [n for n in globals() if _FORBIDDEN.search(n)])
    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", default="../data/events_v3.csv")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())
    print(f"forward_surprise.py v{VERSION}   PREREGISTRATION_v32 Part B -- records only")
    key = load_key()
    if not key:
        print("  no FRED key -- nothing recorded this tick"); return
    done = set()
    if os.path.exists(OUT):
        done = {(r["release"], r["date"]) for r in csv.DictReader(open(OUT))}
    #: history of first prints, v29's fetch plus what this file has recorded
    hist = {"CPI": [], "NFP": []}
    for r in csv.DictReader(open(HIST)):
        s = {"CPIAUCSL": "CPI", "PAYEMS": "NFP"}.get(r["series"])
        if s and r["vintage_ok"] == "1":
            hist[s].append((r["event_date"], headline(s, float(r["prev_value"]), float(r["last_value"]))))
    if os.path.exists(OUT):
        for r in csv.DictReader(open(OUT)):
            hist[r["release"]].append((r["date"], float(r["first_print"])))
    today = dt.date.today()
    todo = sorted({(r["event"], dt.date.fromisoformat(r["date"]))
                   for r in csv.DictReader(open(a.events))
                   if r["event"] in SPEC and r.get("time_et", "").startswith("08:3")})
    todo = [(e, d) for e, d in todo if START <= d <= today and (e, d.isoformat()) not in done]
    if not todo:
        print("  nothing new to record"); return
    new = not os.path.exists(OUT)
    with open(OUT, "a", newline="") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(["release", "date", "first_print", "naive_surprise",
                        "kalshi_median", "crowd_surprise", "code_version", "written_utc"])
        for rel, d in todo:
            fred, kal = SPEC[rel]
            try:
                got = last_two(fetch(fred, d, key))
            except Exception as e:                               # noqa: BLE001
                print(f"  {rel} {d}: FRED not ready ({type(e).__name__}); retry next tick")
                continue
            if not got or got[2] != expected_month(d):
                print(f"  {rel} {d}: first print not published yet; retry next tick")
                continue
            fp = headline(rel, got[1], got[3])
            prior = [v for dd, v in sorted(hist[rel]) if dd < d.isoformat()][-PRIOR:]
            naive = fp - st.median(prior) if len(prior) == PRIOR else None
            med = kalshi_call(kal, event_ticker(kal, d))
            if med is None:
                print(f"  {rel} {d}: Kalshi call not available yet; retry next tick")
                continue
            w.writerow([rel, d.isoformat(), fp, naive, med, fp - med, VERSION,
                        dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"])
            hist[rel].append((d.isoformat(), fp))
            print(f"  {rel} {d}: recorded  print {fp}  naive {naive}  crowd {fp - med:+.3g}")


if __name__ == "__main__":
    main()
