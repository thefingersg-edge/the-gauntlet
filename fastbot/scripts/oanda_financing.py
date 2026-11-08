#!/usr/bin/env python3
"""What the pre-FOMC window actually costs to FINANCE.

RESULT_PREANN.md section 7 put a 1.64 bp per-event financing figure in a
table of measurements and labelled it an estimate. This replaces it with
a measurement, and it turns out the estimate was wrong in two ways that
pull in opposite directions.

WHY A FLAT RATE IS THE WRONG SHAPE
----------------------------------
1. **The benchmark moved.** Financing tracks the short rate. That was
   ~0.05% through 2013-2015 and ~5.4% in 2023-2024. A single 6%/yr
   number overcharges the flat years and undercharges nothing. And the
   effect measured in RESULT_PREANN is concentrated in 2020-2023 -- the
   high-rate half -- so the error is not symmetric.

2. **One weekday is charged three days** -- and v1.0 guessed which one
   wrong. It asserted Wednesday, on the FX convention. **OANDA books the
   weekend on FRIDAY for SPX500_USD** (Mon 1, Tue 1, Wed 1, Thu 1, Fri
   3, Sat 0, Sun 0, fetched 2026-09-04).

   The consequence is that this guard cannot fire on this event set at
   all. Every window crosses exactly one 17:00 ET rollover, on D-1;
   FOMC announcements fall Tuesday to Thursday, so D-1 is Monday,
   Tuesday or Wednesday -- **never Friday**. All 160 events are charged
   one day.

   The mechanism is real and the lookup stays, because it WOULD bite an
   event whose D-1 is a Friday and because the table is read from the
   API rather than assumed. But the claim that it mattered here was
   wrong, and it was wrong in the direction of making this file sound
   more necessary than it was.

So the per-event charge is

    (benchmark on that date + OANDA's markup) * daysCharged / 365

with the markup measured once from the live API and the benchmark read
per event from DGS3MO.

THE TOKEN
---------
Found by fetch_oanda.load_token(): $OANDA_API_TOKEN, then ~/.oanda_token,
then a .oanda_token beside fetch_oanda.py. It is never printed, never
placed in a URL, and every error string is passed through fo.redact()
before display. This file reads only; it holds no order function.

    python3 oanda_financing.py --self-test     # offline, no token
    python3 oanda_financing.py --fetch         # one API call, writes JSON
    python3 oanda_financing.py --apply         # per-event, offline
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import os
import statistics as st
import sys
from zoneinfo import ZoneInfo

VERSION = "1.1"

#: Fetched 2026-09-04. Recorded so the self-test checks the LOOKUP
#: against what the API actually returns, not against what the FX
#: convention led v1.0 to assume.
OBSERVED_DAYS = {"MONDAY": 1, "TUESDAY": 1, "WEDNESDAY": 1, "THURSDAY": 1,
                 "FRIDAY": 3, "SATURDAY": 0, "SUNDAY": 0}

ET = ZoneInfo("America/New_York")
UTC = dt.timezone.utc

DEFAULT_FO_DIR = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "silver15", "scripts"))

INSTRUMENT = "SPX500_USD"
#: OANDA's own convention: financing is charged on the day-count basis
#: below, not 360. Wrong here would be a 1.4% error on the whole line.
DAYS_IN_YEAR = 365.0
#: The window is entered at T-24h and exited at T-1h, so it is open
#: across exactly one 17:00 ET rollover, on D-1. Asserted per event
#: rather than assumed -- see rollover_et_date().
ROLLOVER_ET_HOUR = 17

#: Fallback only, and it is deliberately the WORST plausible case rather
#: than a typical one: if the API cannot be reached the number produced
#: must not flatter the candidate.
FALLBACK_MARKUP = 0.025


def load_fo(fo_dir):
    if not os.path.isdir(fo_dir):
        raise SystemExit(
            f"cannot find fetch_oanda.py in {fo_dir}\n"
            f"  pass --fetch-oanda-dir /path/to/silver15/scripts")
    sys.path.insert(0, fo_dir)
    import fetch_oanda as fo
    return fo


def build_accounts_url(host):
    """No token parameter. That is the point: a URL builder that cannot
    take a token cannot leak one, and the self-test checks the signature
    rather than grepping this file for a string."""
    return f"{host}/v3/accounts"


def build_instruments_url(host, account, instrument=INSTRUMENT):
    return (f"{host}/v3/accounts/{account}/instruments"
            f"?instruments={instrument}")


def rollover_et_date(release_utc_dt):
    """The Eastern date whose 17:00 rollover this window crosses.

    Entry is T-24h, exit is T-1h. For any release between 08:00 and
    16:00 ET the window opens before 17:00 on D-1 and closes before
    17:00 on D, so it spans exactly one rollover: D-1's.

    Returns (date, n_rollovers). n != 1 means the assumption above has
    broken for this event and the caller must stop rather than guess.
    """
    entry = (release_utc_dt - dt.timedelta(hours=24)).astimezone(ET)
    exit_ = (release_utc_dt - dt.timedelta(hours=1)).astimezone(ET)
    n, hit = 0, None
    d = entry.date()
    while d <= exit_.date():
        roll = dt.datetime(d.year, d.month, d.day,
                           ROLLOVER_ET_HOUR, 0, tzinfo=ET)
        if entry < roll <= exit_:
            n += 1
            hit = d
        d += dt.timedelta(days=1)
    return hit, n


def days_charged(days_table, d):
    """How many days of financing OANDA books on Eastern date `d`.

    days_table maps dayOfWeek name -> daysCharged, as returned by the
    API. Python's weekday() is Mon=0; OANDA names them.
    """
    names = ("MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY",
             "FRIDAY", "SATURDAY", "SUNDAY")
    return days_table.get(names[d.weekday()], 0)


def per_event_bp(annual_rate, n_days):
    """Cost in basis points of notional for n_days of financing."""
    return annual_rate / DAYS_IN_YEAR * n_days * 1e4


def load_series(path, col=1):
    out = {}
    if not os.path.exists(path):
        return out
    for r in csv.reader(open(path)):
        if len(r) <= col:
            continue
        try:
            out[dt.date.fromisoformat(r[0].strip())] = float(r[col])
        except (ValueError, IndexError):
            continue
    return out


def rate_asof(dates_sorted, series, d):
    """The benchmark on or before `d`. Not lagged -- financing is charged
    at the rate in force, which is knowable at the time."""
    import bisect
    i = bisect.bisect_right(dates_sorted, d)
    if i == 0:
        return None
    k = dates_sorted[i - 1]
    return series[k] if (d - k).days <= 10 else None


# --------------------------------------------------------------------- #
#  the API call
# --------------------------------------------------------------------- #

def do_fetch(fo, env, out_path, account=None):
    host = fo.HOSTS[env]
    token = fo.load_token()

    if not account:
        payload = fo.api_get(build_accounts_url(host), token)
        accts = payload.get("accounts", [])
        if not accts:
            raise SystemExit("no accounts on this token")
        account = accts[0]["id"]
        print(f"  accounts visible: {len(accts)}  using the first")
    #: The account id is not a secret but there is no reason to print it.
    print(f"  account: ...{account[-4:]}")

    url = build_instruments_url(host, account)
    if token in url:                       # belt and braces, not an assert
        raise SystemExit("token leaked into a URL -- refusing to send")
    data = fo.api_get(url, token)
    ins = data.get("instruments", [])
    if not ins:
        raise SystemExit(f"{INSTRUMENT} not returned -- is it tradeable "
                         f"on this account?")
    fin = ins[0].get("financing", {})
    long_rate = float(fin.get("longRate", "nan"))
    short_rate = float(fin.get("shortRate", "nan"))
    table = {x["dayOfWeek"]: int(x["daysCharged"])
             for x in fin.get("financingDaysOfWeek", [])}

    print(f"\n  {INSTRUMENT} financing, live from the API")
    print(f"    longRate  {long_rate:+.6f}   ({long_rate*100:+.3f} %/yr)")
    print(f"    shortRate {short_rate:+.6f}   ({short_rate*100:+.3f} %/yr)")
    print(f"    daysCharged: "
          + "  ".join(f"{k[:3].title()} {v}" for k, v in sorted(
              table.items(), key=lambda kv: ("MONDAY TUESDAY WEDNESDAY "
                                             "THURSDAY FRIDAY SATURDAY "
                                             "SUNDAY").split().index(kv[0]))))
    total = sum(table.values())
    print(f"    total days charged per week: {total}"
          + ("  OK" if total == 7 else "  <-- not 7, check this"))

    rec = {"tool": "oanda_financing.py", "version": VERSION,
           "fetched_utc": dt.datetime.now(UTC).isoformat(),
           "instrument": INSTRUMENT, "env": env,
           "long_rate": long_rate, "short_rate": short_rate,
           "days_charged": table}
    with open(out_path, "w") as fh:
        json.dump(rec, fh, indent=2)
    print(f"\n  written to {out_path}")
    return rec


# --------------------------------------------------------------------- #
#  applying it per event
# --------------------------------------------------------------------- #

def do_apply(rec, events_path, dump_path, bench_path, bid_p, ask_p):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import preann as P

    bench = load_series(bench_path)
    if not bench:
        raise SystemExit(f"no benchmark series at {bench_path}")
    bdates = sorted(bench)
    bench_today = bench[bdates[-1]] / 100.0

    long_rate = rec["long_rate"]
    #: OANDA quotes the long rate as a signed number: negative means the
    #: long PAYS. Take the magnitude of what a long is charged, and
    #: derive the markup over the benchmark in force today.
    charged = abs(long_rate)
    markup = charged - bench_today
    print(f"  today's benchmark ({bdates[-1]}): {bench_today*100:.2f} %/yr")
    print(f"  a long is charged:                {charged*100:.2f} %/yr")
    print(f"  implied OANDA markup:             {markup*100:+.2f} %/yr")
    if markup < 0:
        print("    NOTE: negative markup. The quoted rate is below the "
              "3M bill,")
        print("    which usually means OANDA is benchmarking to a "
              "different rate.")
        print("    The historical charge below is therefore a LOWER "
              "bound.")

    #: bars, only to confirm each event actually had a measurable window
    def rd(p):
        o = {}
        for r in csv.DictReader(open(p)):
            o[dt.datetime.fromisoformat(r["time"]).replace(tzinfo=UTC)] = (
                float(r["open"]), float(r["close"]))
        return o
    bid, ask = rd(bid_p), rd(ask_p)
    measured = {(r["event"], r["date"])
                for r in csv.DictReader(open(dump_path))}

    rows = []
    bad_roll = 0
    for r in csv.DictReader(open(events_path)):
        if r["event"] != "FOMC" or r["time_quality"] == "UNCERTAIN":
            continue
        if not r["time_et"] or ("FOMC", r["date"]) not in measured:
            continue
        T = P.release_utc(r["date"], r["time_et"])
        e, x = T - P.WINDOW_START, T - P.WINDOW_END - P.BAR
        if e not in bid or x not in bid:
            continue
        roll_d, n_roll = rollover_et_date(T)
        if n_roll != 1:
            bad_roll += 1
            continue
        nd = days_charged(rec["days_charged"], roll_d)
        d = dt.date.fromisoformat(r["date"])
        b = rate_asof(bdates, bench, d)
        if b is None:
            continue
        rate = b / 100.0 + markup
        rows.append(dict(date=r["date"], y=d.year, roll=roll_d,
                         wd=roll_d.strftime("%a"), nd=nd,
                         rate=rate, bp=per_event_bp(rate, nd),
                         net=(bid[x][1] / ask[e][0] - 1) * 1e4))
    if bad_roll:
        print(f"\n  STOP: {bad_roll} events did not cross exactly one "
              f"rollover.")
        sys.exit(3)
    print(f"\n  {len(rows)} events, every one crossing exactly one "
          f"17:00 ET rollover")

    print(f"\n  which weekday the rollover lands on -- this is the part a "
          f"flat number hides")
    wk = {}
    for r in rows:
        k = (r["wd"], r["nd"])
        wk.setdefault(k, []).append(r["bp"])
    for (wd, nd), v in sorted(wk.items(), key=lambda kv: -len(kv[1])):
        print(f"    {wd}  charged {nd} day(s)  n={len(v):>3}   "
              f"mean {st.mean(v):5.2f} bp   max {max(v):5.2f}")

    print(f"\n  financing by era -- the benchmark is not a constant")
    for lo in range(2004, 2028, 4):
        b = [r for r in rows if lo <= r["y"] <= lo + 3]
        if not b:
            continue
        print(f"    {lo}-{lo+3}  n={len(b):>3}  rate "
              f"{st.mean([r['rate'] for r in b])*100:5.2f} %/yr   "
              f"financing {st.mean([r['bp'] for r in b]):5.2f} bp/event")
    return rows


def self_test():
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        if not isinstance(cond, (bool, int)):
            raise TypeError(f"check({name!r}) got {type(cond).__name__}")
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}"
              + (f"   {detail}" if detail else ""))

    print(f"oanda_financing.py v{VERSION} self-test\n")

    print("every window crosses exactly ONE rollover -- asserted, not assumed")
    for date, tm, want_wd in (("2015-06-17", "14:00", "Tue"),   # Wed FOMC
                              ("2015-12-16", "14:00", "Tue"),
                              ("2020-03-06", "08:30", "Thu"),   # Fri NFP
                              ("2013-01-30", "14:15", "Tue"),
                              ("2026-01-29", "14:00", "Wed")):  # Thu FOMC
        T = dt.datetime.combine(dt.date.fromisoformat(date),
                                dt.time(*[int(x) for x in tm.split(":")]),
                                tzinfo=ET).astimezone(UTC)
        d, n = rollover_et_date(T)
        check(f"{date} {tm} ET crosses 1 rollover, on a {want_wd}",
              n == 1 and d.strftime("%a") == want_wd,
              f"n={n} on {d} ({d.strftime('%a')})")

    print("\nthe triple charge -- and WHICH day carries it is read, not assumed")
    #: v1.0 hard-coded a Wednesday-triple fixture on the FX convention
    #: and called it "the thing a flat number hides". The API says
    #: FRIDAY. The lookup was always right; the story around it was not.
    tbl = dict(OBSERVED_DAYS)
    triple = [k for k, v in tbl.items() if v == 3]
    check("exactly one day carries the weekend", len(triple) == 1,
          f"{triple[0].title()}")
    check("it is FRIDAY for SPX500_USD, not Wednesday",
          triple == ["FRIDAY"], f"{triple}")
    check("the week still totals 7 days", sum(tbl.values()) == 7)
    check("a Tuesday rollover is charged 1 day",
          days_charged(tbl, dt.date(2015, 6, 16)) == 1)
    check("a Wednesday rollover is charged 1, not 3",
          days_charged(tbl, dt.date(2015, 6, 17)) == 1)
    check("a Friday rollover is charged 3",
          days_charged(tbl, dt.date(2015, 6, 19)) == 3)
    check("a Saturday rollover is charged 0",
          days_charged(tbl, dt.date(2015, 6, 20)) == 0)
    #: PLANTED: the lookup must still be able to SEE a 3, or the check
    #: above is passing for the wrong reason.
    fri = per_event_bp(0.06, days_charged(tbl, dt.date(2015, 6, 19)))
    tue = per_event_bp(0.06, days_charged(tbl, dt.date(2015, 6, 16)))
    check("a Friday rollover costs 3x a Tuesday one",
          abs(fri - 3 * tue) < 1e-9, f"{fri:.2f} bp vs {tue:.2f} bp")

    print("\nand it cannot fire on FOMC at all -- stated, not hoped")
    #: FOMC announcements fall Tue-Thu, so D-1 is Mon/Tue/Wed. For the
    #: triple to bite, D-1 would have to be a Friday, i.e. the
    #: announcement would have to be a Saturday.
    hits = []
    for wd, name in enumerate(("Mon", "Tue", "Wed", "Thu", "Fri")):
        d = dt.date(2015, 6, 15) + dt.timedelta(days=wd)   # Mon..Fri
        if days_charged(tbl, d - dt.timedelta(days=1)) == 3:
            hits.append(name)
    check("no Monday-to-Friday announcement rolls over on a Friday",
          hits == [], f"would hit on {hits}")
    check("only a Saturday announcement could",
          days_charged(tbl, dt.date(2015, 6, 20) - dt.timedelta(days=1)) == 3)

    print("\nthe arithmetic")
    check("6%/yr for one day is 1.64 bp",
          abs(per_event_bp(0.06, 1) - 1.6438) < 1e-3,
          f"{per_event_bp(0.06, 1):.4f}")
    check("0%/yr costs nothing", per_event_bp(0.0, 3) == 0.0)
    check("the day count is 365, not 360",
          abs(per_event_bp(0.0365, 1) - 1.0) < 1e-9)

    print("\nthe benchmark lookup")
    ser = {dt.date(2015, 6, 12): 0.02, dt.date(2015, 6, 16): 0.05}
    ds = sorted(ser)
    check("a rate on the day itself is used",
          rate_asof(ds, ser, dt.date(2015, 6, 16)) == 0.05)
    check("otherwise the last one before it",
          rate_asof(ds, ser, dt.date(2015, 6, 15)) == 0.02)
    check("a stale gap returns nothing rather than a wrong number",
          rate_asof(ds, ser, dt.date(2015, 8, 1)) is None)
    check("before the series starts returns nothing",
          rate_asof(ds, ser, dt.date(2015, 1, 1)) is None)

    print("\nno token can leak")
    #: v1.0's first attempt grepped this file for "print(token" -- and
    #: FAILED, because the check's own needle is in the source it
    #: searches. A test that cannot distinguish the thing from a
    #: description of the thing is not a test. These are behavioural
    #: and structural instead.
    import inspect
    PLANTED = "abcd1234-SECRET-TOKEN-dead"
    u1 = build_accounts_url("https://api-fxtrade.oanda.com")
    u2 = build_instruments_url("https://api-fxtrade.oanda.com", "001-004-X")
    check("a planted token appears in neither built URL",
          PLANTED not in u1 and PLANTED not in u2)
    for fn in (build_accounts_url, build_instruments_url):
        params = list(inspect.signature(fn).parameters)
        check(f"{fn.__name__} cannot even accept a token",
              not any("token" in p.lower() or "secret" in p.lower()
                      or "auth" in p.lower() for p in params),
              f"({', '.join(params)})")
    check("the instruments URL is well formed",
          u2.endswith(f"/instruments?instruments={INSTRUMENT}")
          and "001-004-X" in u2, u2)
    #: PLANTED: a builder that DOES leak, to prove the check above can
    #: fail. A gate that can only pass has not been tested.
    def leaky(host, account, token):
        return f"{host}/v3/{account}?token={token}"
    bad = leaky("h", "a", PLANTED)
    check("and the same check catches a builder that does leak",
          PLANTED in bad
          and any("token" in p for p in inspect.signature(leaky).parameters))
    check("the fallback markup is pessimistic, not typical",
          FALLBACK_MARKUP >= 0.02, f"{FALLBACK_MARKUP*100:.1f}%")

    print("\nthis file holds no position")
    import oanda_financing as _self
    banned = ("order", "submit", "execute", "buy", "sell", "position",
              "sweep", "optimi")
    check("no order or fitting function exists",
          [x for x in dir(_self) if not x.startswith("_")
           and any(w in x.lower() for w in banned)] == [])

    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--env", default="live", choices=("live", "practice"))
    ap.add_argument("--account", default=None)
    ap.add_argument("--fetch-oanda-dir", default=DEFAULT_FO_DIR)
    ap.add_argument("--out", default="../data/oanda_financing.json")
    ap.add_argument("--events", default="../data/events.csv")
    ap.add_argument("--dump", default="../data/preann_events.csv")
    ap.add_argument("--bench", default="../data/DGS3MO.csv")
    ap.add_argument("--bid", default="../data/spx500usd_bid_15m.csv")
    ap.add_argument("--ask", default="../data/spx500usd_ask_15m.csv")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())

    print(f"oanda_financing.py v{VERSION}\n")
    rec = None
    if a.fetch:
        rec = do_fetch(load_fo(a.fetch_oanda_dir), a.env, a.out, a.account)
    if a.apply:
        if rec is None:
            if not os.path.exists(a.out):
                raise SystemExit(f"no {a.out} -- run --fetch first")
            rec = json.load(open(a.out))
            print(f"  using rates fetched {rec['fetched_utc'][:19]}Z\n")
        rows = do_apply(rec, a.events, a.dump, a.bench, a.bid, a.ask)
        #: The headline: what RESULT_PREANN section 6 said, redone with
        #: measured financing instead of a flat 1.64 bp.
        import preann as P
        vix = {(r["event"], r["date"]): r["vix"]
               for r in csv.DictReader(open(a.dump))}
        real = [r for r in rows if r["y"] >= 2013]
        for r in real:
            v = vix.get(("FOMC", r["date"]), "")
            r["vix"] = float(v) if v else None
        real = [r for r in real if r["vix"] is not None]
        med = st.median([r["vix"] for r in real])
        CTRL = 4.69
        print(f"\n  RESULT_PREANN section 6, redone with measured "
              f"financing")
        print(f"  {'':16}{'n':>4}{'net spread':>12}{'financing':>11}"
              f"{'net all':>10}{'%/yr':>8}{'Sharpe':>8}")
        for nm, rr in (("all events", real),
                       ("high VIX", [r for r in real if r["vix"] >= med]),
                       ("low VIX", [r for r in real if r["vix"] < med])):
            ns = st.mean([r["net"] for r in rr]) - CTRL
            fb = st.mean([r["bp"] for r in rr])
            fin = [r["net"] - r["bp"] for r in rr]
            na = st.mean(fin) - CTRL
            py = len(rr) / 13.67
            sd = st.stdev(fin)
            print(f"  {nm:<16}{len(rr):>4}{ns:>+12.2f}{fb:>11.2f}"
                  f"{na:>+10.2f}{py*na/100:>+8.2f}"
                  f"{(py*na)/(sd*math.sqrt(py)):>8.2f}")
        print(f"\n  (control mean {CTRL} bp; median VIX {med:.1f}; "
              f"financing is now measured, not assumed)")
    if not (a.fetch or a.apply):
        ap.error("nothing to do -- pass --fetch, --apply or --self-test")


if __name__ == "__main__":
    main()
