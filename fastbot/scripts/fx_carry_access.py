#!/usr/bin/env python3
"""PREREGISTRATION_v15 -- how much of the carry differential arrives.

Carry is the archetypal risk premium: paid an interest differential,
occasionally destroyed in a crash. FINDINGS.md rule 3 says that category
survives. Rule 2, now five for five, says it will die on ACCESS.

So this measures the access side first and touches no price series at
all. From OANDA's published financing rates alone:

    longRate  =  d - s          d = (longRate - shortRate) / 2
    shortRate = -d - s          s = -(longRate + shortRate) / 2

    net = |d| - s        pass-through = (|d| - s) / |d|

**If s >= |d| the pair pays negative carry in BOTH directions** and no
skill in picking the side recovers it.

THE CHAINING TEST -- the part nobody bothers with
--------------------------------------------------
The differentials must be internally consistent. Anchor USD at zero,
read each currency's implied rate off its USD pair, and every cross is
then PREDICTED:

    r_XXX = d(XXX_USD)   or   -d(USD_XXX)
    residual = d_quoted(XXX_YYY) - (r_XXX - r_YYY)

Zero residual means d is a real reference and s is the whole cost. A
non-zero residual means the reference is being shaded per pair -- a
second markup hiding behind the first, which a naive s calculation
cannot see.

THE TOKEN
---------
Found by fetch_oanda.load_token(). Never printed, never placed in a URL,
every error passed through fo.redact(). This file reads only.

    python3 fx_carry_access.py --self-test    # offline, no token
    python3 fx_carry_access.py --fetch        # one API call
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import statistics as st
import sys

VERSION = "1.1"

#: v1.1 -- A ZERO IS NOT A RATE.
#:
#: The live run returned longRate == shortRate == 0.000 for USD_CAD,
#: USD_MXN and USD_TRY. v1.0 took those at face value, so d = 0 and the
#: anchored rate for CAD, MXN and TRY came out at exactly 0.00 %/yr --
#: which then made every CAD and TRY cross look violently shaded:
#: EUR_TRY -2811 bp, TRY_JPY +2808 bp, six CAD crosses at +/-147.5 bp.
#:
#: **None of that was the broker. All of it was this file.** Excluding
#: the missing rows drops the worst residual from 2811 bp to 5.0 bp.
#:
#: Same class as bid==ask read as a zero spread, `tradeable` read as
#: traded, and a 2000-row page cap read as history depth. Fourth time.
MISSING_RATE_EPS = 1e-12

DEFAULT_FO_DIR = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "silver15", "scripts"))

#: ---- FROZEN IN PREREGISTRATION_v15 SECTION 4 ----
GATE_A_MIN_POSITIVE = 5          # instruments with net > 0
GATE_B_TOP_N = 10                # by |d|
GATE_B_MIN_PASSTHROUGH = 0.50    # median
GATE_C_MAX_RESIDUAL = 0.0025     # 0.25 %/yr, median |residual|
GATE_D_MIN_SPREAD = 0.020        # 2.0 %/yr on a 1-long/1-short book
QUINTILE = 5
ANCHOR = "USD"


def build_instruments_url(host, account):
    """No token parameter, by construction -- see oanda_financing.py."""
    return f"{host}/v3/accounts/{account}/instruments"


def build_accounts_url(host):
    return f"{host}/v3/accounts"


def has_financing(long_rate, short_rate):
    """False when the API returned no rate rather than a rate of zero.

    A genuine zero differential with a genuine markup would still give
    longRate == shortRate == -s, i.e. both NEGATIVE and equal. Both
    EXACTLY zero means no data: it would imply a broker quoting a pair
    with no differential AND no markup, which is not a thing.
    """
    return not (abs(long_rate) < MISSING_RATE_EPS
                and abs(short_rate) < MISSING_RATE_EPS)


def decompose(long_rate, short_rate):
    """(d, s) -- the implied differential and the per-side markup."""
    d = (long_rate - short_rate) / 2.0
    s = -(long_rate + short_rate) / 2.0
    return d, s


def net_carry(d, s):
    """What the receiving side actually nets, annualised. May be < 0."""
    return abs(d) - s


def pass_through(d, s):
    """Fraction of the differential that arrives. None if d is ~0."""
    if abs(d) < 1e-9:
        return None
    return (abs(d) - s) / abs(d)


def split_pair(name):
    """'EUR_USD' -> ('EUR', 'USD'). None if it is not a currency pair."""
    parts = name.split("_")
    if len(parts) != 2 or not all(len(p) == 3 and p.isalpha() for p in parts):
        return None
    return parts[0].upper(), parts[1].upper()


def implied_rates(pairs, anchor=ANCHOR):
    """{currency -> implied annual rate}, anchoring `anchor` at zero.

    Read ONLY off pairs quoted against the anchor, so the crosses stay
    unused and can therefore be predicted rather than fitted. Fitting
    them would guarantee small residuals and destroy the test.
    """
    r = {anchor: 0.0}
    for name, d in pairs.items():
        sp = split_pair(name)
        if not sp:
            continue
        a, b = sp
        if b == anchor:
            r[a] = d
        elif a == anchor:
            r[b] = -d
    return r


def residuals(pairs, rates, anchor=ANCHOR):
    """{cross -> quoted d minus predicted d}, crosses only."""
    out = {}
    for name, d in pairs.items():
        sp = split_pair(name)
        if not sp:
            continue
        a, b = sp
        if anchor in (a, b):
            continue                      # used to build the rates
        if a in rates and b in rates:
            out[name] = d - (rates[a] - rates[b])
    return out


def leg_rates(name, long_rate, short_rate, anchor=ANCHOR):
    """(long_the_foreign, short_the_foreign) financing, or None.

    For XXX_USD, long the foreign currency IS long the instrument.
    For USD_XXX it is SHORT the instrument -- getting this backwards
    would silently invert half the book.
    """
    sp = split_pair(name)
    if not sp:
        return None
    a, b = sp
    if b == anchor:
        return a, long_rate, short_rate
    if a == anchor:
        return b, short_rate, long_rate
    return None


def self_test():
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        if not isinstance(cond, (bool, int)):
            raise TypeError(f"check({name!r}) got {type(cond).__name__}")
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}"
              + (f"   {detail}" if detail else ""))

    print(f"fx_carry_access.py v{VERSION} self-test\n")

    print("the decomposition recovers what was planted")
    #: PLANTED: d = +3.00%, s = 1.00%. So longRate = +2%, shortRate = -4%.
    d, s = decompose(0.02, -0.04)
    check("d comes back as +3.00%", abs(d - 0.03) < 1e-12, f"{d*100:.2f}%")
    check("s comes back as 1.00%", abs(s - 0.01) < 1e-12, f"{s*100:.2f}%")
    check("net is 2.00%", abs(net_carry(d, s) - 0.02) < 1e-12)
    check("pass-through is 66.7%",
          abs(pass_through(d, s) - 2 / 3) < 1e-9,
          f"{pass_through(d,s)*100:.1f}%")
    #: the SPX500_USD numbers already measured -- a real anchor point
    d2, s2 = decompose(-0.0615, 0.0115)
    check("SPX500_USD gives d=-3.65% and s=2.50% as measured",
          abs(d2 + 0.0365) < 1e-12 and abs(s2 - 0.025) < 1e-12,
          f"d={d2*100:.2f}% s={s2*100:.2f}%")

    print("\nnegative carry in BOTH directions is detected")
    #: PLANTED: a tiny differential swamped by the markup.
    d3, s3 = decompose(-0.005, -0.015)
    check("d = +0.50%, s = 1.00%", abs(d3 - 0.005) < 1e-12
          and abs(s3 - 0.01) < 1e-12)
    check("net is NEGATIVE -- you pay to hold it either way",
          net_carry(d3, s3) < 0, f"{net_carry(d3,s3)*100:+.2f}%")
    check("and pass-through is negative, not merely small",
          pass_through(d3, s3) < 0)

    print("\nchaining recovers planted rates and predicts the crosses")
    #: PLANTED: r_EUR=2%, r_JPY=0.5%, r_GBP=4%, anchored at USD=3.9%.
    #: Quoted as differentials against USD in OANDA's own directions.
    R = {"EUR": 0.020, "JPY": 0.005, "GBP": 0.040, "USD": 0.039}
    q = {"EUR_USD": R["EUR"] - R["USD"],
         "GBP_USD": R["GBP"] - R["USD"],
         "USD_JPY": R["USD"] - R["JPY"],
         "EUR_JPY": R["EUR"] - R["JPY"],
         "EUR_GBP": R["EUR"] - R["GBP"],
         "GBP_JPY": R["GBP"] - R["JPY"]}
    rates = implied_rates(q)
    check("USD is the anchor at zero", rates["USD"] == 0.0)
    check("EUR's implied rate is r_EUR - r_USD",
          abs(rates["EUR"] - (R["EUR"] - R["USD"])) < 1e-12)
    check("JPY comes off a USD_XXX pair with the sign flipped",
          abs(rates["JPY"] - (R["JPY"] - R["USD"])) < 1e-12,
          f"{rates['JPY']*100:.2f}%")
    res = residuals(q, rates)
    check("all three crosses are predicted, none used to fit",
          set(res) == {"EUR_JPY", "EUR_GBP", "GBP_JPY"}, f"{sorted(res)}")
    check("and every residual is zero on consistent quotes",
          all(abs(v) < 1e-12 for v in res.values()),
          f"max {max(abs(v) for v in res.values()):.2e}")

    #: PLANTED: shade ONE cross by 40bp. If the test cannot see this it
    #: is decorative -- a check that only ever passes is not a check.
    q_bad = dict(q)
    q_bad["EUR_JPY"] += 0.004
    res_bad = residuals(q_bad, implied_rates(q_bad))
    check("a 40bp shading on one cross IS caught",
          abs(res_bad["EUR_JPY"] - 0.004) < 1e-12,
          f"{res_bad['EUR_JPY']*1e4:.0f} bp")
    check("and the untouched crosses stay clean",
          abs(res_bad["EUR_GBP"]) < 1e-12 and abs(res_bad["GBP_JPY"]) < 1e-12)
    check("shading a cross cannot move the anchored rates",
          implied_rates(q_bad) == rates)

    print("\nthe long/short legs are not inverted")
    #: PLANTED: for USD_JPY, being long JPY means being SHORT the
    #: instrument. Getting this backwards inverts half the book and
    #: would still produce a plausible-looking number.
    got = leg_rates("USD_JPY", long_rate=0.030, short_rate=-0.040)
    check("USD_JPY resolves to the JPY leg", got[0] == "JPY", f"{got[0]}")
    check("long JPY = SHORT USD_JPY, so it earns the short rate",
          got[1] == -0.040, f"{got[1]}")
    check("short JPY = long the instrument", got[2] == 0.030)
    got2 = leg_rates("EUR_USD", long_rate=-0.019, short_rate=0.009)
    check("EUR_USD resolves to the EUR leg and is not flipped",
          got2 == ("EUR", -0.019, 0.009), f"{got2}")
    check("a cross returns nothing -- the book is built vs the anchor",
          leg_rates("EUR_JPY", 0.01, -0.02) is None)
    check("a non-pair returns nothing",
          leg_rates("SPX500_USD", 0.01, -0.02) is None
          and split_pair("SPX500_USD") is None)

    print("\na zero is not a rate (v1.1)")
    check("0.000/0.000 is refused as missing",
          not has_financing(0.0, 0.0))
    #: PLANTED: a GENUINE zero differential still carries a markup, so
    #: both rates are negative and equal. That must survive.
    check("a real zero differential with a markup survives",
          has_financing(-0.01, -0.01))
    check("an ordinary pair survives", has_financing(0.02, -0.04))
    check("a one-sided zero survives", has_financing(0.0, -0.02))
    #: PLANTED: the whole v1.0 failure, reproduced. Anchoring off a
    #: missing row put TRY at 0.00%/yr and invented 2811 bp of shading.
    q = {"TRY_JPY": 0.3088, "USD_JPY": 0.028, "USD_TRY": 0.0}
    bad = implied_rates(q)
    check("v1.0's bug reproduces: a missing row anchors TRY at zero",
          abs(bad.get("TRY", None) - 0.0) < 1e-12)
    r_bad = residuals(q, bad)
    check("and invents ~2800 bp of shading on TRY_JPY",
          abs(r_bad["TRY_JPY"]) > 0.25,
          f"{r_bad['TRY_JPY']*1e4:+.0f} bp")
    q_ok = {k: v for k, v in q.items() if k != "USD_TRY"}
    check("excluding the missing row removes TRY entirely",
          "TRY" not in implied_rates(q_ok))
    check("and then no false residual is produced",
          residuals(q_ok, implied_rates(q_ok)) == {})

    print("\nGate C's median is the wrong statistic -- demonstrated, not asserted")
    #: PLANTED: 20 clean crosses and one shaded by 300bp. The median
    #: passes; the max does not. This is why v1.1 prints both.
    conc = [0.0] * 20 + [0.03]
    med = st.median([abs(x) for x in conc])
    check("median passes Gate C on concentrated shading",
          med <= GATE_C_MAX_RESIDUAL, f"{med*1e4:.1f} bp")
    check("while the max plainly fails it",
          max(abs(x) for x in conc) > GATE_C_MAX_RESIDUAL,
          f"{max(abs(x) for x in conc)*1e4:.0f} bp")

    print("\nthe gates are the frozen ones and can fail")
    check("Gate A needs 5 positive", GATE_A_MIN_POSITIVE == 5)
    check("Gate B needs 50% median pass-through",
          GATE_B_MIN_PASSTHROUGH == 0.50)
    check("Gate C allows 25bp of shading", GATE_C_MAX_RESIDUAL == 0.0025)
    check("Gate D needs 2.0%/yr on the spread", GATE_D_MIN_SPREAD == 0.020)
    #: PLANTED: gates that cannot fail are not gates.
    check("Gate B rejects a 40% pass-through",
          not (0.40 >= GATE_B_MIN_PASSTHROUGH))
    check("Gate C rejects 50bp of shading",
          not (0.005 <= GATE_C_MAX_RESIDUAL))
    check("Gate D rejects a 1.5% spread",
          not (0.015 >= GATE_D_MIN_SPREAD))

    print("\nno token can leak")
    import inspect
    P = "abcd-SECRET-1234"
    for fn in (build_accounts_url, build_instruments_url):
        ps = list(inspect.signature(fn).parameters)
        check(f"{fn.__name__} cannot accept a token",
              not any(w in p.lower() for p in ps
                      for w in ("token", "secret", "auth")),
              f"({', '.join(ps)})")
    check("neither URL can contain one",
          P not in build_accounts_url("h")
          and P not in build_instruments_url("h", "a"))

    print("\nthis file holds no position and fits nothing")
    import fx_carry_access as _self
    banned = ("order", "submit", "execute", "sweep", "optimi", "tune",
              "refit", "position")
    check("no order or fitting function exists",
          [x for x in dir(_self) if not x.startswith("_")
           and any(w in x.lower() for w in banned)] == [])

    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def load_fo(fo_dir):
    if not os.path.isdir(fo_dir):
        raise SystemExit(f"cannot find fetch_oanda.py in {fo_dir}\n"
                         f"  pass --fetch-oanda-dir /path/to/silver15/scripts")
    sys.path.insert(0, fo_dir)
    import fetch_oanda as fo
    return fo


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--env", default="live", choices=("live", "practice"))
    ap.add_argument("--account", default=None)
    ap.add_argument("--fetch-oanda-dir", default=DEFAULT_FO_DIR)
    ap.add_argument("--out", default="../data/fx_carry_access.json")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())
    if not a.fetch:
        ap.error("pass --fetch (one API call) or --self-test")

    fo = load_fo(a.fetch_oanda_dir)
    host = fo.HOSTS[a.env]
    token = fo.load_token()
    print(f"fx_carry_access.py v{VERSION}   PREREGISTRATION_v15\n")

    account = a.account
    if not account:
        accts = fo.api_get(build_accounts_url(host), token).get("accounts", [])
        if not accts:
            raise SystemExit("no accounts on this token")
        account = accts[0]["id"]
    print(f"  account: ...{account[-4:]}")

    url = build_instruments_url(host, account)
    if token in url:
        raise SystemExit("token leaked into a URL -- refusing to send")
    data = fo.api_get(url, token)
    ins = data.get("instruments", [])
    print(f"  instruments returned: {len(ins)}")

    rows, missing = {}, []
    for i in ins:
        if i.get("type") != "CURRENCY":
            continue
        name = i["name"]
        if not split_pair(name):
            continue
        f = i.get("financing", {})
        try:
            lr, sr = float(f["longRate"]), float(f["shortRate"])
        except (KeyError, TypeError, ValueError):
            continue
        if not has_financing(lr, sr):        # v1.1 -- a zero is not a rate
            missing.append(name)
            continue
        days = {x["dayOfWeek"]: int(x["daysCharged"])
                for x in f.get("financingDaysOfWeek", [])}
        d, s = decompose(lr, sr)
        rows[name] = dict(name=name, lr=lr, sr=sr, d=d, s=s,
                          net=net_carry(d, s), pt=pass_through(d, s),
                          days=sum(days.values()))
    print(f"  currency pairs with financing: {len(rows)}")
    if missing:
        print(f"  EXCLUDED -- API returned 0.000/0.000, which is no data "
              f"rather than\n  a zero rate ({len(missing)}): "
              f"{', '.join(sorted(missing))}")
        print(f"  Their currencies get no anchored rate and enter neither "
              f"the\n  chaining test nor the book. v1.0 read these as real "
              f"zeros and\n  invented 2811 bp of broker shading that was "
              f"not there.")
    print()
    if len(rows) < 10:
        raise SystemExit("too few currency pairs to say anything")

    odd = [r["name"] for r in rows.values() if r["days"] != 7]
    if odd:
        print(f"  NOTE: {len(odd)} pairs do not charge 7 days a week: "
              f"{odd[:5]}\n")

    by_d = sorted(rows.values(), key=lambda r: -abs(r["d"]))
    print(f"  THE TWENTY LARGEST DIFFERENTIALS")
    print(f"    {'pair':<10}{'longRate':>10}{'shortRate':>11}{'d %/yr':>9}"
          f"{'s %/yr':>8}{'net %/yr':>10}{'pass-thru':>11}")
    for r in by_d[:20]:
        pt = f"{r['pt']*100:9.1f}%" if r["pt"] is not None else f"{'--':>10}"
        print(f"    {r['name']:<10}{r['lr']*100:>10.3f}{r['sr']*100:>11.3f}"
              f"{r['d']*100:>9.2f}{r['s']*100:>8.2f}{r['net']*100:>10.2f}{pt}")

    pos = [r for r in rows.values() if r["net"] > 0]
    ga = len(pos) >= GATE_A_MIN_POSITIVE

    top = by_d[:GATE_B_TOP_N]
    pts = [r["pt"] for r in top if r["pt"] is not None]
    med_pt = st.median(pts) if pts else None
    gb = med_pt is not None and med_pt >= GATE_B_MIN_PASSTHROUGH

    dmap = {n: r["d"] for n, r in rows.items()}
    rates = implied_rates(dmap)
    res = residuals(dmap, rates)
    med_res = st.median([abs(v) for v in res.values()]) if res else None
    gc = med_res is not None and med_res <= GATE_C_MAX_RESIDUAL

    #: the long-short book, built only against the anchor
    legs = {}
    for n, r in rows.items():
        g = leg_rates(n, r["lr"], r["sr"])
        if g:
            legs[g[0]] = (g[1], g[2])
    ranked = sorted((c for c in legs if c in rates),
                    key=lambda c: -rates[c])
    k = max(1, len(ranked) // QUINTILE)
    longs, shorts = ranked[:k], ranked[-k:]
    lr_avg = st.mean([legs[c][0] for c in longs])
    sr_avg = st.mean([legs[c][1] for c in shorts])
    spread = lr_avg + sr_avg
    gd = spread >= GATE_D_MIN_SPREAD

    print(f"\n  IMPLIED RATES (anchor {ANCHOR} = 0), top and bottom")
    for c in ranked[:5]:
        print(f"    {c}  {rates[c]*100:+7.2f} %/yr")
    print(f"    ...")
    for c in ranked[-5:]:
        print(f"    {c}  {rates[c]*100:+7.2f} %/yr")

    print(f"\n  CHAINING -- {len(res)} crosses PREDICTED, none fitted")
    worst = sorted(res.items(), key=lambda kv: -abs(kv[1]))[:8]
    for n, v in worst:
        print(f"    {n:<10} residual {v*1e4:+8.1f} bp")
    if med_res is not None:
        mx = max(abs(v) for v in res.values())
        over = sum(1 for v in res.values() if abs(v) > GATE_C_MAX_RESIDUAL)
        print(f"    median |residual| {med_res*1e4:.1f} bp   "
              f"MAX {mx*1e4:.1f} bp   over threshold: {over}/{len(res)}")
        #: v15 chose the MEDIAN for Gate C, and that was a design error:
        #: per-pair shading concentrates in a few currencies, and a
        #: median is built to ignore exactly that. The gate is scored as
        #: frozen, but the max and the count are printed beside it so a
        #: pass on a robust statistic cannot hide a concentrated fault.
        if over:
            print(f"    NOTE: Gate C scores the MEDIAN, as frozen. A median "
                  f"is the wrong\n    statistic for shading that "
                  f"concentrates in a few pairs -- read the\n    max and "
                  f"the count above, not the gate alone.")

    print(f"\n  VERDICT -- gates frozen in PREREGISTRATION_v15 section 4")
    print(f"    [{'PASS' if ga else 'FAIL'}] Gate A  {len(pos)} pairs with "
          f"net carry > 0 (need {GATE_A_MIN_POSITIVE})")
    print(f"    [{'PASS' if gb else 'FAIL'}] Gate B  median pass-through "
          f"{med_pt*100:.1f}% on the top {GATE_B_TOP_N} by |d| "
          f"(need {GATE_B_MIN_PASSTHROUGH*100:.0f}%)"
          if med_pt is not None else "    [N/A ] Gate B")
    print(f"    [{'PASS' if gc else 'FAIL'}] Gate C  median |residual| "
          f"{med_res*1e4:.1f} bp (need <= {GATE_C_MAX_RESIDUAL*1e4:.0f})"
          if med_res is not None else "    [N/A ] Gate C")
    print(f"    [{'PASS' if gd else 'FAIL'}] Gate D  long-short book "
          f"{spread*100:+.2f} %/yr (need {GATE_D_MIN_SPREAD*100:.1f})")
    print(f"           long {', '.join(longs)} at {lr_avg*100:+.2f}   "
          f"short {', '.join(shorts)} at {sr_avg*100:+.2f}")

    allp = ga and gb and gc and gd
    print(f"\n    {'PROCEED' if allp else 'FAIL'}")
    if not gc:
        print(f"\n    Gate C failed, so Gate B's pass-through is an UPPER")
        print(f"    BOUND, not a measurement -- the reference itself is")
        print(f"    being shaded per pair. v15 section 7.")
    print(f"\n  v15 section 6: these are ADVERTISED rates. What posts to "
          f"the\n  account can differ, so every number here is an upper "
          f"bound on\n  what arrives. Nothing above touches crash risk, "
          f"which is the\n  actual cost of carry.")

    rec = {"tool": "fx_carry_access.py", "version": VERSION,
           "fetched_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
           "env": a.env, "n_pairs": len(rows),
           "gates": {"A": ga, "B": gb, "C": gc, "D": gd},
           "median_pass_through": med_pt, "median_residual": med_res,
           "spread": spread,
           "pairs": {n: {k: v for k, v in r.items() if k != "name"}
                     for n, r in rows.items()},
           "implied_rates": rates, "residuals": res}
    with open(a.out, "w") as fh:
        json.dump(rec, fh, indent=2)
    print(f"\n  written to {a.out}")


if __name__ == "__main__":
    main()
