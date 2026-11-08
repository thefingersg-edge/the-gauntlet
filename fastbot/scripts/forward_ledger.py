#!/usr/bin/env python3
"""The forward-test ledger. PREREGISTRATION_v25, amended by v25.1.

Records the plain release fade (variant A) forward, on six instruments,
with real bid and ask. IT DOES NOT TRADE. Nothing here places an order.

    python3 forward_ledger.py --self-test
    python3 forward_ledger.py                 # append any new events
    python3 forward_ledger.py --status        # what is recorded, what is next

WHAT MAKES THIS DIFFERENT FROM A BACKTEST
-----------------------------------------
v25 section 7: **history is never recomputed.** A ledger you can rebuild
is a ledger you can quietly improve, so this one only ever APPENDS, and
every row carries the code version that wrote it. A bug fix applies
forward; the old rows stay and are marked. That is the whole discipline
and it is enforced in code below, not by intention.

WHY THE TRADE MATHS IS LOCAL RATHER THAN IMPORTED
-------------------------------------------------
This job runs unattended for years. Importing cont_bp from
premarket_event.py would guarantee the two can never drift, but it would
also mean a sibling file moving breaks the record. So the maths is
defined here, planted with the same cases, AND cross-checked against
premarket_event when that module happens to be importable -- independent
in operation, tied together whenever anyone looks.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import os
import statistics as st
import sys
from zoneinfo import ZoneInfo

VERSION = "1.1"   # 1.1 (PREREGISTRATION_v25.2): an event is due only after its exit bar has closed, in New York time

ET = ZoneInfo("America/New_York")
UTC = dt.timezone.utc
BAR = dt.timedelta(minutes=15)

#: ---- FROZEN IN v25 ----
#: PREREGISTRATION_v25 was written 2026-09-18. A FORWARD test records
#: from its own registration and not one day before. Without this the
#: first run walks the calendar back to 1994 and backfills ~4,800
#: historical rows into a ledger whose entire claim is that nothing in
#: it was computed with hindsight. The backfill would even look
#: plausible -- which is what makes it worth a constant and a test.
START_DATE = dt.date(2026, 9, 18)
SLOT = (8, 30)                       # section 2
RELEASES = ("CPI", "NFP")            # section 2 -- claims excluded
ENTRY_OFF, EXIT_OFF = 1, 5           # section 2: in at 08:45, out at 09:45
INSTRUMENTS = ("SPX500_USD", "NAS100_USD", "US30_USD",
               "DE30_EUR", "EUR_USD", "XAU_USD")          # section 3
MIN_FUTURE_EVENTS = 2                # v25.1 section 2 -- the hard abort
RUNWAY_WARN_DAYS = 90                # v25.1 section 2 -- a prompt, not a halt
QUIET_PIPELINE_DAYS = 7              # v25 section 6
FAST_ARM_AT = 60                     # v25 section 8
COST_FLAG_RATIO = 1.5                # v25 section 8
#: the backtest's assumption, per RESULT_PREMARKET section 1 as corrected
ASSUMED_COST_BP = 1.83

#: v25.2 -- an event is DUE only once its 09:45 ET exit bar has closed (10:00 ET)
#: plus a margin for OANDA to publish the completed candle. Before v25.2 the
#: ledger used the Mac's local calendar date, so the first tick of an event day
#: (00:52 London) wrote every instrument as bars_present=no before the release.
DUE_AFTER_ET = dt.time(10, 30)


def due(events, now_et):
    """Event dates from START_DATE whose exit bar has closed by now_et (aware, ET)."""
    now_et = now_et.astimezone(ET)
    return sorted(d for d in events
                  if START_DATE <= d and now_et >= dt.datetime.combine(d, DUE_AFTER_ET, ET))


HEADER = ["date", "instrument", "release", "signal_open", "signal_close",
          "direction", "entry_bid", "entry_ask", "exit_bid", "exit_ask",
          "mid_gross_bp", "net_bp", "spread_entry_bp", "spread_exit_bp",
          "bars_present", "written_at", "code_version"]


def stem(instrument):
    return instrument.replace("_", "").lower()


def fade(sig_open, sig_close, entry_bid, entry_ask, exit_bid, exit_ask):
    """(direction, mid_gross_bp, net_bp) for one fade, or None on a doji.

    direction +1 is LONG the fade (the signal bar fell), -1 is SHORT.
    net takes the side actually dealt, and the short leg's return is on
    the ENTRY notional -- (Pe - Px)/Pe. Writing that as Pe/Px - 1 divides
    by the wrong price and leaves a residue that is invisible at 10 bp
    and wrong in every row. It cost a correction to RESULT_PREMARKET.
    """
    if sig_close == sig_open:
        return None
    d = 1 if sig_close < sig_open else -1
    me = (entry_bid + entry_ask) / 2.0
    mx = (exit_bid + exit_ask) / 2.0
    if me <= 0 or mx <= 0:
        return None
    gross = d * (mx / me - 1.0) * 1e4
    if d == 1:                       # long: in at ask, out at bid
        net = (exit_bid / entry_ask - 1.0) * 1e4
    else:                            # short: in at bid, out at ask
        net = (1.0 - exit_ask / entry_bid) * 1e4
    return d, gross, net


def read_side(path, keep_dates=None):
    """{utc datetime -> (o,h,l,c)}. keep_dates narrows to the ET dates we
    actually need, because these files run to half a million rows and a
    decade-long job should not hold all of them."""
    out = {}
    with open(path) as fh:
        for r in csv.DictReader(fh):
            t = dt.datetime.fromisoformat(r["time"]).replace(tzinfo=UTC)
            if keep_dates is not None and t.astimezone(ET).date() not in keep_dates:
                continue
            out[t] = (float(r["open"]), float(r["high"]),
                      float(r["low"]), float(r["close"]))
    return out


def load_events(path):
    """{date -> set(release)} for CPI/NFP landing in the 08:30 bar."""
    out = {}
    if not os.path.exists(path):
        return out
    for r in csv.DictReader(open(path)):
        if r["event"] not in RELEASES:
            continue
        if not r.get("time_et") or r.get("time_quality") == "UNCERTAIN":
            continue
        hh, mm = (int(x) for x in r["time_et"].split(":"))
        if (hh, (mm // 15) * 15) != SLOT:
            continue
        out.setdefault(dt.date.fromisoformat(r["date"]), set()).add(r["event"])
    return out


def load_ledger(path):
    if not os.path.exists(path):
        return []
    return list(csv.DictReader(open(path)))


def already(rows):
    return {(r["date"], r["instrument"]) for r in rows}


def runway(events, today):
    fut = sorted(d for d in events if d > today)
    return fut, ((fut[-1] - today).days if fut else 0)


def self_test():
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        if not isinstance(cond, (bool, int)):
            raise TypeError(f"check({name!r}) got {type(cond).__name__}")
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}"
              + (f"   {detail}" if detail else ""))

    print(f"forward_ledger.py v{VERSION} self-test\n")

    print("the fade is signed the way v25 section 2 fixed it")
    #: signal bar ROSE -> short. price then falls -> the fader is paid.
    d, g, n = fade(100.0, 101.0, 101.0, 101.0, 100.0, 100.0)
    check("an UP signal bar is faded SHORT", d == -1)
    check("and a fall after it PAYS", g > 0, f"{g:+.1f} bp gross")
    #: signal bar FELL -> long. price then falls further -> the fader loses.
    d2, g2, _ = fade(100.0, 99.0, 99.0, 99.0, 98.0, 98.0)
    check("a DOWN signal bar is faded LONG", d2 == 1)
    check("and a further fall LOSES", g2 < 0, f"{g2:+.1f} bp")
    check("a doji is not a trade", fade(100.0, 100.0, 1.0, 1.0, 1.0, 1.0) is None)

    print("\ncost is real, and zero only when the spread is zero")
    _, g3, n3 = fade(100.0, 101.0, 100.9, 101.1, 99.9, 100.1)
    check("net is worse than gross when a spread exists", n3 < g3,
          f"gross {g3:+.2f}  net {n3:+.2f}  cost {g3 - n3:.2f} bp")
    _, g4, n4 = fade(100.0, 101.0, 101.0, 101.0, 100.0, 100.0)
    #: PLANTED: the bug that cost RESULT_PREMARKET a correction. With bid
    #: equal to ask the cost must be EXACTLY zero on both legs.
    check("with bid == ask the SHORT leg costs exactly zero",
          abs(g4 - n4) < 1e-9, f"{abs(g4 - n4):.2e}")
    _, g5, n5 = fade(100.0, 99.0, 99.0, 99.0, 100.0, 100.0)
    check("and so does the LONG leg", abs(g5 - n5) < 1e-9)

    print("\nand it agrees with premarket_event, when that is importable")
    try:
        from premarket_event import cont_bp
        d6, g6, _ = fade(100.0, 101.0, 101.0, 101.0, 102.0, 102.0)
        c6 = cont_bp(100.0, 101.0, 101.0, 102.0)
        check("fade gross is exactly minus cont_bp", abs(g6 + c6) < 1e-9,
              f"fade {g6:+.2f}  cont {c6:+.2f}")
    except ImportError:
        check("premarket_event not importable -- cross-check skipped", True,
              "the maths is local by design; this is a tie, not a dependency")

    print("\nthe ledger APPENDS and never recomputes (v25 section 7)")
    rows = [{"date": "2026-10-02", "instrument": "SPX500_USD"},
            {"date": "2026-10-02", "instrument": "EUR_USD"}]
    seen = already(rows)
    check("a recorded (date, instrument) is recognised",
          ("2026-10-02", "SPX500_USD") in seen)
    #: PLANTED: the same date on a DIFFERENT instrument is a new record,
    #: not a duplicate. Keying on date alone would silently record one
    #: instrument and call the event done.
    check("the same date on another instrument is NOT a duplicate",
          ("2026-10-02", "NAS100_USD") not in seen)
    check("every row carries the code version that wrote it",
          "code_version" in HEADER,
          "v25 s7: a fix applies forward and old rows stay MARKED")
    check("and bars_present is a column, so a skip is recorded",
          "bars_present" in HEADER,
          "an event that vanishes is indistinguishable from one that lost")

    print("\nthe aborts are v25.1's, not v25's")
    today = dt.date(2026, 9, 19)
    ev = {dt.date(2026, 10, 2): {"NFP"}, dt.date(2026, 12, 10): {"CPI"}}
    fut, days = runway(ev, today)
    check("two future events is enough to run", len(fut) >= MIN_FUTURE_EVENTS)
    check("runway is measured to the LAST known event", days == 82, f"{days}")
    #: PLANTED: 82 days is below the 90-day PROMPT but above the abort.
    #: v25's original hard floor would have halted the test on day zero.
    check("82 days warns but does NOT halt",
          days < RUNWAY_WARN_DAYS and len(fut) >= MIN_FUTURE_EVENTS,
          "v25.1 section 2 -- the floor was unsatisfiable")
    one, _ = runway({dt.date(2026, 10, 2): {"NFP"}}, today)
    check("ONE future event DOES halt", len(one) < MIN_FUTURE_EVENTS,
          "the second is what says the calendar has not ended behind it")
    check("a past-only calendar halts",
          len(runway({dt.date(2020, 1, 1): {"CPI"}}, today)[0]) == 0)

    print("\nthe ledger starts at the REGISTRATION, not at the data")
    #: PLANTED: the calendar reaches back to 1994. A forward test that
    #: silently backfills is a backtest with a better name.
    cal = {dt.date(2015, 6, 10): {"CPI"}, dt.date(2026, 9, 18): {"NFP"},
           dt.date(2026, 10, 2): {"NFP"}}
    now = dt.date(2026, 9, 19)
    rec = sorted(d for d in cal if START_DATE <= d <= now)
    check("a 2015 event is NOT recorded", dt.date(2015, 6, 10) not in rec)
    check("an event on the registration date IS recorded",
          dt.date(2026, 9, 18) in rec)
    check("and a future one waits its turn",
          dt.date(2026, 10, 2) not in rec, "it has not happened yet")
    check("the start date is v25's own registration date",
          START_DATE == dt.date(2026, 9, 18))

    print("\nv25.2: an event is due only after its exit bar has closed")
    #: PLANTED: the 2026-10-02 failure. 23:52 UTC on 1 Oct is 00:52 in London
    #: (already 2 Oct there) and 19:52 on 1 Oct in New York.
    nfp = {dt.date(2026, 10, 2): {"NFP"}}
    at = lambda y, mo, d, h, mi: dt.datetime(y, mo, d, h, mi, tzinfo=UTC)
    check("the 23:52 UTC tick the night before does NOT record the event",
          due(nfp, at(2026, 10, 1, 23, 52)) == [])
    check("the 05:53 UTC tick on the day (01:53 ET) does NOT record it",
          due(nfp, at(2026, 10, 2, 5, 53)) == [])
    check("the 11:53 UTC tick (07:53 ET, before the release) does NOT record it",
          due(nfp, at(2026, 10, 2, 11, 53)) == [])
    check("10:29 ET is still too early; 10:30 ET is due",
          due(nfp, dt.datetime(2026, 10, 2, 10, 29, tzinfo=ET)) == []
          and due(nfp, dt.datetime(2026, 10, 2, 10, 30, tzinfo=ET)) == [dt.date(2026, 10, 2)])
    check("the 17:53 UTC tick (13:53 ET) DOES record it",
          due(nfp, at(2026, 10, 2, 17, 53)) == [dt.date(2026, 10, 2)])
    check("winter time: 14:30 UTC on a January CPI day is 09:30 ET, NOT due",
          due({dt.date(2027, 1, 13): {"CPI"}}, at(2027, 1, 13, 14, 30)) == [])
    check("and events before START_DATE are still never due",
          due({dt.date(2015, 6, 10): {"CPI"}}, at(2026, 10, 2, 17, 53)) == [])

    print("\nthe spec's constants are the spec's")
    check("entry 08:45, exit 09:45 -- four bars held",
          (ENTRY_OFF, EXIT_OFF) == (1, 5) and EXIT_OFF - ENTRY_OFF == 4)
    check("six instruments", len(INSTRUMENTS) == 6)
    check("CPI and payrolls only", RELEASES == ("CPI", "NFP"))
    check("the fast arm fires at 60 records", FAST_ARM_AT == 60)

    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def find_files(dirs, ins):
    for d in dirs:
        b = os.path.join(d, f"{stem(ins)}_bid_15m.csv")
        a = os.path.join(d, f"{stem(ins)}_ask_15m.csv")
        if os.path.exists(b) and os.path.exists(a):
            return b, a
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", default="../data/events_v3.csv")
    ap.add_argument("--ledger", default="../data/forward_ledger.csv")
    ap.add_argument("--data-dirs", default="../data/v24,../data")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())

    print(f"forward_ledger.py v{VERSION}   PREREGISTRATION_v25 / v25.1\n")
    print("  This RECORDS. It does not trade, and places no order.\n")
    dirs = [x.strip() for x in a.data_dirs.split(",") if x.strip()]
    now_et = dt.datetime.now(ET)
    today = now_et.date()          # v25.2: New York date, never the Mac's local date

    events = load_events(a.events)
    if not events:
        raise SystemExit(f"  no CPI/NFP events in {a.events}")
    fut, days = runway(events, today)
    rows = load_ledger(a.ledger)
    seen = already(rows)
    print(f"  calendar {len(events)} events, last {max(events)}   "
          f"future {len(fut)}   runway {days} days")
    print(f"  ledger   {len(rows)} rows"
          + (f", last written {max(r['written_at'] for r in rows)[:10]}"
             if rows else ", empty"))

    if len(fut) < MIN_FUTURE_EVENTS:
        print(f"\n  HALT -- only {len(fut)} future release(s) known. "
              f"v25.1 section 2 requires {MIN_FUTURE_EVENTS}.")
        print(f"  Run calendar_forward.py. The test does not run blind.")
        sys.exit(2)
    if days < RUNWAY_WARN_DAYS:
        print(f"  NOTE: {days} days of runway, under the "
              f"{RUNWAY_WARN_DAYS}-day prompt. Refresh the calendar soon.")

    if a.status:
        if not rows:
            print(f"\n  nothing recorded yet. Next release: {fut[0]}")
            sys.exit(0)
        print(f"\n  RECORDED, by instrument")
        by = {}
        for r in rows:
            by.setdefault(r["instrument"], []).append(r)
        print(f"    {'instrument':<12}{'n':>5}{'gross':>9}{'net':>9}"
              f"{'cost':>8}{'assumed':>9}")
        for ins in INSTRUMENTS:
            v = [r for r in by.get(ins, []) if r["bars_present"] == "yes"]
            if not v:
                continue
            g = [float(r["mid_gross_bp"]) for r in v]
            n = [float(r["net_bp"]) for r in v]
            c = st.mean(x - y for x, y in zip(g, n))
            flag = "  <- OVER" if c > ASSUMED_COST_BP * COST_FLAG_RATIO else ""
            print(f"    {ins:<12}{len(v):>5}{st.mean(g):>+9.2f}"
                  f"{st.mean(n):>+9.2f}{c:>8.2f}{ASSUMED_COST_BP:>9.2f}{flag}")
        done = sum(1 for r in rows if r["bars_present"] == "yes")
        print(f"\n  {done} complete records."
              + (f" v25 section 8's fast arm reports from {FAST_ARM_AT}."
                 if done < FAST_ARM_AT else
                 " v25 section 8's fast arm is live -- see the cost column."))
        print(f"  Next release: {fut[0]}")
        sys.exit(0)

    want = due(events, now_et)
    old = sum(1 for d in events if d < START_DATE)
    print(f"  {old} pre-registration event(s) in the calendar, "
          f"correctly NOT recorded")
    need = {d for d in want if any((d.isoformat(), i) not in seen
                                   for i in INSTRUMENTS)}
    if not need:
        print(f"\n  nothing new. Next release: {fut[0]}")
        sys.exit(0)
    print(f"\n  {len(need)} event date(s) not yet fully recorded\n")

    out = []
    for ins in INSTRUMENTS:
        pb, pa = find_files(dirs, ins)
        if not pb:
            print(f"  {ins:<12} NO DATA in {dirs} -- skipped, not recorded")
            continue
        bid, ask = read_side(pb, need), read_side(pa, need)
        slot = {}
        for t in bid.keys() & ask.keys():
            e = t.astimezone(ET)
            if (e.hour, e.minute) == SLOT:
                slot[e.date()] = t
        added = 0
        for d in sorted(need):
            if (d.isoformat(), ins) in seen:
                continue
            t = slot.get(d)
            te = t + BAR * ENTRY_OFF if t else None
            tx = t + BAR * EXIT_OFF if t else None
            have = bool(t) and te in bid and te in ask and tx in bid and tx in ask
            row = dict.fromkeys(HEADER, "")
            row.update(date=d.isoformat(), instrument=ins,
                       release="+".join(sorted(events[d])),
                       bars_present="yes" if have else "no",
                       written_at=dt.datetime.now(UTC).isoformat(timespec="seconds"),
                       code_version=VERSION)
            if have:
                so = (bid[t][0] + ask[t][0]) / 2.0
                sc = (bid[t][3] + ask[t][3]) / 2.0
                r = fade(so, sc, bid[te][0], ask[te][0], bid[tx][0], ask[tx][0])
                if r is None:
                    row["bars_present"] = "doji"
                else:
                    d_, g, n = r
                    me = (bid[te][0] + ask[te][0]) / 2.0
                    mx = (bid[tx][0] + ask[tx][0]) / 2.0
                    row.update(signal_open=f"{so:.5f}", signal_close=f"{sc:.5f}",
                               direction=d_, entry_bid=f"{bid[te][0]:.5f}",
                               entry_ask=f"{ask[te][0]:.5f}",
                               exit_bid=f"{bid[tx][0]:.5f}",
                               exit_ask=f"{ask[tx][0]:.5f}",
                               mid_gross_bp=f"{g:.4f}", net_bp=f"{n:.4f}",
                               spread_entry_bp=f"{(ask[te][0]-bid[te][0])/me*1e4:.4f}",
                               spread_exit_bp=f"{(ask[tx][0]-bid[tx][0])/mx*1e4:.4f}")
            out.append(row)
            added += 1
        print(f"  {ins:<12}{added:>4} new record(s)")

    if not out:
        print(f"\n  nothing to append.")
        sys.exit(0)
    #: APPEND. The existing file is opened "a" and never rewritten --
    #: v25 section 7, and the reason this job cannot quietly improve its
    #: own history.
    fresh = not os.path.exists(a.ledger)
    with open(a.ledger, "a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=HEADER)
        if fresh:
            w.writeheader()
        w.writerows(out)
    good = sum(1 for r in out if r["bars_present"] == "yes")
    print(f"\n  appended {len(out)} row(s) ({good} complete) to {a.ledger}")
    print(f"  Next release: {fut[0]}")


if __name__ == "__main__":
    main()
