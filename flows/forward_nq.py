#!/usr/bin/env python3
"""
forward_nq.py -- FORWARD_NQ: record fastbot v36 rule N on NQ futures, forward only.
Implements flows/PREREGISTRATION_FORWARD_NQ.md and refuses to run if it has changed.
RECORDS ONLY: places no order and touches no broker account. Stdlib + numpy
(through momentum_v36), so it runs under the Mac's plain python3.

    python3 forward_nq.py --self-test   equivalence with vehicle.py on 2026 history (needs pandas)
    python3 forward_nq.py --pull        append NQ 1m bars from Databento (key ~/.databento_key, never printed)
    python3 forward_nq.py --record      write complete sessions to data/forward_nq.csv
    python3 forward_nq.py --tick        --pull then --record (what forward_tick.sh step 7 runs)
    python3 forward_nq.py --status      row counts only (s.2: no mean before the 500th trade-session)
"""
from __future__ import annotations
import argparse, csv, datetime as dt, hashlib, json, os, re, subprocess, sys, urllib.parse
from collections import Counter, defaultdict
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "fastbot", "scripts"))
from momentum_v36 import noise_rows        # noqa: E402  (the v36 rule, unchanged)
sys.path.insert(0, HERE)
import nq_stop_rule as NSR                 # noqa: E402  (FORWARD_NQ_STOP)

VERSION = "1.2"   # 1.1: A1 reports every 50 trade-sessions; 1.2: FORWARD_NQ_STOP ledger (fixed 0.5% stop)
DOC = os.path.join(HERE, "PREREGISTRATION_FORWARD_NQ.md")
PIN = "de80d50c3cb646b4504f8009dd7c39a303548c19a8de39b830e289bafaf3e494"
DOC_A1 = os.path.join(HERE, "PREREGISTRATION_FORWARD_NQ_A1.md")
PIN_A1 = "93296d25990a9d61c58986f53db1675fbf786cee535116ff8ccd91e286e65713"
REPORTS = os.path.join(HERE, "data", "forward_nq_reports")
CFD_LEDGER = os.path.join(os.path.dirname(HERE), "fastbot", "data", "forward_noiseband.csv")
DOC_STOP = os.path.join(HERE, "PREREGISTRATION_FORWARD_NQ_STOP.md")
PIN_STOP = "c7806055efde2fc3361e38ad6db4541e2b508aa65a3fa84eaee158b5edf05b74"
STOP_KIND, STOP_D = "fixed-pct", 0.5
STOP_LEDGER = os.path.join(HERE, "data", "forward_nq_stop.csv")
STOP_COLS = ["date", "trades", "gross_bp", "net_bp", "instrument_id", "status", "recorded_utc", "stops_hit"]
BT_EDGE, BT_SD = 5.8, 65.0      # FLOWS-15 NQ net mean and per-trade-session SD (A1)
NY, UTC = ZoneInfo("America/New_York"), dt.timezone.utc
START = dt.date(2026, 10, 12)
SEED_FROM = "2026-08-01"
TICK, MULT, COMM_USD, MIN_BARS = 0.25, 20.0, 2.50, 70
D = os.path.join(HERE, "data", "forward_nq")
RAW = os.path.join(D, "NQ_1m.csv")
SEED_SRC = os.path.join(HERE, "data", "futures", "NQ_2026.csv")
LEDGER = os.path.join(HERE, "data", "forward_nq.csv")
PULLLOG = os.path.join(D, "pull_log.jsonl")
API = "https://hist.databento.com/v0/"
COLS = ["date", "trades", "gross_bp", "net_bp", "instrument_id", "status", "recorded_utc"]
RAWCOLS = ["ts_event", "instrument_id", "open", "high", "low", "close"]
_FORBIDDEN = re.compile(r"order|execute|submit|position", re.I)
assert not [n for n in list(globals()) if _FORBIDDEN.search(n)]


def check_pin():
    got = hashlib.sha256(open(DOC, "rb").read()).hexdigest()
    if got != PIN:
        sys.exit(f"REFUSING: PREREGISTRATION_FORWARD_NQ.md changed ({got[:16]} != {PIN[:16]})")
    got = hashlib.sha256(open(DOC_A1, "rb").read()).hexdigest()
    if got != PIN_A1:
        sys.exit(f"REFUSING: PREREGISTRATION_FORWARD_NQ_A1.md changed ({got[:16]} != {PIN_A1[:16]})")
    got = hashlib.sha256(open(DOC_STOP, "rb").read()).hexdigest()
    if got != PIN_STOP:
        sys.exit(f"REFUSING: PREREGISTRATION_FORWARD_NQ_STOP.md changed ({got[:16]} != {PIN_STOP[:16]})")


# ------------------------------------------------------------------ bars
def parse_ts(s: str) -> dt.datetime:
    return dt.datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=UTC)


def _mode(vals):
    c = Counter(vals); top = max(c.values())
    return min(v for v, k in c.items() if k == top)            # pandas .mode().iloc[0]: smallest of ties


def build_days(rows):
    """rows: iterable of (ts_utc_str, iid, o, h, l, c). Same construction as
    vehicle.py 1.1 days_from(): RTH minutes 09:30-15:59 ET, 5-minute bars labelled
    by start, bid/ask = price -/+ one tick, sessions with >= 70 bars; per-session
    instrument = mode over the 5-minute bars' modal instrument."""
    buck = defaultdict(list)
    for ts, iid, o, h, l, c in rows:
        e = parse_ts(ts).astimezone(NY)
        t = e.time()
        if not (dt.time(9, 30) <= t < dt.time(16, 0)):
            continue
        k = e.replace(minute=e.minute - e.minute % 5, second=0, tzinfo=None)
        buck[k].append((e, iid, o, h, l, c))
    days, iids = {}, defaultdict(list)
    for k in sorted(buck):
        b = sorted(buck[k], key=lambda x: x[0])
        o, c = b[0][2], b[-1][5]
        hi, lo = max(x[3] for x in b), min(x[4] for x in b)
        days.setdefault(k.date(), {})[k.strftime("%H:%M")] = (o, hi, lo, c, o - TICK, o + TICK, c - TICK, c + TICK)
        iids[k.date()].append(_mode([x[1] for x in b]))
    days = {d: v for d, v in days.items() if len(v) >= MIN_BARS}
    return days, {d: _mode(iids[d]) for d in days}


def drop_rolls(days, iid):
    ds, out, rolled = sorted(days), {}, set()
    for i, d in enumerate(ds):
        if i > 0 and iid[d] != iid[ds[i - 1]]:
            rolled.add(d); continue
        out[d] = days[d]
    return out, rolled


def read_raw(path):
    with open(path) as f:
        r = csv.DictReader(f)
        for x in r:
            yield (x["ts_event"], int(x["instrument_id"]), float(x["open"]), float(x["high"]),
                   float(x["low"]), float(x["close"]))


# ------------------------------------------------------------------ pull
def key():
    k = os.environ.get("DATABENTO_API_KEY", "").strip()
    p = os.path.expanduser("~/.databento_key")
    if not k and os.path.exists(p):
        k = open(p).read().strip()
    if not k:
        sys.exit("no Databento key ($DATABENTO_API_KEY or ~/.databento_key)")
    return k


def api(endpoint, params, k):
    url = API + endpoint + "?" + urllib.parse.urlencode(params)
    r = subprocess.run(["curl", "-sS", "--fail-with-body", "-u", f"{k}:", "--max-time", "300", url],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{endpoint}: {(r.stdout or r.stderr).strip()[:300]}")
    return r.stdout


def seed():
    os.makedirs(D, exist_ok=True)
    if os.path.exists(RAW):
        return
    n = 0
    with open(SEED_SRC) as f, open(RAW, "w", newline="") as g:
        w = csv.writer(g); w.writerow(RAWCOLS)
        for x in csv.DictReader(f):
            if x["ts_event"] >= SEED_FROM:
                w.writerow([x[c] for c in RAWCOLS]); n += 1
    print(f"seeded {n} rows from {os.path.basename(SEED_SRC)} (from {SEED_FROM})")


def last_ts():
    last = None
    with open(RAW) as f:
        for line in f:
            pass
        last = line.split(",")[0]
    return parse_ts(last)


def pull(max_usd=1.0):
    seed()
    k = key()
    rng = json.loads(api("metadata.get_dataset_range", dict(dataset="GLBX.MDP3"), k))
    avail = rng.get("end") or rng.get("schema", {}).get("ohlcv-1m", {}).get("end")
    a = (last_ts() + dt.timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%S")
    b = avail[:19]
    if a >= b:
        print("pull: nothing new"); return 0
    p = dict(dataset="GLBX.MDP3", symbols="NQ.v.0", stype_in="continuous", schema="ohlcv-1m", start=a, end=b)
    cost = float(api("metadata.get_cost", p, k))
    if cost > max_usd:
        sys.exit(f"pull: cost ${cost:.4f} above ${max_usd} -- stopped")
    txt = api("timeseries.get_range", dict(p, encoding="csv", pretty_px="true", pretty_ts="true", map_symbols="true"), k)
    rows = list(csv.DictReader(txt.splitlines()))
    rows = [x for x in rows if x["ts_event"][:19] > last_ts().strftime("%Y-%m-%dT%H:%M:%S")]
    with open(RAW, "a", newline="") as g:
        w = csv.writer(g)
        for x in rows:
            w.writerow([x[c] for c in RAWCOLS])
    with open(PULLLOG, "a") as f:
        f.write(json.dumps(dict(utc=dt.datetime.now(UTC).isoformat(timespec="seconds"), start=a, end=b,
                                rows=len(rows), cost_usd=cost)) + "\n")
    print(f"pull: {len(rows)} new 1m bars {a} .. {b} (${cost:.4f})")
    return 0


# ------------------------------------------------------------------ record
def _write_sessions(path, cols, rth_dates, days, kept, rolled, iid, end, traded_row):
    """One row per complete session from START, written once (base and stop ledgers alike).
    traded_row(d) -> list of the variant's columns between date and instrument_id, or None."""
    have = {r["date"] for r in csv.DictReader(open(path))} if os.path.exists(path) else set()
    extra = len(cols) - 7                                     # stop ledger carries stops_hit
    new, ds = [], sorted(kept)
    now = dt.datetime.now(UTC).isoformat(timespec="seconds")
    blank = [""] * extra
    for d in sorted(rth_dates):
        close_utc = dt.datetime.combine(d, dt.time(16, 5), NY).astimezone(UTC)
        if d < START or d.isoformat() in have or end < close_utc:
            continue
        if d in rolled:
            new.append([d.isoformat(), "", "", "", iid[d], "roll", now] + blank); continue
        if d not in days:
            new.append([d.isoformat(), "", "", "", "", "short session (<70 bars)", now] + blank); continue
        tr = traded_row(d)
        if tr is not None:
            new.append([d.isoformat()] + tr[:3] + [iid[d], "ok", now] + tr[3:]); continue
        i = ds.index(d)
        ok = i > 0 and "09:30" in kept[d] and "15:55" in kept[d] and "15:55" in kept[ds[i - 1]]
        new.append([d.isoformat(), 0 if ok else "", "0.0000" if ok else "", "0.0000" if ok else "", iid[d],
                    "ok" if ok else "not evaluable", now] + (["0"] * extra if ok else blank))
    if new:
        exists = os.path.exists(path)
        with open(path, "a", newline="") as f:
            w = csv.writer(f)
            if not exists:
                w.writerow(cols)
            w.writerows(new)
    return len(new)


def record():
    check_pin()
    raw = list(read_raw(RAW))
    end = parse_ts(raw[-1][0])
    days, iid = build_days(raw)
    rth_dates = {parse_ts(r[0]).astimezone(NY).date() for r in raw
                 if dt.time(9, 30) <= parse_ts(r[0]).astimezone(NY).time() < dt.time(16, 0)}
    kept, rolled = drop_rolls(days, iid)
    # FORWARD_NQ: the rule as registered (unchanged since 1.0)
    traded = {r["date"]: r for r in noise_rows(kept, "NQ")}
    def base_row(d):
        if d not in traded:
            return None
        r = traded[d]
        comm = COMM_USD / (kept[d]["09:30"][0] * MULT) * 1e4 if "09:30" in kept[d] else 0.0
        return [r["n"], f"{r['Ng']:.4f}", f"{r['Nn'] - r['n'] * comm:.4f}"]
    n1 = _write_sessions(LEDGER, COLS, rth_dates, days, kept, rolled, iid, end, base_row)
    # FORWARD_NQ_STOP: the same rule with a fixed 0.5% stop (nq_stop_rule.py)
    trades, _ = NSR.run_variant(kept, STOP_KIND, STOP_D)
    by = defaultdict(list)
    for t in trades:
        by[t["date"]].append(t)
    def stop_row(d):
        if d not in by:
            return None
        x = by[d]
        return [len(x), f"{sum(t['g'] for t in x):.4f}", f"{sum(t['n'] for t in x):.4f}",
                sum(1 for t in x if t["how"] == "stop")]
    n2 = _write_sessions(STOP_LEDGER, STOP_COLS, rth_dates, days, kept, rolled, iid, end, stop_row)
    reports()
    print(f"record: {n1} new base rows, {n2} new stop rows; {status(quiet=True)}")
    return 0


def _pf(vals):
    w = sum(v for v in vals if v > 0); l = -sum(v for v in vals if v <= 0)
    return w / l if l > 0 else float("inf")


def reports():
    """A1 reports for FORWARD_NQ, and the FORWARD_NQ_STOP s.3 reports. Gate nothing."""
    _report_for(LEDGER, "report", "FORWARD_NQ")
    _report_for(STOP_LEDGER, "stop_report", "FORWARD_NQ_STOP (fixed 0.5% stop)", compare=LEDGER)


def _report_for(ledger, prefix, title, compare=None):
    import math, statistics as st
    rows = list(csv.DictReader(open(ledger))) if os.path.exists(ledger) else []
    tr = [r for r in rows if r["trades"] not in ("", "0")]
    os.makedirs(REPORTS, exist_ok=True)
    cfd = {r["date"]: r for r in csv.DictReader(open(CFD_LEDGER))} if os.path.exists(CFD_LEDGER) else {}
    for n in range(50, len(tr) + 1, 50):
        p = os.path.join(REPORTS, f"{prefix}_{n:03d}.md")
        if os.path.exists(p):
            continue
        sub = tr[:n]
        net = [float(r["net_bp"]) for r in sub]; gross = [float(r["gross_bp"]) for r in sub]
        m, sd = st.mean(net), st.stdev(net); se = sd / math.sqrt(n)
        band = 1.96 * BT_SD / math.sqrt(n)
        lo, hi = BT_EDGE - band, BT_EDGE + band
        inside = lo <= m <= hi
        worst = min(sub, key=lambda r: float(r["net_bp"])); best = max(sub, key=lambda r: float(r["net_bp"]))
        pairs = [(float(r["gross_bp"]), float(cfd[r["date"]]["gross_bp"])) for r in sub
                 if r["date"] in cfd and cfd[r["date"]]["gross_bp"] not in ("", None)]
        corr = ""
        if len(pairs) >= 10:
            xs, ys = zip(*pairs)
            try:
                corr = f"{st.correlation(xs, ys):+.2f} over {len(pairs)} shared sessions"
            except Exception:
                corr = "n/a"
        sess = [r for r in rows if r["date"] <= sub[-1]["date"]]
        txt = f"""# {title} progress report {n // 50} — {n} trade-sessions (to {sub[-1]['date']})

*Descriptive only (amendment A1). Gates nothing, stops nothing, changes nothing. Verdict at 500.*

| | value |
|---|---|
| sessions recorded / with a trade | {len(sess)} / {n} |
| mean **net** per trade-session | **{m:+.2f} bp** (t {m / se if se else float('nan'):+.2f}; 95% interval {m - 1.96 * se:+.1f} to {m + 1.96 * se:+.1f}) |
| mean gross | {st.mean(gross):+.2f} bp |
| sum of net, all trade-sessions | {sum(net):+.1f} bp |
| trades per trade-session | {st.mean(int(r['trades']) for r in sub):.2f} |
| worst / best session | {worst['date']} {float(worst['net_bp']):+.1f} bp / {best['date']} {float(best['net_bp']):+.1f} bp |
| same-day gross vs FORWARD_v36 NAS100 CFD | {corr or 'not enough shared sessions yet'} |

**Is it still consistent with the backtest?** If the true edge is +{BT_EDGE} bp, a
mean at this sample size would fall between **{lo:+.1f} and {hi:+.1f} bp** 95% of the time.
If the true edge is 0, it would fall between {-band:+.1f} and {band:+.1f} bp. This mean is
**{'inside' if inside else 'outside'}** the backtest range{' and also inside the zero range' if -band <= m <= band else ''}.
{'At this size the two ranges overlap, so the record cannot yet tell them apart.' if lo < band else ''}

Next report at {n + 50}; interim check at 250; verdict at 500.
"""
        if compare and os.path.exists(compare):
            base = {r["date"]: r for r in csv.DictReader(open(compare))}
            shared = [r for r in rows if r["date"] <= sub[-1]["date"] and r["date"] in base
                      and r["trades"] != "" and base[r["date"]]["trades"] != ""]
            sv = [float(r["net_bp"]) for r in shared if r["trades"] != "0"]
            bv = [float(base[r["date"]]["net_bp"]) for r in shared if base[r["date"]]["trades"] != "0"]
            diff = [float(r["net_bp"]) - float(base[r["date"]]["net_bp"]) for r in shared]
            nstop = sum(int(r["stops_hit"] or 0) for r in sub)
            dm = st.mean(diff) if diff else float("nan")
            dse = st.stdev(diff) / math.sqrt(len(diff)) if len(diff) > 1 else float("nan")
            txt += f"""
## Stop versus no stop, same sessions (S1, descriptive until the base's 500th trade-session)

| | with 0.5% stop | without |
|---|---|---|
| profit factor | {_pf(sv):.3f} | {_pf(bv):.3f} |
| mean net per trade-session | {st.mean(sv) if sv else float('nan'):+.2f} bp | {st.mean(bv) if bv else float('nan'):+.2f} bp |

Stops hit so far: {nstop}. Mean of (stop - no stop) per session: {dm:+.2f} bp (t {dm / dse if dse == dse and dse else float('nan'):+.2f}).
The backtest difference was +0.66 bp a session, with an SD of about 16 bp, so for hundreds of sessions
this number is mostly noise (PREREGISTRATION_FORWARD_NQ_STOP s.2).
"""
        open(p, "w").write(txt)
        print(f"report: wrote {os.path.relpath(p, HERE)}")


def _status_one(ledger, label, quiet):
    rows = list(csv.DictReader(open(ledger))) if os.path.exists(ledger) else []
    ts = sum(1 for r in rows if r["trades"] not in ("", "0"))
    s = f"{label}: {len(rows)} sessions, {ts} trade-sessions (report every 50, interim check at 250, evaluation at 500)"
    if ts >= 250 and not quiet:
        vals = [float(r["net_bp"]) for r in rows if r["trades"] not in ("", "0")]
        if ts >= 500:
            import statistics as st, math
            v = vals[:500]; m = st.mean(v); t = m / (st.stdev(v) / math.sqrt(500))
            s += (f"\n  EVALUATION (first 500): mean net {m:+.2f} bp, t {t:+.2f}; F1 {'PASS' if m > 0 and t >= 1.65 else 'FAIL'};"
                  f" F2 {'PASS' if m >= 2.0 else 'FAIL'}")
        else:
            s += "\n  interim check at 250: " + ("KILL" if sum(vals[:250]) / 250 <= -2.0 else "continue")
    return s, rows, ts


def status(quiet=False):
    s1, base, ts = _status_one(LEDGER, "FORWARD_NQ", quiet)
    s2, stop, _ = _status_one(STOP_LEDGER, "FORWARD_NQ_STOP", quiet)
    s = s1 + "\n" + s2
    rp = sorted(os.listdir(REPORTS)) if os.path.isdir(REPORTS) else []
    if rp and not quiet:
        s += "\nreports: flows/data/forward_nq_reports/ (latest " + ", ".join(sorted(rp)[-2:]) + ")"
    if ts >= 500 and not quiet:                             # FORWARD_NQ_STOP S1, at the base's 500th
        tr = [r for r in base if r["trades"] not in ("", "0")][:500]
        last = tr[-1]["date"]
        sm = {r["date"]: r for r in stop}
        dates = [r["date"] for r in base if r["date"] <= last and r["trades"] != "" and r["date"] in sm
                 and sm[r["date"]]["trades"] != ""]
        bv = [float(r["net_bp"]) for r in base if r["date"] in dates and r["trades"] != "0"]
        sv = [float(sm[d]["net_bp"]) for d in dates if sm[d]["trades"] != "0"]
        import statistics as st
        diff = st.mean(float(sm[d]["net_bp"]) - float(next(r for r in base if r["date"] == d)["net_bp"]) for d in dates)
        s += (f"\nS1 (stop vs no stop, same sessions): PF {_pf(sv):.3f} vs {_pf(bv):.3f} -> S1a {'PASS' if _pf(sv) > _pf(bv) else 'FAIL'};"
              f" mean difference {diff:+.2f} bp -> S1b {'PASS' if diff > 0 else 'FAIL'}")
    if not quiet:
        print(s)
    return s


# ------------------------------------------------------------------ self-test
def self_test():
    """Equivalence with FLOWS-15 on 2026-01..08 NQ history (s.4). Needs pandas (VM)."""
    import pandas as pd
    import vehicle as V
    ok = True
    def check(n, c):
        nonlocal ok; print(f"  {'PASS' if c else 'FAIL'}  {n}"); ok = ok and bool(c)
    raw = list(read_raw(SEED_SRC))
    mine, iid1 = build_days(raw)
    d = pd.read_csv(SEED_SRC, usecols=["ts_event", "instrument_id", "open", "high", "low", "close"])
    d["ts"] = pd.to_datetime(d["ts_event"], utc=True)
    d = d.drop(columns="ts_event").sort_values("ts").drop_duplicates("ts")
    ref, iid2 = V.days_from(d, TICK)
    check(f"same sessions ({len(mine)} vs {len(ref)})", sorted(mine) == sorted(ref))
    same = all(mine[k].keys() == ref[k].keys() and
               all(abs(a - b) < 1e-9 for kk in mine[k] for a, b in zip(mine[k][kk], ref[k][kk])) for k in mine if k in ref)
    check("identical 5-minute bars in every session", same)
    check("identical session instrument ids", all(iid1[k] == iid2[k] for k in iid1 if k in iid2))
    k1, r1 = drop_rolls(mine, iid1); k2, r2 = V.drop_rolls(ref, iid2)
    check(f"same roll sessions dropped ({sorted(r1)})", r2 == len(r1))
    a = noise_rows(k1, "NQ"); b = noise_rows(k2, "NQ")
    check(f"identical v36 trades ({len(a)} trade-sessions)",
          [(r["date"], r["n"], round(r["Ng"], 9)) for r in a] == [(r["date"], r["n"], round(r["Ng"], 9)) for r in b])
    # FORWARD_NQ_STOP s.4: the stop logic on the full 2013-2026 NQ history
    import stops_nq as SN
    full, fid = V.prep("NQ"); full, _ = V.drop_rolls(full, fid)
    _, r0 = NSR.run_variant(full, None, None)
    ref0 = noise_rows(full, "NQ")
    check(f"nq_stop_rule without a stop == momentum_v36.noise_rows ({len(r0)} sessions)",
          len(r0) == len(ref0) and all(x["date"] == y["date"] and x["n"] == y["n"] and abs(x["Nn"] - y["Nn"]) < 1e-9
                                       for x, y in zip(r0, ref0)))
    t5, rows5 = NSR.run_variant(full, STOP_KIND, STOP_D)
    st5 = SN.stats(t5, rows5)
    check(f"fixed 0.5% stop reproduces stops_nq: trades {st5['trades']} (3374), PF {st5['pf']:.3f} (1.275), "
          f"{st5['sess']:+.2f} bp/session (+6.42)",
          st5["trades"] == 3374 and round(st5["pf"], 3) == 1.275 and round(st5["sess"], 2) == 6.42)
    check("no forbidden names", not [n for n in globals() if _FORBIDDEN.search(n)])
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); g = ap.add_mutually_exclusive_group(required=True)
    for f in ("--self-test", "--pull", "--record", "--tick", "--status"):
        g.add_argument(f, action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())
    if a.status:
        status(); sys.exit(0)
    check_pin()
    if a.pull:
        sys.exit(pull())
    if a.record:
        sys.exit(record())
    pull(); sys.exit(record())
