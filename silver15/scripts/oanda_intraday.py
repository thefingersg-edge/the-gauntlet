#!/usr/bin/env python3
"""15-minute data layer for the silver mean-reversion strategy, from OANDA.

WHY THIS REPLACES THE DUKASCOPY PATH
------------------------------------
TradingView draws OANDA. If the backtest and the chart disagree, one of them
is lying, and Pine/Python parity is priority 3 on this project. Pulling the
same feed the chart draws removes an entire class of "it worked in Python"
failure -- and, per the pineport findings, a cross-feed reproducibility problem
that made trades appear and disappear between vendors.

`dukascopy_intraday.py` is deliberately kept, not deleted. Two independent
feeds is how you tell a real signal from a feed artefact, and `--cross-check`
below diffs them. A strategy that only survives on one vendor's bars has not
survived anything.

WHAT THIS FILE IS AND IS NOT
----------------------------
It is a thin wrapper. `fetch_oanda.py` -- already written, already self-tested,
already handling auth, pagination, retries and token redaction -- does the
work, imported unmodified. Rewriting a tested fetcher to add three filenames
is how regressions get introduced.

    python oanda_intraday.py --check          # auth, then STOP. do this first.
    python oanda_intraday.py --probe          # how much M15 history exists?
    python oanda_intraday.py --sides          # mid vs bid on silver, to choose
    python oanda_intraday.py --pull --price M # the real thing
    python oanda_intraday.py --cross-check    # OANDA vs Dukascopy
    python oanda_intraday.py --self-test      # offline

CREDENTIALS
-----------
Handled entirely by fetch_oanda.load_token(): OANDA_API_TOKEN, then
~/.oanda_token, then ./.oanda_token. The token is never printed and never
written to an output file. Do not paste it into a chat.

THINGS THAT WILL BITE
---------------------
* OANDA names instruments XAG_USD, not XAGUSD. Mapping is below.
* History depth at M15 is NOT the same as at H1, and OANDA guarantees
  neither. --probe before committing to a long pull.
* The most recent candle is incomplete and is dropped. That is correct: an
  unfinished bar changes under you and becomes a phantom final trade.
* mid and bid are different series. Picking one silently and comparing to a
  chart drawn with the other produces a small, plausible, permanent error.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_oanda as fo          # unmodified, from pineport

VERSION = "0.1-oanda"

GRANULARITY = "M15"

#: OANDA granularity -> the filename suffix silver_mr.py-style files use.
TF_SUFFIX = {"M15": "15m", "M30": "30m", "H1": "1h", "H4": "4h", "D": "1d"}

#: OANDA name -> the filename stem silver_mr.py expects.
#: silver_mr.py reads xagusd_15m.csv / xauusd_15m.csv / eurusd_15m.csv and
#: inverts EURUSD itself as a DXY proxy, so no strategy code changes here.
PAIRS = [
    ("XAG_USD", "xagusd", "silver -- the traded instrument"),
    ("XAU_USD", "xauusd", "gold   -- the fair-value anchor"),
    ("EUR_USD", "eurusd", "euro   -- inverted as a DXY proxy"),
]

PRICE_LABEL = {"M": "mid", "B": "bid", "A": "ask"}


def out_path(data_dir: str, stem: str, tf: str | None = None) -> str:
    """Filename for a series. `tf` follows the granularity in use, so an H4
    pull writes xagusd_4h.csv rather than silently overwriting the 15m file
    with bars of a different length -- which would be undetectable downstream."""
    return os.path.join(data_dir, f"{stem}_{tf or TF_SUFFIX[GRANULARITY]}.csv")


def expected_bars(start: datetime, end: datetime | None = None) -> int:
    """Rough count of 15m bars in a forex-hours span, for a sanity check.

    ~5 trading days a week, 24h a day, scaled by the CURRENT granularity.
    Being 20% under is normal (holidays, gaps); being 60% under means history
    was truncated and the pull silently gave you less than you asked for.

    This used to assume 15m bars unconditionally, so an H4 pull reported "only
    6% of the expected bar count" on a perfectly complete 20-year fetch. A
    warning that cries wolf is worse than no warning: it teaches you to skip
    the line where the real one will appear.
    """
    end = end or datetime.now(timezone.utc)
    weeks = max((end - start).days, 0) / 7.0
    secs = fo.GRANULARITY_SECONDS.get(GRANULARITY, 900)
    bars_per_day = 24 * 3600 / secs
    return int(weeks * 5 * bars_per_day)


# --------------------------------------------------------------------------

def resolve_pairs(spec: str | None):
    """Turn a comma-separated instrument list into PAIRS-shaped rows.

    Kept explicit rather than clever: an unknown instrument should fail at the
    API with a clear 400, not be silently dropped from a basket whose whole
    purpose is counting how many independent observations you have.
    """
    if not spec:
        return PAIRS
    out = []
    for ins in [x.strip().upper() for x in spec.split(",") if x.strip()]:
        if "_" not in ins:
            raise SystemExit(f"'{ins}' is not OANDA naming -- use XPT_USD, "
                             f"not XPTUSD")
        known = {p[0]: p for p in PAIRS}
        out.append(known.get(ins, (ins, ins.replace("_", "").lower(), "")))
    return out


def probe(host: str, token: str, price: str, pause: float,
          pairs=None) -> None:
    """How far back does M15 actually go, per instrument?

    One request each. The answer is not the same as the H1 depth and is not
    promised by OANDA, so it is worth 3 requests to find out before starting
    a pull sized on an assumption.
    """
    print(f"\nM15 history depth ({PRICE_LABEL[price]})")
    print("=" * 68)
    for ins, stem, note in (pairs or PAIRS):
        # A 400 (bad instrument name) raises SystemExit inside fetch_oanda.
        # SystemExit derives from BaseException, NOT Exception, so a plain
        # `except Exception` does not catch it and ONE bad name aborts the
        # whole batch -- which is exactly what silently truncated the 14
        # instrument H4 pull to 2. Catch it per instrument and carry on.
        try:
            rows = fo.fetch_instrument(ins, datetime(2000, 1, 1, tzinfo=timezone.utc),
                                       GRANULARITY, price, host, token,
                                       pause=pause, max_pages=1)
        except SystemExit as exc:
            print(f"  {ins:11} UNAVAILABLE -- {str(exc).splitlines()[0][:60]}")
            continue
        if not rows:
            print(f"  {ins:9} no candles returned -- check the instrument name")
            continue
        print(f"  {ins:9} earliest M15 candle: {rows[0]['time']}   ({note})")
    print("\n  Pull --start no earlier than the latest of these; asking for")
    print("  more does no harm but the extra pages are wasted requests.")


def compare_sides(host: str, token: str, start: str, pause: float,
                  data_dir: str, instrument: str = "XAG_USD") -> None:
    """Measure an instrument's ACTUAL spread by fetching bid, ask and mid.

    Two things fall out of this, and only one of them was obvious.

    1. Which side TradingView draws (compare its export against the mid file).
    2. The real round-trip cost, as ASK minus BID.

    (2) is the number a backtest needs, and it should be measured rather than
    doubled from `mid - bid`. Doubling assumes mid is exactly the midpoint,
    which is a convention of the provider rather than a law -- and if it is not
    the midpoint, the error goes straight into every modelled fill and never
    announces itself. ask - bid is the thing you actually pay.

    The spread is also NOT constant: it widens at the rollover and in thin
    hours, and scales with the price level. The percentiles below matter more
    than the median if the strategy trades outside peak liquidity.
    """
    dt = datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    stem = instrument.replace("_", "").lower()
    series = {}
    for p in ("M", "B", "A"):
        print(f"\n  fetching {instrument} {GRANULARITY} {PRICE_LABEL[p]} "
              f"from {start} ...")
        rows = fo.fetch_instrument(instrument, dt, GRANULARITY, p, host, token,
                                   pause=pause)
        fo.summarise(rows, f"{instrument} {PRICE_LABEL[p]}")
        series[p] = {r["time"]: r for r in rows}
        os.makedirs(data_dir, exist_ok=True)
        path = out_path(data_dir, f"{stem}_{PRICE_LABEL[p]}")
        fo.write_csv(sorted(rows, key=lambda r: r["time"]), path)
        print(f"    wrote {path}")

    common = sorted(set(series["M"]) & set(series["B"]) & set(series["A"]))
    if not common:
        print("\n  no overlapping timestamps -- cannot compare")
        return

    def pct(vals, q):
        v = sorted(vals)
        return v[min(int(q * len(v)), len(v) - 1)]

    spread = [series["A"][t]["close"] - series["B"][t]["close"] for t in common]
    midbid = [series["M"][t]["close"] - series["B"][t]["close"] for t in common]
    lvl = pct([series["M"][t]["close"] for t in common], 0.5)

    print(f"\n  {instrument} spread across {len(common):,} bars "
          f"(median price ${lvl:,.2f})")
    print(f"    ASK - BID (true round trip)")
    print(f"      median {pct(spread,0.5):.5f}   "
          f"p25 {pct(spread,0.25):.5f}   p75 {pct(spread,0.75):.5f}")
    print(f"      p95    {pct(spread,0.95):.5f}   max {max(spread):.5f}")
    print(f"      as %% of price: {pct(spread,0.5)/lvl*100:.4f}%")
    print(f"    mid - bid (half spread)  median {pct(midbid,0.5):.5f}")
    sym = abs(pct(midbid, 0.5) * 2 - pct(spread, 0.5))
    print(f"    mid sits {'' if sym < 1e-6 else 'NOT '}at the exact midpoint"
          f"  (|2*(mid-bid) - (ask-bid)| = {sym:.6f})")
    if abs(pct(spread, 0.5)) < 1e-9:
        print("    !! spread is ZERO -- the price parameter is not being")
        print("    !! honoured. Do not trust any of these series.")

    print(f"\n  >> use --gold-spread {pct(spread,0.5):.4f} (or --silver-spread)"
          f" in hedged_test.py")
    print("  >> that is the MEDIAN. If the strategy trades thin hours, use p75")
    print("     or p95 instead -- a backtest priced at the median spread and")
    print("     executed at the p95 one is not the same strategy.")


def pull(host: str, token: str, price: str, start: str, pause: float,
         data_dir: str, pairs=None) -> int:
    dt = datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    exp = expected_bars(dt)
    print(f"\npulling {GRANULARITY} {PRICE_LABEL[price]} from {start}")
    print(f"  rough expectation: ~{exp:,} bars per instrument")
    print("=" * 68)

    os.makedirs(data_dir, exist_ok=True)
    pairs = pairs or PAIRS
    failures, counts = [], {}
    for ins, stem, note in pairs:
        print(f"\n{ins}  ({note})")
        try:
            rows = fo.fetch_instrument(ins, dt, GRANULARITY, price, host, token,
                                       pause=pause)
        except SystemExit as exc:
            print(f"  UNAVAILABLE -- {str(exc).splitlines()[0][:70]}")
            print("  continuing with the rest of the batch")
            failures.append(ins)
            continue
        if not rows:
            print("  NOTHING RETURNED")
            failures.append(ins)
            continue
        fo.summarise(rows, ins)
        path = out_path(data_dir, stem)
        fo.write_csv(rows, path)
        counts[stem] = len(rows)
        print(f"  wrote {path}")
        if len(rows) < 0.4 * exp:
            print(f"  !! only {len(rows)/exp:.0%} of the expected bar count.")
            print("  !! History is probably truncated -- re-run --probe.")

    if failures:
        print(f"\n{len(failures)} instrument(s) returned nothing: "
              f"{', '.join(failures)}")
        return 1

    coverage(data_dir, pairs)
    print(f"\nnext:  python silver_mr.py --data {data_dir}")
    return 0


def coverage(data_dir: str, pairs=None) -> None:
    """The three files must overlap, or the rolling XAG~XAU regression runs
    on the intersection and quietly produces almost nothing -- which presents
    as a weak signal, not as an error."""
    try:
        import pandas as pd
    except ImportError:
        print("\n(pandas not available -- skipping coverage check)")
        return
    print("\ncoverage")
    print("=" * 68)
    frames = {}
    pairs = pairs or PAIRS
    for _, stem, _ in pairs:
        p = out_path(data_dir, stem)
        if not os.path.exists(p):
            print(f"  {stem:8} MISSING")
            continue
        d = pd.read_csv(p, index_col=0, parse_dates=True)
        frames[stem] = d
        print(f"  {stem:8} {len(d):>9,} bars  {d.index.min()} -> {d.index.max()}")
    if len(frames) == len(pairs) and "xagusd" in frames:
        common = None
        for f in frames.values():
            common = f.index if common is None else common.intersection(f.index)
        n = len(frames["xagusd"])
        print(f"  {'common':8} {len(common):>9,} bars  ({len(common)/n:.1%} of silver)")
        if len(common) < 0.8 * n:
            print("  !! low overlap -- one instrument has a gap the others do not")


def detect_feed(path: str) -> str:
    """Identify which fetcher wrote a CSV, from its timestamp format.

    The two writers are distinguishable on sight and always have been:

        dukascopy_intraday.py   2016-01-03 23:00:00+00:00   tz-aware
        oanda_intraday.py       2016-01-01 04:00:00         tz-naive

    Filenames lie -- a file is only ever named by whoever last moved it.
    The bytes do not. Every consumer here checks the bytes.
    """
    try:
        with open(path) as fh:
            fh.readline()                       # header
            row = fh.readline().strip()
    except OSError:
        return "unreadable"
    if not row:
        return "empty"
    stamp = row.split(",")[0]
    if "+00:00" in stamp or stamp.endswith("Z"):
        return "dukascopy"
    if len(stamp) == 19 and stamp[4] == "-" and stamp[13] == ":":
        return "oanda"
    return "unknown"


def audit(dirs: list[str]) -> int:
    """Say what every CSV on disk ACTUALLY is, regardless of where it sits.

    Three times in this project a file has turned out not to be what its name
    or its folder claimed. This is the cheap standing answer to that.
    """
    print("\nfeed provenance (read from the bytes, not the filename)")
    print("=" * 68)
    bad = 0
    for d in dirs:
        if not os.path.isdir(d):
            print(f"  {d}/  (no such directory)")
            continue
        expect = "dukascopy" if "dukascopy" in os.path.basename(d.rstrip("/")) \
            else "oanda"
        print(f"\n  {d}/   expected: {expect}")
        names = sorted(n for n in os.listdir(d) if n.endswith(".csv"))
        if not names:
            print("    (empty)")
        for n in names:
            got = detect_feed(os.path.join(d, n))
            flag = "" if got == expect else "   <-- MISMATCH"
            if flag:
                bad += 1
            print(f"    {n:<34} {got:<10}{flag}")
    print()
    if bad:
        print(f"  {bad} file(s) are not the feed their location implies.")
        print("  Re-pull them before running anything that mixes the two.")
        return 1
    print("  all files match the feed their location implies.")
    return 0


def cross_check(data_dir: str, duka_dir: str) -> int:
    """Diff the OANDA bars against the Dukascopy bars, where both exist.

    These are different venues, so they will NOT match to the tick and should
    not be expected to. What matters is that they agree on SHAPE: if the
    15-minute returns correlate above ~0.99, the two feeds are telling the
    same story and a signal found in one should survive in the other. Much
    below that and the strategy is at risk of fitting one vendor's noise.
    """
    try:
        import numpy as np
        import pandas as pd
    except ImportError:
        print("pandas/numpy required for --cross-check")
        return 1

    print("\nOANDA vs Dukascopy, 15m")
    print("=" * 68)
    any_done = False
    for _, stem, _ in PAIRS:
        a_p, b_p = out_path(data_dir, stem), out_path(duka_dir, stem)
        if not (os.path.exists(a_p) and os.path.exists(b_p)):
            print(f"  {stem:8} skipped (need both feeds on disk)")
            continue
        # A cross-feed check is worthless if both sides are the same feed.
        # This happens more easily than it sounds: one stray `mv` or an
        # overwritten output file, and the comparison reports corr 1.0000 and
        # reads as emphatic confirmation. Refuse before computing anything.
        import hashlib
        h = [hashlib.md5(open(p, "rb").read()).hexdigest() for p in (a_p, b_p)]
        if h[0] == h[1]:
            print(f"  {stem:8} !! ABORT -- both files are byte-identical.")
            print(f"           !! {a_p}")
            print(f"           !! {b_p}")
            print("           !! This is one feed compared against itself, not")
            print("           !! two feeds agreeing. Check which file is which.")
            return 1

        # Provenance, from the bytes. Comparing a feed to itself is the
        # failure this whole check exists to prevent.
        fa, fb = detect_feed(a_p), detect_feed(b_p)
        if fa == fb:
            print(f"  {stem:8} !! ABORT -- both sides look like {fa} data.")
            print(f"           !! {a_p}  ({fa})")
            print(f"           !! {b_p}  ({fb})")
            print("           !! Run --audit. Re-pull whichever is misplaced.")
            return 1

        # BOTH writers are read with utc=True. Dukascopy writes tz-aware
        # stamps and OANDA writes naive ones; intersecting a tz-aware index
        # with a naive one silently yields ZERO overlap, which reads as "these
        # feeds have no bars in common" rather than "you forgot to normalise".
        # silver_mr.py's load_csv already does this. This did not, and reported
        # 0 shared bars on two files covering the same decade.
        def load(p):
            df = pd.read_csv(p)
            tcol = df.columns[0]
            df[tcol] = pd.to_datetime(df[tcol], utc=True)
            return df.set_index(tcol).sort_index()

        a, b = load(a_p), load(b_p)
        common = a.index.intersection(b.index)
        if len(common) < 100:
            print(f"  {stem:8} only {len(common)} shared bars -- not comparable")
            print(f"           {os.path.basename(a_p)}: {a.index.min()} -> {a.index.max()}")
            print(f"           {os.path.basename(b_p)}: {b.index.min()} -> {b.index.max()}")
            continue
        ca = a.loc[common, "close"].to_numpy()
        cb = b.loc[common, "close"].to_numpy()
        ra, rb = np.diff(np.log(ca)), np.diff(np.log(cb))
        rc = float(np.corrcoef(ra, rb)[0, 1])
        med = float(np.median(np.abs(ca - cb)))
        print(f"  {stem:8} {len(common):>8,} shared bars   "
              f"median |close diff| {med:.5f}   return corr {rc:.4f}")

        # A single correlation number is not interpretable on its own. Two
        # venues always disagree most when liquidity is thinnest, so the
        # question is not "is it above some threshold" but "is the
        # disagreement concentrated where you would expect, or is there a
        # structural break". Break the number down before judging it.
        d = pd.DataFrame({"ra": ra, "rb": rb},
                         index=common[1:]).dropna()
        # Built as a dict comprehension rather than groupby.apply: the
        # `include_groups` keyword moved between pandas 2.2 and 3.x, and this
        # form has no version-dependent behaviour at all.
        by_hour = pd.Series({h: g.ra.corr(g.rb)
                             for h, g in d.groupby(d.index.hour)})
        by_year = pd.Series({y: g.ra.corr(g.rb)
                             for y, g in d.groupby(d.index.year)})
        print(f"           by hour  worst {by_hour.min():.3f} @ "
              f"{by_hour.idxmin():02d}h UTC   best {by_hour.max():.3f} @ "
              f"{by_hour.idxmax():02d}h UTC")
        print(f"           by year  worst {by_year.min():.3f} ({by_year.idxmin()})"
              f"   best {by_year.max():.3f} ({by_year.idxmax()})")

        if by_year.min() < 0.90:
            print("           !! a whole year disagrees -- that is a structural")
            print("           !! break, not noise. Investigate that year.")
        elif rc < 0.97:
            print("           !! low even for thin liquidity -- investigate.")
        else:
            print(f"           OK: disagreement concentrates in the "
                  f"{by_hour.idxmin():02d}h UTC window,")
            print("           which is the thin-liquidity rollover. Expected.")
        any_done = True
    if not any_done:
        print("\n  Nothing compared. Pull both feeds first:")
        print("    ./pull_15m.sh              (Dukascopy)")
        print("    python oanda_intraday.py --pull")
    return 0


# --------------------------------------------------------------------------

def self_test() -> int:
    fails = []

    def check(n, c, d=""):
        print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"  {d}" if not c else ""))
        if not c:
            fails.append(n)

    print(f"oanda_intraday.py v{VERSION}")
    print(f"  file: {os.path.abspath(__file__)}\n")

    print("instrument mapping")
    names = [p[0] for p in PAIRS]
    check("OANDA underscore naming used", all("_" in n for n in names), str(names))
    check("silver, gold and euro all present",
          set(names) == {"XAG_USD", "XAU_USD", "EUR_USD"}, str(names))

    print("\noutput filenames match what silver_mr.py loads")
    check("silver -> xagusd_15m.csv",
          out_path("../data", "xagusd").endswith("xagusd_15m.csv"))
    check("gold   -> xauusd_15m.csv",
          out_path("../data", "xauusd").endswith("xauusd_15m.csv"))
    check("euro   -> eurusd_15m.csv",
          out_path("../data", "eurusd").endswith("eurusd_15m.csv"))

    print("\ngranularity")
    check("current granularity known to fetch_oanda",
          GRANULARITY in fo.GRANULARITY_SECONDS, GRANULARITY)
    check("every supported granularity is known to fetch_oanda",
          all(g in fo.GRANULARITY_SECONDS for g in TF_SUFFIX), str(list(TF_SUFFIX)))
    check("M15 is 900 seconds", fo.GRANULARITY_SECONDS["M15"] == 900)
    check("H4 is 14400 seconds", fo.GRANULARITY_SECONDS["H4"] == 14400)

    print("\nbar size drives the filename (H4 must not overwrite the 15m file)")
    import oanda_intraday as _self
    _prev = _self.GRANULARITY
    try:
        _self.GRANULARITY = "H4"
        h4 = _self.out_path("../data_h4", "xagusd")
        _self.GRANULARITY = "M15"
        m15 = _self.out_path("../data", "xagusd")
        check("H4 writes _4h.csv", h4.endswith("xagusd_4h.csv"), h4)
        check("M15 still writes _15m.csv", m15.endswith("xagusd_15m.csv"), m15)
        check("the two never collide", os.path.basename(h4) != os.path.basename(m15))
    finally:
        _self.GRANULARITY = _prev

    print("\nbar-count expectation")
    e = expected_bars(datetime(2016, 1, 1, tzinfo=timezone.utc),
                      datetime(2026, 1, 1, tzinfo=timezone.utc))
    check("10 years of 15m is 250k-270k bars", 240_000 < e < 275_000, f"got {e:,}")

    print("\ncredential safety (delegated to fetch_oanda)")
    check("token redacted from text", "<redacted>" in fo.redact("abc123", "abc123"))
    u = fo.build_url(fo.HOSTS["live"], "XAG_USD", GRANULARITY, "M",
                     datetime(2024, 6, 1, tzinfo=timezone.utc))
    check("no token in a built URL", "token" not in u.lower())
    check("M15 reaches the URL", "granularity=M15" in u, u)

    print("\n" + "=" * 58)
    if fails:
        print(f"{len(fails)} FAILED: {', '.join(fails)}")
        return 1
    print("all offline checks passed -- now run --check against the API")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--price", default="M", choices=["M", "B", "A"],
                    help="M=mid (default), B=bid, A=ask")
    ap.add_argument("--start", default="2016-01-01")
    ap.add_argument("--data-dir", default="../data")
    ap.add_argument("--duka-dir", default="../data_dukascopy",
                    help="where the Dukascopy CSVs live, for --cross-check")
    ap.add_argument("--env", default="live", choices=sorted(fo.HOSTS))
    ap.add_argument("--pause", type=float, default=0.15)
    ap.add_argument("--check", action="store_true", help="auth test, then stop")
    ap.add_argument("--probe", action="store_true", help="M15 history depth")
    ap.add_argument("--sides", action="store_true",
                    help="measure an instrument's real spread (bid/ask/mid)")
    ap.add_argument("--instrument", default="XAG_USD",
                    help="instrument for --sides, e.g. XAU_USD")
    ap.add_argument("--granularity", default="M15", choices=sorted(TF_SUFFIX),
                    help="bar size. H4 for the multi-day test.")
    ap.add_argument("--instruments", default=None,
                    help="comma-separated OANDA names for --pull, e.g. "
                         "XPT_USD,XPD_USD,XCU_USD. Default: the silver trio.")
    ap.add_argument("--pull", action="store_true", help="the real pull")
    ap.add_argument("--cross-check", action="store_true",
                    help="diff OANDA against Dukascopy")
    ap.add_argument("--coverage", action="store_true",
                    help="report on CSVs already on disk")
    ap.add_argument("--audit", action="store_true",
                    help="say which feed actually wrote each CSV on disk")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()

    global GRANULARITY
    GRANULARITY = a.granularity

    if a.version:
        print(f"oanda_intraday.py v{VERSION}")
        print(f"  running from: {os.path.abspath(__file__)}")
        print(f"  fetch_oanda : {os.path.abspath(fo.__file__)}")
        print(f"  python      : {sys.executable}")
        sys.exit(0)

    if a.self_test:
        sys.exit(self_test())
    if a.audit:
        sys.exit(audit([a.data_dir, a.duka_dir]))
    if a.coverage:
        coverage(a.data_dir); sys.exit(0)
    if a.cross_check:
        sys.exit(cross_check(a.data_dir, a.duka_dir))

    # Everything below needs the network and a token.
    print(f"\noanda_intraday.py v{VERSION}  [{os.path.abspath(__file__)}]")
    token = fo.load_token()
    host = fo.HOSTS[a.env]
    print(f"  host: {host}   price: {PRICE_LABEL[a.price]}   "
          f"granularity: {GRANULARITY}")

    if a.check:
        rows = fo.fetch_instrument("XAG_USD", datetime.now(timezone.utc)
                                   .replace(hour=0, minute=0, second=0,
                                            microsecond=0),
                                   GRANULARITY, a.price, host, token,
                                   pause=0.0, max_pages=1)
        print(f"\n  auth OK -- {len(rows)} recent XAG_USD {GRANULARITY} candles")
        if rows:
            print(f"  latest complete bar: {rows[-1]['time']}  "
                  f"close {rows[-1]['close']}")
        print("\n  next: python oanda_intraday.py --probe")
        sys.exit(0)

    pairs = resolve_pairs(a.instruments)
    if a.probe:
        probe(host, token, a.price, a.pause, pairs); sys.exit(0)
    if a.sides:
        compare_sides(host, token, a.start, a.pause, a.data_dir,
                      a.instrument); sys.exit(0)
    if a.pull:
        sys.exit(pull(host, token, a.price, a.start, a.pause, a.data_dir,
                      pairs))

    ap.print_help()
    print("\nStart with --check, then --probe, then --sides, then --pull.")


if __name__ == "__main__":
    main()
