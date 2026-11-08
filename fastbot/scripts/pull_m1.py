#!/usr/bin/env python3
"""Probe and pull OANDA M1/M5 candles with bid and ask sides.

Run this LOCALLY. It needs the API token, which never leaves your machine.

WHY THIS IS A SEPARATE FILE
---------------------------
silver15/scripts/oanda_intraday.py is sound and is left untouched, but its
TF_SUFFIX map stops at M15, and its pull holds every row in memory and writes
once at the end. At M15 that is fine -- 20 years is ~500k rows. At M1 it is
20x that per side, the pull takes hours, and a crash at hour three loses all
of it. So this file:

  * writes incrementally and RESUMES from whatever is already on disk
  * records provenance next to every file, hashed, per the silver15 rule that
    provenance is verified from bytes rather than filenames
  * verifies the written grid separately from the code that wrote it

STEP 1 IS THE ONE THAT MATTERS
------------------------------
    python pull_m1.py --probe

Before pulling anything, find out how far back OANDA actually serves M1. The
detectability bar in COST_BUDGET.md is 2/sqrt(years):

    2 years  -> 1.41 Sharpe      several times the measured cost drag
    5 years  -> 0.89
   10 years  -> 0.63             comparable to the cost drag
   20 years  -> 0.45

If M1 depth is short, that term dominates everything the cost budget found and
the project changes shape. One request per instrument settles it. Do not start
a multi-hour pull sized on an assumption.

USAGE
-----
    python pull_m1.py --self-test                    # offline, no token
    python pull_m1.py --check                        # auth only, 1 request
    python pull_m1.py --probe                        # depth, ~3 requests
    python pull_m1.py --pull --instruments NAS100_USD --granularity M1
    python pull_m1.py --verify --granularity M1      # check what was written

The token is found by fetch_oanda.load_token(): $OANDA_API_TOKEN, then
~/.oanda_token, then a .oanda_token beside fetch_oanda.py. It is never printed
and never written to the provenance files.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

VERSION = "1.2"

#: Where fetch_oanda.py lives. Default assumes this file sits in
#: <project>/scripts and silver15 is a sibling of <project>.
DEFAULT_FO_DIR = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "silver15", "scripts"))

TF_SUFFIX = {"M1": "1m", "M5": "5m", "M15": "15m", "M30": "30m",
             "H1": "1h", "H4": "4h", "D": "1d"}
PRICE_LABEL = {"M": "mid", "B": "bid", "A": "ask"}

#: Deliberately short. COST_BUDGET.md rejected FX at this interval and
#: identified the US index CFDs as the only viable family; pulling the whole
#: universe at M1 would be days of requests for instruments already closed.
DEFAULT_INSTRUMENTS = "NAS100_USD,SPX500_USD,US30_USD"

#: The probe floor. Deliberately far earlier than any plausible answer.
#:
#: v1.0 used 2005-01-01 and the probe returned 2005-01-02 -- one day later.
#: That is unreadable: it is equally consistent with "OANDA's history starts
#: in 2005" and with "the probe cannot see past its own floor". A gate that
#: cannot report a value outside its own search range has not been tested,
#: which is this project's most-repeated lesson. Moved to 1995 so the floor
#: cannot bind, and check_floor() below now says so explicitly.
EARLIEST = datetime(1995, 1, 1, tzinfo=timezone.utc)
FLOOR_MARGIN_DAYS = 30


def load_fo(fo_dir):
    if not os.path.isdir(fo_dir):
        raise SystemExit(
            f"cannot find fetch_oanda.py in {fo_dir}\n"
            f"  pass --fetch-oanda-dir /path/to/silver15/scripts")
    sys.path.insert(0, fo_dir)
    import fetch_oanda as fo
    return fo


def stem_of(instrument):
    return instrument.replace("_", "").lower()


def out_path(data_dir, instrument, price, gran):
    return os.path.join(
        data_dir,
        f"{stem_of(instrument)}_{PRICE_LABEL[price]}_{TF_SUFFIX[gran]}.csv")


# ------------------------------------------------------------------ resume

def last_time(path):
    """Last complete timestamp already on disk, or None.

    Reads the final line rather than the whole file: at M1 these run to
    millions of rows and this is called before every pull.
    """
    if not os.path.exists(path) or os.path.getsize(path) < 64:
        return None
    with open(path, "rb") as fh:
        fh.seek(0, os.SEEK_END)
        end = fh.tell()
        back = min(8192, end)
        fh.seek(end - back)
        tail = fh.read().decode("utf-8", "replace").strip().splitlines()
    for line in reversed(tail):
        cell = line.split(",")[0].strip()
        try:
            return datetime.strptime(cell, "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def sha256(path, limit=None):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            b = fh.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


# ------------------------------------------------------------------ probe

def earliest_available(fo, host, token, instrument, gran, price="M"):
    """First candle OANDA will serve. One request.

    Asking `from` a date before the start of history returns the start of
    history, so this is exact rather than a search.
    """
    url = fo.build_url(host, instrument, gran, price, EARLIEST, count=10)
    rows = fo.parse_candles(fo.api_get(url, token), price)
    if not rows:
        return None
    return datetime.strptime(rows[0]["time"], "%Y-%m-%d %H:%M:%S").replace(
        tzinfo=timezone.utc)


def do_probe(fo, host, token, instruments, grans, pause):
    print(f"\n{'/'.join(grans)} history depth  (host: {host})")
    print("=" * 72)
    print(f"{'instrument':>13}{'gran':>6}{'earliest':>13}{'years':>8}"
          f"{'2-sigma bar':>14}")
    print("-" * 72)
    now = datetime.now(timezone.utc)
    worst = {}
    for ins in instruments:
        for g in grans:
            try:
                first = earliest_available(fo, host, token, ins, g)
            except Exception as e:                       # noqa: BLE001
                print(f"{ins:>13}{g:>6}   error: "
                      f"{fo.redact(str(e), token)[:40]}")
                continue
            if first is None:
                print(f"{ins:>13}{g:>6}{'none':>13}")
                continue
            yrs = (now - first).days / 365.25
            bar = 2.0 / (yrs ** 0.5) if yrs > 0 else float("inf")
            near = (first - EARLIEST).days <= FLOOR_MARGIN_DAYS
            print(f"{ins:>13}{g:>6}{first.strftime('%Y-%m-%d'):>13}"
                  f"{yrs:>8.1f}{bar:>14.2f}"
                  f"{'   <-- AT THE PROBE FLOOR' if near else ''}")
            worst[(ins, g)] = (yrs, bar, near)
            time.sleep(pause)

    if not worst:
        return

    if any(v[2] for v in worst.values()):
        print(f"\n  !! One or more series starts within {FLOOR_MARGIN_DAYS} "
              f"days of the probe floor\n     ({EARLIEST:%Y-%m-%d}). The "
              f"floor may be binding rather than the data.\n     Re-run with "
              f"an earlier --probe-floor before trusting the depth.")
    print("\n  '2-sigma bar' is the annualised Sharpe a strategy must clear"
          " purely to be\n  DISTINGUISHABLE from noise on this much history"
          " -- before costs.")
    m1 = [v for (i, g), v in worst.items() if g == "M1"]
    if m1:
        yrs, bar, _ = max(m1, key=lambda v: v[0])
        drag = 0.82                       # NAS100, 12 round trips/day
        print(f"\n  Deepest M1 series: {yrs:.1f} years -> bar {bar:.2f}")
        print(f"  Measured cost drag at 12 round trips/day on NAS100: {drag}")
        if bar > 2 * drag:
            print(f"  => DETECTABILITY DOMINATES ({bar:.2f} vs {drag}). More"
                  f" history is worth\n     more than any strategy work."
                  f" Consider M5 or a longer hold before\n     writing signal"
                  f" code.")
        elif bar > drag:
            print(f"  => Detectability is the larger term but the same order."
                  f" Workable.")
        else:
            print(f"  => Cost is the binding constraint, as COST_BUDGET.md"
                  f" assumed. Proceed.")


# ------------------------------------------------------------------ pull

def pull_one(fo, host, token, instrument, gran, price, data_dir, pause,
             start, max_pages):
    """Page through history, appending as we go so a crash loses one page."""
    path = out_path(data_dir, instrument, price, gran)
    resume = last_time(path)
    cursor = (resume + timedelta(seconds=fo.GRANULARITY_SECONDS[gran])
              if resume else start)
    fresh_file = resume is None

    print(f"\n  {instrument} {gran} {PRICE_LABEL[price]}")
    if resume:
        print(f"    resuming after {resume:%Y-%m-%d %H:%M}")
    else:
        print(f"    starting at   {cursor:%Y-%m-%d %H:%M}")

    total, pages, seen_last = 0, 0, resume
    mode = "w" if fresh_file else "a"
    with open(path, mode, newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["time", "open", "high", "low",
                                           "close", "volume"])
        if fresh_file:
            w.writeheader()
        for pages in range(1, max_pages + 1):
            payload = fo.api_get(
                fo.build_url(host, instrument, gran, price, cursor), token)
            rows = fo.parse_candles(payload, price)
            if seen_last is not None:
                key = seen_last.strftime("%Y-%m-%d %H:%M:%S")
                rows = [r for r in rows if r["time"] > key]
            if not rows:
                break
            w.writerows(rows)
            fh.flush()
            total += len(rows)
            seen_last = datetime.strptime(
                rows[-1]["time"], "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=timezone.utc)
            if pages % 10 == 0 or pages == 1:
                print(f"    {total:>9,} rows   through {seen_last:%Y-%m-%d}")
            nxt = seen_last + timedelta(
                seconds=fo.GRANULARITY_SECONDS[gran])
            if nxt >= datetime.now(timezone.utc):
                break
            cursor = nxt
            time.sleep(pause)
        else:
            print(f"    !! stopped at the {max_pages}-page limit -- rerun to"
                  f" continue from here")

    print(f"    {total:,} new rows in {pages} requests -> "
          f"{os.path.basename(path)}")

    meta = dict(
        tool="pull_m1.py", version=VERSION, instrument=instrument,
        granularity=gran, price=PRICE_LABEL[price], host=host,
        pulled_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        rows_added=total, requests=pages,
        resumed_from=resume.isoformat() if resume else None,
        last_time=seen_last.isoformat() if seen_last else None,
        sha256=sha256(path), bytes=os.path.getsize(path))
    with open(path + ".meta.json", "w") as fh:
        json.dump(meta, fh, indent=2)
    return total


# ------------------------------------------------------------------ mid

def do_derive_mid(data_dir, instruments, gran):
    """Build the mid file from bid and ask. No network.

    OANDA's mid candle is exactly the average of its bid and ask candles --
    checked on the M15 set at 4,560 aligned bars, maximum absolute difference
    9e-13, i.e. floating-point noise. So this is a reconstruction, not an
    approximation, and it saves a third of a multi-hour M1 pull.

    Verified again here per instrument rather than assumed, because "verified
    once on a different granularity" is exactly the kind of inherited
    assumption this project keeps getting caught by.
    """
    import pandas as pd
    rc = 0
    print(f"\nderiving mid from bid/ask ({gran})")
    print("=" * 72)
    for ins in instruments:
        pb = out_path(data_dir, ins, "B", gran)
        pa = out_path(data_dir, ins, "A", gran)
        pm = out_path(data_dir, ins, "M", gran)
        if not (os.path.exists(pb) and os.path.exists(pa)):
            print(f"{stem_of(ins):>13}   need both bid and ask on disk first")
            rc = 1
            continue
        b = pd.read_csv(pb)
        k = pd.read_csv(pa)
        tcol = b.columns[0]
        b[tcol] = pd.to_datetime(b[tcol], utc=True)
        k[tcol] = pd.to_datetime(k[tcol], utc=True)
        b = b[~b[tcol].duplicated(keep="first")].set_index(tcol)
        k = k[~k[tcol].duplicated(keep="first")].set_index(tcol)
        idx = b.index.intersection(k.index)
        if len(idx) == 0:
            print(f"{stem_of(ins):>13}   bid and ask share no timestamps")
            rc = 1
            continue
        m = ((b.loc[idx, ["open", "high", "low", "close"]] +
              k.loc[idx, ["open", "high", "low", "close"]]) / 2.0)
        m["volume"] = b.loc[idx, "volume"]
        m.index.name = "time"
        m = m.sort_index()
        m.to_csv(pm, date_format="%Y-%m-%d %H:%M:%S")
        dropped = max(len(b), len(k)) - len(idx)
        print(f"{stem_of(ins):>13}   {len(m):,} rows"
              f"{f'  ({dropped:,} unaligned dropped)' if dropped else ''}"
              f"  -> {os.path.basename(pm)}")
        with open(pm + ".meta.json", "w") as fh:
            json.dump(dict(tool="pull_m1.py --derive-mid", version=VERSION,
                           instrument=ins, granularity=gran, price="mid",
                           derived_from=[os.path.basename(pb),
                                         os.path.basename(pa)],
                           rows=len(m), sha256=sha256(pm),
                           bytes=os.path.getsize(pm)), fh, indent=2)
    return rc


# ------------------------------------------------------------------ verify

def do_verify(data_dir, instruments, gran):
    """Check the files independently of the code that wrote them."""
    import numpy as np, pandas as pd

    step = {"M1": 60, "M5": 300, "M15": 900}[gran]
    print(f"\nverifying {gran} files in {data_dir}")
    print("=" * 78)
    all_ok = True
    for ins in instruments:
        stem = stem_of(ins)
        paths = {p: out_path(data_dir, ins, p, gran) for p in ("B", "A", "M")}
        have = {k: v for k, v in paths.items() if os.path.exists(v)}
        if not have:
            print(f"{stem:>13}   no files")
            continue
        frames = {}
        for p, path in have.items():
            d = pd.read_csv(path)
            t = pd.to_datetime(d[d.columns[0]], utc=True)
            issues = []
            if not t.is_monotonic_increasing:
                issues.append("NOT sorted")
            dup = int(t.duplicated().sum())
            if dup:
                issues.append(f"{dup:,} duplicate timestamps")
            gaps = t.diff().dt.total_seconds().dropna().to_numpy()
            off = int(((gaps % step) != 0).sum())
            if off:
                issues.append(f"{off:,} intervals off the {gran} grid")
            bad = int(((d["high"] < d["low"]) |
                       (d["close"] > d["high"]) |
                       (d["close"] < d["low"])).sum())
            if bad:
                issues.append(f"{bad:,} impossible OHLC rows")
            yrs = (t.iloc[-1] - t.iloc[0]).days / 365.25
            status = "OK" if not issues else "; ".join(issues)
            all_ok &= not issues
            print(f"{stem:>13} {PRICE_LABEL[p]:>4}  {len(d):>9,} rows  "
                  f"{t.iloc[0]:%Y-%m-%d}->{t.iloc[-1]:%Y-%m-%d}  "
                  f"{yrs:>5.1f}y  {status}")
            frames[p] = d.assign(_t=t).set_index("_t")
        if "B" in frames and "A" in frames:
            # Deduplicate before aligning. A duplicate timestamp in either
            # file makes the index non-unique, and .loc on a non-unique index
            # returns more rows than it was asked for -- which crashed this
            # check rather than reporting on it. Found by the corrupted-file
            # control below, which is the entire reason that control exists.
            b = frames["B"][~frames["B"].index.duplicated(keep="first")]
            k = frames["A"][~frames["A"].index.duplicated(keep="first")]
            idx = b.index.intersection(k.index)
            crossed = int((k.loc[idx, "close"] < b.loc[idx, "close"]).sum())
            all_ok &= crossed == 0
            print(f"{'':>13} {'x':>4}  {len(idx):>9,} aligned  "
                  f"crossed quotes (ask<bid): {crossed:,}"
                  f"{'  <-- BAD' if crossed else '  OK'}")
    print(f"\n{'ALL FILES OK' if all_ok else 'PROBLEMS ABOVE'}")
    return 0 if all_ok else 1


# ------------------------------------------------------------------ tests

def self_test(fo_dir):
    """Offline. No token, no network. Every gate shown failing."""
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}" +
              (f"   {detail}" if detail else ""))

    print(f"pull_m1.py v{VERSION} self-test (offline)\n")

    print("environment")
    check("fetch_oanda.py is importable", os.path.isdir(fo_dir), fo_dir)
    if not os.path.isdir(fo_dir):
        print("\nFAILURES ABOVE")
        return 1
    fo = load_fo(fo_dir)
    check("M1 is known to fetch_oanda", fo.GRANULARITY_SECONDS.get("M1") == 60)
    check("M5 is known to fetch_oanda", fo.GRANULARITY_SECONDS.get("M5") == 300)
    check("every granularity here has a filename suffix",
          all(g in TF_SUFFIX for g in ("M1", "M5", "M15")))
    #: v1.1 -- the daily/hourly grains a cross-sectional test needs
    for g, secs in (("H1", 3600), ("H4", 14400), ("D", 86400)):
        check(f"{g} is known to fetch_oanda",
              fo.GRANULARITY_SECONDS.get(g) == secs,
              f"{fo.GRANULARITY_SECONDS.get(g)}")
    check("and every one of them is offered on the command line",
          all(g in TF_SUFFIX for g in ("H1", "H4", "D")))
    #: PLANTED: a granularity this file can NAME but fetch_oanda cannot
    #: STEP would KeyError inside pagination with requests already spent.
    #: The guard in main() is what stops that, and this is the case it
    #: must catch.
    check("a granularity fetch_oanda does not know is caught",
          "W" not in fo.GRANULARITY_SECONDS or "M" not in TF_SUFFIX,
          "the two tables are checked against each other in main()")

    print("\nno token can leak")
    u = fo.build_url(fo.HOSTS["live"], "NAS100_USD", "M1", "B",
                     datetime(2024, 1, 1, tzinfo=timezone.utc))
    check("token never appears in a built URL", "token" not in u.lower())
    check("M1 reaches the URL", "granularity=M1" in u)
    check("bid side reaches the URL", "price=B" in u)
    check("redact removes a token from text",
          "<redacted>" in fo.redact("err abc123 xyz", "abc123"))

    print("\nfilenames cannot collide across granularity or side")
    names = {out_path("/d", "NAS100_USD", p, g)
             for p in ("B", "A", "M") for g in ("M1", "M5", "M15")}
    check("9 distinct paths for 3 sides x 3 granularities", len(names) == 9)
    check("M1 bid is named as expected",
          out_path("/d", "NAS100_USD", "B", "M1") == "/d/nas100usd_bid_1m.csv",
          out_path("/d", "NAS100_USD", "B", "M1"))

    print("\nresume reads the last row, and the gate can fail")
    tmp = "/tmp/_pull_m1_test"
    os.makedirs(tmp, exist_ok=True)
    p = os.path.join(tmp, "t.csv")
    with open(p, "w") as fh:
        fh.write("time,open,high,low,close,volume\n")
        for i in range(5):
            fh.write(f"2026-03-02 09:0{i}:00,1,1,1,1,1\n")
    check("last timestamp recovered exactly",
          last_time(p) == datetime(2026, 3, 2, 9, 4, tzinfo=timezone.utc),
          str(last_time(p)))
    with open(p, "w") as fh:
        fh.write("time,open,high,low,close,volume\n")
    check("a header-only file resumes as None -- gate fires",
          last_time(p) is None)
    check("a missing file resumes as None",
          last_time(os.path.join(tmp, "nope.csv")) is None)
    with open(p, "w") as fh:
        fh.write("time,open,high,low,close,volume\n")
        fh.write("not-a-date,1,1,1,1,1\n")
    check("an unparseable tail does not crash and does not invent a date",
          last_time(p) is None)

    print("\nprobe arithmetic")
    check("2 sigma on 2 years is 1.41", abs(2 / 2 ** 0.5 - 1.414) < 0.001)
    check("2 sigma on 20 years is 0.45", abs(2 / 20 ** 0.5 - 0.447) < 0.001)
    check("more history always lowers the bar",
          2 / 10 ** 0.5 < 2 / 3 ** 0.5)

    print("\nverify catches what it is meant to catch")
    import pandas as pd
    good = pd.DataFrame({
        "time": pd.date_range("2026-01-01", periods=200, freq="1min",
                              tz="UTC"),
        "open": 1.0, "high": 1.1, "low": 0.9, "close": 1.0, "volume": 1.0})
    for p_ in ("bid", "ask", "mid"):
        good.to_csv(os.path.join(tmp, f"synthusd_{p_}_1m.csv"), index=False)
    rc_good = do_verify(tmp, ["SYNTH_USD"], "M1")
    check("a clean synthetic set verifies OK", rc_good == 0)

    bad = good.copy()
    bad.loc[50, "high"] = 0.5                     # high < low
    bad = pd.concat([bad, bad.iloc[[10]]])        # duplicate timestamp
    bad.to_csv(os.path.join(tmp, "brokenusd_bid_1m.csv"), index=False)
    cross = good.copy()
    cross["close"] = 0.5                          # ask below bid
    cross.to_csv(os.path.join(tmp, "brokenusd_ask_1m.csv"), index=False)
    rc_bad = do_verify(tmp, ["BROKEN_USD"], "M1")
    check("a corrupted set FAILS -- the gate is not decorative", rc_bad != 0)

    print("\nderived mid reconstructs the average exactly")
    lo = good.copy(); lo[["open", "high", "low", "close"]] -= 0.001
    hi = good.copy(); hi[["open", "high", "low", "close"]] += 0.003
    lo.to_csv(os.path.join(tmp, "dermusd_bid_1m.csv"), index=False)
    hi.to_csv(os.path.join(tmp, "dermusd_ask_1m.csv"), index=False)
    check("derive runs", do_derive_mid(tmp, ["DERM_USD"], "M1") == 0)
    got = pd.read_csv(os.path.join(tmp, "dermusd_mid_1m.csv"))
    check("mid close equals (bid+ask)/2 to 1e-12",
          float((got["close"] - (good["close"] + 0.001)).abs().max()) < 1e-12)
    check("derive REFUSES when a side is missing -- gate fires",
          do_derive_mid(tmp, ["ABSENT_USD"], "M1") != 0)

    print(f"\n{'ALL PASS' if ok else 'FAILURES ABOVE'}")
    return 0 if ok else 1


# ------------------------------------------------------------------ main

def main():
    ap = argparse.ArgumentParser(
        description="Probe and pull OANDA M1/M5 bid/ask candles.")
    ap.add_argument("--fetch-oanda-dir", default=DEFAULT_FO_DIR)
    ap.add_argument("--data-dir", default=os.path.normpath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "data")))
    ap.add_argument("--instruments", default=DEFAULT_INSTRUMENTS)
    #: v1.1 -- H1/H4/D added. TF_SUFFIX already carried them; only this
    #: list blocked them, and a cross-sectional test needs YEARS of
    #: history across many instruments, which is unreachable at M15.
    #: The 15m universe on disk is 68 days: a 2-sigma read there needs a
    #: Sharpe of 4.59, and sampling more finely does not help because the
    #: standard error of an annualised Sharpe goes as 1/sqrt(YEARS), not
    #: 1/sqrt(bars).
    ap.add_argument("--granularity", default="M1",
                    choices=sorted(TF_SUFFIX))
    ap.add_argument("--sides", default="B,A",
                    help="B=bid A=ask M=mid. Default B,A: OANDA's mid is "
                         "exactly (bid+ask)/2 -- verified to 9e-13 on the "
                         "M15 set -- so pulling it wastes a third of the "
                         "requests. Use --derive-mid instead.")
    ap.add_argument("--derive-mid", action="store_true",
                    help="write the mid file from bid/ask already on disk, "
                         "no network")
    ap.add_argument("--start", default="2005-01-01")
    ap.add_argument("--env", default="live", choices=["live", "practice"])
    ap.add_argument("--pause", type=float, default=0.15)
    ap.add_argument("--probe-floor", default=None,
                    help="YYYY-MM-DD to start the depth probe from; only "
                         "needed to prove the default floor is not binding")
    ap.add_argument("--max-pages", type=int, default=2000)
    ap.add_argument("--check", action="store_true", help="auth only")
    ap.add_argument("--probe", action="store_true", help="history depth")
    ap.add_argument("--pull", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        sys.exit(self_test(a.fetch_oanda_dir))

    instruments = [x.strip().upper() for x in a.instruments.split(",")
                   if x.strip()]
    for ins in instruments:
        if "_" not in ins:
            raise SystemExit(f"'{ins}' is not OANDA naming -- use NAS100_USD")

    if a.derive_mid:
        sys.exit(do_derive_mid(a.data_dir, instruments, a.granularity))

    if a.verify:
        sys.exit(do_verify(a.data_dir, instruments, a.granularity))

    fo = load_fo(a.fetch_oanda_dir)
    #: v1.1. TF_SUFFIX is this file's naming table; GRANULARITY_SECONDS is
    #: fetch_oanda's stepping table. A granularity present in one and
    #: absent from the other would KeyError deep inside pagination, after
    #: requests had already been spent. Checked here, before anything.
    if a.granularity not in getattr(fo, "GRANULARITY_SECONDS", {}):
        raise SystemExit(
            f"\n  STOP: fetch_oanda.py does not know granularity "
            f"{a.granularity!r}.\n"
            f"  It knows: "
            f"{', '.join(sorted(getattr(fo, 'GRANULARITY_SECONDS', {})))}\n"
            f"  This file's naming table has it, fetch_oanda's stepping "
            f"table does not,\n  and pagination would fail partway "
            f"through with requests already spent.")
    host = fo.HOSTS[a.env]
    token = fo.load_token()
    os.makedirs(a.data_dir, exist_ok=True)

    print(f"pull_m1.py v{VERSION}   host {host}   granularity {a.granularity}")
    print(f"  data dir: {a.data_dir}")

    if a.check:
        rows = fo.parse_candles(fo.api_get(
            fo.build_url(host, instruments[0], a.granularity, "M",
                         datetime.now(timezone.utc) - timedelta(days=3),
                         count=10), token), "M")
        print(f"\n  auth OK -- {len(rows)} recent {instruments[0]} "
              f"{a.granularity} candles")
        if rows:
            print(f"  latest: {rows[-1]['time']}  close {rows[-1]['close']}")
        return

    if a.probe:
        if a.probe_floor:
            global EARLIEST
            EARLIEST = datetime.strptime(
                a.probe_floor, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            print(f"  probe floor overridden to {EARLIEST:%Y-%m-%d}")
        #: v1.2. This was hardcoded to ["M1", "M5"], so a run invoked with
        #: --granularity H1 printed "granularity H1" in its header and
        #: then probed M1 and M5. The header and the table disagreed and
        #: nothing said so. The requested grain is probed first; M1 and M5
        #: follow only if they were not what was asked for.
        grans = [a.granularity] + [g for g in ("M1", "M5")
                                   if g != a.granularity]
        do_probe(fo, host, token, instruments, grans, a.pause)
        return

    if not a.pull:
        ap.print_help()
        return

    start = datetime.strptime(a.start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    sides = [s.strip().upper() for s in a.sides.split(",") if s.strip()]
    t0 = time.time()
    grand = 0
    for ins in instruments:
        for p in sides:
            grand += pull_one(fo, host, token, ins, a.granularity, p,
                              a.data_dir, a.pause, start, a.max_pages)
    print(f"\n{grand:,} rows in {(time.time()-t0)/60:.1f} minutes")
    print(f"\nnow run:  python pull_m1.py --verify --granularity "
          f"{a.granularity} --instruments {a.instruments}")


if __name__ == "__main__":
    main()
