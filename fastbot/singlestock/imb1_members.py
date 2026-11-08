#!/usr/bin/env python3
"""IMB1 step 1: point-in-time S&P 500 members per trading day (2018-05-01 .. 2026-09-30) with their listing venue,
for the Databento puller. Uses BREADTH2's membership rules (snapshots + adds/removes). No prices, no outcomes.
Output data/imb1/members.csv: date,dataset,symbols (space separated)."""
import os, csv, io, subprocess, datetime as dt
import ss_lib
FB = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."); D0 = dt.date(1970, 1, 1)
DS = {"NASDAQ": "XNAS.ITCH", "NYSE": "XNYS.PILLAR"}
def main():
    raw = subprocess.run(["unzip", "-p", ss_lib.find("sp500")], capture_output=True, text=True).stdout
    rows = list(csv.DictReader(io.StringIO(raw))); snaps, evs = {}, []
    for r in rows:
        if r["action"] == "historical": snaps.setdefault(r["date"], set()).add(r["ticker"])
        elif r["action"] in ("added", "removed"): evs.append((r["date"], r["action"], r["ticker"]))
    rd, ix = ss_lib.reader(ss_lib.find("tickers"), "tickers"); ex = {}
    for r in rd:
        if r[ix["table"]] == "SEP": ex[r[ix["ticker"]]] = r[ix["exchange"]]
    items = sorted([(d, 0, a, t) for d, a, t in evs] + [(d, 1, "snap", d) for d in snaps])
    cur, k, out = set(), 0, []
    d = dt.date(2018, 5, 1)
    while d <= dt.date(2026, 9, 30):
        if d.weekday() < 5:
            s = d.isoformat()
            while k < len(items) and items[k][0] <= s:
                _, _, a, t = items[k]
                if a == "snap": cur = set(snaps[t])
                elif a == "added": cur.add(t)
                else: cur.discard(t)
                k += 1
            for v, dsn in DS.items():
                sy = sorted(t.replace(".", ".") for t in cur if ex.get(t) == v)
                if sy: out.append((s, dsn, " ".join(sy)))
        d += dt.timedelta(days=1)
    w = csv.writer(open(os.path.join(FB, "data", "imb1", "members.csv"), "w", newline="")); w.writerow(["date", "dataset", "symbols"]); w.writerows(out)
    print("rows", len(out), "  e.g.", out[0][0], out[0][1], len(out[0][2].split()), "symbols")
if __name__ == "__main__": main()
