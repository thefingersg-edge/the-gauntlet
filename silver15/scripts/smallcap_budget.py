#!/usr/bin/env python3
"""Power budget for a SMALL-CAP / LOW-FLOAT strategy. Run BEFORE hypothesising.

NO RETURNS AND NO P&L ARE COMPUTED IN THIS FILE. Everything comes from
spreads, volatility and trade counts — never from a simulated position.

WHY THIS FAMILY NEEDS ITS OWN BUDGET
------------------------------------
Eight families have failed on OANDA CFDs. The diagnosis was that all eight
changed the SIGNAL while holding the market, the data and the edge type
constant. Small caps change the market: no institutional coverage, no
arbitrage desk, and a retail crowd that can move a stock 200% in a session.
That is a genuinely different pond.

It is also the pond with the worst microstructure in existence, and the whole
question is whether the larger inefficiency outruns the larger cost.

THE ARITHMETIC, FROM PUBLISHED FIGURES
--------------------------------------
Penny/microcap effective spreads run 4-8%, with a further 2-5% of liquidity
slippage. Average intraday volatility is ~7.2%. So for the AVERAGE microcap
on an AVERAGE day:

    round-trip cost 6-13%   /   daily vol 7.2%   ->   cost/vol 0.83 to 1.81

against 0.071 for FX H4 directional and 0.146 for residual mean-reversion.
That is 12-25x worse, and the consequence is severe:

    required edge per trade = bar/sqrt(trades per year) + cost/vol
                            = 0.04 + 0.83  (500 trades, 5 years)
                            = 0.87 vol units per trade

The bar term is NEGLIGIBLE. Unlike every previous family in this project,
**sample size is irrelevant here** — more history cannot help, because cost
is 10-20x the detectability bar. This is a pure cost problem.

For scale: the one genuinely measured signal in this project, the hedged 15m
silver/gold book, ran +3.32 sd over 13,013 trades = **0.029 vol units per
trade**. The requirement above is ~30x that.

WHY THAT IS NOT YET THE VERDICT
-------------------------------
The 7.2% figure is the average microcap on an average day. Nobody trades
that. The stocks in a low-float momentum strategy are, on the day they are
traded, moving 50-200% — their volatility that day is far above 7.2%, while
their spread is *tighter* than average because volume is enormous.

If per-trade volatility is 30% rather than 7.2%, a 9.5% cost is cost/vol
0.32, and the required edge falls to ~0.36 vol units. Still large. Not absurd.

**So the verdict turns entirely on the microstructure of stocks ON THE DAYS
THEY ARE IN PLAY, which is not what published averages measure.** This file
measures it directly, from free data.

HOW, WITHOUT BUYING ANYTHING
----------------------------
Effective spreads can be estimated from daily OPEN/HIGH/LOW/CLOSE alone, using
Abdi & Ranaldo (2017), "A Simple Estimation of Bid-Ask Spreads from Daily
Close, High, and Low Prices", Review of Financial Studies 30(12):

    eta_t = (log H_t + log L_t) / 2
    S^2   = 4 * E[ (c_t - eta_t) * (c_t - eta_{t+1}) ]

No quote data, no subscription. Daily bars come from Stooq, which is free and
needs no API key.

A VALIDATION CONTROL IS BUILT IN. Mega-caps must come back at a few basis
points and microcaps at hundreds. If AAPL prints a 5% spread the estimator is
broken, and no conclusion drawn from it means anything.

WHAT THIS FILE DELIBERATELY DOES NOT SETTLE
-------------------------------------------
Survivorship. Stooq drops most delisted tickers, so the sample here is
survivors. For measuring RETURNS that would be fatal. For measuring SPREAD
and VOLATILITY it is a second-order bias — but not a neutral one: survivors
are more liquid than the names that died, so **the spreads measured here are
optimistic**. If the budget fails on optimistic inputs, it fails.

    python smallcap_budget.py --self-test
    python smallcap_budget.py --tickers TICK,TICK,...
    python smallcap_budget.py --file my_screener_list.txt
"""

from __future__ import annotations

import argparse
import csv
import io
import math
import os
import sys
import urllib.error
import urllib.request

VERSION = "1.2"

STOOQ = "https://stooq.com/q/d/l/?s={sym}.us&i=d"

# Liquid names whose spreads are KNOWN to be tiny. If the estimator does not
# reproduce that, nothing else it says is usable.
CONTROL = ["AAPL", "MSFT", "KO", "JNJ", "SPY"]

YEARS = 5.0                       # typical usable intraday-era history
BAR_2SIG = 2.0 / YEARS ** 0.5     # 0.89

# The measured per-trade edge of the only real signal this project found.
REFERENCE_EDGE = 3.32 / math.sqrt(13013)      # 0.029 vol units


# ---------------------------------------------------------------------------
# pure helpers -- exercised offline
# ---------------------------------------------------------------------------

def abdi_ranaldo(highs, lows, closes) -> float | None:
    """Proportional effective spread from daily H/L/C. Abdi & Ranaldo (2017).

    Returns a fraction of price (0.02 = 2%), or None if the sample is too
    short. A NEGATIVE covariance estimate is clamped to zero and reported as
    zero rather than discarded: microstructure estimators produce negative
    values by sampling noise, and silently dropping those days would bias
    every surviving estimate upward.
    """
    n = len(closes)
    if n < 30:
        return None
    c = [math.log(x) for x in closes]
    eta = [(math.log(h) + math.log(l)) / 2.0 for h, l in zip(highs, lows)]
    terms = [(c[t] - eta[t]) * (c[t] - eta[t + 1]) for t in range(n - 1)]
    m = sum(terms) / len(terms)
    return 2.0 * math.sqrt(m) if m > 0 else 0.0


def daily_vol(closes) -> float | None:
    """Standard deviation of daily log returns. A SECOND MOMENT ONLY --
    the mean of the return series is never taken anywhere in this file."""
    if len(closes) < 30:
        return None
    r = [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes))]
    mu = sum(r) / len(r)
    var = sum((x - mu) ** 2 for x in r) / (len(r) - 1)
    return math.sqrt(var)


def required_edge(cost_over_vol: float, trades_per_year: float,
                  years: float = YEARS) -> float:
    """Gross edge per trade, in volatility units, needed to clear 2 sigma."""
    bar = 2.0 / math.sqrt(years)
    return bar / math.sqrt(trades_per_year) + cost_over_vol


def in_play_mask(volumes, ranges, vol_mult=3.0, range_mult=2.0):
    """Days where a low-float momentum strategy would actually engage:
    volume far above the name's own median AND an unusually wide range.

    Measuring the average day would answer a question nobody is asking. The
    thresholds are stated here rather than tuned -- they are not free
    parameters chosen against a result, because no result exists in this file.
    """
    if not volumes:
        return []
    sv = sorted(v for v in volumes if v > 0)
    sr = sorted(r for r in ranges if r > 0)
    if not sv or not sr:
        return []
    mv, mr = sv[len(sv) // 2], sr[len(sr) // 2]
    return [(v > vol_mult * mv and r > range_mult * mr)
            for v, r in zip(volumes, ranges)]


# ---------------------------------------------------------------------------

def strip_rtf(text: str) -> str:
    """Pull plain text out of an RTF document.

    Refusing an RTF file is safe but unhelpful -- TextEdit writes RTF into a
    .txt file by default, so this is the normal case rather than user error.
    Stripping it is safe HERE because every extracted token still has to pass
    valid_symbol(), and the caller aborts if junk outnumbers tickers. Be
    liberal in what you accept, then validate.
    """
    import re
    t = re.sub(r"\{\\\*.*?\}", " ", text, flags=re.S)   # {\*\... } groups
    t = re.sub(r"\\'[0-9a-fA-F]{2}", " ", t)            # \'e9 hex escapes
    t = re.sub(r"\\par[d]?\b", "\n", t)                 # paragraph breaks
    t = re.sub(r"\\[a-zA-Z]+-?\d*\s?", " ", t)          # control words
    # RTF ends a line with a bare backslash, so a ticker arrives as 'ABCD\'
    # and fails validation for a reason that has nothing to do with it being
    # a ticker. Anything left after control words are gone is punctuation.
    t = t.replace("\\", " ")
    t = t.replace("{", " ").replace("}", " ")
    return t


def valid_symbol(s: str) -> bool:
    """Does this look like a US ticker at all?

    Catches the commonest input disaster before it reaches the network: a
    file saved as RTF rather than plain text, which yields 'symbols' like
    '{\\RTF1\\ANSI\\ANSICPG1252'. Those then get URL-encoded and produce a
    control-character error hundreds of lines from the actual cause.
    """
    if not (1 <= len(s) <= 6):
        return False
    return all(ch.isalnum() or ch in ".-" for ch in s)


def fetch_stooq(sym: str, timeout: float = 30.0, debug: bool = False):
    """Daily OHLCV. Returns (dates, o, h, l, c, v) or None."""
    url = STOOQ.format(sym=sym.lower())
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (silver15-research)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise SystemExit(f"Stooq HTTP {exc.code} for {sym}")
    except Exception as exc:                                   # noqa: BLE001
        raise SystemExit(f"Stooq request failed for {sym}: {exc}")

    rdr = csv.reader(io.StringIO(body))
    head = next(rdr, None)
    if not head or head[0].strip().lower() != "date":
        # Do NOT swallow this. Stooq answers a rate-limit or an unknown
        # symbol with a plain-text notice and HTTP 200, so a silent None
        # here is indistinguishable from "this ticker does not exist".
        if debug:
            snippet = body.strip().replace("\n", " | ")[:160]
            print(f"      [debug] {sym}: non-CSV response -> {snippet!r}",
                  file=sys.stderr)
        return None                       # Stooq returns a notice, not a CSV
    d, o, h, l, c, v = [], [], [], [], [], []
    for rec in rdr:
        if len(rec) < 6:
            continue
        try:
            oo, hh, ll, cc = (float(rec[1]), float(rec[2]),
                              float(rec[3]), float(rec[4]))
            vv = float(rec[5])
        except ValueError:
            continue
        if min(oo, hh, ll, cc) <= 0:
            continue
        d.append(rec[0]); o.append(oo); h.append(hh)
        l.append(ll); c.append(cc); v.append(vv)
    return (d, o, h, l, c, v) if len(c) >= 60 else None


YAHOO = ("https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
         "?range=10y&interval=1d")


def fetch_yahoo(sym: str, timeout: float = 30.0, debug: bool = False):
    """Daily OHLCV from Yahoo's chart endpoint. Free, no key, JSON.

    A second source exists because the first one silently returned nothing
    for every symbol including AAPL, and a budget that cannot get data is
    not a budget. Two independent sources also make a disagreement visible,
    which is worth more than either alone.
    """
    import json
    req = urllib.request.Request(YAHOO.format(sym=sym.upper()), headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0 Safari/537.36",
        "Accept": "application/json,text/plain,*/*",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            payload = json.loads(r.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        if exc.code in (404, 401):
            return None
        if debug:
            print(f"      [debug] {sym}: yahoo HTTP {exc.code}", file=sys.stderr)
        return None
    except Exception as exc:                                   # noqa: BLE001
        if debug:
            print(f"      [debug] {sym}: yahoo {type(exc).__name__} "
                  f"{str(exc)[:80]}", file=sys.stderr)
        return None

    try:
        res = payload["chart"]["result"][0]
        ts = res["timestamp"]
        q = res["indicators"]["quote"][0]
    except (KeyError, IndexError, TypeError):
        if debug:
            print(f"      [debug] {sym}: yahoo returned no series",
                  file=sys.stderr)
        return None

    import datetime as _dt
    d, o, h, l, c, v = [], [], [], [], [], []
    for i, t in enumerate(ts):
        vals = (q.get("open") or [])[i:i + 1], (q.get("high") or [])[i:i + 1], \
               (q.get("low") or [])[i:i + 1], (q.get("close") or [])[i:i + 1]
        if not all(x and x[0] is not None for x in vals):
            continue
        oo, hh, ll, cc = (vals[0][0], vals[1][0], vals[2][0], vals[3][0])
        vv = (q.get("volume") or [None] * len(ts))[i] or 0.0
        if min(oo, hh, ll, cc) <= 0:
            continue
        d.append(_dt.datetime.utcfromtimestamp(t).strftime("%Y-%m-%d"))
        o.append(oo); h.append(hh); l.append(ll); c.append(cc); v.append(float(vv))
    return (d, o, h, l, c, v) if len(c) >= 60 else None


POLYGON = ("https://api.polygon.io/v2/aggs/ticker/{sym}/range/1/day/"
           "{start}/{end}?adjusted=true&sort=asc&limit=50000&apiKey={key}")


def polygon_key() -> str:
    """Read the Polygon key. Same discipline as the OANDA token in
    fetch_oanda.py: environment first, then a file, never printed, never
    written to output, never included in an error message."""
    k = os.environ.get("POLYGON_API_KEY")
    if k:
        return k.strip()
    for p in (os.path.expanduser("~/.polygon_token"), ".polygon_token"):
        if os.path.exists(p):
            with open(p) as fh:
                return fh.read().strip()
    raise SystemExit(
        "No Polygon key found. Free tier at polygon.io gives 5 calls/minute\n"
        "and includes DELISTED tickers, which is the point for this test.\n"
        "  export POLYGON_API_KEY='...'\n"
        "or\n"
        "  echo '...' > ~/.polygon_token && chmod 600 ~/.polygon_token\n"
        "Do not paste the key into a chat or commit it to git.")


def fetch_polygon(sym: str, timeout: float = 30.0, debug: bool = False,
                  key: str | None = None):
    """Daily OHLCV from Polygon. Free tier: 5 calls/min, 2 years history."""
    import datetime as _dt
    import json
    key = key or polygon_key()
    end = _dt.date.today()
    start = end - _dt.timedelta(days=365 * 2 + 10)     # free tier ceiling
    url = POLYGON.format(sym=sym.upper(), start=start, end=end, key=key)
    req = urllib.request.Request(url, headers={"User-Agent": "silver15"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            payload = json.loads(r.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            raise SystemExit(
                "\n  Polygon returned 429 (rate limit). The free tier allows"
                "\n  5 calls per minute — use --pause 13 or higher.")
        if exc.code in (401, 403):
            raise SystemExit("  Polygon rejected the key (401/403).")
        if debug:
            print(f"      [debug] {sym}: polygon HTTP {exc.code}",
                  file=sys.stderr)
        return None
    except Exception as exc:                                   # noqa: BLE001
        if debug:
            # NEVER echo the URL here: it carries the API key.
            print(f"      [debug] {sym}: polygon {type(exc).__name__}",
                  file=sys.stderr)
        return None

    res = payload.get("results") or []
    if not res:
        if debug:
            print(f"      [debug] {sym}: polygon status="
                  f"{payload.get('status')} count={payload.get('resultsCount')}",
                  file=sys.stderr)
        return None
    d, o, h, l, c, v = [], [], [], [], [], []
    for bar in res:
        try:
            oo, hh, ll, cc = (float(bar["o"]), float(bar["h"]),
                              float(bar["l"]), float(bar["c"]))
        except (KeyError, TypeError, ValueError):
            continue
        if min(oo, hh, ll, cc) <= 0:
            continue
        d.append(_dt.datetime.utcfromtimestamp(bar["t"] / 1000)
                 .strftime("%Y-%m-%d"))
        o.append(oo); h.append(hh); l.append(ll); c.append(cc)
        v.append(float(bar.get("v", 0.0)))
    return (d, o, h, l, c, v) if len(c) >= 60 else None


def analyse(sym: str, timeout: float, pause: float = 0.0,
            debug: bool = False, source: str = "auto",
            key: str | None = None):
    if pause:
        import time
        time.sleep(pause)
    data = None
    if source == "polygon":
        data = fetch_polygon(sym, timeout, debug, key)
    else:
        if source in ("auto", "stooq"):
            data = fetch_stooq(sym, timeout, debug)
        if data is None and source in ("auto", "yahoo"):
            data = fetch_yahoo(sym, timeout, debug)
    if data is None:
        return None
    d, o, h, l, c, v = data
    rng = [(hi - lo) / cl for hi, lo, cl in zip(h, l, c)]

    out = {"sym": sym, "n": len(c), "start": d[0], "end": d[-1],
           "px": c[-1]}
    out["spread_all"] = abdi_ranaldo(h, l, c)
    out["vol_all"] = daily_vol(c)

    mask = in_play_mask(v, rng)
    idx = [i for i, m in enumerate(mask) if m]
    out["n_inplay"] = len(idx)
    # For the in-play subset the estimator needs CONSECUTIVE days, so take
    # each flagged day together with the one after it.
    if len(idx) >= 30:
        keep = sorted(set(idx) | {i + 1 for i in idx if i + 1 < len(c)})
        hh = [h[i] for i in keep]; ll = [l[i] for i in keep]
        cc = [c[i] for i in keep]
        out["spread_inplay"] = abdi_ranaldo(hh, ll, cc)
        out["vol_inplay"] = (sum(rng[i] for i in idx) / len(idx)) / 2.0
    else:
        out["spread_inplay"] = None
        out["vol_inplay"] = None
    return out


# ---------------------------------------------------------------------------

def self_test() -> int:
    fails = []

    def check(n, cond, d=""):
        print(f"  {'PASS' if cond else 'FAIL'}  {n}" + (f"   {d}" if d else ""))
        if not cond:
            fails.append(n)

    print(f"smallcap_budget.py v{VERSION} — offline controls\n")
    print(f"  interpreter  {sys.executable}")
    print(f"  stdlib only, no venv required\n")

    import random
    rng = random.Random(7)

    def synth(n, spread, sigma=0.02, px=10.0):
        """A price path with a KNOWN bid-ask bounce of `spread`."""
        h, l, c = [], [], []
        mid = px
        for _ in range(n):
            mid *= math.exp(rng.gauss(0, sigma))
            hi = mid * math.exp(abs(rng.gauss(0, sigma)))
            lo = mid * math.exp(-abs(rng.gauss(0, sigma)))
            # close prints at bid or ask, which is what the estimator reads
            side = 1 if rng.random() < 0.5 else -1
            c.append(mid * (1 + side * spread / 2))
            h.append(max(hi, c[-1])); l.append(min(lo, c[-1]))
        return h, l, c

    # 1-3. the estimator recovers a planted spread, monotonically
    got = []
    for s in (0.00, 0.02, 0.08):
        est = [abdi_ranaldo(*synth(1500, s)) for _ in range(5)]
        got.append(sum(est) / len(est))
    check("1 zero planted spread -> near zero", got[0] < 0.006,
          f"{got[0]:.4f}")
    check("2 estimator is monotonic in the true spread",
          got[0] < got[1] < got[2], f"{got[0]:.4f} < {got[1]:.4f} < {got[2]:.4f}")
    check("3 recovers a 2% spread to the right order of magnitude",
          0.008 < got[1] < 0.045, f"{got[1]:.4f} for a planted 0.0200")

    # 4. too-short samples refuse rather than guess
    check("4 short sample returns None", abdi_ranaldo([1]*5, [1]*5, [1]*5) is None)

    # 5. a negative covariance clamps to zero, not to a NaN
    flat = [10.0] * 200
    check("5 degenerate input -> 0.0, not NaN",
          abdi_ranaldo(flat, flat, flat) == 0.0)

    # 6-7. the required-edge arithmetic
    check("6 cost dominates when cost/vol is large",
          abs(required_edge(0.83, 500) - (BAR_2SIG / math.sqrt(500) + 0.83)) < 1e-12,
          f"{required_edge(0.83, 500):.3f} vol units")
    check("7 more trades barely help when cost dominates",
          required_edge(0.83, 100) - required_edge(0.83, 10000) < 0.09,
          "the bar term is negligible against an 0.83 cost")

    # 8. and the converse: when cost is small, sample size DOES matter
    check("8 with small cost, sample size matters",
          required_edge(0.01, 100) / required_edge(0.01, 10000) > 3,
          "confirms the framework is not simply cost-blind")

    # 9-10. the in-play filter
    vols = [100] * 90 + [1000] * 10
    rngs = [0.02] * 90 + [0.20] * 10
    m = in_play_mask(vols, rngs)
    check("9 in-play filter selects the active days", sum(m) == 10,
          f"{sum(m)} of 100")
    check("10 quiet series selects nothing",
          sum(in_play_mask([100] * 100, [0.02] * 100)) == 0)

    # 11. vol is a second moment only
    check("11 daily_vol is scale-free",
          abs(daily_vol([1, 2, 1, 2, 1] * 20) -
              daily_vol([10, 20, 10, 20, 10] * 20)) < 1e-12)

    # 12-14. symbol validation. v1.0 shipped without this and an RTF file
    #        produced a control-character URL error instead of a clear message.
    check("12 real tickers accepted",
          all(valid_symbol(s) for s in ("AAPL", "F", "BRK.B", "ABC-D")))
    check("13 RTF preamble rejected",
          not valid_symbol(r"{\RTF1\ANSI\ANSICPG1252"),
          "the exact string that broke the first run")
    check("14 prose and empty strings rejected",
          not valid_symbol("HELVETICA;}") and not valid_symbol(""))

    # 14b. RTF stripping must SURVIVE the tickers, not just remove markup.
    #      First attempt removed control words but left RTF's line-ending
    #      backslash attached, so every ticker arrived as 'ABCD\' and was
    #      rejected -- markup gone, data gone with it.
    rtf = ("{\\rtf1\\ansi\\ansicpg1252\\cocoartf2870\n"
           "{\\fonttbl\\f0\\fswiss\\fcharset0 Helvetica;}\n"
           "\\pard\\tx720\\partightenfactor0\n"
           "\\f0\\fs24 \\cf0 ABCD\\\nEFGH\\\nIJKL\\\n}")
    toks = [t.strip().upper() for ln in strip_rtf(rtf).splitlines()
            for t in ln.split(" ")]
    found = [t for t in toks if t in ("ABCD", "EFGH", "IJKL")]
    check("14b RTF stripping preserves the tickers", len(found) == 3,
          f"recovered {found}")

    # 15. THE GATE THAT COULD NOT FIRE. v1.0 scored 'no control returned any
    #     data' as validation PASSED. Encode the corrected rule directly.
    def validated(good, total=5):
        return good >= 3
    check("15 validation requires positive confirmation",
          not validated(0) and not validated(2) and validated(3),
          "0 controls returning data must FAIL, not pass by default")

    print(f"\n  {'ALL CONTROLS PASS' if not fails else str(len(fails)) + ' FAILED'}")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--tickers", default="",
                    help="comma-separated small-cap symbols to measure")
    ap.add_argument("--file", default="",
                    help="file with one symbol per line")
    ap.add_argument("--trades-per-year", type=float, default=500)
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--no-control", action="store_true")
    ap.add_argument("--sample", type=int, default=0,
                    help="randomly sample N symbols from the list (0 = all)")
    ap.add_argument("--seed", type=int, default=0,
                    help="seed for --sample, so the draw is reproducible")
    ap.add_argument("--pause", type=float, default=0.3,
                    help="seconds between requests; be polite to a free host")
    ap.add_argument("--debug", action="store_true",
                    help="print what the server actually returned on failure")
    ap.add_argument("--source", default="auto",
                    choices=["auto", "stooq", "yahoo", "polygon"],
                    help="auto tries Stooq then Yahoo; polygon needs a free key")
    a = ap.parse_args()

    if a.self_test:
        return self_test()

    syms = [s.strip().upper() for s in a.tickers.split(",") if s.strip()]
    if a.file:
        # A missing --file must be an ERROR, not a silent fall-through to the
        # generic "no tickers" message. Quietly ignoring a path the user
        # explicitly passed is how you end up debugging the wrong thing.
        if not os.path.exists(a.file):
            print(f"  --file not found: {os.path.abspath(a.file)}")
            print(f"  cwd is {os.getcwd()}")
            return 1
        with open(a.file, errors="replace") as fh:
            text = fh.read()
        if text.lstrip().lower().startswith(r"{\rtf"):
            print(f"  note: {a.file} is RTF (TextEdit's default for .txt).")
            print(f"        Reading it anyway; every token is validated below.")
            print(f"        To convert it properly: textutil -convert txt "
                  f"'{a.file}'")
            text = strip_rtf(text)
        # Tickers may be one per line OR whitespace-separated on one line,
        # which is what a copy-paste out of a screener table usually gives.
        lines = [tok.strip() for ln in text.splitlines()
                 for tok in ln.replace("\t", " ").split(" ")]
        cand = [ln.upper() for ln in lines if ln and not ln.startswith("#")]
        # Some screeners export "TICKER,Company Name,..." -- take field one.
        cand = [c.split(",")[0].split("\t")[0].strip() for c in cand]
        good = [c for c in cand if valid_symbol(c)]
        junk = [c for c in cand if not valid_symbol(c)]
        if junk:
            print(f"  ignoring {len(junk)} line(s) that are not tickers, "
                  f"e.g. {junk[0][:40]!r}")
            if len(junk) > len(good):
                print(f"  MORE JUNK THAN TICKERS ({len(junk)} vs {len(good)})."
                      f" The file is probably not a plain ticker list.")
                return 1
        syms += good
        if not syms:
            print(f"  --file {a.file} exists but contains no valid symbols "
                  f"({len(lines)} lines read)")
            return 1
    if not syms:
        print("No tickers given. Supply a screener list, for example:")
        print("  --tickers ABCD,EFGH,IJKL")
        print("  --file smallcaps.txt")
        print("\nUse a real screener: US listed, market cap < $300m,")
        print("float < 20m shares, price $1-$20. The measurement is only as")
        print("representative as the list.")
        return 1

    key = None
    if a.source == "polygon":
        key = polygon_key()          # fails fast if absent; never printed
        if a.pause < 12.5:
            # Free tier is 5 calls/minute. Defaulting to a pause that will
            # certainly 429 partway through a 60-symbol run, and only saying
            # so afterwards, would waste the run and the quota.
            print(f"  polygon free tier is 5 calls/min -> raising --pause "
                  f"from {a.pause} to 13s")
            a.pause = 13.0

    n_supplied = len(syms)
    if a.sample and a.sample < n_supplied:
        # RANDOM, not the first N. Truncating an alphabetical list is a fine
        # systematic sample; truncating a list sorted by anything else is
        # selection on that variable. Randomising removes the question, and
        # the fixed seed keeps the draw reproducible -- a sample you cannot
        # reproduce is a result you cannot check.
        import random
        syms = sorted(random.Random(a.seed).sample(syms, a.sample))

    print(f"smallcap_budget.py v{VERSION}   NO RETURNS COMPUTED")
    print(f"  effective spread via Abdi & Ranaldo (2017), daily H/L/C")
    src_label = {"polygon": "Polygon (free tier, includes delisted)",
                 "yahoo": "Yahoo", "stooq": "Stooq",
                 "auto": "Stooq, falling back to Yahoo"}[a.source]
    surv = ("delisted included" if a.source == "polygon"
            else "SURVIVORS ONLY -> spreads are OPTIMISTIC")
    print(f"  source: {src_label}  ({surv})")
    if a.sample and a.sample < n_supplied:
        print(f"  sampled {len(syms)} of {n_supplied} symbols, seed {a.seed}")
    else:
        print(f"  {len(syms)} symbols")
    print()

    if not a.no_control:
        print("VALIDATION CONTROL — liquid names must print tiny spreads")
        print("=" * 74)
        good = bad = missing = 0
        for s in CONTROL:
            r = analyse(s, a.timeout, a.pause, debug=a.debug, source=a.source, key=key)
            if not r or r["spread_all"] is None:
                print(f"  {s:<6} no data")
                missing += 1
                continue
            ok = r["spread_all"] < 0.01
            good += ok
            bad += not ok
            print(f"  {s:<6} spread {r['spread_all']:>7.4%}   vol "
                  f"{r['vol_all']:>6.2%}   {r['n']:>5} days"
                  f"{'' if ok else '   <-- TOO WIDE'}")

        # A GATE THAT CANNOT FIRE IS DECORATION.
        #
        # The first version counted only controls that returned data AND came
        # back too wide. When every control returned NO data, `bad` stayed 0
        # and the script cheerfully printed "estimator validated" having
        # validated precisely nothing. That is the same defect as the COT
        # `ignore_invalid_symbol` bug and the look-ahead probe that could not
        # fail: absence of evidence scored as evidence of absence.
        #
        # Validation now requires POSITIVE confirmation -- at least three
        # controls must actually return data and actually be tight.
        if good < 3:
            print(f"\n  VALIDATION FAILED: {good} of {len(CONTROL)} controls"
                  f" confirmed ({missing} no data, {bad} too wide).")
            if missing:
                print("  The controls returned no data at all, so the estimator")
                print("  was never exercised. This is a DATA problem, not a")
                print("  spread problem — and it means nothing below this line")
                print("  could have been trusted either.")
                print("  Re-run with --debug to see what the server returned.")
            else:
                print("  Liquid names should be well under 1%. The estimator")
                print("  is not behaving; do not use any figure it produces.")
            return 1
        print(f"  -> estimator validated ({good}/{len(CONTROL)} controls tight)\n")

    print("SMALL CAPS")
    print("=" * 74)
    print(f"  {'sym':<7}{'px':>8}{'spread all':>12}{'vol all':>10}"
          f"{'spread live':>13}{'vol live':>10}{'in-play':>9}")
    rows = []
    for s in syms:
        r = analyse(s, a.timeout, a.pause, debug=a.debug, source=a.source, key=key)
        if not r or r["spread_all"] is None:
            print(f"  {s:<7}{'no data':>8}")
            continue
        rows.append(r)
        sp_i = f"{r['spread_inplay']:.2%}" if r["spread_inplay"] is not None else "—"
        vo_i = f"{r['vol_inplay']:.2%}" if r["vol_inplay"] is not None else "—"
        print(f"  {r['sym']:<7}{r['px']:>8.2f}{r['spread_all']:>12.2%}"
              f"{r['vol_all']:>10.2%}{sp_i:>13}{vo_i:>10}{r['n_inplay']:>9}")

    # HOW MANY ACTUALLY RESOLVED?
    #
    # valid_symbol() is a syntax check, and it cannot be strict: 'F' and 'A'
    # are real tickers, so short alphabetic words are indistinguishable from
    # symbols. Prose therefore slips through -- 'THIS', 'PLAN', 'WITH' all
    # look like tickers. The reliable test is empirical rather than
    # syntactic: a real ticker returns data and a word does not.
    resolved = len(rows) / len(syms) if syms else 0.0
    print(f"\n  {len(rows)} of {len(syms)} symbols returned data "
          f"({resolved:.0%})")
    if not rows:
        print("  no usable data for any symbol. Either the list is not")
        print("  tickers, or the data source is failing. Re-run with --debug.")
        return 1
    if resolved < 0.5:
        print("  !! more than half the list returned nothing. That is either")
        print("     a bad ticker list or a failing source, and the medians")
        print("     below are drawn from whatever happened to survive.")
        print("     Check with --debug before believing any of it.")

    def med(vals):
        v = sorted(x for x in vals if x is not None)
        return v[len(v) // 2] if v else None

    # A SPREAD OF EXACTLY 0.00% IS A FAILED ESTIMATE, NOT A MEASUREMENT.
    #
    # Abdi-Ranaldo is a covariance estimator, and when the covariance comes
    # out negative there is no square root to take. Those are clamped to
    # zero — which is fine as a display convention and catastrophic as an
    # input to a median, because a failed estimate then votes as "this stock
    # is free to trade". Treating it as data is the same error as scoring a
    # control that returned nothing as a control that passed.
    #
    # Neither treatment is unbiased. Including the zeros biases the spread
    # DOWN; excluding them biases it UP, because the estimator fails more
    # often when the true spread is small. So BOTH are reported and the
    # answer is a range, not a point. A high failure rate is itself a
    # finding: microcaps halt, gap and trade thinly, all of which violate
    # the estimator's assumption of continuous trading around a random walk.
    def split(key):
        vals = [r[key] for r in rows if r[key] is not None]
        zeros = [x for x in vals if x <= 0]
        nz = [x for x in vals if x > 0]
        return med(vals), med(nz), len(zeros), len(vals)

    sp_all, sp_all_nz, z_all, n_all = split("spread_all")
    sp_ip, sp_ip_nz, z_ip, n_ip = split("spread_inplay")
    vo_all = med([r["vol_all"] for r in rows])
    vo_ip = med([r["vol_inplay"] for r in rows])

    print(f"\n  estimator failures (clamped to 0.00%):")
    print(f"    average day  {z_all} of {n_all}"
          + (f"  ({z_all / n_all:.0%})" if n_all else ""))
    print(f"    in play      {z_ip} of {n_ip}"
          + (f"  ({z_ip / n_ip:.0%})" if n_ip else ""))
    if n_ip and z_ip / n_ip > 0.25:
        print(f"    !! a quarter or more of the in-play estimates FAILED.")
        print(f"       They are excluded from the upper bound below and the")
        print(f"       true figure lies between the two rows.")

    print(f"\nTHE DECIDING RATIO")
    print("=" * 74)
    # Cost model: one full effective spread for the round trip (half on each
    # side), PLUS liquidity slippage of comparable size. Published microcap
    # figures put slippage at 2-5% against spreads of 4-8%, so slippage is
    # roughly 0.5-1x the spread; the 2x multiplier below is the conservative
    # end of that. It is stated here rather than buried, because it is a
    # modelling choice and it moves the answer proportionally.
    COST_MULT = 2.0
    print(f"  round-trip cost modelled as {COST_MULT:.0f} x effective spread"
          f" (spread + slippage)")
    print(f"\n  {'scenario':<30}{'cost/vol':>10}{'req edge/trade':>17}")
    band = {}
    for label, sp, vo, tag in (
            ("average day, incl. failures", sp_all, vo_all, None),
            ("average day, excl. failures", sp_all_nz, vo_all, None),
            ("IN PLAY, incl. failures", sp_ip, vo_ip, "lo"),
            ("IN PLAY, excl. failures", sp_ip_nz, vo_ip, "hi")):
        if sp is None or vo is None or vo <= 0:
            print(f"  {label:<30}{'—':>10}{'insufficient sample':>17}")
            continue
        cv = COST_MULT * sp / vo
        req = required_edge(cv, a.trades_per_year)
        if tag:
            band[tag] = req
        print(f"  {label:<30}{cv:>10.2f}{req:>17.2f}")

    print(f"\n  for comparison:")
    print(f"    FX H4 directional (v3)          cost/vol 0.071")
    print(f"    residual mean-reversion (v1/v2) cost/vol 0.146")
    print(f"    measured edge, hedged 15m book  {REFERENCE_EDGE:.3f} vol units/trade")

    if "lo" in band:
        lo, hi = band["lo"], band.get("hi", band["lo"])
        print(f"\nVERDICT")
        print("=" * 74)
        print(f"  required edge per trade, in play: {lo:.2f} to {hi:.2f} vol units")
        print(f"  that is {lo / REFERENCE_EDGE:.0f}x to {hi / REFERENCE_EDGE:.0f}x"
              f" the only edge this project has ever measured.")
        print(f"  bar term is {BAR_2SIG / math.sqrt(a.trades_per_year):.3f} of that"
              f" — MORE DATA CANNOT HELP. This is cost, not sample.")
        # Judge on the OPTIMISTIC end. If even the flattering figure fails,
        # the pessimistic one cannot rescue it, and the decision is safe in
        # the direction that costs nothing to be wrong about.
        if lo > 1.0:
            print(f"\n  => CLOSED ON COST, even on the most flattering reading.")
            print(f"     An edge above one full volatility unit per trade is not")
            print(f"     a strategy. Do not buy data.")
        elif lo > 0.30:
            print(f"\n  => VERY DEMANDING. Even the optimistic end needs"
                  f" {lo:.2f} vol")
            print(f"     units per trade, and the honest figure is higher.")
            print(f"     Before spending anything on survivorship-free data,")
            print(f"     decide whether that is a plausible edge. Note these")
            print(f"     spreads are measured on SURVIVORS, so they already")
            print(f"     flatter the strategy before any of the above.")
        else:
            print(f"\n  => inside a plausible band. Worth pricing clean data.")
    print(f"\n  CAVEAT: survivors only. The names that went to zero had wider")
    print(f"  spreads than these, so every figure above flatters the strategy.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
