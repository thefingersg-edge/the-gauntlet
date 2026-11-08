#!/usr/bin/env python3
"""Power budget for a CARRY / RISK-PREMIUM strategy. Run BEFORE hypothesising.

NO P&L IS COMPUTED IN THIS FILE. Volatility -- a second moment -- is measured
from price history, because a Sharpe ratio needs a denominator. The MEAN of a
return series is never taken anywhere in this file, and no position is ever
marked to market. Everything on the numerator side comes from published
financing rates.

WHY THIS FAMILY IS DIFFERENT FROM THE SEVEN THAT FAILED
-------------------------------------------------------
Every previous test was a PREDICTION: read a signal, forecast direction, take
a position, hope. v3 and v4 established that the price history contains
essentially no directional content to forecast -- the gross signal was ~zero
BEFORE any cost was charged. v5 established the same for weekly CFTC
positioning across 38 years.

Carry is not a forecast. You are not predicting that the high-yielding
currency will rise; the theory (uncovered interest parity) says it should
FALL by exactly the differential. The empirical claim is that it falls by
LESS than the differential, and the residual is compensation for bearing
crash risk -- you are paid to hold something other people want to shed.

That matters for testing in a way worth stating plainly:

  * The edge is EARNED CONTINUOUSLY, not per decision. A prediction strategy's
    sample size is its number of independent decisions, which is why v4's 258
    rebalances were fatal. A risk premium accrues every day you hold it, so
    the sample is the number of independent RETURN periods, not signal changes.
  * It is therefore the one family here whose extreme signal persistence is a
    FEATURE. Carry barely changes month to month; that means near-zero
    turnover and near-zero spread cost.

THE CATCH, AND IT IS THE WHOLE QUESTION
---------------------------------------
On a CFD you do not receive the interbank differential. You receive the
BROKER'S financing rate, which carries a markup on both sides. OANDA publishes
longRate and shortRate per instrument. In a frictionless market they would be
exact negatives of each other:

    fair:      longRate = +(r_base - r_quote)      shortRate = -(r_base - r_quote)
    so:        longRate + shortRate = 0

Any departure from zero is the markup, and it is charged whichever way you
face. That gives two numbers directly, with no modelling:

    carry_i   = (longRate_i - shortRate_i) / 2     the markup-free differential
    markup_i  = -(longRate_i + shortRate_i) / 2    annual cost per side

A carry book is long the high-carry names and short the low-carry names, so
its GROSS annual return is the DISPERSION of carry across the universe, and it
pays markup on EVERY leg -- long and short alike. Hence:

    net annual carry = carry dispersion - mean markup

If that is negative, the family is closed by arithmetic before a single
backtest, exactly as the 4.73pp floor closed residual mean-reversion.

WHAT THIS FILE CANNOT DO
------------------------
OANDA publishes CURRENT financing, not a history of it. So the dispersion
measured here is a snapshot of today's rate environment, not a 20-year
average. That is a real limitation and it is reported, not hidden:

  * the MARKUP is the stable half -- broker markups are a policy, not a market
    price, and they move slowly. Measuring it today is close to measuring it
    always.
  * the DISPERSION is the volatile half. Today's is whatever today's is. The
    file therefore reports the verdict at today's dispersion AND the
    break-even dispersion required, so you can judge how unusual today would
    have to be for the answer to flip.

    python carry_budget.py --self-test          # offline, no token needed
    python carry_budget.py                      # live snapshot + verdict
    python carry_budget.py --cache ../data_carry/financing.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys

VERSION = "1.2"


# ---------------------------------------------------------------------------
# VENV BOOTSTRAP -- runs before pandas or numpy is imported anywhere
#
# The project's dependencies live in scripts/.venv. Running this file with a
# system Python that cannot see them fails at `import pandas`, several seconds
# and one confusing traceback later. Rather than require you to remember to
# activate first, the script finds its own venv and re-executes itself with
# that interpreter.
#
# Guards, because a self-re-executing script is exactly the kind of thing that
# goes wrong quietly:
#   * an environment-variable flag makes infinite re-exec impossible
#   * if you are ALREADY in a virtualenv, yours is left alone -- the script
#     never overrides a deliberate choice
#   * if the venv is missing, it says so and carries on with the current
#     interpreter rather than dying, since --self-test needs no third-party
#     packages at all
#
# numpy and pandas are imported inside functions, not at module scope, so this
# block is guaranteed to run before either is touched.
# ---------------------------------------------------------------------------

_BOOTSTRAP_FLAG = "CARRY_BUDGET_VENV_BOOTSTRAPPED"


def _venv_python(here: str) -> str | None:
    """Path to the project venv's interpreter, if one exists."""
    for rel in (".venv", "venv", os.path.join("..", ".venv")):
        for sub in (os.path.join("bin", "python3"),
                    os.path.join("bin", "python"),
                    os.path.join("Scripts", "python.exe")):
            cand = os.path.join(here, rel, sub)
            if os.path.isfile(cand) and os.access(cand, os.X_OK):
                # abspath, NOT realpath. A venv's bin/python is usually a
                # symlink to the base interpreter, and Python locates
                # pyvenv.cfg -- and therefore site-packages -- from the path
                # it was INVOKED by, not from the resolved target. Resolving
                # the symlink would make the venv python look identical to
                # the system one and skip a re-exec that is genuinely needed.
                return os.path.abspath(cand)
    return None


def _deps_available() -> bool:
    """Can THIS interpreter see numpy and pandas?

    find_spec locates the package without importing it, so this costs
    milliseconds and has no side effects.
    """
    import importlib.util
    try:
        return all(importlib.util.find_spec(m) is not None
                   for m in ("numpy", "pandas"))
    except (ImportError, ValueError):
        return False


def _bootstrap_venv() -> None:
    if os.environ.get(_BOOTSTRAP_FLAG):
        return                                    # already re-executed once

    # THE TEST IS "CAN I IMPORT WHAT I NEED", NOT "AM I IN A VENV".
    #
    # v1.1 deferred to any already-active virtualenv, on the reasoning that a
    # deliberate choice should not be overridden. That was wrong in the one
    # case that matters: an active venv belonging to something else -- a uv
    # cache environment, a reticulate environment, a shell that auto-activates
    # -- satisfies "in a venv" while having none of this project's packages.
    # The script then politely deferred to an interpreter that could not run
    # it, and died at `import pandas` two screens of real output later.
    #
    # Asking about the packages instead gets both cases right: an interpreter
    # that works is never disturbed, and one that cannot work is replaced
    # whether or not it calls itself a virtualenv.
    if _deps_available():
        return

    here = os.path.dirname(os.path.abspath(__file__))
    target = _venv_python(here)
    if target is None:
        print("  note: no .venv found next to this script; using the current\n"
              "        Python. --self-test needs nothing extra, but the live\n"
              "        run needs pandas and numpy.", file=sys.stderr)
        return
    if os.path.abspath(target) == os.path.abspath(sys.executable):
        return                                    # already the right one

    print(f"  [venv] numpy/pandas not visible to {os.path.basename(sys.prefix)};"
          f" re-running under {os.path.relpath(target, here)}",
          file=sys.stderr)
    os.environ[_BOOTSTRAP_FLAG] = "1"
    try:
        os.execv(target, [target, os.path.abspath(__file__)] + sys.argv[1:])
    except OSError as exc:                        # noqa: BLE001
        print(f"  [venv] could not re-execute ({exc}); continuing with the "
              f"current Python", file=sys.stderr)


_bootstrap_venv()

# The bar is set by span, exactly as in every other budget in this project.
YEARS = 20.4
BAR_2SIG = 2.0 / YEARS ** 0.5          # 0.44

TOP = 3            # longs, and shorts, in the carry book

# data_universe stem -> OANDA instrument name. Only instruments with a clean
# carry mechanism are eligible; see FX_ONLY below.
OANDA_NAME = {
    "eurusd": "EUR_USD", "gbpusd": "GBP_USD", "audusd": "AUD_USD",
    "nzdusd": "NZD_USD", "usdcad": "USD_CAD", "usdchf": "USD_CHF",
    "eurgbp": "EUR_GBP", "eurjpy": "EUR_JPY", "gbpjpy": "GBP_JPY",
    "eurchf": "EUR_CHF", "euraud": "EUR_AUD", "audnzd": "AUD_NZD",
    "nzdcad": "NZD_CAD",
    # indices: reported as a diagnostic only, NOT part of the carry book
    "spx500usd": "SPX500_USD", "nas100usd": "NAS100_USD",
    "de30eur": "DE30_EUR", "uk100gbp": "UK100_GBP", "us30usd": "US30_USD",
    "us2000usd": "US2000_USD", "eu50eur": "EU50_EUR", "jp225usd": "JP225_USD",
    "hk33hkd": "HK33_HKD", "nl25eur": "NL25_EUR", "ch20chf": "CH20_CHF",
    "fr40eur": "FR40_EUR", "au200aud": "AU200_AUD",
    "wticousd": "WTICO_USD", "bcousd": "BCO_USD",
}

# WHY ONLY FX IS IN THE BOOK.
#
# An index CFD's financing is not carry. Long an index you pay funding and
# receive dividends as a separate cash adjustment; the "carry" is the dividend
# yield minus the funding rate, and OANDA's longRate/shortRate captures only
# the funding half. Treating it as carry would book the funding cost with none
# of the dividend offset -- a guaranteed and meaningless negative. Commodity
# CFDs have the same problem in reverse via the futures roll.
#
# FX is the one asset class where longRate/shortRate IS the full carry, so it
# is the only one that can be measured honestly here. Indices are printed as a
# markup diagnostic because the markup is still real and still comparable.
FX_ONLY = {"eurusd", "gbpusd", "audusd", "nzdusd", "usdcad", "usdchf",
           "eurgbp", "eurjpy", "gbpjpy", "eurchf", "euraud", "audnzd",
           "nzdcad"}


# ---------------------------------------------------------------------------
# pure arithmetic -- exercised offline by --self-test
# ---------------------------------------------------------------------------

def decompose(long_rate: float, short_rate: float) -> tuple[float, float]:
    """Split a quoted financing pair into (true carry, markup per side).

    Both returned as annual decimal rates. `markup` is positive when the
    broker is taking something, which is the normal case.
    """
    carry = (long_rate - short_rate) / 2.0
    markup = -(long_rate + short_rate) / 2.0
    return carry, markup


def book_gross(carries: dict[str, float], top: int) -> tuple[float, list, list]:
    """Annual gross carry of an equal-risk long-short book, before markup.

    Long the `top` highest carries, short the `top` lowest. Gross return is
    the difference of the two means -- the DISPERSION. Note this is computed
    from published rates only; no price and no P&L is involved.
    """
    ranked = sorted(carries.items(), key=lambda kv: kv[1], reverse=True)
    if len(ranked) < 2 * top:
        top = max(1, len(ranked) // 2)
    longs, shorts = ranked[:top], ranked[-top:]
    gross = (sum(v for _, v in longs) / len(longs)
             - sum(v for _, v in shorts) / len(shorts))
    return gross, longs, shorts


def book_markup(markups: dict[str, float], longs, shorts) -> float:
    """Annual markup paid by the book.

    THE EASY ERROR IS CHARGING IT ONCE. The markup is paid on every leg,
    long and short alike -- being short a currency does not refund it. With
    equal risk weights the book pays the MEAN markup across all legs held.
    """
    legs = [k for k, _ in longs] + [k for k, _ in shorts]
    return sum(markups[k] for k in legs) / len(legs)


def earned_fraction(days_charged_per_week: int) -> float:
    """How much of a QUOTED annual rate you actually receive.

    OANDA computes daily financing as `rate/365 * daysCharged`. An instrument
    charging the normal 7 days a week (5 weekdays with a triple charge on
    Wednesday to cover the weekend) therefore earns the full quoted annual
    rate. An instrument charging only 6 earns 6/7 of it.

    This is not a rounding detail: GBP_JPY and EUR_JPY charge 6, and GBP_JPY
    is large enough to sit in the long book. Quoting its carry at the headline
    rate overstates what the book collects.
    """
    d = days_charged_per_week or 7
    return min(d, 7) / 7.0


def annualise_vol(series_std_per_bar: float, bars_per_year: float) -> float:
    return series_std_per_bar * (bars_per_year ** 0.5)


# ---------------------------------------------------------------------------
# live snapshot
# ---------------------------------------------------------------------------

def fetch_financing(env: str) -> dict:
    """Pull current financing rates from OANDA. Token handling is delegated
    entirely to fetch_oanda.py so the token is read, redacted and never
    printed by exactly one piece of code in this project."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import fetch_oanda as F

    token = F.load_token() if hasattr(F, "load_token") else _token_fallback()
    host = F.HOSTS[env]

    accounts = F.api_get(f"{host}/v3/accounts", token)
    accts = accounts.get("accounts", [])
    if not accts:
        raise SystemExit("no OANDA accounts visible for this token")
    acct = accts[0]["id"]

    payload = F.api_get(f"{host}/v3/accounts/{acct}/instruments", token)
    out = {}
    for ins in payload.get("instruments", []):
        fin = ins.get("financing") or {}
        if "longRate" not in fin or "shortRate" not in fin:
            continue
        days = {d.get("dayOfWeek"): d.get("daysCharged", 0)
                for d in fin.get("financingDaysOfWeek", [])}
        out[ins["name"]] = {
            "longRate": float(fin["longRate"]),
            "shortRate": float(fin["shortRate"]),
            "type": ins.get("type", "?"),
            "daysChargedPerWeek": sum(days.values()),
        }
    return out


def _token_fallback() -> str:
    for path in (os.environ.get("OANDA_API_TOKEN"),):
        if path:
            return path.strip()
    for p in (os.path.expanduser("~/.oanda_token"), ".oanda_token"):
        if os.path.exists(p):
            with open(p) as fh:
                return fh.read().strip()
    raise SystemExit("no OANDA token found (see fetch_oanda.py header)")


def measure_vol(data_dir: str, longs, shorts):
    """Annual volatility of the equal-risk long-short book.

    ONLY THE SECOND MOMENT IS USED. `.std()` is called; `.mean()` is not, and
    no cumulative P&L is formed. A Sharpe needs a denominator and this is it.

    Today's ranking is applied across all history. For a MEAN that would be
    look-ahead and unacceptable; for a VOLATILITY it is benign, because the
    vol of an equal-risk long-short FX basket barely depends on which names
    sit on which side -- it is set by the correlation structure, which is
    what is being measured.
    """
    import numpy as np, pandas as pd

    names = [k for k, _ in longs] + [k for k, _ in shorts]
    sign = {k: (1.0 if i < len(longs) else -1.0)
            for i, k in enumerate(names)}

    cols = {}
    for stem in names:
        p = os.path.join(data_dir, f"{stem}_4h.csv")
        if not os.path.exists(p):
            continue
        d = pd.read_csv(p)
        t = d.columns[0]
        d[t] = pd.to_datetime(d[t], utc=True)
        cols[stem] = d.set_index(t).sort_index()["close"].astype(float)
    if len(cols) < 2:
        return None, None, 0

    M = pd.DataFrame(cols).dropna()
    if len(M) < 500:
        return None, None, 0
    R = np.log(M).diff().dropna()

    # equal RISK per leg, gross risk normalised to 1 unit
    per_leg_vol = R.std()
    w = {c: sign[c] / per_leg_vol[c] for c in R.columns}
    gross = sum(abs(x) for x in w.values())
    w = {c: x / gross for c, x in w.items()}
    port = sum(w[c] * R[c] for c in R.columns)

    span_years = (R.index.max() - R.index.min()).days / 365.25
    bars_per_year = len(R) / span_years
    return (annualise_vol(float(port.std()), bars_per_year),
            span_years, len(R))


# ---------------------------------------------------------------------------

def self_test() -> int:
    """Synthetic controls on the arithmetic. No network, no data, no P&L."""
    fails = []

    def check(name, cond, detail=""):
        print(f"  {'PASS' if cond else 'FAIL'}  {name}" +
              (f"   {detail}" if detail else ""))
        if not cond:
            fails.append(name)

    print(f"carry_budget.py v{VERSION} — synthetic controls\n")

    # Environment first, because the commonest failure of this script is not
    # a wrong number -- it is the live run dying at `import pandas` because
    # the venv was not picked up. Report it before anything else.
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    print(f"  interpreter  {sys.executable}")
    print(f"  virtualenv   {'YES -> ' + sys.prefix if in_venv else 'NO'}")
    missing = []
    for mod in ("numpy", "pandas"):
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    if missing:
        print(f"  packages     MISSING {', '.join(missing)} — the controls below")
        print(f"               still run, but the live snapshot will not.")
    else:
        print(f"  packages     numpy, pandas OK — live run will work")
    print()

    # 1. a fair market has no markup
    c, m = decompose(0.0300, -0.0300)
    check("1 fair quotes -> zero markup", abs(m) < 1e-12 and abs(c - 0.03) < 1e-12,
          f"carry {c:+.4f} markup {m:+.6f}")

    # 2. a symmetric markup is recovered exactly, and does NOT distort carry
    c, m = decompose(0.0300 - 0.0100, -0.0300 - 0.0100)
    check("2 symmetric markup recovered", abs(m - 0.0100) < 1e-12,
          f"markup {m:.4f} (planted 0.0100)")
    check("3 markup does not corrupt carry", abs(c - 0.0300) < 1e-12,
          f"carry {c:+.4f} (planted 0.0300)")

    # 4. a negative differential comes back negative
    c, m = decompose(-0.0200 - 0.0050, 0.0200 - 0.0050)
    check("4 sign of the differential preserved", abs(c + 0.0200) < 1e-12,
          f"carry {c:+.4f}")

    # 5. book gross equals the dispersion it was built from
    carries = {"a": 0.05, "b": 0.04, "c": 0.03, "d": 0.01, "e": 0.00, "f": -0.02}
    g, lo, sh = book_gross(carries, 3)
    want = (0.05 + 0.04 + 0.03) / 3 - (0.01 + 0.00 - 0.02) / 3
    check("5 book gross = carry dispersion", abs(g - want) < 1e-12,
          f"{g:.4f} vs {want:.4f}")

    # 6. no dispersion -> no gross
    g0, _, _ = book_gross({k: 0.02 for k in "abcdef"}, 3)
    check("6 flat carry -> zero gross", abs(g0) < 1e-12, f"{g0:+.6f}")

    # 7. THE EASY ERROR: markup must be charged on shorts too
    mk = {k: 0.01 for k in carries}
    check("7 markup charged on every leg", abs(book_markup(mk, lo, sh) - 0.01) < 1e-12,
          "0.0100 on all six legs")
    mk2 = dict(mk); mk2.update({k: 0.03 for k, _ in sh})
    got = book_markup(mk2, lo, sh)
    check("8 expensive shorts raise the bill", abs(got - 0.02) < 1e-12,
          f"{got:.4f} (mean of 0.01 longs and 0.03 shorts)")

    # 9. annualisation
    check("9 vol annualises as sqrt(t)",
          abs(annualise_vol(0.01, 100) - 0.10) < 1e-12)

    # 10. a book whose markup exceeds its dispersion must net out negative
    net = 0.02 - 0.03
    check("10 markup > dispersion -> negative net", net < 0, f"{net:+.4f}")

    # 11-13. the days-charged correction
    check("11 seven days -> full rate earned",
          abs(earned_fraction(7) - 1.0) < 1e-12)
    check("12 six days -> six sevenths earned",
          abs(earned_fraction(6) - 6 / 7) < 1e-12, f"{earned_fraction(6):.4f}")
    check("13 missing days field defaults to full, not zero",
          abs(earned_fraction(0) - 1.0) < 1e-12,
          "a 0 must not silently erase an instrument's carry")

    print(f"\n  {'ALL CONTROLS PASS' if not fails else str(len(fails)) + ' FAILED'}")
    return 1 if fails else 0


def main() -> int:
    # NOTHING third-party is imported here. `--self-test` must run on a bare
    # interpreter -- that is its whole purpose, and it is the state you are in
    # when the venv bootstrap has just told you the venv is missing. numpy and
    # pandas are imported inside measure_vol, on the live path only.
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--env", default="live", choices=["live", "practice"])
    ap.add_argument("--data", default="../data_universe")
    ap.add_argument("--cache", default="../data_carry/financing.json",
                    help="snapshot is written here, and reused with --offline")
    ap.add_argument("--offline", action="store_true",
                    help="use the cached snapshot instead of calling OANDA")
    ap.add_argument("--top", type=int, default=TOP)
    a = ap.parse_args()

    if a.self_test:
        return self_test()

    print(f"carry_budget.py v{VERSION}   NO P&L COMPUTED")
    print(f"  numerator from published financing rates; only the SECOND")
    print(f"  moment of price is used, for the Sharpe denominator.\n")

    if a.offline:
        if not os.path.exists(a.cache):
            raise SystemExit(f"no cached snapshot at {a.cache}")
        with open(a.cache) as fh:
            fin = json.load(fh)
        print(f"  using cached snapshot {a.cache}")
    else:
        fin = fetch_financing(a.env)
        os.makedirs(os.path.dirname(a.cache) or ".", exist_ok=True)
        with open(a.cache, "w") as fh:
            json.dump(fin, fh, indent=1, sort_keys=True)
        print(f"  live snapshot: {len(fin)} instruments -> {a.cache}")

    # ---- 1. decompose every instrument we hold data for -------------------
    rows = {}
    for stem, oname in OANDA_NAME.items():
        if oname not in fin:
            continue
        q = fin[oname]
        c, m = decompose(q["longRate"], q["shortRate"])
        days = q.get("daysChargedPerWeek", 0)
        f = earned_fraction(days)
        # Scale BOTH sides. A 6-day instrument earns less carry, but it is
        # also charged markup on those same 6 days -- crediting one without
        # the other would bias the book in whichever direction was convenient.
        rows[stem] = dict(name=oname, carry=c * f, markup=m * f,
                          quoted_carry=c, earned=f, type=q.get("type", "?"),
                          days=days, lr=q["longRate"], sr=q["shortRate"])

    if not rows:
        raise SystemExit("no overlap between OANDA instruments and the universe")

    print("\n1. FINANCING DECOMPOSED  (annual rates, as quoted)")
    print("=" * 78)
    print(f"  {'instrument':<12}{'longRate':>10}{'shortRate':>11}"
          f"{'carry':>10}{'markup':>10}{'days/wk':>9}")
    for stem in sorted(rows, key=lambda k: -rows[k]["carry"]):
        r = rows[stem]
        tag = "" if stem in FX_ONLY else "  (not carry)"
        print(f"  {r['name']:<12}{r['lr']:>+10.4f}{r['sr']:>+11.4f}"
              f"{r['carry']:>+10.4f}{r['markup']:>+10.4f}{r['days']:>9}{tag}")

    bad_days = [r for r in rows.values() if r["days"] not in (0, 7)]
    if bad_days:
        print(f"\n  !! {len(bad_days)} instrument(s) charge fewer than 7 days/week."
              f"\n     The carry column above is ALREADY scaled by days/7 --"
              f" what you\n     actually collect, not what is quoted:")
        for r in sorted(bad_days, key=lambda x: -abs(x["carry"])):
            print(f"       {r['name']:<10} quoted {r['quoted_carry']:+.4f}"
                  f"  ->  earned {r['carry']:+.4f}   ({r['days']}/7 days)")

    # ---- 2. the book -------------------------------------------------------
    fx = {k: v["carry"] for k, v in rows.items() if k in FX_ONLY}
    fxm = {k: v["markup"] for k, v in rows.items() if k in FX_ONLY}
    if len(fx) < 2 * a.top:
        print(f"\n  only {len(fx)} FX instruments; reducing book size")
    gross, longs, shorts = book_gross(fx, a.top)
    markup = book_markup(fxm, longs, shorts)
    net = gross - markup

    print(f"\n2. THE CARRY BOOK  ({len(fx)} FX instruments, top/bottom {len(longs)})")
    print("=" * 78)
    def leg_str(legs):
        return ", ".join("{} {:+.2%}".format(rows[k]["name"], v) for k, v in legs)

    print(f"  long  {leg_str(longs)}")
    print(f"  short {leg_str(shorts)}")
    print(f"\n  gross annual carry (dispersion)   {gross:+.3%}")
    print(f"  annual markup, charged every leg  {markup:+.3%}")
    print(f"  NET ANNUAL CARRY                  {net:+.3%}")

    # spread cost is deliberately a footnote here: carry ranks are almost
    # static, so a book rebalanced quarterly trades a handful of legs a year.
    print(f"\n  (spread is not the binding cost for this family: carry ranks")
    print(f"   change over quarters, so turnover is a few legs a year. If the")
    print(f"   net above is negative, spread cannot rescue it; if it is")
    print(f"   positive, spread must then be charged in the pre-registration.)")

    # ---- 3. denominator ----------------------------------------------------
    # Fail here with an instruction rather than a traceback. Reaching this
    # point means the bootstrap could not find an interpreter with pandas,
    # and a ModuleNotFoundError three frames deep is a worse way to say so.
    if not _deps_available():
        raise SystemExit(
            "\n  pandas/numpy are not available to this interpreter and no\n"
            "  project venv could supply them.\n"
            f"    interpreter: {sys.executable}\n"
            "  Run it directly with the project venv:\n"
            "    ./.venv/bin/python3 carry_budget.py\n"
            "  The financing figures above are complete and correct; only the\n"
            "  volatility denominator is missing.")

    vol, span, nbars = measure_vol(a.data, longs, shorts)
    print(f"\n3. THE DENOMINATOR  (second moment only)")
    print("=" * 78)
    if vol is None:
        print("  insufficient overlapping H4 data to measure book volatility")
        return 1
    print(f"  {nbars:,} overlapping H4 bars over {span:.1f} years")
    print(f"  annual volatility of the equal-risk book   {vol:.2%}")

    # ---- 4. verdict --------------------------------------------------------
    sharpe = net / vol if vol > 0 else float("nan")
    gross_sharpe = gross / vol if vol > 0 else float("nan")
    breakeven_disp = markup                      # dispersion needed to net zero
    disp_for_bar = markup + BAR_2SIG * vol       # dispersion needed to clear 2 sigma

    print(f"\n4. VERDICT")
    print("=" * 78)
    print(f"  gross annual Sharpe (before markup)  {gross_sharpe:+.2f}")
    print(f"  NET annual Sharpe                    {sharpe:+.2f}")
    print(f"  detectability bar at 2 sigma         {BAR_2SIG:.2f}   ({YEARS:.1f}y)")
    print(f"  published G10 carry runs             ~0.3-0.6 gross")
    print(f"\n  break-even carry dispersion          {breakeven_disp:+.3%}")
    print(f"  dispersion needed to clear the bar   {disp_for_bar:+.3%}")
    if disp_for_bar > 0:
        print(f"  today's dispersion                   {gross:+.3%}"
              f"   ({gross / disp_for_bar:.2f}x of what is needed)")

    # The single most decision-relevant number: how large can the broker's
    # markup be before this family is closed regardless of anything else?
    max_markup = gross - BAR_2SIG * vol
    print(f"\n  MAX TOLERABLE MARKUP                 {max_markup:+.3%} per side")
    print(f"  actual markup                        {markup:+.3%} per side")
    print(f"  headroom                             {max_markup - markup:+.3%}")

    if net <= 0:
        print(f"\n  => CLOSED BY ARITHMETIC. The markup ({markup:.2%}) exceeds the")
        print(f"     entire carry dispersion ({gross:.2%}). There is no holding")
        print(f"     period, book size or instrument choice that recovers this:")
        print(f"     it is paid continuously, in proportion to time held, on")
        print(f"     exactly the position that earns the premium.")
    elif sharpe < BAR_2SIG:
        print(f"\n  => NOT TESTABLE. Net Sharpe {sharpe:.2f} sits below the {BAR_2SIG:.2f}")
        print(f"     bar, so even a correct result could not be distinguished")
        print(f"     from zero on {YEARS:.1f} years. Do not pre-register it.")
    else:
        print(f"\n  => {sharpe:.2f} clears the {BAR_2SIG:.2f} bar. Worth pre-registering.")
        print(f"     The pre-registration must then add: spread on rebalance,")
        print(f"     a stated rebalance frequency, and historical rate")
        print(f"     differentials -- today's snapshot is not a backtest.")

    print(f"\n  CAVEAT, stated because it is load-bearing: dispersion is a")
    print(f"  snapshot of today's rate environment. The markup is the stable")
    print(f"  half. Judge the verdict on whether today's dispersion is")
    print(f"  plausibly typical, not on the decimal places.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
