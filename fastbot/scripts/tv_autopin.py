#!/usr/bin/env python3
"""tv_autopin.py -- apply Dave's standing rule for TradingView revisions (2026-11-01: "keep the original number,
lets not change odd data ... keep a flag for the records").

When tv_series.py --convert refuses a pull with VINTAGE CHANGED, run:
    python3 tv_autopin.py <raw.json> --pulled-utc <ISO> [--max-rel 0.01]
For every stored trade date whose close the new pull revises:
  * |revised/stored - 1| <= max-rel (default 1%): add a VINTAGE_PINS.json entry that KEEPS the stored value,
    and log it in data/tv/VINTAGE_REVISIONS.csv with action "kept_original_auto";
  * larger: do NOT pin; log it with action "FLAGGED_large_not_pinned" and exit 2, so a person looks at it.
Every revision ever seen is logged (append-only), so the record of what TradingView changed is never lost.
Then rerun tv_series.py --convert; it will keep the pinned rows and write the new days.

    python3 tv_autopin.py --self-test
I am not a financial adviser. This is a measurement, not a recommendation."""
import argparse, csv, datetime as dt, json, os, shutil, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import tv_series as TV

VERSION = "1.0"
LOG_COLS = ["found_utc", "symbol", "name", "trade_date", "stored_close", "revised_close", "rel_change", "action", "raw_file"]


def scan(raw_path, pulled_utc, out_dir):
    d = json.load(open(raw_path)); sym = d["symbol"]; name = TV.BY_SYMBOL[sym]; kind = TV.SPECS[name][1]
    pulled = dt.datetime.fromisoformat(pulled_utc.replace("Z", "+00:00")).astimezone(TV.NY).replace(tzinfo=None)
    path = os.path.join(out_dir, f"{name}.csv")
    if not os.path.exists(path):
        return sym, name, []
    have = {TV.trade_date(int(r["time"]), kind): float(r["close"]) for r in csv.DictReader(open(path))}
    pins = (json.load(open(os.path.join(out_dir, "VINTAGE_PINS.json"))) if os.path.exists(os.path.join(out_dir, "VINTAGE_PINS.json")) else {}).get(name, {})
    same = lambda a, b: abs(a - b) <= 1e-9 * max(1.0, abs(b))
    out = []
    for b in d["bars"]:
        td = TV.trade_date(b["t"], kind)
        if TV.avail(name, td) > pulled or td not in have or same(have[td], b["c"]):
            continue
        p = pins.get(td.isoformat())
        if p and same(have[td], p["keep"]) and same(b["c"], p["revised"]):
            continue                                       # already pinned with exactly this revision
        out.append((td, have[td], b["c"]))
    return sym, name, out


def apply(raw_path, pulled_utc, out_dir=TV.TV_DIR, max_rel=0.01, now_utc=None):
    now_utc = now_utc or dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    sym, name, revs = scan(raw_path, pulled_utc, out_dir)
    if not revs:
        print(f"  {sym}: no revisions to handle"); return 0
    pins_p = os.path.join(out_dir, "VINTAGE_PINS.json")
    pins = json.load(open(pins_p)) if os.path.exists(pins_p) else {}
    log_p = os.path.join(out_dir, "VINTAGE_REVISIONS.csv"); fresh = not os.path.exists(log_p)
    large = 0
    with open(log_p, "a", newline="") as fh:
        w = csv.writer(fh)
        if fresh: w.writerow(LOG_COLS)
        for td, old, new in sorted(revs):
            rel = (new / old - 1) if old else float("inf")
            if abs(rel) <= max_rel:
                pins.setdefault(name, {})[td.isoformat()] = {"keep": old, "revised": new,
                    "decided": f"{now_utc[:10]} auto: Dave's standing rule (2026-11-01) keep the original value; logged in VINTAGE_REVISIONS.csv"}
                act = "kept_original_auto"; print(f"  AUTO_PINNED {sym} {td} stored {old} revised {new} ({rel * 100:+.4f}%)")
            else:
                act = "FLAGGED_large_not_pinned"; large += 1
                print(f"  LARGE_REVISION {sym} {td} stored {old} revised {new} ({rel * 100:+.2f}%) -- NOT pinned, needs Dave")
            w.writerow([now_utc, sym, name, td.isoformat(), old, new, f"{rel:.6g}", act, os.path.basename(raw_path)])
    json.dump(pins, open(pins_p, "w"), indent=1)
    return 2 if large else 0


def self_test():
    ok = True
    def chk(n, c):
        nonlocal ok; ok &= bool(c); print(f"  [{'PASS' if c else 'FAIL'}] {n}")
    tmp = tempfile.mkdtemp()
    # stored PCC file: two days; a pull revises one by 0.001% and the other by 5%
    t1, t2, t3 = 1792675800, 1792762200, 1793021400              # Thu 2026-10-22, Fri 10-23, Mon 10-26 (09:30 ET bars)
    with open(os.path.join(tmp, "PCC.csv"), "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["time", "open", "high", "low", "close"])
        w.writerow([t1, 1, 1, 1, 0.80000]); w.writerow([t2, 1, 1, 1, 0.84477])
    raw = os.path.join(tmp, "USI_PCC_1D.json")
    json.dump({"symbol": "USI:PCC", "bars": [{"t": t1, "o": 1, "h": 1, "l": 1, "c": 0.84000},
                                             {"t": t2, "o": 1, "h": 1, "l": 1, "c": 0.84476},
                                             {"t": t3, "o": 1, "h": 1, "l": 1, "c": 0.9}]}, open(raw, "w"))
    rc = apply(raw, "2026-11-01T10:00:00Z", tmp, now_utc="2026-11-01T10:00:00+00:00")
    pins = json.load(open(os.path.join(tmp, "VINTAGE_PINS.json")))["PCC"]
    log = list(csv.DictReader(open(os.path.join(tmp, "VINTAGE_REVISIONS.csv"))))
    d1 = TV.trade_date(t1, "index").isoformat(); d2 = TV.trade_date(t2, "index").isoformat()
    chk("a tiny revision is pinned to the ORIGINAL value", pins.get(d2, {}).get("keep") == 0.84477 and pins[d2]["revised"] == 0.84476)
    chk("a 5% revision is NOT pinned and the run exits 2 (flag for a person)", d1 not in pins and rc == 2)
    chk("both are logged for the record", [r["action"] for r in log] == ["FLAGGED_large_not_pinned", "kept_original_auto"])
    # tv_series then keeps the pinned day; the large one still refuses
    try:
        TV.convert(raw, "2026-11-01T10:00:00Z", tmp, "test"); conv = "wrote"
    except SystemExit as e:
        conv = str(e)
    chk("tv_series still refuses while the large revision is unresolved", "VINTAGE CHANGED" in conv)
    rc2 = apply(raw, "2026-11-01T10:00:00Z", tmp, now_utc="2026-11-01T11:00:00+00:00")
    log2 = list(csv.DictReader(open(os.path.join(tmp, "VINTAGE_REVISIONS.csv"))))
    chk("a rerun does not re-pin or re-log the already pinned date", sum(r["trade_date"] == d2 for r in log2) == 1)
    shutil.rmtree(tmp)
    print("ALL PASS" if ok else "FAILURES"); return ok


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("raw", nargs="?"); ap.add_argument("--pulled-utc")
    ap.add_argument("--max-rel", type=float, default=0.01); ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test: sys.exit(0 if self_test() else 1)
    if not (a.raw and a.pulled_utc): sys.exit(__doc__)
    sys.exit(apply(a.raw, a.pulled_utc, max_rel=a.max_rel))
