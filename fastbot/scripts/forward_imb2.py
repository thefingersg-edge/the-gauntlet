#!/usr/bin/env python3
"""forward_imb2.py -- FORWARD_IMB2 (PREREGISTRATION_FORWARD_IMB2.md): paper record of the 15:50 imbalance trade at L = 1 s.
RECORDS ONLY: places no order and touches no broker account. Stdlib only, so it runs under the Mac's plain python3.
Databento key from ~/.databento_key (or $DATABENTO_API_KEY); it is never printed.

    python3 forward_imb2.py --self-test    reproduces IMB2's primary (n 487, +1.31 bp) from the historic files; planted CSV parse
    python3 forward_imb2.py --cost         estimated cost of the pending days (no download)
    python3 forward_imb2.py --tick         pull pending days (refuses any day over $1), then append ledger rows
    python3 forward_imb2.py --status       counts only (no running mean before the 12-month review)
I am not a financial adviser. This is a measurement, not a recommendation."""
import csv, datetime as dt, hashlib, json, math, os, subprocess, sys, urllib.parse
from collections import defaultdict
from zoneinfo import ZoneInfo
VERSION = "1.0"
HERE = os.path.dirname(os.path.abspath(__file__)); FB = os.path.join(HERE, ".."); D = os.path.join(FB, "data", "imb1")
SPEC = os.path.join(FB, "PREREGISTRATION_FORWARD_IMB2.md"); SPEC_SHA = "bba7f3d414552577b63e4216245857314632734cfc7810ef496655feccfdeda5"
HIST_MSG, HIST_PX, MEMBERS = os.path.join(D, "imb2_msgs.csv"), os.path.join(D, "imb2_px.csv"), os.path.join(D, "members.csv")
FMSG, FPX = os.path.join(D, "fwd_msgs.csv"), os.path.join(D, "fwd_px.csv")
LEDGER = os.path.join(FB, "data", "forward_imb2.csv"); PULLLOG = os.path.join(D, "fwd_pull_log.jsonl")
API = "https://hist.databento.com/v0/"; NY = ZoneInfo("America/New_York")
START = dt.date(2026, 10, 12); L_MS = 1000; EXIT_MS = 60000; COMM_SH = 0.0035; MAXUSD_DAY = 1.00
OFF = [-500, 0, 50, 100, 250, 500, 1000, 2000, 5000, 15000, 60000]
PXCOLS = ["date", "inst"] + [f"{s}{o}" for o in OFF for s in ("b", "a")]
MSGCOLS = ["date", "venue", "symbol", "ms", "side", "imb_qty", "paired_qty", "ref_price"]
LCOLS = ["date", "status", "S", "z", "side", "entry_bid", "entry_ask", "exit_bid", "exit_ask", "gross_bp", "net_bp", "mid_move_bp",
         "n_msgs", "written_utc", "version"]


def pin():
    if SPEC_SHA and hashlib.sha256(open(SPEC, "rb").read()).hexdigest() != SPEC_SHA: sys.exit("REFUSING: PREREGISTRATION_FORWARD_IMB2.md changed")


# ------------------------------------------------------------------ the rule (IMB2, defined locally)
def first_msgs(paths):
    first = {}
    for p in paths:
        if not os.path.exists(p): continue
        with open(p) as fh:
            for r in csv.DictReader(fh):
                k = (r["date"], r["venue"], r["symbol"]); ms = float(r["ms"])
                if k not in first or ms < first[k][0]:
                    sg = 1 if r["side"] == "B" else (-1 if r["side"] in ("A", "S") else 0)
                    first[k] = (ms, sg * float(r["imb_qty"]) * float(r["ref_price"]), float(r["paired_qty"]) * float(r["ref_price"]))
    byday = defaultdict(list)
    for (d, _, _), v in first.items(): byday[d].append(v)
    return byday


def signal_series(byday, Lm=L_MS):
    S, dd = [], []
    for d in sorted(byday):
        num = sum(s for ms, s, p in byday[d] if ms <= Lm); den = sum(p for ms, s, p in byday[d] if ms <= Lm)
        if den > 0: S.append(num / den); dd.append(d)
    z = {}
    for i in range(250, len(dd)):
        w = S[i - 250:i]; m = sum(w) / 250; sd = math.sqrt(sum((x - m) ** 2 for x in w) / 249)
        if sd > 0: z[dd[i]] = (S[i] - m) / sd
    return dict(zip(dd, S)), z


def read_px(paths):
    PX = {}
    for p in paths:
        if not os.path.exists(p): continue
        with open(p) as fh:
            for r in csv.DictReader(fh):
                q = {}
                for o in (L_MS, EXIT_MS, 0):
                    try: q[o] = (float(r[f"b{o}"]), float(r[f"a{o}"]))
                    except (ValueError, KeyError, TypeError): q[o] = None
                PX[(r["date"], r["inst"])] = q
    return PX


def trade(z, q):
    """Returns (status, side, b0, a0, b1, a1, gross, net, midmove)."""
    if abs(z) < 1: return ("no_signal",) + (None,) * 8
    if not q or q.get(L_MS) is None or q.get(EXIT_MS) is None: return ("missing_px",) + (None,) * 8
    (b0, a0), (b1, a1) = q[L_MS], q[EXIT_MS]
    if min(b0, a0, b1, a1) <= 0 or a0 < b0 or a1 < b1: return ("missing_px",) + (None,) * 8
    s = 1 if z > 0 else -1
    g = (b1 / a0 - 1) * 1e4 if s > 0 else (b0 / a1 - 1) * 1e4
    mid0 = (b0 + a0) / 2; net = g - 2 * COMM_SH / mid0 * 1e4
    return ("traded", s, b0, a0, b1, a1, g, net, s * (((b1 + a1) / 2) / mid0 - 1) * 1e4)


# ------------------------------------------------------------------ Databento (curl, like flows/forward_nq.py)
def key():
    k = os.environ.get("DATABENTO_API_KEY", "").strip(); p = os.path.expanduser("~/.databento_key")
    if not k and os.path.exists(p): k = open(p).read().strip()
    if not k.startswith("db-"): sys.exit("no Databento key (~/.databento_key)")
    return k


def api(endpoint, params, k):
    url = API + endpoint
    r = subprocess.run(["curl", "-sS", "--fail-with-body", "-u", f"{k}:", "--max-time", "300", "-X", "POST", "--data", urllib.parse.urlencode(params), url],
                       capture_output=True, text=True)
    if r.returncode != 0:                                   # fall back to GET (the form flows/forward_nq.py uses)
        r = subprocess.run(["curl", "-sS", "--fail-with-body", "-u", f"{k}:", "--max-time", "300", url + "?" + urllib.parse.urlencode(params)],
                           capture_output=True, text=True)
    if r.returncode != 0: raise RuntimeError(f"{endpoint}: {(r.stdout or r.stderr).strip()[:300]}")
    return r.stdout


def t0(d): y, m, dd = map(int, d.split("-")); return dt.datetime(y, m, dd, 15, 50, tzinfo=NY)


def win(d, a, b):
    return ((t0(d) + dt.timedelta(milliseconds=a)).astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z",
            (t0(d) + dt.timedelta(milliseconds=b)).astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z")


def parse_ts(s):
    """'2026-10-12T19:50:00.123456789Z' -> (datetime to the microsecond, extra ns)."""
    s = s.rstrip("Z"); base, _, frac = s.partition("."); frac = (frac + "000000000")[:9]
    t = dt.datetime.fromisoformat(base).replace(tzinfo=dt.timezone.utc) + dt.timedelta(microseconds=int(frac[:6]))
    return t, int(frac[6:])


def ms_after(ts, d):
    t, ns = parse_ts(ts); return (t - t0(d)).total_seconds() * 1000 + ns / 1e6


def members():
    last = None; M = {}
    with open(MEMBERS) as fh:
        for r in csv.DictReader(fh):
            if last is None or r["date"] >= last:
                if r["date"] != last: M = {}
                last = r["date"]; M[r["dataset"]] = r["symbols"].split()
    return last, M


def reqs(d, M):
    out = []
    for dsn, sy in M.items():
        a, b = win(d, -500, 5000); out.append(("imb", dsn, dict(dataset=dsn, schema="imbalance", symbols=",".join(sy), stype_in="raw_symbol", start=a, end=b)))
    a, b = win(d, -500, 61000); out.append(("px", "XNAS.ITCH", dict(dataset="XNAS.ITCH", schema="mbp-1", symbols="SPY", stype_in="raw_symbol", start=a, end=b)))
    return out


def parse_imb(txt, d, venue):
    first = {}
    for r in csv.DictReader(txt.splitlines()):
        ms = ms_after(r["ts_recv"], d)
        if ms < 0: continue
        sym = r.get("symbol") or r.get("instrument_id")
        if sym not in first or ms < first[sym][0]:
            first[sym] = (ms, r["side"], float(r["total_imbalance_qty"]), float(r["paired_qty"]), float(r["ref_price"]))
    return [[d, venue[:4], s, round(v[0], 3), v[1], v[2], v[3], v[4]] for s, v in first.items()]


def parse_px(txt, d):
    rows = []
    for r in csv.DictReader(txt.splitlines()):
        try: b, a = float(r["bid_px_00"]), float(r["ask_px_00"])
        except (ValueError, KeyError): continue
        if b > 0 and a > b: rows.append((ms_after(r["ts_recv"], d), b, a))
    rows.sort(); out = {}
    for o in OFF:
        s = [x for x in rows if x[0] <= o]
        if s: out[f"b{o}"], out[f"a{o}"] = s[-1][1], s[-1][2]
    return out


def pending():
    have = set()
    if os.path.exists(FPX): have = {r["date"] for r in csv.DictReader(open(FPX))}
    today_ny = dt.datetime.now(NY).date(); d = START; out = []
    while d < today_ny:
        if d.weekday() < 5 and d.isoformat() not in have: out.append(d.isoformat())
        d += dt.timedelta(days=1)
    return out


def day_cost(d, M, k):
    return sum(float(api("metadata.get_cost", p, k)) for _, _, p in reqs(d, M))


def tick_pull(k, dry=False):
    asof, M = members(); days = pending(); log = open(PULLLOG, "a"); tot = 0.0
    for d in days:
        c = day_cost(d, M, k); tot += c
        log.write(json.dumps(dict(utc=dt.datetime.now(dt.timezone.utc).isoformat(), date=d, est_usd=c, members_asof=asof)) + "\n"); log.flush()
        if dry: continue
        if c > MAXUSD_DAY: print(f"{d}: REFUSED, estimated ${c:.2f} > ${MAXUSD_DAY:.2f}"); continue
        msgs, px = [], {}
        try:
            for kind, dsn, p in reqs(d, M):
                txt = api("timeseries.get_range", dict(p, encoding="csv", pretty_px="true", pretty_ts="true", map_symbols="true"), k)
                if kind == "imb": msgs += parse_imb(txt, d, dsn)
                else: px = parse_px(txt, d)
        except RuntimeError as ex:
            print(f"{d}: {str(ex)[:160]} -- will retry on the next tick"); break
        for path, cols, rows in ((FMSG, MSGCOLS, msgs), (FPX, PXCOLS, [dict(date=d, inst="SPY", **px)])):
            new = not os.path.exists(path)
            with open(path, "a", newline="") as f:
                if cols is MSGCOLS:
                    w = csv.writer(f)
                    if new: w.writerow(cols)
                    w.writerows(rows)
                else:
                    w = csv.DictWriter(f, fieldnames=cols)
                    if new: w.writeheader()
                    w.writerows(rows)
        print(f"{d}: msgs {len(msgs)}, spy quotes {len(px) // 2}, est ${c:.3f}")
    if dry: print(f"pending {len(days)} days, estimated ${tot:.2f} total")


def tick_record():
    byday = first_msgs([HIST_MSG, FMSG]); S, Z = signal_series(byday); PX = read_px([FPX])
    have = {r["date"] for r in csv.DictReader(open(LEDGER))} if os.path.exists(LEDGER) else set()
    fdays = sorted({r["date"] for r in csv.DictReader(open(FPX))}) if os.path.exists(FPX) else []
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"); n = 0; new = not os.path.exists(LEDGER)
    with open(LEDGER, "a", newline="") as f:
        w = csv.writer(f)
        if new: w.writerow(LCOLS)
        for d in fdays:
            if d in have or d < START.isoformat(): continue
            if d not in byday or d not in Z:
                w.writerow([d, "no_auction" if d not in byday else "no_z", "", "", "", "", "", "", "", "", "", "", len(byday.get(d, [])), now, VERSION]); n += 1; continue
            st, s, b0, a0, b1, a1, g, net, mm = trade(Z[d], PX.get((d, "SPY")))
            f6 = lambda x: "" if x is None else f"{x:.6g}"
            w.writerow([d, st, f"{S[d]:.6f}", f"{Z[d]:+.3f}", "" if s is None else s, f6(b0), f6(a0), f6(b1), f6(a1),
                        "" if g is None else f"{g:+.3f}", "" if net is None else f"{net:+.3f}", "" if mm is None else f"{mm:+.3f}",
                        len(byday[d]), now, VERSION]); n += 1
    print(f"ledger rows +{n}")


def status():
    if not os.path.exists(LEDGER): print("no ledger yet"); return
    c = defaultdict(int)
    for r in csv.DictReader(open(LEDGER)): c[r["status"]] += 1
    print("FORWARD_IMB2 rows by status:", dict(c), "(no running mean before the 12-month review, 2027-10)")


def self_test():
    ok = True
    byday = first_msgs([HIST_MSG]); S, Z = signal_series(byday); PX = read_px([HIST_PX])
    nets = [trade(z, PX.get((d, "SPY")))[7] for d, z in Z.items()]; nets = [x for x in nets if x is not None]
    m = sum(nets) / len(nets); sd = math.sqrt(sum((x - m) ** 2 for x in nets) / (len(nets) - 1)); t = m / (sd / math.sqrt(len(nets)))
    e1 = len(nets) == 487 and abs(m - 1.31) < 0.005 and abs(t - 3.15) < 0.005; ok &= e1
    print(f"  [{'PASS' if e1 else 'FAIL'}] reproduces IMB2 primary from the historic files: n {len(nets)}, net {m:+.3f} bp, t {t:+.3f} (want 487, +1.31, 3.15)")
    d = "2026-10-12"
    imb = "ts_recv,ts_event,symbol,side,total_imbalance_qty,paired_qty,ref_price\n" \
          "2026-10-12T19:49:59.900000000Z,x,AAA,B,100,1000,10.0\n2026-10-12T19:50:00.250500000Z,x,AAA,B,200,1000,10.0\n" \
          "2026-10-12T19:50:00.900000000Z,x,BBB,S,50,500,20.0\n"
    rows = parse_imb(imb, d, "XNAS.ITCH")
    e2 = sorted((r[2], r[3]) for r in rows) == [("AAA", 250.5), ("BBB", 900.0)]; ok &= e2
    print(f"  [{'PASS' if e2 else 'FAIL'}] imbalance CSV: first message at/after 15:50:00.000 ET, ms to the nanosecond ({rows})")
    px = "ts_recv,bid_px_00,ask_px_00\n2026-10-12T19:50:00.900000000Z,100.00,100.01\n2026-10-12T19:50:01.100000000Z,100.05,100.06\n" \
         "2026-10-12T19:50:59.000000000Z,100.20,100.21\n"
    q = parse_px(px, d); e3 = q["b1000"] == 100.00 and q["a60000"] == 100.21 and "b-500" not in q; ok &= e3
    print(f"  [{'PASS' if e3 else 'FAIL'}] mbp-1 snapshot: last quote at or before each offset")
    st = trade(1.5, {L_MS: (100.0, 100.01), EXIT_MS: (100.20, 100.21), 0: None})
    e4 = st[0] == "traded" and abs(st[6] - (100.20 / 100.01 - 1) * 1e4) < 1e-9; ok &= e4
    print(f"  [{'PASS' if e4 else 'FAIL'}] long pays the ask, exits at the bid")
    a, b = win("2026-10-12", 1000, 61000); e5 = a == "2026-10-12T19:50:01.000000Z" and b == "2026-10-12T19:51:01.000000Z"; ok &= e5
    print(f"  [{'PASS' if e5 else 'FAIL'}] request windows in UTC (EDT)  ({a})")
    print("ALL PASS" if ok else "FAILURES"); return ok


def main():
    pin(); a = sys.argv[1:]
    if a == ["--self-test"]: sys.exit(0 if self_test() else 1)
    if a == ["--cost"]: tick_pull(key(), dry=True); return
    if a == ["--tick"]: tick_pull(key()); tick_record(); return
    if a == ["--status"]: status(); return
    print(__doc__)


if __name__ == "__main__":
    main()
