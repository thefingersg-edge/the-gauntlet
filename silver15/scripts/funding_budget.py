#!/usr/bin/env python3
"""Power budget for a CRYPTO CASH-AND-CARRY strategy. Run BEFORE hypothesising.

NO PRICE RETURNS AND NO P&L ARE COMPUTED IN THIS FILE. The funding rate is a
PUBLISHED CASH FLOW — the same class of input as OANDA's financing rates in
carry_budget.py. No position is simulated, no price series is marked to
market, and no trade is filled.

STDLIB ONLY. urllib and json. Kraken's derivatives API is public and needs no
key, so this file needs no credentials and no virtualenv.

THE MECHANISM, WHICH IS THE POINT
---------------------------------
Nine families have failed. Eight of them forecast a direction and found no
directional content; the ninth (FX carry) harvested a premium whose entire
existence depends on uncovered interest parity failing — and in 2006-2026 it
did not fail enough. v6's lesson was precise and worth repeating:

    A power budget bounds what a test can RESOLVE. It cannot tell you the
    effect is there. v6's budget measured the markup honestly and was simply
    SILENT on the spot move, which turned out to be the decisive quantity.

Perpetual futures are structurally different, and the difference is exactly
the thing that killed v6. A perpetual has no expiry, so the exchange forces
convergence to spot by making one side pay the other: when the perp trades
above spot — which it does whenever the levered crowd is long — longs pay
shorts. Hold long spot and short perp and you are **market-neutral by
construction**. The spot move cancels between the legs instead of eating the
carry.

That is why this budget is closer to decisive than v6's was: the quantity
that was silent there is hedged here. Not absent — hedged, which is a claim
this file states rather than assumes, and lists the residuals of below.

WHAT DECIDES IT
---------------
  1. HOW MUCH funding actually pays, annualised, measured from published
     history rather than from a bull-market anecdote.
  2. HOW OFTEN it is positive. A mean dragged up by 2021 is not a strategy.
  3. FEES, which are one-off and therefore amortise over the holding period.
     This is the first family in the project where holding LONGER reduces
     cost per unit time instead of the reverse.
  4. THE BAR, 2/sqrt(years), which the length of funding history sets.

WHAT THIS BUDGET CANNOT SEE — read before believing the verdict
---------------------------------------------------------------
Written before the run, in the same spirit as v6's "anticipated failure
modes", because a budget that oversells itself is worse than no budget:

  * BASIS RISK AT ENTRY AND EXIT. The legs are neutral while held, not while
    being put on. If the perp is at a premium when you enter and at par when
    you exit, that premium is a real loss no funding figure shows.
  * LIQUIDATION OF THE SHORT PERP LEG. A spot rally is neutral in P&L but
    NOT in margin: the short leg loses margin while the spot gain sits in a
    different account. Undercollateralise and you get liquidated at exactly
    the wrong moment, which converts a market-neutral trade into a directional
    loss. Real capital requirement is far above notional/leverage.
  * EXCHANGE COUNTERPARTY RISK. FTX went to zero with customer funds inside
    it. This is not diversifiable by holding more pairs on one venue, and it
    does not appear in any Sharpe ratio.
  * FILLS. Published funding is what the exchange paid, not what you would
    have captured after slippage on two legs.
  * FUNDING GOES NEGATIVE. In a bear market shorts pay longs, and the trade
    bleeds rather than merely stopping.

    python funding_budget.py --self-test
    python funding_budget.py
    python funding_budget.py --symbols PF_XBTUSD,PF_ETHUSD --hold-days 90
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import urllib.error
import urllib.request

VERSION = "1.1"

KRAKEN_FUNDING = ("https://futures.kraken.com/derivatives/api/v4/"
                  "historicalfundingrates?symbol={sym}")
KRAKEN_TICKERS = "https://futures.kraken.com/derivatives/api/v3/tickers"

DEFAULT_SYMBOLS = ["PF_XBTUSD", "PF_ETHUSD", "PF_SOLUSD", "PF_XRPUSD"]

# Kraken fee schedule at the lowest volume tier, as fractions. These are
# DEFAULTS, not measurements -- override them with your actual tier. They are
# stated here rather than buried because they move the answer.
SPOT_TAKER = 0.0026          # Kraken spot, lowest tier
FUTURES_TAKER = 0.0005       # Kraken Futures, lowest tier

SEC_PER_YEAR = 365.25 * 24 * 3600


# ---------------------------------------------------------------------------
# pure helpers -- exercised offline
# ---------------------------------------------------------------------------

def parse_ts(s: str) -> float:
    """RFC3339 -> epoch seconds. Kraken uses '2019-02-27T16:00:00.000Z'."""
    import datetime as dt
    s = s.strip().replace("Z", "+00:00")
    return dt.datetime.fromisoformat(s).timestamp()


def median(vals):
    v = sorted(vals)
    n = len(v)
    if not n:
        return None
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2.0


def interval_seconds(timestamps) -> float | None:
    """MEASURE the funding interval rather than assuming it.

    Kraken has changed funding cadence over the life of these contracts and
    documents it in prose. Taking the median gap between consecutive events
    makes the annualisation correct whatever the exchange currently does, and
    makes a change in cadence visible instead of silently rescaling every
    figure downstream.
    """
    if len(timestamps) < 3:
        return None
    gaps = [b - a for a, b in zip(timestamps, timestamps[1:]) if b > a]
    return median(gaps) if gaps else None


def annualise(mean_rate_per_interval: float, interval_sec: float) -> float:
    """Simple (not compounded) annualisation of a per-interval rate.

    Simple, deliberately. Compounding an 8-hourly rate over a year turns a
    0.01% payment into a headline that flatters by tens of percent, and you
    cannot compound a payment you have to actively re-collateralise anyway.
    """
    if interval_sec <= 0:
        return 0.0
    return mean_rate_per_interval * (SEC_PER_YEAR / interval_sec)


def roundtrip_fee(spot_fee: float = SPOT_TAKER,
                  fut_fee: float = FUTURES_TAKER) -> float:
    """Cost of putting the trade on and taking it off, both legs.

    Enter: buy spot + sell perp. Exit: sell spot + buy perp. Four fills.
    """
    return 2.0 * (spot_fee + fut_fee)


def amortised_fee(hold_days: float, spot_fee: float = SPOT_TAKER,
                  fut_fee: float = FUTURES_TAKER) -> float:
    """Round-trip fee expressed as an ANNUAL rate for a given holding period.

    THE SIGN OF THIS RELATIONSHIP IS THE NEWS. In every other family here,
    cost per unit time rose with trading frequency and the drag scaled as
    sqrt(trades). A one-off fee amortised over a hold falls as 1/hold. This
    is the first family where patience is rewarded rather than punished.
    """
    if hold_days <= 0:
        return float("inf")
    return roundtrip_fee(spot_fee, fut_fee) * (365.25 / hold_days)


def detectability_bar(years: float) -> float:
    return 2.0 / math.sqrt(years) if years > 0 else float("inf")


# ---------------------------------------------------------------------------

def fetch_funding(sym: str, timeout: float = 30.0, debug: bool = False):
    """Published funding history for one perpetual. Public, no key."""
    req = urllib.request.Request(KRAKEN_FUNDING.format(sym=sym), headers={
        "User-Agent": "silver15-research", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            payload = json.loads(r.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode(errors="replace")[:160]
        except Exception:                                      # noqa: BLE001
            pass
        if debug:
            print(f"      [debug] {sym}: HTTP {exc.code} {body}",
                  file=sys.stderr)
        if exc.code in (400, 404):
            return None
        raise SystemExit(f"Kraken HTTP {exc.code} for {sym}: {body}")
    except Exception as exc:                                   # noqa: BLE001
        raise SystemExit(f"Kraken request failed for {sym}: "
                         f"{type(exc).__name__} {str(exc)[:80]}")

    rates = payload.get("rates") or []
    if not rates:
        if debug:
            print(f"      [debug] {sym}: no rates, result="
                  f"{payload.get('result')}", file=sys.stderr)
        return None

    ts, rel = [], []
    for r in rates:
        t = r.get("timestamp")
        # relativeFundingRate is the rate as a FRACTION of notional, which is
        # what a return calculation needs. `fundingRate` is denominated in
        # currency and is not comparable across symbols or across price levels.
        v = r.get("relativeFundingRate")
        if t is None or v is None:
            continue
        try:
            ts.append(parse_ts(t))
            rel.append(float(v))
        except (ValueError, TypeError):
            continue
    return (ts, rel) if len(rel) >= 50 else None


def summarise(sym, ts, rel, hold_days, spot_fee, fut_fee):
    n = len(rel)
    span_years = (max(ts) - min(ts)) / SEC_PER_YEAR
    iv = interval_seconds(ts)
    mu = sum(rel) / n
    var = sum((x - mu) ** 2 for x in rel) / (n - 1) if n > 1 else 0.0
    sd = math.sqrt(var)
    per_year = SEC_PER_YEAR / iv if iv else 0.0

    gross = annualise(mu, iv) if iv else 0.0
    # Volatility of the ANNUAL funding stream: per-interval sd scaled by the
    # square root of the number of intervals. A second moment only.
    vol = sd * math.sqrt(per_year) if per_year else 0.0
    fee = amortised_fee(hold_days, spot_fee, fut_fee)
    return {
        "sym": sym, "n": n, "span": span_years, "interval_h": (iv / 3600) if iv else None,
        "gross": gross, "vol": vol, "net": gross - fee, "fee": fee,
        "pos_frac": sum(1 for x in rel if x > 0) / n,
        "first": min(ts), "last": max(ts),
    }


# ---------------------------------------------------------------------------

def self_test() -> int:
    fails = []

    def check(name, cond, d=""):
        print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"   {d}" if d else ""))
        if not cond:
            fails.append(name)

    print(f"funding_budget.py v{VERSION} — offline controls\n")
    print(f"  interpreter  {sys.executable}")
    print(f"  stdlib only, no key and no venv required\n")

    # 1-2. timestamp parsing
    t0 = parse_ts("2019-02-27T16:00:00.000Z")
    t1 = parse_ts("2019-02-27T20:00:00.000Z")
    check("1 RFC3339 parsed", abs(t1 - t0 - 4 * 3600) < 1e-6,
          f"4h apart -> {(t1 - t0) / 3600:.1f}h")
    check("2 parser handles a missing millisecond field",
          abs(parse_ts("2020-01-01T00:00:00Z") -
              parse_ts("2020-01-01T00:00:00.000Z")) < 1e-9)

    # 3-4. the interval is MEASURED, not assumed
    eight = [i * 8 * 3600 for i in range(100)]
    check("3 8h cadence measured as 8h",
          abs(interval_seconds(eight) - 8 * 3600) < 1e-6)
    # A cadence change must land the median BETWEEN the two rates, so it can
    # neither be mistaken for the old cadence nor for the new one. The first
    # version of this control ended in `or True`, which made it incapable of
    # failing — the same defect as the small-cap validation gate and the v6
    # look-ahead probe. Written out as a strict inequality so it can bite.
    mixed = [i * 3600 for i in range(60)] + [60 * 3600 + i * 8 * 3600
                                             for i in range(1, 60)]
    iv_mixed = interval_seconds(mixed)
    check("4 a cadence CHANGE is not read as either single rate",
          3600 < iv_mixed < 8 * 3600,
          f"median gap {iv_mixed / 3600:.1f}h, strictly between 1h and 8h")

    # 5-6. annualisation
    check("5 annualisation is simple, not compounded",
          abs(annualise(0.0001, 8 * 3600) - 0.0001 * (365.25 * 3)) < 1e-9,
          f"{annualise(0.0001, 8 * 3600):.4%} from 0.01% per 8h")
    check("6 zero interval does not divide by zero",
          annualise(0.01, 0) == 0.0)

    # 7-9. fees. THE SIGN OF THE HOLD RELATIONSHIP IS THE POINT.
    rt = roundtrip_fee()
    check("7 round trip is four fills, two legs",
          abs(rt - 2 * (SPOT_TAKER + FUTURES_TAKER)) < 1e-12,
          f"{rt:.4%}")
    f30, f180 = amortised_fee(30), amortised_fee(180)
    check("8 longer holds cost LESS per year", f180 < f30,
          f"30d {f30:.2%}/yr vs 180d {f180:.2%}/yr")
    check("9 fee scales as 1/hold", abs(f30 / f180 - 6.0) < 1e-9,
          "6x the hold -> 1/6 the annual drag")

    # 10. the bar
    check("10 bar falls as 1/sqrt(years)",
          abs(detectability_bar(4) - 1.0) < 1e-12,
          f"4 years -> {detectability_bar(4):.2f}")

    # 11-13. the summary, on a synthetic stream with a KNOWN answer
    iv = 8 * 3600
    n = int(365.25 * 3 * 2)                     # two years of 8h intervals
    ts = [i * iv for i in range(n)]
    rel = [0.0001] * n                          # exactly 0.01% per interval
    s = summarise("TEST", ts, rel, 180, SPOT_TAKER, FUTURES_TAKER)
    check("11 gross recovered from a constant stream",
          abs(s["gross"] - 0.0001 * 365.25 * 3) < 1e-6,
          f"{s['gross']:.2%} annual")
    check("12 a constant stream has zero volatility", s["vol"] < 1e-12)
    check("13 net = gross - amortised fee",
          abs(s["net"] - (s["gross"] - amortised_fee(180))) < 1e-12,
          f"net {s['net']:.2%}")

    # 14. NEGATIVE funding must come through negative, not be clipped
    s2 = summarise("TEST", ts, [-0.0001] * n, 180, SPOT_TAKER, FUTURES_TAKER)
    check("14 negative funding stays negative", s2["gross"] < 0,
          f"{s2['gross']:.2%} — a bear market must be visible, not clipped")

    # 15. positive fraction is honest about a mean carried by a minority
    lumpy = [0.01] * 10 + [-0.0005] * 90
    s3 = summarise("TEST", [i * iv for i in range(100)], lumpy, 180,
                   SPOT_TAKER, FUTURES_TAKER)
    check("15 positive fraction exposes a lumpy mean",
          abs(s3["pos_frac"] - 0.10) < 1e-9 and s3["gross"] > 0,
          "mean positive while 90% of intervals pay nothing")

    print(f"\n  {'ALL CONTROLS PASS' if not fails else str(len(fails)) + ' FAILED'}")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--symbols", default=",".join(DEFAULT_SYMBOLS))
    ap.add_argument("--hold-days", type=float, default=90)
    ap.add_argument("--spot-fee", type=float, default=SPOT_TAKER)
    ap.add_argument("--futures-fee", type=float, default=FUTURES_TAKER)
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--risk-free", type=float, default=0.0366,
                    help="annual risk-free rate for the comparison that\n"
                         "actually decides this: US 3-month, from FRED")
    ap.add_argument("--debug", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        return self_test()

    syms = [s.strip().upper() for s in a.symbols.split(",") if s.strip()]
    print(f"funding_budget.py v{VERSION}   NO PRICE RETURNS COMPUTED")
    print(f"  funding is a PUBLISHED cash flow, not a simulated position")
    print(f"  fees: spot {a.spot_fee:.3%} + futures {a.futures_fee:.3%} taker,"
          f" four fills = {roundtrip_fee(a.spot_fee, a.futures_fee):.3%}"
          f" round trip")
    print(f"  amortised over a {a.hold_days:.0f}-day hold ="
          f" {amortised_fee(a.hold_days, a.spot_fee, a.futures_fee):.2%}/yr\n")

    print("PUBLISHED FUNDING HISTORY")
    print("=" * 78)
    print(f"  {'symbol':<12}{'events':>8}{'span':>7}{'every':>8}"
          f"{'gross/yr':>10}{'vol/yr':>9}{'net/yr':>9}{'% pos':>8}")
    rows = []
    for s in syms:
        got = fetch_funding(s, a.timeout, a.debug)
        if not got:
            print(f"  {s:<12}{'no data':>8}")
            continue
        ts, rel = got
        r = summarise(s, ts, rel, a.hold_days, a.spot_fee, a.futures_fee)
        rows.append(r)
        iv = f"{r['interval_h']:.0f}h" if r["interval_h"] else "?"
        print(f"  {r['sym']:<12}{r['n']:>8,}{r['span']:>7.1f}{iv:>8}"
              f"{r['gross']:>10.2%}{r['vol']:>9.2%}{r['net']:>9.2%}"
              f"{r['pos_frac']:>8.0%}")

    if not rows:
        print("\n  no funding history returned. Re-run with --debug.")
        return 1

    span = median([r["span"] for r in rows])
    gross = median([r["gross"] for r in rows])
    vol = median([r["vol"] for r in rows])
    fee = amortised_fee(a.hold_days, a.spot_fee, a.futures_fee)
    net = gross - fee

    print(f"\nTHE DECIDING NUMBERS  (medians across {len(rows)} perpetuals)")
    print("=" * 78)
    print(f"  median span                    {span:.1f} years")
    print(f"  gross annual funding           {gross:+.2%}")
    print(f"  annual fee at {a.hold_days:.0f}-day hold      {fee:.2%}")
    print(f"  NET annual                     {net:+.2%}")
    print(f"  intervals paying positive      "
          f"{median([r['pos_frac'] for r in rows]):.0%}")

    # ---- WHY NO SHARPE IS PRINTED ----------------------------------------
    #
    # v1.0 divided net funding by the volatility of the FUNDING STREAM and
    # called it a Sharpe ratio. That produced +8.48 at a one-year hold, which
    # should have been obviously impossible and instead looked like a result.
    #
    # The denominator was wrong by orders of magnitude. The risk in this
    # trade is NOT that funding varies -- funding is a contractual payment
    # and it varies by fractions of a percent. The risk is BASIS: the
    # perp-versus-spot spread at the moments you enter and exit, plus margin
    # and counterparty. None of those are in the funding series, so no
    # denominator computable from this file is the right one.
    #
    # Printing a wrong Sharpe is worse than printing none, because a large
    # number invites belief. So: none.
    print(f"\n  NO SHARPE IS REPORTED, DELIBERATELY.")
    print(f"  Funding-stream volatility is {vol:.2%}/yr, which is not the")
    print(f"  risk of this trade. The risk is basis at entry and exit, margin")
    print(f"  on the short leg, and the exchange. Dividing by {vol:.2%} gives")
    print(f"  a number in the high single or double digits and it would be")
    print(f"  meaningless. The honest comparison is against cash.")

    # ---- THE COMPARISON THAT ACTUALLY DECIDES IT -------------------------
    print(f"\n  VERSUS THE RISK-FREE ALTERNATIVE")
    print(f"  {'hold':>6}{'fee/yr':>9}{'net/yr':>9}{'vs T-bill':>12}")
    best_h, best_net = None, -1e9
    for h in (30, 90, 180, 365):
        f = amortised_fee(h, a.spot_fee, a.futures_fee)
        n = gross - f
        if n > best_net:
            best_h, best_net = h, n
        print(f"  {h:>6}{f:>9.2%}{n:>+9.2%}{n - a.risk_free:>+12.2%}")
    print(f"\n  risk-free rate assumed {a.risk_free:.2%}"
          f"  (US 3-month; override with --risk-free)")

    print(f"\nVERDICT")
    print("=" * 78)
    excess = best_net - a.risk_free
    print(f"  best case is a {best_h}-day hold: {best_net:+.2%} net,"
          f" {excess:+.2%} versus cash")
    if best_net <= 0:
        print(f"\n  => CLOSED. Fees exceed the entire published funding stream")
        print(f"     at every holding period tested.")
    elif excess <= 0:
        print(f"\n  => CLOSED ON THE RISK PREMIUM, not on the arithmetic.")
        print(f"     The trade pays {best_net:.2%} and a Treasury bill pays")
        print(f"     {a.risk_free:.2%}. You would be accepting exchange")
        print(f"     counterparty risk, basis risk and margin calls to earn")
        print(f"     LESS than cash. FTX went to zero with customer funds in")
        print(f"     it; that is the risk being paid {excess:.2%} to take.")
    else:
        print(f"\n  => pays {excess:+.2%} over cash at a {best_h}-day hold.")
        print(f"     Worth pre-registering ONLY with, because this file")
        print(f"     cannot see them:")
        print(f"       - basis at entry and exit (the legs are neutral while")
        print(f"         HELD, not while being PUT ON)")
        print(f"       - margin for the short leg, sized so a spot rally")
        print(f"         cannot liquidate it")
        print(f"       - an explicit exchange-failure assumption")

    if span < 3:
        print(f"\n  !! only {span:.1f} years of published history. Note this is")
        print(f"     a different kind of uncertainty from the rest of the")
        print(f"     project: funding is a CONTRACTUAL payment, so you do not")
        print(f"     need statistical significance to know it was received.")
        print(f"     The risk is that the regime does not persist, and one")
        print(f"     year tells you almost nothing about that.")

    print(f"\n  Reminder from v6: a budget bounds what a test can RESOLVE.")
    print(f"  It cannot tell you the effect is there.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
