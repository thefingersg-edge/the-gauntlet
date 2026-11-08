#!/usr/bin/env python3
"""ARM 2 of PREREGISTRATION_v11 -- the fourteen excluded 2011-2012 events.

events.csv flags fourteen FOMC meetings between 2011-04-27 and
2012-12-12 as UNCERTAIN, because in that era the statement came out at
**12:30 ET on press-conference days and 14:15 ET on every other day**,
and event_table.py had no sourced list of which was which. An hour and
three quarters of ambiguity is not a window this project will guess at,
so those fourteen were dropped from RESULT_PREANN.

They are 37% of Kurov, Wolfe & Gilbert's sample, and their mean VIX is
21.35 against 15.03 for the years we share. v11 section 5 predicted they
would pay high-VIX magnitude and close under half the gap.

THE SOURCE -- v11 section 4 makes this a hard precondition
----------------------------------------------------------
The press-conference list is NOT inferred from a quarterly pattern. It
is read from the Federal Reserve's own pages, and the 12:30 timing is
read from the Board's announcement of the press-conference programme:

    "the FOMC statement is expected to be released at around 12:30 p.m.,
     one hour and forty-five minutes earlier than for other FOMC
     meetings"
        -- Board of Governors, 2011-03-24

That sentence is what pins BOTH times: 12:30 for press-conference days,
and 12:30 + 1h45m = 14:15 for the rest. Neither is assumed.

events.csv is NOT modified. RESULT_PREANN is closed and its inputs stay
as they were; this file carries a sourced overlay instead.

    python3 preann_arm2.py --self-test
    python3 preann_arm2.py
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import math
import os
import re
import statistics as st
import sys

VERSION = "1.1"


def _cal(y):
    return (f"https://www.federalreserve.gov/monetarypolicy/"
            f"fomchistorical{y}.htm")


SRC_CAL_2011, SRC_CAL_2012 = _cal(2011), _cal(2012)
SRC_TIMING = ("https://www.federalreserve.gov/newsevents/pressreleases/"
              "monetary20110324a.htm")
SRC_PAPER = ("https://www.skidmore.edu/economics/documents/"
             "KurovWolfeGilbert-TheDisappearingPre-FOMC-Announce-Drift-"
             "200914.pdf")

#: ------------------------------------------------------------------ #
#: v1.1 -- THE COMPARISON v11 GOT WRONG
#:
#: v11 section 1 set the target at "+44.50 bp, 2011-04..2015-12" and
#: compared it to an ALL-MEETINGS mean. Reading the paper itself shows
#: that figure is for **press-conference announcements only**, on 20
#: announcements, over a window running "from the stock market open on
#: the day before the announcement to 15 minutes before the
#: announcement", in E-mini S&P 500 futures.
#:
#: They also report **-0.051%** for announcements WITHOUT a press
#: conference, 2011-04..2018-12, on 30 meetings. That is a second,
#: independent thing to check against -- and it is negative, so it is a
#: comparison that can embarrass this measurement rather than flatter
#: it.
#:
#: The lists below are sourced per year from the Board's own calendars.
#: The counts they produce -- 20 and 30 -- are checked against the
#: paper's own counts in the self-test. Matching both is what says these
#: are the same sets, rather than a subset chosen because it reconciles.
PRESSER_ALL = {}
for _y, _dates in {
    2011: ["04-27", "06-22", "11-02"],
    2012: ["01-25", "04-25", "06-20", "09-13", "12-12"],
    2013: ["03-20", "06-19", "09-18", "12-18"],
    2014: ["03-19", "06-18", "09-17", "12-17"],
    2015: ["03-18", "06-17", "09-17", "12-16"],
    2016: ["03-16", "06-15", "09-21", "12-14"],
    2017: ["03-15", "06-14", "09-20", "12-13"],
    2018: ["03-21", "06-13", "09-26", "12-19"],
}.items():
    for _d in _dates:
        PRESSER_ALL[f"{_y}-{_d}"] = _cal(_y)

KUROV_PC_BP = 44.50          # press-conference only, 2011-04..2015-12
KUROV_PC_N = 20
KUROV_NOPC_BP = -5.10        # -0.051%, no press conference, 2011-04..2018-12
KUROV_NOPC_N = 30
NOPC_FROM, NOPC_TO = "2011-04-01", "2018-12-31"
#: Registered BEFORE computing either. Arm 2 showed press-conference
#: days paying +35.47 against +20.38 for the rest across the fourteen,
#: so restricting to press conferences should RAISE this figure. That
#: much is already known; the size is not.
PREDICTED_PC_BP = 25.0
#: They report a NEGATIVE mean for non-press-conference meetings. The
#: FOMC excess measured in RESULT_PREANN is clearly positive, so I
#: expect to DISAGREE with this one -- registered now so that agreeing
#: with it counts as evidence rather than as a relief.
PREDICTED_NOPC_POSITIVE = True

#: Sourced, not inferred. 2011: the three named in the 2011-03-24
#: release. 2012: the five carrying SEP + press conference on the
#: Board's own 2012 calendar page.
PRESSER_DATES = {
    "2011-04-27": SRC_CAL_2011, "2011-06-22": SRC_CAL_2011,
    "2011-11-02": SRC_CAL_2011,
    "2012-01-25": SRC_CAL_2012, "2012-04-25": SRC_CAL_2012,
    "2012-06-20": SRC_CAL_2012, "2012-09-13": SRC_CAL_2012,
    "2012-12-12": SRC_CAL_2012,
}
#: Same era, no press conference -> the legacy time.
NON_PRESSER_DATES = {
    "2011-08-09": SRC_CAL_2011, "2011-09-21": SRC_CAL_2011,
    "2011-12-13": SRC_CAL_2011,
    "2012-03-13": SRC_CAL_2012, "2012-08-01": SRC_CAL_2012,
    "2012-10-24": SRC_CAL_2012,
}
TIME_PRESSER = "12:30"
TIME_LEGACY = "14:15"
#: The gap the release itself states, and the arithmetic that ties the
#: two times together. If these ever disagree the overlay is wrong.
STATED_GAP = dt.timedelta(hours=1, minutes=45)

#: RESULT_PREANN's control mean, so the excess is on the same footing.
CTRL_BP = 4.69
#: v11 section 1 and section 5.
KUROV_BP = 44.50
MINE_BP = 0.36
KUROV_FROM, KUROV_TO = "2011-04-01", "2015-12-31"
PREDICTED_EVENT_BP = 50.0
PREDICTED_POOLED_BP = 18.6


def resolve_time(date_iso):
    """(time_et, has_presser, source) or (None, None, None)."""
    if date_iso in PRESSER_DATES:
        return TIME_PRESSER, True, PRESSER_DATES[date_iso]
    if date_iso in NON_PRESSER_DATES:
        return TIME_LEGACY, False, NON_PRESSER_DATES[date_iso]
    return None, None, None


def source_is_real(s):
    """A source that is a placeholder is not a source. RESULT_TRACKA_D2
    exists because a runnable example once carried an invented one."""
    t = (s or "").strip()
    if not t:
        return False
    low = t.lower()
    for p in ("<", ">", "todo", "tbd", "example", "your ", "..."):
        if p in low:
            return False
    return bool(re.match(r"^https://www\.federalreserve\.gov/\S{10,}$", t))


def self_test():
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        if not isinstance(cond, (bool, int)):
            raise TypeError(f"check({name!r}) got {type(cond).__name__}")
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}"
              + (f"   {detail}" if detail else ""))

    print(f"preann_arm2.py v{VERSION} self-test\n")

    print("the two times are tied together by the sourced sentence")
    p = dt.datetime.strptime(TIME_PRESSER, "%H:%M")
    l = dt.datetime.strptime(TIME_LEGACY, "%H:%M")
    check("14:15 is exactly 1h45m after 12:30, as the release states",
          (l - p) == STATED_GAP, f"{l - p}")
    #: PLANTED: if either constant is edited without the other, this
    #: fails. The pair is the claim, not each number alone.
    check("neither time can be changed alone", (l - p) == STATED_GAP)

    print("\nthe overlay is complete and disjoint")
    both = set(PRESSER_DATES) & set(NON_PRESSER_DATES)
    check("no date is in both lists", both == set(), str(both))
    n = len(PRESSER_DATES) + len(NON_PRESSER_DATES)
    check("fourteen dates in total", n == 14, f"{n}")
    check("eight have a press conference", len(PRESSER_DATES) == 8)
    check("all fall in the 2011-04 .. 2012-12 ambiguous era",
          all("2011-04-27" <= d <= "2012-12-12"
              for d in list(PRESSER_DATES) + list(NON_PRESSER_DATES)))
    check("every date is a real calendar date",
          all(dt.date.fromisoformat(d)
              for d in list(PRESSER_DATES) + list(NON_PRESSER_DATES)))
    check("none is a weekend",
          all(dt.date.fromisoformat(d).weekday() < 5
              for d in list(PRESSER_DATES) + list(NON_PRESSER_DATES)))

    print("\nresolution")
    check("a press-conference day resolves to 12:30",
          resolve_time("2011-04-27") == (TIME_PRESSER, True, SRC_CAL_2011))
    check("a non-press-conference day resolves to 14:15",
          resolve_time("2011-08-09") == (TIME_LEGACY, False, SRC_CAL_2011))
    #: PLANTED: a date NOT in the overlay must resolve to nothing, not
    #: to a default. A silent default is how event_table.py filed a page
    #: footer as a meeting.
    check("an unknown date resolves to nothing, not a default",
          resolve_time("2011-03-15") == (None, None, None))
    check("and so does a date from another era",
          resolve_time("2015-06-17") == (None, None, None))

    print("\nevery source is a real Fed URL")
    for d, s in sorted({**PRESSER_DATES, **NON_PRESSER_DATES}.items()):
        if not source_is_real(s):
            check(f"{d} has a real source", False, s)
    check("all fourteen sources are federalreserve.gov URLs",
          all(source_is_real(s)
              for s in list(PRESSER_DATES.values())
              + list(NON_PRESSER_DATES.values())))
    check("the timing source is one too", source_is_real(SRC_TIMING))
    #: PLANTED: the check must reject a plausible-looking fake.
    check("a placeholder source is rejected",
          not source_is_real("https://www.federalreserve.gov/<the page>"))
    check("a non-Fed URL is rejected",
          not source_is_real("https://en.wikipedia.org/wiki/FOMC"))
    check("an empty source is rejected", not source_is_real(""))

    print("\nthe window is RESULT_PREANN's, unchanged")
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import preann as P
    check("start is T-24h", P.WINDOW_START == dt.timedelta(hours=24))
    check("end is T-1h", P.WINDOW_END == dt.timedelta(hours=1))
    check("this file defines no window of its own",
          not any(k.startswith("WINDOW") for k in globals()))

    print("\nthe press-conference lists reproduce the paper's own counts")
    #: PLANTED: this is the check that says these are the SAME sets the
    #: paper used, not a subset that happens to reconcile. If either
    #: count is off, the list is wrong and the comparison is void.
    pc20 = [d for d in PRESSER_ALL if "2011-04-01" <= d <= "2015-12-31"]
    check(f"{KUROV_PC_N} press-conference announcements 2011-04..2015-12",
          len(pc20) == KUROV_PC_N, f"{len(pc20)}")
    pc_all = [d for d in PRESSER_ALL if NOPC_FROM <= d <= NOPC_TO]
    check("32 press conferences across 2011-04..2018-12",
          len(pc_all) == 32, f"{len(pc_all)}")
    check("which leaves 30 without, matching the paper",
          62 - len(pc_all) == KUROV_NOPC_N, f"{62 - len(pc_all)}")
    check("four a year from 2013, the quarterly programme",
          all(len([d for d in PRESSER_ALL if d[:4] == str(y)]) == 4
              for y in range(2013, 2019)))
    check("2011 has three -- the programme began in April",
          len([d for d in PRESSER_ALL if d[:4] == "2011"]) == 3)
    check("every press-conference date is a weekday",
          all(dt.date.fromisoformat(d).weekday() < 5 for d in PRESSER_ALL))
    check("the 2011-2012 overlay agrees with the full list",
          set(PRESSER_DATES) == {d for d in PRESSER_ALL if d < "2013"})
    check("every year's source is a real Fed URL",
          all(source_is_real(s) for s in PRESSER_ALL.values()))

    print("\nthe prediction is in the file, not in the retelling")
    check("v11 predicted these pay ~50 bp",
          PREDICTED_EVENT_BP == 50.0)
    check("and that pooled lands near 18.6", PREDICTED_POOLED_BP == 18.6)
    check("v1.1 predicts press-conference-only near +25 bp",
          PREDICTED_PC_BP == 25.0)
    check("and predicts DISAGREEING with their negative no-PC figure",
          PREDICTED_NOPC_POSITIVE is True and KUROV_NOPC_BP < 0)

    print("\nthis file holds no position and fits nothing")
    import preann_arm2 as _self
    banned = ("sweep", "optimi", "tune", "refit", "order", "submit",
              "position")
    check("no fitting or trading function exists",
          [x for x in dir(_self) if not x.startswith("_")
           and any(w in x.lower() for w in banned)] == [])

    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", default="../data/events.csv")
    ap.add_argument("--bid", default="../data/spx500usd_bid_15m.csv")
    ap.add_argument("--ask", default="../data/spx500usd_ask_15m.csv")
    ap.add_argument("--vix", default="../data/VIXCLS.csv")
    ap.add_argument("--dump", default="../data/preann_events.csv")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import preann as P

    print(f"preann_arm2.py v{VERSION}   ARM 2 -- PREREGISTRATION_v11\n")
    print(f"  window T-24h -> T-1h, imported from preann.py unchanged")
    print(f"  press-conference list sourced, not inferred:")
    print(f"    {SRC_CAL_2011}")
    print(f"    {SRC_CAL_2012}")
    print(f"    {SRC_TIMING}\n")

    #: The overlay must cover exactly the events events.csv could not
    #: resolve -- no more, no less.
    unc = sorted(r["date"] for r in csv.DictReader(open(a.events))
                 if r["event"] == "FOMC" and r["time_quality"] == "UNCERTAIN")
    over = set(PRESSER_DATES) | set(NON_PRESSER_DATES)
    missing, extra = set(unc) - over, over - set(unc)
    print(f"  UNCERTAIN in events.csv: {len(unc)}   overlay: {len(over)}")
    if missing or extra:
        print(f"    STOP: unresolved {sorted(missing)}  "
              f"not-uncertain {sorted(extra)}")
        sys.exit(3)
    print(f"  every UNCERTAIN event is resolved, and nothing else is\n")

    bars, nb, na, nc = P.load_bars(a.bid, a.ask)
    print(f"  bars aligned: {nc:,}")
    vix = P.load_vix(a.vix)
    vd = sorted(vix)

    rows, viol, drop = [], 0, {}
    for d in unc:
        tm, pc, src = resolve_time(d)
        T = P.release_utc(d, tm)
        ret, n, last = P.window_return(bars, T)
        if ret is None:
            drop[n] = drop.get(n, 0) + 1
            continue
        if last >= T:
            viol += 1
            continue
        w = P.window_open_et_date(T)
        v, vdate = P.vix_asof(vd, vix, w)
        rows.append(dict(date=d, tm=tm, pc=pc, bp=ret, vix=v))
    print(f"  KILL CHECK -- bars at or after T: {viol} "
          f"({'OK' if viol == 0 else 'RUN IS VOID'})")
    if viol:
        sys.exit(3)
    if drop:
        print(f"  dropped: " + ", ".join(f"{k}={v}"
                                         for k, v in sorted(drop.items())))

    print(f"\n  THE FOURTEEN")
    print(f"    {'date':<12}{'T (ET)':>8}{'presser':>9}{'VIX':>7}"
          f"{'window bp':>11}")
    for r in sorted(rows, key=lambda r: r["date"]):
        print(f"    {r['date']:<12}{r['tm']:>8}{'yes' if r['pc'] else 'no':>9}"
              f"{r['vix']:>7.1f}{r['bp']:>11.2f}")
    vals = [r["bp"] for r in rows]
    print(f"\n    n={len(vals)}  mean {st.mean(vals):+.2f} bp   "
          f"median {st.median(vals):+.2f}   "
          f"excess vs control {st.mean(vals)-CTRL_BP:+.2f}   "
          f"positive {sum(1 for x in vals if x > 0)}/{len(vals)}")
    if len(vals) > 1:
        t = st.mean(vals) / (st.stdev(vals) / math.sqrt(len(vals)))
        print(f"    t vs zero {t:.2f}   sd {st.stdev(vals):.0f}")

    pc = [r["bp"] for r in rows if r["pc"]]
    npc = [r["bp"] for r in rows if not r["pc"]]
    if pc and npc:
        print(f"\n    press-conference days  n={len(pc):>2}  "
              f"mean {st.mean(pc):+8.2f} bp   (statement 12:30)")
        print(f"    the rest               n={len(npc):>2}  "
              f"mean {st.mean(npc):+8.2f} bp   (statement 14:15)")

    #: The reconciliation, on RAW means -- v11 section 1 established
    #: that both published figures are raw, so this compares like with
    #: like rather than mixing an excess with a level.
    already = [(r["date"], float(r["window_bp"]))
               for r in csv.DictReader(open(a.dump))
               if r["event"] == "FOMC" and KUROV_FROM <= r["date"] <= KUROV_TO]
    new = [(r["date"], r["bp"]) for r in rows
           if KUROV_FROM <= r["date"] <= KUROV_TO]
    pool = [x[1] for x in already + new]
    print(f"\n  RECONCILIATION over Kurov's window {KUROV_FROM} .. {KUROV_TO}")
    print(f"    already measured in RESULT_PREANN   n={len(already):>3}  "
          f"mean {st.mean([x[1] for x in already]):+8.2f} bp")
    print(f"    recovered by this arm               n={len(new):>3}  "
          f"mean {st.mean([x[1] for x in new]):+8.2f} bp")
    print(f"    pooled                              n={len(pool):>3}  "
          f"mean {st.mean(pool):+8.2f} bp")
    print(f"    Kurov, Wolfe & Gilbert                    "
          f"mean {KUROV_BP:+8.2f} bp")
    gap = KUROV_BP - MINE_BP
    closed = st.mean(pool) - MINE_BP
    print(f"\n    the gap was {gap:.2f} bp; this arm closes {closed:+.2f} "
          f"({100*closed/gap:+.1f}%)")
    print(f"    residual unexplained {KUROV_BP - st.mean(pool):+.2f} bp")

    print(f"\n  AGAINST THE REGISTERED PREDICTION (v11 section 5)")
    print(f"    predicted per event  {PREDICTED_EVENT_BP:+.1f} bp   "
          f"measured {st.mean(vals):+.2f}")
    print(f"    predicted pooled     {PREDICTED_POOLED_BP:+.1f} bp   "
          f"measured {st.mean(pool):+.2f}")
    print(f"    predicted a residual would remain: "
          f"{'YES, it did' if abs(KUROV_BP - st.mean(pool)) > 5 else 'NO -- it closed, which v11 called the WORSE outcome'}")

    #: --------------------------------------------------------------- #
    #: v1.1: the comparison v11 should have made.
    all_bp = dict(already)
    all_bp.update({r["date"]: r["bp"] for r in rows})

    def summarise(label, dates, target, n_expect):
        got = [(d, all_bp[d]) for d in sorted(dates) if d in all_bp]
        if len(got) < 2:
            print(f"    {label:<34} too few measured ({len(got)})")
            return None
        v = [x[1] for x in got]
        se = st.stdev(v) / math.sqrt(len(v))
        inside = abs(target - st.mean(v)) < 1.96 * se
        print(f"    {label:<34}n={len(got):>3}/{n_expect:<3} "
              f"mean {st.mean(v):+7.2f}  median {st.median(v):+7.2f}  "
              f"SE {se:5.2f}")
        print(f"    {'':34}theirs {target:+7.2f} -> "
              f"{(target-st.mean(v))/se:+5.2f} SE, "
              f"{'INSIDE' if inside else 'OUTSIDE'} the 95% interval")
        return st.mean(v)

    print(f"\n  THE COMPARISON v11 GOT WRONG (v1.1) -- their figures are")
    print(f"  press-conference-conditional; v11 compared them to an "
          f"all-meetings mean.")
    print(f"  source: {SRC_PAPER}\n")
    pc = [d for d in PRESSER_ALL if KUROV_FROM <= d <= KUROV_TO]
    nopc = [d for d in all_bp
            if NOPC_FROM <= d <= NOPC_TO and d not in PRESSER_ALL]
    m_pc = summarise("with press conference 2011-15", pc,
                     KUROV_PC_BP, KUROV_PC_N)
    print()
    m_no = summarise("without, 2011-04..2018-12", nopc,
                     KUROV_NOPC_BP, KUROV_NOPC_N)

    print(f"\n  AGAINST THE v1.1 PREDICTIONS")
    if m_pc is not None:
        print(f"    predicted press-conference-only ~{PREDICTED_PC_BP:+.1f} "
              f"bp   measured {m_pc:+.2f}")
    if m_no is not None:
        held = (m_no > 0) == PREDICTED_NOPC_POSITIVE
        verdict = ("HELD -- mine is positive, theirs negative" if held else
                   "FAILED -- mine is negative too, which is agreement "
                   "I did not expect")
        print(f"    predicted DISAGREEING with their {KUROV_NOPC_BP:+.2f} "
              f"(i.e. mine positive)   measured {m_no:+.2f}")
        print(f"    -> the prediction {verdict}")


if __name__ == "__main__":
    main()
