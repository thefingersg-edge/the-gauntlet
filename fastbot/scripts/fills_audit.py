#!/usr/bin/env python3
"""Cost audit of Dave's real OANDA trades (data/fills/fills.csv from oanda_fills_pull.py).
DESCRIPTIVE MEASUREMENT, not a backtest. Answers three questions:
 1. Fees: is the spread he actually paid the same as the spread the backtests charge?
    (paid = mid move - executed move, per trade; quoted = (ask-bid)/mid at each fill;
     backtest = the bid/ask in our own OANDA candles at the same 15m bar)
 2. Size: are his trades' moves bigger than the moves our tests trade? (|mid move| per trade, holding time)
 3. Edge: is his net result per trade distinguishable from zero, and from simply being long a rising market?
I am not a financial adviser. This is a measurement, not a recommendation."""
import csv, datetime as dt, math, os, sys, bisect
from collections import defaultdict
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(HERE, "..", "data")
OURS = {"SPX500_USD": ("v24", "spx500usd", "15m"), "NAS100_USD": ("v24", "nas100usd", "15m"), "XAU_USD": ("v24", "xauusd", "15m"),
        "DE30_EUR": ("v24", "de30eur", "15m"), "US30_USD": ("v24", "us30usd", "15m"), "EUR_USD": ("v24", "eurusd", "15m"),
        "UK100_GBP": ("v38", "uk100gbp", "5m")}

def f(x):
    try: return float(x)
    except (TypeError, ValueError): return None

def ts(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00")[:26] + ("+00:00" if s.endswith("Z") else ""))  if s else None

def load_trades(path):
    opens, closes = {}, defaultdict(list)
    for r in csv.DictReader(open(path)):
        r["t"] = dt.datetime.fromisoformat(r["time"].replace("Z", "")[:26]).replace(tzinfo=dt.timezone.utc)
        (opens.__setitem__(r["trade_id"], r) if r["role"] == "open" else closes[r["trade_id"]].append(r))
    out = []
    for tid, o in opens.items():
        cs = closes.get(tid, [])
        u0 = f(o["units"]); uc = sum(abs(f(c["units"]) or 0) for c in cs)
        if not cs or u0 is None or abs(uc - abs(u0)) > 1e-9 * max(1, abs(u0)): continue        # still open or partial
        side = 1 if u0 > 0 else -1
        ep = f(o["price"]); emid = (f(o["bid"]) + f(o["ask"])) / 2 if f(o["bid"]) and f(o["ask"]) else None
        xp = sum(f(c["price"]) * abs(f(c["units"])) for c in cs) / uc
        xm = [((f(c["bid"]) + f(c["ask"])) / 2, abs(f(c["units"]))) for c in cs if f(c["bid"]) and f(c["ask"])]
        xmid = sum(m * w for m, w in xm) / sum(w for _, w in xm) if xm else None
        if emid is None or xmid is None: continue
        net = side * (xp / ep - 1) * 1e4; gross = side * (xmid / emid - 1) * 1e4
        out.append(dict(id=tid, ins=o["instrument"], side=side, t0=o["t"], t1=max(c["t"] for c in cs),
                        units=abs(u0), notional=abs(u0) * ep, net=net, gross=gross, paid=gross - net,
                        q_in=(f(o["ask"]) / f(o["bid"]) - 1) * 1e4, q_out=np.mean([(f(c["ask"]) / f(c["bid"]) - 1) * 1e4 for c in cs if f(c["bid"])]),
                        pl=sum(f(c["pl"]) or 0 for c in cs), fin=sum(f(c["financing"]) or 0 for c in cs), reason=cs[-1]["reason"]))
    return out

_CACHE = {}
def our_spread(ins, t):
    if ins not in OURS: return None
    if ins not in _CACHE:
        fold, stem, g = OURS[ins]; b, a = {}, {}
        for fn, dst in ((f"{stem}_bid_{g}.csv", b), (f"{stem}_ask_{g}.csv", a)):
            p = os.path.join(D, fold, fn)
            if not os.path.exists(p): _CACHE[ins] = None; return None
            for r in csv.reader(open(p)):
                if r[0] != "time" and r[0] >= "2018": dst[r[0]] = float(r[1])
        ks = sorted(k for k in b if k in a); _CACHE[ins] = (ks, [(a[k] / b[k] - 1) * 1e4 for k in ks])
    c = _CACHE[ins]
    if c is None: return None
    key = t.strftime("%Y-%m-%d %H:%M:%S"); i = bisect.bisect_right(c[0], key) - 1
    return c[1][i] if i >= 0 and (t - dt.datetime.fromisoformat(c[0][i]).replace(tzinfo=dt.timezone.utc)).total_seconds() < 3600 else None

def mt(x):
    x = np.asarray(x, float); n = len(x)
    if n < 2: return (float(x.mean()) if n else float("nan")), float("nan"), n
    return float(x.mean()), float(x.mean() / (x.std(ddof=1) / math.sqrt(n))), n

def report(T):
    print(f"  completed trades: {len(T)}   {min(t['t0'] for t in T):%Y-%m-%d} .. {max(t['t1'] for t in T):%Y-%m-%d}")
    hold = np.array([(t["t1"] - t["t0"]).total_seconds() / 60 for t in T])
    print(f"  holding time: median {np.median(hold):.0f} min, mean {hold.mean():.0f} min;  share held overnight {np.mean([t['t0'].date() != t['t1'].date() for t in T]):.0%}")
    print("\n  1. FEES -- spread actually paid vs what the backtests charge (bp of price)")
    for ins in sorted({t["ins"] for t in T}):
        S = [t for t in T if t["ins"] == ins]; ours = [our_spread(ins, t["t0"]) for t in S]; ours = [x for x in ours if x is not None]
        print(f"    {ins:<11} n {len(S):4d}  paid per round trip {np.median([t['paid'] for t in S]):5.2f} (median) {np.mean([t['paid'] for t in S]):5.2f} (mean)"
              f"   quoted at entry {np.median([t['q_in'] for t in S]):5.2f}   our candles same bar {('%.2f' % np.median(ours)) if ours else '  n/a'}")
    print("\n  2. SIZE -- how far price moved during his trades (bp of price, before spread)")
    a = np.abs([t["gross"] for t in T])
    print(f"    |mid move| per trade: median {np.median(a):.1f}  mean {a.mean():.1f}   spread paid as share of |move|: median {np.median([t['paid'] / max(abs(t['gross']), 1e-9) for t in T]):.0%}")
    print(f"    notional per trade (quote currency): median {np.median([t['notional'] for t in T]):,.0f}  -- size in money does not change cost in bp")
    print("\n  3. EDGE -- per trade, bp of price")
    for lab, S in (("all", T), ("longs", [t for t in T if t["side"] == 1]), ("shorts", [t for t in T if t["side"] == -1])):
        if not S: continue
        g, n_ = mt([t["gross"] for t in S]), mt([t["net"] for t in S])
        print(f"    {lab:<6} n {n_[2]:4d}  gross {g[0]:+6.2f} (t {g[1]:+.2f})  net {n_[0]:+6.2f} (t {n_[1]:+.2f})  win rate {np.mean([t['net'] > 0 for t in S]):.0%}")
    net = np.array([t["net"] for t in T]); m, s = net.mean(), net.std(ddof=1)
    need = (2.8 * s / m) ** 2 if m > 0 else float("inf")
    print(f"    trades needed to tell this mean from zero (80% power, 5%): about {need:,.0f}" if np.isfinite(need) else "    mean net <= 0")
    print(f"    money: realised P/L {sum(t['pl'] for t in T):+,.2f}  financing {sum(t['fin'] for t in T):+,.2f}  (account currency)")
    by = defaultdict(list)
    for t in T: by[t["reason"]].append(t["net"])
    print("    exits by reason: " + "  ".join(f"{k} n {len(v)} mean {np.mean(v):+.1f}" for k, v in by.items()))

def self_test():
    import tempfile
    rows = [["time", "fill_id", "role", "trade_id", "instrument", "units", "price", "bid", "ask", "halfSpreadCost", "pl", "financing", "reason"],
            ["2026-01-05T15:00:00.000000000Z", "1", "open", "10", "NAS100_USD", "1", "20001", "19999", "20001", "0.01", "", "", "MARKET_ORDER"],
            ["2026-01-05T16:00:00.000000000Z", "2", "close", "10", "NAS100_USD", "-1", "20039", "20039", "20041", "0.01", "38", "0", "MARKET_ORDER"]]
    p = os.path.join(tempfile.mkdtemp(), "f.csv"); csv.writer(open(p, "w", newline="")).writerows(rows)
    T = load_trades(p); t = T[0]
    ok = abs(t["gross"] - 20.0) < 1e-6 and abs(t["net"] - (38 / 20001 * 1e4)) < 1e-6 and abs(t["paid"] - (20.0 - 38 / 20001 * 1e4)) < 1e-6
    print(f"  self-test: long, mid 20000 -> 20040, bought at ask, sold at bid: gross {t['gross']:.2f} net {t['net']:.2f} paid {t['paid']:.2f} -> {'OK' if ok else 'BROKEN'}")
    return ok

if __name__ == "__main__":
    print("fills_audit.py -- DESCRIPTIVE. I am not a financial adviser. This is a measurement, not a recommendation.\n")
    if not self_test(): sys.exit(1)
    p = sys.argv[1] if len(sys.argv) > 1 else os.path.join(D, "fills", "fills.csv")
    if not os.path.exists(p): sys.exit(f"\n  no {p} yet -- run oanda_fills_pull.py on the Mac first")
    T = load_trades(p)
    if not T: sys.exit("  no completed trades found")
    report(T)
