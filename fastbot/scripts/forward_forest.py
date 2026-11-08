#!/usr/bin/env python3
"""FORWARD v41 -- record the frozen v39 FOREST (model M, data/v41) on SPX500 and
NAS100, forward only. RECORDS ONLY; nothing here places an order.

Runs in the Cowork VM (needs scikit-learn 1.7.2, which the Mac lacks), whenever
Claude and Dave refresh it -- intended monthly. Prices come from the forward job's
M5 pulls (data/v36fwd) merged over the historical files for warm-up.

v1.1 (PREREGISTRATION_v41.1, 2026-10-01, before the first record). Three fixes,
nothing about the model, thresholds, entries, exits or decision rules changes:

  1. PHANTOM CALENDAR ROWS. events.csv / events_v2 / events_v3 carry CPI, NFP
     and CLAIMS rows dated SATURDAY 2026-09-12 (an ALFRED vintage, not a
     release). The forward calendar now drops any release dated on a weekend.
     The tables themselves are not edited (closed results ran on them).
  2. FRESH INPUTS WITHOUT EDITING THE ORIGINALS. v1.0 read the macro inputs in
     place; the VIX file stopped on 2026-08-31 and the VX exports on 2026-08-18
     (whose last row was exported mid-session). And the v41 "refresh" scripts
     could not refresh: fred_fetch_v31.py skips files already on disk and
     sentiment_fetch.py never re-downloads the current year's CFTC zip.
     v1.1 assembles data/v41/inputs/ on every run: each ORIGINAL file, with rows
     dated after its last row appended from a refresh source --
        VIX, VX1/VX2, SKEW   data/tv/ (TradingView connector, tv_series.py)
        AAII, COT, DGS2, DTWEXBGS, GASREGW   data/v41/refresh/ (refresh_v41_inputs.py, Mac)
     and then calls tl_build2.macro_events UNCHANGED on that folder. The VX
     export's last (partial) row is replaced by the settled value.
  3. COMPLETENESS GUARD. A stale file does not show up as a missing feature: the
     "minutes since the last VIX drop" feature silently counts from the last
     drop IN THE FILE. So a session is recorded only once EVERY event-producing
     input has a row available at or after that session's last decision
     (13:45 ET). Sessions that fail are not recorded and not logged as
     no-signal; they wait for the next run and are listed in
     data/forward_forest_deferred.log. (Cboe total put/call is excluded: it
     ended 2019-10-04, so it was constant in all training rows after 2019-12
     and stays constant forward.)

    python3 forward_forest.py --self-test
    python3 forward_forest.py SPX500_USD | NAS100_USD
"""
import csv, datetime as dt, hashlib, json, os, pickle, shutil, sys
from zoneinfo import ZoneInfo
import numpy as np
import tl_build2 as T2, tl_build as T1, tv_series as TV
from reactive import load
from v40_confirm import run_exit

VERSION = "1.2"     # 1.2 (PREREGISTRATION_v41.2): DTWEXBGS stamped at its weekly H.10 release; 1.1.1: no rmtree
START = dt.date(2026, 9, 28)
FREEZE = "../data/v41/freeze_v41.json"
FREEZE_SHA = "7c338b9562f8534c059c78be0bf1f4757b851ab4042f000de835139d8bc37d56"
OUT = "../data/forward_forest.csv"
DEFER = "../data/forward_forest_deferred.log"
COLS = ["instrument", "date", "signal_bar", "side", "p_up", "barrier_bp", "spread_bp",
        "net_E1", "net_E2", "missing_macro", "recorded_utc"]
MACRO = ["vix", "vx_ratio", "skew", "aaii", "cot_z", "y2_chg5", "usd_chg5"]
T2.FORWARD_START = dt.date(2100, 1, 1)
DATA = os.path.abspath("../data")
INPUTS = os.path.join(DATA, "v41/inputs")
REFRESH = os.path.join(DATA, "v41/refresh")
VX_FILES = ("CBOE_DLY_VX1!, 1D_1f2b8.csv", "CBOE_DLY_VX2!, 1D_7782c.csv")
LAST_DECISION = "13:45"


def calendar_forward(here=None):
    """tl_build's calendar reads events_v2.csv, which has no CPI/NFP/claims after
    2026-09. Forward, use events_v3.csv (kept current by the forward job;
    identical to v2 before 2026-09-18) plus weekly jobless claims on every
    Thursday 08:30 ET from 2026-09-18 (the BLS rule; holiday shifts, a few a
    year, are not modelled and are logged here as a known approximation).
    v1.1: rows dated on a weekend are dropped (the 2026-09-12 ALFRED vintage)."""
    ev, sched = [], {k: [] for k in ("CPI", "NFP", "FOMC", "CLAIMS")}
    for r in csv.DictReader(open(os.path.join(DATA, "events_v3.csv"))):
        if r["event"] not in sched:
            continue
        d = dt.date.fromisoformat(r["date"])
        if d.weekday() >= 5:
            continue
        s_ = T2._dt(d, r["time_et"] or ("14:00" if r["event"] == "FOMC" else "08:30"))
        sched[r["event"]].append(s_); ev.append((s_, r["event"]))
        if r["event"] == "FOMC" and r.get("press_conference") == "yes":
            ev.append((s_ + dt.timedelta(minutes=30), "FOMC_PC"))
    have = {t.date() for t in sched["CLAIMS"]}
    d = dt.date(2026, 9, 18)
    while d <= dt.date(2028, 12, 31):
        if d.weekday() == 3 and d not in have:
            s_ = T2._dt(d, "08:30"); sched["CLAIMS"].append(s_); ev.append((s_, "CLAIMS"))
        d += dt.timedelta(days=1)
    return ev, {k: sorted(v) for k, v in sched.items()}


T2.calendar = calendar_forward


# ---- v41.2 (2026-10-04): the broad dollar index (FRED DTWEXBGS, Fed H.10) is published WEEKLY, on the Monday after
# the week it covers (~16:15 ET). tl_build2 1.x stamps each daily value at 18:00 on its own date -- up to a week early.
# The forward recorder now stamps every usd value / usd event at its real release. tl_build2 itself is not edited
# (closed results ran on it). Monday holidays (release on Tuesday) are not modelled -- a known approximation.
def h10_release(d):
    return d + dt.timedelta(days=7 - d.weekday())          # next Monday strictly after d

_T2_macro_events = T2.macro_events
def macro_events_v412(here):
    ev, ser, vix = _T2_macro_events(here)
    re_ = lambda s: T2._dt(h10_release(s.date()), "16:15")
    ser["usd_chg5"] = sorted((re_(s), v) for s, v in ser["usd_chg5"])
    ev = sorted([(re_(s), k) if k in ("usd_up1", "usd_dn1") else (s, k) for s, k in ev], key=lambda q: q[0])
    return ev, ser, vix
T2.macro_events = macro_events_v412


# ------------------------------------------------------------ v1.1 inputs
def _rows(p):
    return list(csv.reader(open(p)))


def _write(p, rows):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", newline="") as fh:
        csv.writer(fh).writerows(rows)


def _aaii_series(path):
    """tl_build's own AAII parse: {survey date: bull - bear}."""
    import xlrd
    wb = xlrd.open_workbook(path); sh = wb.sheet_by_index(0); out = {}
    for i in range(sh.nrows):
        v = sh.row_values(i)
        if isinstance(v[0], float) and v[0] > 30000 and v[1] != "" and v[3] != "":
            out[xlrd.xldate_as_datetime(v[0], wb.datemode).date()] = round((float(v[1]) - float(v[3])) * (100 if float(v[1]) <= 1 else 1), 6)
    return out


def build_inputs(data=DATA, inputs=INPUTS, tv_dir=None, refresh=REFRESH):
    """Assemble <inputs>/data/ from the originals plus refresh rows. Returns a
    manifest {file: {"original_last": ..., "appended": n, "source": ...}}."""
    tv_dir = tv_dir or os.path.join(data, "tv")
    D = os.path.join(inputs, "data")
    # v1.1.1 (2026-10-02, before any record): every assembled file is rewritten in
    # full on each run, so nothing is deleted. The Cowork VM cannot delete files in
    # Dave's folder without a per-session approval, which a scheduled run cannot give.
    for sub in ("", "sentiment", "v31"):
        os.makedirs(os.path.join(D, sub), exist_ok=True)
    os.makedirs(os.path.join(inputs, "scripts"), exist_ok=True)
    man = {}
    have_tv = lambda n: os.path.exists(os.path.join(tv_dir, f"{n}.csv"))
    # VIX (FRED VIXCLS format: date,vix)
    rows = _rows(os.path.join(data, "VIXCLS.csv"))
    last = max(dt.date.fromisoformat(r[0]) for r in rows[1:] if r[1] not in ("", "."))
    add = [[d.isoformat(), repr(v)] for d, v in TV.read("VIX", tv_dir) if d > last] if have_tv("VIX") else []
    _write(os.path.join(D, "VIXCLS.csv"), rows + add)
    man["VIXCLS.csv"] = {"original_last": last.isoformat(), "appended": len(add), "source": "data/tv/VIX.csv"}
    # VX1/VX2 (TradingView export format; the export's LAST row is treated as partial)
    for fn, name in zip(VX_FILES, ("VX1", "VX2")):
        rows = _rows(os.path.join(data, fn))
        body = rows[1:]
        last = TV.trade_date(int(body[-1][0]), "cfe")
        keep = [r for r in body if TV.trade_date(int(r[0]), "cfe") < last]
        add = []
        if have_tv(name):
            for r in _rows(os.path.join(tv_dir, f"{name}.csv"))[1:]:
                if TV.trade_date(int(r[0]), "cfe") >= last:
                    add.append(r)
        if not add:
            keep = body                                   # nothing to replace it with
        _write(os.path.join(D, fn), [rows[0]] + keep + add)
        man[fn] = {"original_last": last.isoformat(), "replaced_partial_last_row": bool(add), "appended": len(add), "source": f"data/tv/{name}.csv"}
    # SKEW (Cboe format: DATE,SKEW mm/dd/YYYY)
    rows = _rows(os.path.join(data, "sentiment/cboe_skew.csv"))
    last = max(dt.datetime.strptime(r[0], "%m/%d/%Y").date() for r in rows[1:])
    add = [[d.strftime("%m/%d/%Y"), f"{v:.6f}"] for d, v in TV.read("SKEW", tv_dir) if d > last] if have_tv("SKEW") else []
    _write(os.path.join(D, "sentiment/cboe_skew.csv"), rows + add)
    man["sentiment/cboe_skew.csv"] = {"original_last": last.isoformat(), "appended": len(add), "source": "data/tv/SKEW.csv"}
    # Cboe total put/call: dead since 2019-10-04, copied as is
    shutil.copy(os.path.join(data, "sentiment/cboe_totalpc.csv"), os.path.join(D, "sentiment/cboe_totalpc.csv"))
    # AAII: the refreshed workbook is used only if it agrees with the original on every shared week
    orig = os.path.join(data, "sentiment/aaii_sentiment.csv")
    new = os.path.join(refresh, "aaii_sentiment.xls")
    use, note = orig, "original"
    if os.path.exists(new):
        a, b = _aaii_series(orig), _aaii_series(new)
        shared = set(a) & set(b)
        bad = [k for k in shared if abs(a[k] - b[k]) > 1e-6]
        if len(shared) > 1000 and not bad and max(b) > max(a):
            use, note = new, f"refreshed ({len(b) - len(shared)} new weeks)"
        else:
            note = f"refresh REJECTED: {len(bad)} of {len(shared)} shared weeks differ"
    shutil.copy(use, os.path.join(D, "sentiment/aaii_sentiment.csv"))
    man["sentiment/aaii_sentiment.csv"] = {"original_last": max(_aaii_series(orig)).isoformat(), "source": note}
    # COT: append refresh rows dated after the original's last report, per (report, instrument)
    rows = _rows(os.path.join(data, "sentiment/cftc_positions.csv"))
    head, body = rows[0], rows[1:]
    lastk = {}
    for r in body:
        k = (r[0], r[1]); lastk[k] = max(lastk.get(k, ""), r[4])
    add = []
    rp = os.path.join(refresh, "cftc_positions.csv")
    if os.path.exists(rp):
        rr = _rows(rp)
        assert rr[0] == head, "refresh cftc header differs"
        add = [r for r in rr[1:] if r[4] > lastk.get((r[0], r[1]), "")]
    _write(os.path.join(D, "sentiment/cftc_positions.csv"), [head] + body + sorted(add, key=lambda r: (r[1], r[4])))
    man["sentiment/cftc_positions.csv"] = {"original_last": lastk.get(("tff", "SPX500_USD")), "appended": len(add), "source": "data/v41/refresh/cftc_positions.csv"}
    # FRED (date,value)
    for s in ("DGS2", "DTWEXBGS", "GASREGW"):
        rows = _rows(os.path.join(data, f"v31/{s}.csv"))
        last = max(r[0] for r in rows[1:])
        add = []
        rp = os.path.join(refresh, f"{s}.csv")
        if os.path.exists(rp):
            add = [r for r in _rows(rp)[1:] if r[0] > last]
        _write(os.path.join(D, f"v31/{s}.csv"), rows + add)
        man[f"v31/{s}.csv"] = {"original_last": last, "appended": len(add), "source": f"data/v41/refresh/{s}.csv"}
    return man


def coverage(inputs=INPUTS):
    """{input: ET-naive datetime at which its LAST row became available}, using
    tl_build2's own stamping rules."""
    D = os.path.join(inputs, "data")
    c = {}
    vix = [r for r in _rows(os.path.join(D, "VIXCLS.csv"))[1:] if r[1] not in ("", ".")]
    c["VIX"] = T2._dt(dt.date.fromisoformat(vix[-1][0]), "16:15")
    for fn, n in zip(VX_FILES, ("VX1", "VX2")):
        c[n] = T2._dt(TV.trade_date(int(_rows(os.path.join(D, fn))[-1][0]), "cfe"), "16:15")
    c["SKEW"] = T2._dt(dt.datetime.strptime(_rows(os.path.join(D, "sentiment/cboe_skew.csv"))[-1][0], "%m/%d/%Y").date(), "16:15")
    c["AAII"] = T2._dt(max(_aaii_series(os.path.join(D, "sentiment/aaii_sentiment.csv"))) + dt.timedelta(days=1), "00:00")
    cot = max(r[4] for r in _rows(os.path.join(D, "sentiment/cftc_positions.csv"))[1:] if r[1] == "SPX500_USD" and r[0] == "tff")
    c["COT"] = T2._dt(dt.date.fromisoformat(cot) + dt.timedelta(days=3), "15:30")
    for s, hm, lag in (("DGS2", "18:00", 0), ("DTWEXBGS", "18:00", 0), ("GASREGW", "00:00", 1)):
        last = max(r[0] for r in _rows(os.path.join(D, f"v31/{s}.csv"))[1:])
        c[s] = T2._dt(dt.date.fromisoformat(last) + dt.timedelta(days=lag), hm)
    c["DTWEXBGS"] = T2._dt(h10_release(dt.date.fromisoformat(max(r[0] for r in _rows(os.path.join(D, "v31/DTWEXBGS.csv"))[1:]))), "16:15")   # v41.2
    return c


def short_inputs(d, cov):
    need = T2._dt(d, LAST_DECISION)
    return sorted(k for k, v in cov.items() if v < need)


# ------------------------------------------------------------ recorder
def frozen():
    if hashlib.sha256(open(FREEZE, "rb").read()).hexdigest() != FREEZE_SHA:
        sys.exit("freeze_v41.json changed -- refused")
    fz = json.load(open(FREEZE))
    blob = open("../data/v41/forest_v41.pkl", "rb").read()
    if hashlib.sha256(blob).hexdigest() != fz["model_sha256"]:
        sys.exit("model file changed -- refused")
    return fz, pickle.loads(blob)


def merged_days(stem):
    days = load("../data", stem)
    if os.path.exists(f"../data/v36fwd/{stem}_bid_5m.csv"):
        days.update(load("../data/v36fwd", stem))
    return days


def run(ins, today):
    fz, M = frozen()
    man = build_inputs()
    print(f"forward_forest v{VERSION}  inputs assembled: " +
          ", ".join(f"{k.split('/')[-1]} +{v.get('appended', 0)}" for k, v in man.items()))
    cov = coverage()
    stem = ins.replace("_", "").lower()
    days = merged_days(stem)
    rows, feats, _ = T2.build("../data", os.path.join(INPUTS, "scripts"), days=days, verbose=False)
    names = [f"ms_{e}" for e in T1.EVENTS] + [f"n60_{e}" for e in T1.INTRADAY] + T1.STATES
    have = set()
    if os.path.exists(OUT):
        have = {(r["instrument"], r["date"]) for r in csv.DictReader(open(OUT))}
    lo, hi = fz["thresholds"][ins]["lo"], fz["thresholds"][ins]["hi"]
    cand = sorted({r["date"] for r in rows if START <= r["date"] < today and (ins, r["date"].isoformat()) not in have})
    deferred = {d: short_inputs(d, cov) for d in cand if short_inputs(d, cov)}
    if deferred:
        now_ = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with open(DEFER, "a") as fh:
            for d, s in sorted(deferred.items()):
                fh.write(f"{now_} {ins} {d} deferred, inputs not yet past {LAST_DECISION} ET that day: {' '.join(s)}\n")
        print(f"{ins}: {len(deferred)} session(s) deferred for stale inputs: "
              + "; ".join(f"{d} ({' '.join(s)})" for d, s in sorted(deferred.items())))
    ok_days = set(cand) - set(deferred)
    idx = [i for i, r in enumerate(rows) if r["date"] in ok_days]
    if not idx:
        print(f"{ins}: no new complete sessions"); return 0
    X = np.array([[np.nan if feats[i].get(n) is None else feats[i][n] for n in names] for i in idx], np.float32)
    p = M.predict_proba(X)[:, 1]
    new, done = [], set()
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for k, i in enumerate(idx):
        r = rows[i]; d = r["date"]
        side = 1 if p[k] >= hi else (-1 if p[k] <= lo else 0)
        if side == 0 or d in done:
            continue
        bars = days[d]; ks = sorted(bars); j = ks.index(r["hm"])
        after = [bars[x] for x in ks[j + 1:]]
        if len(after) < 24:
            continue
        e = after[0][0]
        path = np.array([((b[1] / e - 1) * 1e4, (b[2] / e - 1) * 1e4, (b[3] / e - 1) * 1e4) for b in after], np.float32)
        miss = sum(feats[i].get(m) is None for m in MACRO)
        new.append([ins, d.isoformat(), r["hm"], side, f"{p[k]:.5f}", f"{r['b_bp']:.2f}", f"{r['spread']:.3f}",
                    f"{run_exit(path, r['b_bp'], side, 'E1') - r['spread']:.3f}",
                    f"{run_exit(path, r['b_bp'], side, 'E2') - r['spread']:.3f}", miss, now])
        done.add(d)
    # sessions with no signal are recorded too, so the log proves they were looked at
    for i in idx:
        d = rows[i]["date"]
        if d not in done:
            done.add(d); new.append([ins, d.isoformat(), "", 0, "", "", "", "", "", "", now])
    fresh = not os.path.exists(OUT)
    with open(OUT, "a", newline="") as fh:
        w = csv.writer(fh)
        if fresh: w.writerow(COLS)
        w.writerows(sorted(new, key=lambda x: x[1]))
    print(f"{ins}: {len(done)} new session(s), {sum(1 for x in new if x[3] != 0)} trade(s)")
    return len(new)


def self_test():
    ok = True
    def check(n, c):
        nonlocal ok; ok &= bool(c); print(f"  [{'PASS' if c else 'FAIL'}] {n}")
    print(f"forward_forest.py v{VERSION} self-test\n")
    fz, M = frozen()
    S = dict(np.load("../data/timeline_v37/matrix.npz"))
    chk = M.predict_proba(S["X"][:2000])[:, 1]
    check("the model reproduces its frozen check predictions exactly",
          hashlib.sha256(np.round(chk, 10).tobytes()).hexdigest() == fz["check_pred_sha256"])
    check("START is frozen at 2026-09-28", START == dt.date(2026, 9, 28))
    check("thresholds present for both instruments", set(fz["thresholds"]) == {"SPX500_USD", "NAS100_USD"})
    check("the builder's forward cut-off is lifted (forward days are built)", T2.FORWARD_START.year == 2100)
    ev, sch = calendar_forward()
    check("forward calendar has claims every Thursday and future CPI/NFP",
          any(t.date() == dt.date(2026, 10, 1) for t in sch["CLAIMS"]) and max(sch["CPI"]).date() > dt.date(2026, 9, 26))
    check("v1.1: no release in the forward calendar falls on a weekend (2026-09-12 dropped)",
          all(t.weekday() < 5 for v in sch.values() for t in v)
          and dt.date(2026, 9, 12) not in {t.date() for v in sch.values() for t in v})
    old = T1.calendar(os.getcwd())[1]
    wk = lambda L: [t for t in L if t.date() < dt.date(2026, 9, 18) and t.weekday() < 5]
    check("forward calendar is identical to v2 before 2026-09-18, weekend rows aside",
          all(wk(sch[k]) == wk(old[k]) for k in sch))
    # v1.1 inputs: the assembled folder reproduces the ORIGINAL macro history exactly
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        man = build_inputs(inputs=td)
        here_new = os.path.join(td, "scripts")
        ev0, ser0, vix0 = T2.macro_events(os.getcwd())
        ev1, ser1, vix1 = T2.macro_events(here_new)
        cut = dt.datetime(2026, 8, 17)                    # before the VX export's partial last row
        check("assembled inputs reproduce every original macro event before 2026-08-17",
              [x for x in ev0 if x[0] < cut] == [x for x in ev1 if x[0] < cut])
        check("... and every original state value before 2026-08-17",
              all([x for x in ser0[k] if x[0] < cut] == [x for x in ser1[k] if x[0] < cut] for k in ser0))
        drops = {x[0].date() for x in ev1 if x[1] == "vix_drop"}
        check("the two VIX drops the stale file missed (2026-09-11, 2026-09-17) are now events",
              {dt.date(2026, 9, 11), dt.date(2026, 9, 17)} <= drops)
        vr = dict((k.date(), v) for k, v in ser1["vx_ratio"])
        check("the VX export's partial 2026-08-18 row is replaced by the settled values (18.1906 / 19.7247)",
              abs(vr[dt.date(2026, 8, 18)] - 18.1906 / 19.7247) < 1e-9)
        cov = coverage(td)
        d0 = dt.date(2026, 9, 28)
        planted = dict(cov); planted["AAII"] = T2._dt(dt.date(2026, 9, 24), "00:00")
        check("PLANTED: a session after an input's last row is deferred, naming that input",
              short_inputs(d0, planted) == ["AAII"] or "AAII" in short_inputs(d0, planted))
        check("a session before every input's last row is not deferred",
              short_inputs(dt.date(2026, 8, 3), cov) == [])
        print("    coverage now: " + ", ".join(f"{k} {v:%Y-%m-%d %H:%M}" for k, v in sorted(cov.items())))
    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        sys.exit(self_test())
    today = dt.datetime.now(ZoneInfo("America/New_York")).date()
    run(sys.argv[1], today)
