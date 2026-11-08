#!/usr/bin/env python3
"""forward_orbcore_dax.py -- ORBCORE1 forward record on DAX (PREREGISTRATION_ORBCORE1.md, "Forward record"). PAPER ONLY.
RECORDS ONLY: places no order and touches no broker account. Stdlib only. Reads the OANDA DE30_EUR 15m bid/ask that forward_tick.sh
step 2 already pulls into data/v24, and appends one row per completed Berlin trading day from 2026-10-13 to data/forward_orbcore_dax.csv.
Rule (15m bars, Europe/Berlin): range = the 4 bars of 08:00-09:00 (>= 50 min covered, so all 4); delta = HH - LL. The first bar starting
09:00-09:45 that CLOSES beyond HH + delta / LL - delta -> enter at the next bar's open (long pays the ask, short sells the bid). Exit at the
close of the last bar starting before 22:00 (long sells the bid, short buys the ask). No stop, no filters.
    python3 forward_orbcore_dax.py --self-test
    python3 forward_orbcore_dax.py          # append completed days
    python3 forward_orbcore_dax.py --status # counts only
I am not a financial adviser. This is a measurement, not a recommendation."""
import csv, datetime as dt, hashlib, os, sys
from zoneinfo import ZoneInfo
VERSION = "1.0"
HERE = os.path.dirname(os.path.abspath(__file__)); FB = os.path.join(HERE, "..")
SPEC = os.path.join(FB, "PREREGISTRATION_ORBCORE1.md"); SPEC_SHA = "66c0aca9d467bf001150558fc5b63b724c32155cd06b42131ec4661b130f1050"
BID, ASK = (os.path.join(FB, "data", "v24", f"de30eur_{s}_15m.csv") for s in ("bid", "ask"))
LEDGER = os.path.join(FB, "data", "forward_orbcore_dax.csv"); START = dt.date(2026, 10, 13)
BER, UTC = ZoneInfo("Europe/Berlin"), dt.timezone.utc
COLS = ["date", "status", "side", "HH", "LL", "entry_berlin", "entry_px", "exit_berlin", "exit_px", "gross_bp", "net_bp", "written_utc", "version"]


def pin():
    if hashlib.sha256(open(SPEC, "rb").read()).hexdigest() != SPEC_SHA: sys.exit("REFUSING: PREREGISTRATION_ORBCORE1.md changed")


def read(p):
    out = {}
    with open(p) as f:
        r = csv.reader(f); next(r)
        for x in r: out[x[0]] = tuple(float(v) for v in x[1:5])
    return out


def days(bid, ask):
    by = {}
    for k in sorted(set(bid) & set(ask)):
        t = dt.datetime.strptime(k[:16], "%Y-%m-%d %H:%M").replace(tzinfo=UTC).astimezone(BER)
        b, a = bid[k], ask[k]; mid = tuple((x + y) / 2 for x, y in zip(b, a))
        by.setdefault(t.date(), []).append((t.hour * 60 + t.minute, t, mid, b, a))
    return by


def one_day(bars):
    rng = [x for x in bars if 480 <= x[0] < 540]
    if len(rng) * 15 < 50: return dict(status="no_range")
    HH = max(x[2][1] for x in rng); LL = min(x[2][2] for x in rng); dl = HH - LL
    sess = [x for x in bars if 540 <= x[0] < 1320]
    if dl <= 0 or not sess: return dict(status="no_range")
    up, dn = HH + dl, LL - dl
    for k, x in enumerate(sess):
        if x[0] >= 600: break
        sd = 1 if x[2][3] > up else (-1 if x[2][3] < dn else 0)
        if sd and k + 1 < len(sess):
            e, z = sess[k + 1], sess[-1]
            p0 = e[4][0] if sd > 0 else e[3][0]; p1 = z[3][3] if sd > 0 else z[4][3]
            m0, m1 = e[2][0], z[2][3]
            return dict(status="traded", side=sd, HH=HH, LL=LL, entry_berlin=e[1].strftime("%H:%M"), entry_px=p0,
                        exit_berlin=z[1].strftime("%H:%M"), exit_px=p1, gross_bp=sd * (m1 / m0 - 1) * 1e4, net_bp=sd * (p1 / p0 - 1) * 1e4)
    return dict(status="no_signal", HH=HH, LL=LL)


def tick():
    by = days(read(BID), read(ASK)); now_b = dt.datetime.now(BER)
    have = {r["date"] for r in csv.DictReader(open(LEDGER))} if os.path.exists(LEDGER) else set()
    new = not os.path.exists(LEDGER); n = 0
    with open(LEDGER, "a", newline="") as f:
        w = csv.writer(f)
        if new: w.writerow(COLS)
        for d in sorted(by):
            if d < START or d.isoformat() in have or d.weekday() >= 5: continue
            if not (d < now_b.date() or now_b.hour >= 23): continue                         # only completed days
            if max(x[0] for x in by[d]) < 1305: continue                                   # wait until the 21:45 bar is on disk
            r = one_day(by[d]); fmt = lambda v: "" if v is None else (f"{v:.6g}" if isinstance(v, float) else v)
            w.writerow([d.isoformat(), r["status"]] + [fmt(r.get(c)) for c in COLS[2:11]] + [dt.datetime.now(UTC).isoformat(timespec="seconds"), VERSION]); n += 1
    print(f"forward_orbcore_dax: +{n} rows")


def self_test():
    ok = True
    def bar(hm, o, h, l, c, sp=1.0):
        t = dt.datetime(2026, 1, 8, hm // 60, hm % 60, tzinfo=BER)
        return (hm, t, (o, h, l, c), (o - sp / 2, h - sp / 2, l - sp / 2, c - sp / 2), (o + sp / 2, h + sp / 2, l + sp / 2, c + sp / 2))
    bars = [bar(m, 100, 101, 99, 100) for m in range(480, 540, 15)] + [bar(540, 100, 103.6, 100, 103.5), bar(555, 103.6, 104, 103, 103.8)]
    bars += [bar(m, 103.8, 104.5, 103, 104.2) for m in range(570, 1320, 15)]
    r = one_day(bars)
    e1 = r["status"] == "traded" and r["side"] == 1 and r["entry_px"] == 104.1 and abs(r["exit_px"] - 103.7) < 1e-9 and r["exit_berlin"] == "21:45"
    ok &= e1; print(f"  [{'PASS' if e1 else 'FAIL'}] long at the next ask (104.1), exit at the 21:45 bar's closing bid ({r.get('exit_px')})")
    e2 = one_day(bars[1:])["status"] == "no_range"; ok &= e2; print(f"  [{'PASS' if e2 else 'FAIL'}] 3 of 4 range bars -> no_range")
    print("ALL PASS" if ok else "FAILURES"); return ok


if __name__ == "__main__":
    pin(); a = sys.argv[1:]
    if a == ["--self-test"]: sys.exit(0 if self_test() else 1)
    if a == ["--status"]:
        if os.path.exists(LEDGER):
            from collections import Counter
            print(dict(Counter(r["status"] for r in csv.DictReader(open(LEDGER)))))
        else: print("no ledger yet")
        sys.exit(0)
    tick()
