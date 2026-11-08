#!/usr/bin/env python3
"""PHASE 0 for PREREGISTRATION_v5 -- how much of FX carry does OANDA keep?

THE IDENTITY THIS RESTS ON
--------------------------
OANDA quotes a long and a short financing rate for every instrument. If the
formula is the standard one -- the interest differential, less a flat
administrative charge applied AGAINST you on both sides -- then

    longRate  =  D - m
    shortRate = -D - m

so both unknowns fall out of OANDA's own two published numbers:

    D = (longRate - shortRate) / 2     the true differential
    m = -(longRate + shortRate) / 2    the broker's take, per side

No external interest-rate data is needed to recover either. The whole cost
budget is one API call.

THE MODEL IS TESTED, NOT ASSUMED. If m is a flat administrative charge it
must be roughly CONSTANT across instruments. This file reports its
dispersion and REFUSES to continue if it is not, because the decomposition
above would then be wrong and everything derived from it worthless.

WHAT IT DECIDES (PREREGISTRATION_v5 section 4)
----------------------------------------------
    Gate 0:  max over FX pairs of  (|D| - m) / annualised vol  >=  0.40

That ratio is an UPPER BOUND on the achievable Sharpe -- it credits the
position with the entire net differential and charges it nothing for spot
drift or for the crash risk that is the premium's reason for existing. If
the upper bound is under the bar for every pair, no history can rescue it.

NO STRATEGY IS SIMULATED AND NO ORDER IS EVER PLACED. Read-only endpoints.
The token is loaded by fetch_oanda and never printed.

    python fx_carry_probe.py --self-test        # offline, no token
    python fx_carry_probe.py
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys

VERSION = "1.2"

#: PREREGISTRATION_v5 sections 4 and 8. Frozen.
GATE_0_RATIO = 0.40
#: Units guard. A 365x error moves EVERY pair, so the median is what
#: detects it; MAX_PLAUSIBLE_D now only marks a pair as worth naming.
MAX_PLAUSIBLE_D = 0.20
MIN_PLAUSIBLE_MEDIAN_D = 0.0005
MAX_PLAUSIBLE_MEDIAN_D = 0.20
MAX_M_DISPERSION = 0.0075     # m must be near-constant if it is a flat fee
VOL_YEARS = 5
CCY = {"AUD", "CAD", "CHF", "EUR", "GBP", "JPY", "NZD", "USD", "SGD",
       "HKD", "NOK", "SEK", "ZAR", "MXN", "TRY", "PLN", "CZK", "HUF",
       "CNH", "THB", "DKK", "INR", "SAR"}

DEFAULT_FO_DIR = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "silver15", "scripts"))


def load_fo(fo_dir):
    if not os.path.isdir(fo_dir):
        raise SystemExit(
            f"cannot find fetch_oanda.py in {fo_dir}\n"
            f"  pass --fetch-oanda-dir /path/to/silver15/scripts")
    sys.path.insert(0, fo_dir)
    import fetch_oanda as fo
    return fo


def is_fx(instrument):
    """A genuine FX pair, not an index or metal CFD.

    This matters for the carry gate and not merely for tidiness. An index
    or metal CFD has a financing COST but no interest differential to
    earn: a long gold position pays carry, it does not collect it. Leaving
    them in would let a large negative D masquerade as a large carry
    opportunity purely by taking its absolute value.
    """
    parts = instrument.upper().split("_")
    return len(parts) == 2 and parts[0] in CCY and parts[1] in CCY


def decompose(long_rate, short_rate):
    """(differential, broker markup per side) from the two quoted rates."""
    return (long_rate - short_rate) / 2.0, -(long_rate + short_rate) / 2.0


def model_holds(markups, tol=MAX_M_DISPERSION):
    """Is the markup a flat administrative charge, as the model claims?

    Reported as (median, spread, ok). A flat fee must be near-constant
    across instruments; if it is not, the long/short decomposition is the
    wrong model of OANDA's formula and nothing derived from it may be
    used. Interquartile spread is used rather than min-max so that one
    exotic pair cannot veto the whole measurement.
    """
    if len(markups) < 4:
        return (None, None, False)
    s = sorted(markups)
    med = s[len(s) // 2]
    q1, q3 = s[len(s) // 4], s[(3 * len(s)) // 4]
    return (med, q3 - q1, (q3 - q1) <= tol)


def units_ok(rows):
    """Catch a daily rate read as annual, or the reverse.

    Silent and catastrophic: reading a daily rate as annual overstates by
    365x and the reverse understates by the same.

    v1.1 tested this PER PAIR -- any |D| above 20% stopped the run, on the
    stated grounds that "majors do not have twenty-point differentials".
    The live universe is 68 pairs, not the majors I had in mind, and it
    duly tripped on USD_TRY, EUR_TRY and TRY_JPY at 28-31%. Turkish policy
    rates really are in that region. The guard was right about majors and
    wrong about the universe.

    So test the failure mode as it actually manifests. A units error is a
    SYSTEMATIC rescaling: every pair moves by the same 365x, not three of
    them. The median is the statistic that sees that and individual
    outliers do not disturb. Genuine high-rate currencies are reported as
    a note rather than treated as a fault.

    Returns (ok, outliers, median |D|).
    """
    ds = sorted(abs(r["D"]) for r in rows)
    if not ds:
        return True, [], None
    med = ds[len(ds) // 2]
    ok = MIN_PLAUSIBLE_MEDIAN_D <= med <= MAX_PLAUSIBLE_MEDIAN_D
    outliers = [r for r in rows if abs(r["D"]) > MAX_PLAUSIBLE_D]
    return ok, outliers, med


def carry_ratio(D, m, vol):
    """(|D| - m) / vol -- an upper bound on the achievable Sharpe."""
    if not vol or vol <= 0:
        return None
    return (abs(D) - m) / vol


def api_url(host, path):
    """Join a host and path with exactly one scheme.

    fetch_oanda.HOSTS already carries "https://". Prefixing it again gives
    "https://https://api-fxtrade.oanda.com/..." which fails DNS with a
    message about the nodename rather than about the URL, so the cause is
    not obvious from the error. Accepts a host with or without a scheme.
    """
    h = str(host).strip().rstrip("/")
    for pre in ("https://", "http://"):
        if h.startswith(pre):
            h = h[len(pre):]
            break
    return "https://" + h + "/" + str(path).lstrip("/")


def closes_from(rows):
    """Closing prices out of whatever shape fetch_oanda hands back.

    I did not have fetch_oanda.py to read when writing this, so the row
    shape is DISCOVERED rather than assumed: a sequence is read
    positionally as (time, o, h, l, c, ...), a mapping by key. Guessing
    one and silently reading the OPEN as the close would bias every
    volatility estimate by a day's drift, which is small enough never to
    look wrong and large enough to move a ratio sitting near the bar.

    Returns [] rather than raising, so the caller reports a pair as
    unmeasured instead of the run dying on one instrument.
    """
    out = []
    for r in rows:
        try:
            if isinstance(r, dict):
                v = (r.get("close") if "close" in r else
                     r.get("c") if "c" in r else
                     r.get("mid", {}).get("c"))
            elif isinstance(r, (list, tuple)) and len(r) >= 5:
                v = r[4]
            else:
                continue
            v = float(v)
        except (TypeError, ValueError, AttributeError):
            continue
        if v > 0:
            out.append(v)
    return out


def annualised_vol(closes, periods_per_year=252):
    """From daily closes."""
    if len(closes) < 30:
        return None
    r = [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes))
         if closes[i - 1] > 0 and closes[i] > 0]
    if len(r) < 30:
        return None
    mu = sum(r) / len(r)
    var = sum((x - mu) ** 2 for x in r) / (len(r) - 1)
    return math.sqrt(var) * math.sqrt(periods_per_year)


def gate_0(rows):
    """PREREGISTRATION_v5 section 4. Pure, so it can be tested."""
    fx = [r for r in rows if r["fx"] and r.get("ratio") is not None]
    best = max(fx, key=lambda r: r["ratio"]) if fx else None
    passed = bool(best and best["ratio"] >= GATE_0_RATIO)
    return passed, best, fx


def report(rows, fo=None, token=None):
    ok_u, bad, med_d = units_ok([r for r in rows if r["fx"]])
    med, spread, flat = model_holds([r["m"] for r in rows if r["fx"]])

    print(f"\n  THE MARKUP MODEL -- tested, not assumed")
    if med is None:
        print("    too few instruments to test the model")
    else:
        print(f"    median markup {med*100:+.3f}%/yr per side, "
              f"interquartile spread {spread*100:.3f} pts")
        print(f"    a flat administrative fee should be near-constant: "
              f"{'CONSISTENT' if flat else 'NOT CONSISTENT'}")
    if not flat:
        raise SystemExit(
            "\n  STOP: the markup is not a flat charge across instruments, "
            "so\n  longRate/shortRate cannot be decomposed into a "
            "differential and a fee.\n  Per section 6 this reports that "
            "OANDA's financing does not fit the model\n  rather than "
            "substituting an assumed markup.")
    print(f"\n  UNITS -- a 365x error moves every pair, so the median sees it")
    print(f"    median |D| across FX pairs: {med_d*100:.2f}%  -> "
          f"{'annual, as expected' if ok_u else 'NOT ANNUAL'}")
    if not ok_u:
        raise SystemExit(
            f"\n  STOP: a median differential of {med_d*100:.2f}% is not an "
            f"annual rate.\n  Fix the units before reading any number "
            f"above.")
    if bad:
        print(f"    {len(bad)} pair(s) above {MAX_PLAUSIBLE_D*100:.0f}%, "
              f"and they are real high-rate currencies:")
        for r in bad[:6]:
            print(f"      {r['instrument']:<12} D = {r['D']*100:+.1f}%")
        print("    These stay in the universe -- section 6 fixes it before "
              "any return is")
        print("    computed. But the carry-to-vol bound is far LOOSER for "
              "them: it credits")
        print("    the whole differential and charges nothing for drift, "
              "and a high-inflation")
        print("    currency's drift is large and one-way against the "
              "carry.")

    fx = sorted([r for r in rows if r["fx"] and r.get("ratio") is not None],
                key=lambda r: -r["ratio"])
    print(f"\n  {'pair':<12}{'gross D':>10}{'markup':>9}{'net':>9}"
          f"{'vol':>8}{'net/vol':>9}{'kept by broker':>16}")
    print("  " + "-" * 73)
    for r in fx:
        keep = (r["m"] / abs(r["D"]) * 100) if r["D"] else float("inf")
        print(f"  {r['instrument']:<12}{r['D']*100:>9.2f}%"
              f"{r['m']*100:>8.2f}%{(abs(r['D'])-r['m'])*100:>8.2f}%"
              f"{r['vol']*100:>7.1f}%{r['ratio']:>9.2f}"
              f"{keep:>15.0f}%")

    other = [r for r in rows if not r["fx"]]
    if other:
        print(f"\n  excluded from the carry gate ({len(other)} non-FX): "
              "an index or metal CFD")
        print("  has a financing cost but no differential to earn -- a long "
              "gold position")
        print("  pays carry, it does not collect it")

    passed, best, _ = gate_0(rows)
    print(f"\n  GATE 0 -- frozen in PREREGISTRATION_v5 section 4")
    print(f"    best carry-to-vol ratio: "
          + (f"{best['ratio']:.2f} on {best['instrument']}"
             if best else "none"))
    print(f"    [{'PASS' if passed else 'FAIL'}] "
          f"upper bound on Sharpe >= {GATE_0_RATIO:.2f}")
    print(f"\n  {'PROCEED to Phase 1' if passed else 'REJECTED'}")
    if not passed:
        print("  The differential net of the broker is arithmetically too "
              "small to")
        print("  reach the bar, and that is BEFORE charging spot drift or "
              "the crash")
        print("  risk the premium exists to pay for. No history can rescue "
              "it, and")
        print("  per section 6 no threshold filter or pair selection is "
              "tried.")
    return passed


def self_test():
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        if not isinstance(cond, (bool, int)):
            raise TypeError(f"check({name!r}) got {type(cond).__name__}")
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}"
              + (f"   {detail}" if detail else ""))

    print(f"fx_carry_probe.py v{VERSION} self-test\n")

    print("the decomposition recovers what was planted (sec 8.1)")
    D, m = 0.032, 0.005
    d2, m2 = decompose(D - m, -D - m)
    check("differential recovered exactly", abs(d2 - D) < 1e-12,
          f"{d2*100:.3f}% vs {D*100:.3f}%")
    check("markup recovered exactly", abs(m2 - m) < 1e-12,
          f"{m2*100:.3f}% vs {m*100:.3f}%")
    #: sign symmetry: the broker takes from BOTH sides
    d3, m3 = decompose(-D - m, D - m)
    check("a negative differential still yields a POSITIVE markup",
          abs(d3 + D) < 1e-12 and abs(m3 - m) < 1e-12,
          f"D {d3*100:+.2f}%  m {m3*100:+.2f}%")

    print("\nthe flat-fee model can be falsified (sec 8.2)")
    flat = [0.005, 0.0051, 0.0049, 0.005, 0.0052, 0.0048, 0.005, 0.005]
    med, sp, good = model_holds(flat)
    check("a genuinely flat fee is CONSISTENT", good,
          f"median {med*100:.3f}%, spread {sp*100:.3f} pts")
    #: planted: a markup that scales with the pair rather than being flat
    wide = [0.001, 0.004, 0.009, 0.016, 0.025, 0.036, 0.049, 0.064]
    med2, sp2, good2 = model_holds(wide)
    check("a markup that varies by pair is REFUSED", not good2,
          f"spread {sp2*100:.3f} pts")
    check("too few instruments is not silently a pass",
          not model_holds([0.005, 0.005])[2])

    print("\nthe units guard, rebuilt around how the error actually looks")
    #: A realistic universe: majors clustered low, plus the three genuine
    #: high-rate pairs the live run tripped on.
    majors = [dict(D=d, instrument=f"P{i}") for i, d in enumerate(
        [0.005, -0.012, 0.021, -0.004, 0.033, -0.028, 0.017, 0.009,
         -0.019, 0.026, 0.031, -0.007])]
    exotics = [dict(D=-0.279, instrument="USD_TRY"),
               dict(D=-0.297, instrument="EUR_TRY"),
               dict(D=+0.310, instrument="TRY_JPY")]
    ok_a, out_a, med_a = units_ok(majors + exotics)
    check("the REAL universe passes: three exotics do not condemn 68 pairs",
          ok_a, f"median |D| {med_a*100:.2f}%, {len(out_a)} named outliers")
    check("and the outliers are still reported, not hidden",
          {r["instrument"] for r in out_a} ==
          {"USD_TRY", "EUR_TRY", "TRY_JPY"},
          f"{sorted(r['instrument'] for r in out_a)}")
    #: the old per-pair rule would have stopped the run on this universe
    check("the v1.1 per-pair rule WOULD have failed it",
          any(abs(r["D"]) > MAX_PLAUSIBLE_D for r in majors + exotics))
    #: planted: a DAILY rate misread as annual is 365x too large ON EVERY
    #: PAIR -- which is what a units error actually looks like
    x365 = [dict(D=r["D"] * 365, instrument=r["instrument"])
            for r in majors + exotics]
    check("every pair scaled 365x is CAUGHT", not units_ok(x365)[0],
          f"median |D| {units_ok(x365)[2]*100:.0f}%")
    #: and the reverse, which the old rule could never have caught
    d365 = [dict(D=r["D"] / 365, instrument=r["instrument"])
            for r in majors + exotics]
    check("an annual rate read as DAILY is caught too", not units_ok(d365)[0],
          f"median |D| {units_ok(d365)[2]*100:.4f}%")
    check("the old per-pair rule could NOT have caught that one",
          all(abs(r["D"]) <= MAX_PLAUSIBLE_D for r in d365),
          "everything shrinks, nothing exceeds 20%")

    print("\nFX pairs only (sec 8.5)")
    check("AUD_JPY is FX", is_fx("AUD_JPY"))
    check("EUR_USD is FX", is_fx("EUR_USD"))
    check("XAU_USD is NOT", not is_fx("XAU_USD"))
    check("SPX500_USD is NOT", not is_fx("SPX500_USD"))
    check("NAS100_USD is NOT", not is_fx("NAS100_USD"))

    print("\nGate 0, either side of the bar (sec 8.3)")
    def row(name, D, m, vol, fx=True):
        r = dict(instrument=name, D=D, m=m, vol=vol, fx=fx)
        r["ratio"] = carry_ratio(D, m, vol)
        return r
    #: 4.5% net on 10% vol = 0.45, just over the bar
    over = [row("AUD_JPY", 0.050, 0.005, 0.10)]
    p1, b1, _ = gate_0(over)
    check("a pair just over the bar PASSES", p1,
          f"{b1['ratio']:.2f}")
    #: 3.5% net on 10% vol = 0.35, just under
    under = [row("AUD_JPY", 0.040, 0.005, 0.10)]
    p2, b2, _ = gate_0(under)
    check("a pair just under the bar FAILS", not p2, f"{b2['ratio']:.2f}")
    #: the markup is what decides it: same D, bigger fee
    p3, b3, _ = gate_0([row("AUD_JPY", 0.050, 0.015, 0.10)])
    check("tripling the markup turns the pass into a FAIL", not p3,
          f"{b1['ratio']:.2f} -> {b3['ratio']:.2f}")
    #: a non-FX instrument must not be able to carry the gate
    p4, b4, fx4 = gate_0([row("XAU_USD", -0.060, 0.005, 0.10, fx=False),
                          row("EUR_GBP", 0.004, 0.005, 0.06)])
    check("a metal CFD cannot pass the gate on the strength of |D|",
          not p4 and all(r["instrument"] != "XAU_USD" for r in fx4),
          f"best is {b4['instrument']}")
    check("a negative net differential gives a negative ratio",
          row("EUR_GBP", 0.004, 0.005, 0.06)["ratio"] < 0)

    print("\nexactly one scheme in a built URL")
    #: The live run failed here. fetch_oanda.HOSTS already carries
    #: "https://", so f"https://{host}/..." produced
    #: "https://https://api-fxtrade.oanda.com/..." -- which fails DNS with
    #: a message about the nodename, not about the URL, so the cause was
    #: invisible in the error.
    want = "https://api-fxtrade.oanda.com/v3/accounts"
    check("a host that already has a scheme is not double-prefixed",
          api_url("https://api-fxtrade.oanda.com", "v3/accounts") == want,
          api_url("https://api-fxtrade.oanda.com", "v3/accounts"))
    check("a bare host gets one added",
          api_url("api-fxtrade.oanda.com", "v3/accounts") == want)
    check("a leading slash on the path does not double up",
          api_url("api-fxtrade.oanda.com", "/v3/accounts") == want)
    check("a trailing slash on the host does not double up",
          api_url("https://api-fxtrade.oanda.com/", "v3/accounts") == want)
    check("no built URL contains two schemes",
          all(u.count("https://") == 1 for u in (
              api_url("https://h.com", "p"), api_url("h.com", "/p"),
              api_url("http://h.com", "p"))))

    print("\nthe candle shape is discovered, not assumed")
    tup = [(1, 1.10, 1.12, 1.09, 1.11, 500), (2, 1.11, 1.13, 1.10, 1.12, 400)]
    check("a positional row reads the CLOSE, not the open",
          closes_from(tup) == [1.11, 1.12], f"{closes_from(tup)}")
    check("a flat dict works", closes_from(
        [{"time": 1, "open": 1.10, "close": 1.11}]) == [1.11])
    check("an OANDA-style nested mid works", closes_from(
        [{"time": 1, "mid": {"o": "1.10", "c": "1.11"}}]) == [1.11])
    #: planted: a shape nothing understands must yield nothing, not a
    #: silently truncated series that still computes a volatility
    check("an unknown shape yields no closes, not a wrong one",
          closes_from([object(), None, (1, 2)]) == [])
    check("a zero or negative price is dropped",
          closes_from([(1, 0, 0, 0, 0.0, 0), (2, 1, 1, 1, 1.5, 0)]) == [1.5])

    print("\nvolatility from closes")
    import random
    rng = random.Random(4)
    px, p = [100.0], 100.0
    for _ in range(1500):
        p *= math.exp(rng.gauss(0, 0.10 / math.sqrt(252)))
        px.append(p)
    v = annualised_vol(px)
    check("a 10% series measures near 10%", abs(v - 0.10) < 0.02,
          f"{v*100:.1f}%")
    check("too few closes returns None, not a number",
          annualised_vol([100.0, 101.0]) is None)

    print("\nthis file places NO orders")
    import fx_carry_probe as _self
    banned = ("order", "trade_", "buy", "sell", "execute", "submit",
              "backtest", "signal")
    def scan():
        return [x for x in dir(_self) if not x.startswith("_")
                and any(w in x.lower() for w in banned)]
    check("no order / execute / submit function", scan() == [], f"{scan()}")
    setattr(_self, "submit_order", lambda: None)
    fired = scan() == ["submit_order"]
    delattr(_self, "submit_order")
    check("and the detector demonstrably FIRES when one is added",
          fired and scan() == [], "planted submit_order, caught, removed")

    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch-oanda-dir", default=DEFAULT_FO_DIR)
    ap.add_argument("--env", default="live", choices=("live", "practice"))
    ap.add_argument("--account", default="")
    ap.add_argument("--pause", type=float, default=0.15)
    ap.add_argument("--out", default="")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())

    import time
    fo = load_fo(a.fetch_oanda_dir)
    host, token = fo.HOSTS[a.env], fo.load_token()
    print(f"fx_carry_probe.py v{VERSION}   PHASE 0 -- COST ONLY, "
          f"host {host}\n")

    acct = a.account
    if not acct:
        js = fo.api_get(api_url(host, "v3/accounts"), token)
        accts = js.get("accounts", [])
        if not accts:
            raise SystemExit("  no accounts visible for this token")
        acct = accts[0]["id"]
    print(f"  account ...{acct[-6:]}   (id not printed in full)")

    js = fo.api_get(
        api_url(host, f"v3/accounts/{acct}/instruments"), token)
    rows = []
    for it in js.get("instruments", []):
        fin = it.get("financing") or {}
        lr, sr = fin.get("longRate"), fin.get("shortRate")
        if lr is None or sr is None:
            continue
        D, m = decompose(float(lr), float(sr))
        rows.append(dict(instrument=it["name"], fx=is_fx(it["name"]),
                         longRate=float(lr), shortRate=float(sr),
                         D=D, m=m, vol=None, ratio=None))
    print(f"  {len(rows)} instruments quote a financing rate, "
          f"{sum(1 for r in rows if r['fx'])} of them FX pairs")

    print(f"\n  VOLATILITY -- {VOL_YEARS} years of daily closes")
    from datetime import datetime, timedelta, timezone
    start = datetime.now(timezone.utc) - timedelta(days=int(VOL_YEARS * 366))
    for r in rows:
        if not r["fx"]:
            continue
        try:
            payload = fo.api_get(
                fo.build_url(host, r["instrument"], "D", "M", start,
                             count=5000), token)
            closes = closes_from(fo.parse_candles(payload, "M"))
        except Exception as exc:                              # noqa: BLE001
            print(f"    {r['instrument']:<12} FAIL "
                  f"{fo.redact(str(exc), token)[:50]}")
            continue
        if len(closes) < 200:
            print(f"    {r['instrument']:<12} only {len(closes)} closes "
                  f"-- not measured")
            continue
        r["vol"] = annualised_vol(closes)
        r["ratio"] = carry_ratio(r["D"], r["m"], r["vol"])
        time.sleep(a.pause)
    got = sum(1 for r in rows if r["fx"] and r["vol"])
    print(f"    {got} of {sum(1 for r in rows if r['fx'])} pairs measured")

    passed = report(rows, fo, token)
    if a.out:
        with open(os.path.expanduser(a.out), "w") as fh:
            json.dump(dict(version=VERSION, rows=rows, proceed=bool(passed)),
                      fh, indent=2)
        print(f"\n  manifest -> {a.out}")
    sys.exit(0 if passed else 2)


if __name__ == "__main__":
    main()
