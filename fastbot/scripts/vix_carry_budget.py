#!/usr/bin/env python3
"""Short VIX futures carry: what survives after cost, margin and the tail?

WHY THIS EXISTS
---------------
RESULT_VIXCURVE.md measured a real term-structure carry premium on the full
2004-2026 futures history: ~0.40 Sharpe of genuine carry, positive in all
three eras including 2008 and 2020. It is the first candidate in eighteen
investigations to survive its own crisis era.

It is also GROSS. This file asks the questions that decide whether a real
premium is a real strategy:

    1. what does the monthly roll cost, against a premium of ~0.88 vol points
    2. how big a position survives the worst month with the account intact
    3. what does MARGIN do in that month -- because margin rises exactly when
       the loss lands, and that is the mechanism that forces people out at
       the bottom rather than letting them ride through
    4. what return on capital is left at the size that survives

The constraint on this trade is not its Sharpe. It is the survivable size.

CONTRACT FACTS (Cboe)
    VX   full size   multiplier 1,000   1 VIX point = $1,000   tick 0.05 = $50
    VXM  mini        multiplier   100   1 VIX point =   $100   tick 0.05 = $5
    VXM lists only the 2-3 nearest months; nearest trades ~1 tick wide,
    can widen to 3 ticks.

MARGIN NUMBERS HERE ARE ESTIMATES AND MUST BE VERIFIED WITH A BROKER before
any of this means anything. They are exposed as parameters and the report
shows the sensitivity, because the answer depends on them heavily.

NO STRATEGY IS SIMULATED. This sizes a premium that was measured elsewhere.

    python vix_carry_budget.py --self-test
    python vix_carry_budget.py --tv-dir
"""

from __future__ import annotations

import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vix_curve_budget as VC                         # noqa: E402

VERSION = "1.2"

#: v1.1, before this was ever run on real data. The self-test caught two
#: things, both of which would have let too much size through:
#:   1. the drawdown function measured peak-to-trough (correct) but was named,
#:      documented and TESTED as "worst run of consecutive negative months"
#:      (wrong, and 1.7x smaller on the planted case). Test was wrong, code
#:      was right; both now say peak-to-trough and a case is planted that the
#:      weaker definition fails.
#:   2. the maximum holdable size was read off the PRINTED grid (0.5, 1, 2,
#:      3, 5, 10 contracts), so it was rounded down to whichever row happened
#:      to be shown and mislabelled the binding constraint as margin when it
#:      was drawdown. Now solved exactly: n < account / (loss + stressed
#:      margin). This one was passing its gate for the wrong reason.

CONTRACTS = {"VXM": dict(mult=100.0, tick=0.05, name="Mini VIX (VXM)"),
             "VX": dict(mult=1000.0, tick=0.05, name="Full VIX (VX)")}

#: ESTIMATES. Verify with the broker. Initial margin per VXM contract in a
#: normal regime, and the multiple it reaches in a stressed one. SPAN margin
#: on volatility products rises with volatility, which is the whole problem.
MARGIN_NORMAL_VXM = 1100.0
MARGIN_STRESS_MULT = 2.5

MAX_DD = 0.30              # the drawdown you are willing to take, of account


def premium_series(near, far, horizon=VC.HORIZON):
    """Monthly premium in VIX points, from the real futures curve."""
    df = VC.measure(near, far, horizon)
    VC._guard(df, "carry budget")
    return VC.monthly(df)["premium"]


def worst_drawdown(p):
    """Worst PEAK-TO-TROUGH cumulative loss -- the real sizing constraint.

    Sizing to survive the worst single month is not enough: 2008-10 was
    followed immediately by 2008-11.

    Note this is NOT "the longest run of negative months". A small positive
    month in the middle of a collapse does not reset the constraint: the
    account is still down from its peak, and it is distance from the peak
    that triggers a margin call. On [-10, -8, +1, +1, -15] the consecutive
    -run definition reports -18; the true peak-to-trough loss is -31. The
    weaker definition would have let 1.7x more size through.

    Returns (worst loss, months from peak to trough).
    """
    v = p.to_numpy()
    worst, cur, run, best_run = 0.0, 0.0, 0, 0
    for x in v:
        cur = min(cur + x, 0.0) if x < 0 or cur < 0 else 0.0
        run = run + 1 if cur < 0 else 0
        if cur < worst:
            worst, best_run = cur, run
    return worst, best_run


def drawdown_episodes(p):
    """Every peak-to-trough episode, with dates and time to recovery.

    The single worst number is not the whole constraint. A drawdown that
    takes 22 months to reach its trough is a different thing to live with
    than one that lands in a fortnight, even at identical depth, and the
    summary statistic cannot tell them apart.
    """
    cum = p.cumsum()
    #: clip at 0: the account is at its peak BEFORE the first month, so a
    #: series that opens with losses is in drawdown from month one. Without
    #: the clip, cummax() starts at the first (negative) value and the whole
    #: opening decline is invisible -- and 2004-03 is the start of a real
    #: sample, not a safe place to lose an episode.
    peak = cum.cummax().clip(lower=0.0)
    under = (cum < peak - 1e-12).to_numpy()
    idx, n, eps, i = p.index, len(p), [], 0
    while i < n:
        if not under[i]:
            i += 1
            continue
        j = i
        while j < n and under[j]:
            j += 1
        seg = cum.iloc[i:j]
        k = int(seg.to_numpy().argmin())          # positional trough
        eps.append(dict(
            start=idx[i - 1] if i else idx[0],    # last month at the peak
            trough=idx[i + k],
            depth=float(seg.iloc[k] - peak.iloc[i]),
            to_trough=k + 1,
            to_recover=(j - i) if j < n else None))
        i = j
    return sorted(eps, key=lambda e: e["depth"])


def underwater_share(p):
    """Fraction of months spent below a previous equity peak."""
    cum = p.cumsum()
    return float((cum < cum.cummax().clip(lower=0.0) - 1e-12).mean())


def report(p, account, contract, roll_ticks, margin_vxm, stress_mult,
           max_dd, commission=0.0):
    import numpy as np
    C = CONTRACTS[contract]
    mult, tick = C["mult"], C["tick"]
    scale = mult / 100.0                       # margin scales with size

    mean_p = float(p.mean())
    worst_m = float(p.min())
    worst_c, run_len = worst_drawdown(p)
    roll = roll_ticks * tick                   # vol points per round trip

    print(f"\n{C['name']}   1 VIX point = ${mult:,.0f}   "
          f"tick {tick} = ${tick*mult:,.0f}")
    print(f"  measured premium  {mean_p:+.2f} vol pts/month = "
          f"${mean_p*mult:+,.0f} per contract")
    print(f"  roll cost         {roll:.2f} vol pts ({roll_ticks:.0f} ticks, "
          f"2 legs) = ${roll*mult:,.0f}")
    #: Two fills per monthly roll, so two commissions. A flat per-trade fee
    #: is a FIXED dollar cost against a premium that scales with the
    #: multiplier, so it hurts the mini ten times as hard as the full size.
    comm = 2.0 * commission / mult                 # dollars -> vol points
    if commission:
        print(f"  commission        {comm:.3f} vol pts "
              f"(2 x ${commission:.2f}) = ${comm*mult:,.0f}")
    net = mean_p - roll - comm
    cost = roll + comm
    print(f"  NET premium       {net:+.2f} vol pts = ${net*mult:+,.0f}"
          f"   ({cost/mean_p*100:.0f}% of gross eaten by cost)")

    print(f"\n  worst single month     {worst_m:+.2f} vol pts = "
          f"${worst_m*mult:+,.0f}")
    print(f"  worst drawdown         {worst_c:+.2f} vol pts, peak to trough "
          f"over {run_len} months = ${worst_c*mult:+,.0f}")

    print(f"\n  SIZE THAT SURVIVES a repeat of the worst drawdown, "
          f"losing at most {max_dd*100:.0f}% of a ${account:,.0f} account")
    n_dd = max_dd * account / abs(worst_c * mult)
    print(f"    {n_dd:.2f} contracts")
    if n_dd < 1:
        print(f"    -> BELOW ONE CONTRACT. The minimum tradeable position "
              f"already\n       risks more than {max_dd*100:.0f}% of this "
              f"account.")

    m_norm = margin_vxm * scale
    m_str = m_norm * stress_mult
    print(f"\n  MARGIN (ESTIMATE -- verify with the broker)")
    print(f"    normal  ${m_norm:,.0f}/contract    stressed "
          f"${m_str:,.0f}/contract ({stress_mult:.1f}x)")
    n_marg = account / m_norm
    print(f"    account supports {n_marg:.2f} contracts at normal margin")

    #: Exact hold limit, NOT read off the display grid below.
    #: equity after the drawdown must still cover stressed margin:
    #:   account - n*L > n*M   =>   n < account / (L + M)
    #: An earlier version took the largest SURVIVING row of the table, which
    #: rounded the limit down to whichever sizes happened to be printed and
    #: mislabelled the binding constraint as margin when it was drawdown.
    loss_per = abs(worst_c) * mult
    n_hold = account / (loss_per + m_str)

    print(f"\n  THE MARGIN SPIRAL -- can the position be HELD "
          f"through the drawdown?")
    print(f"    {'contracts':>10}{'loss':>12}{'equity after':>14}"
          f"{'margin needed':>15}{'survives':>10}")
    print("    " + "-" * 61)
    for n in (0.5, 1, 2, 3, 5, 10):
        loss = n * loss_per
        eq = account - loss
        need = n * m_str
        print(f"    {n:>10.1f}{-loss:>12,.0f}{eq:>14,.0f}{need:>15,.0f}"
              f"{'yes' if eq > need else 'NO':>10}")
    print(f"    exact hold limit: {n_hold:.2f} contracts")

    binding = min(n_dd, n_hold)
    print(f"\n  BINDING SIZE  {binding:.2f} contracts "
          f"({'drawdown' if n_dd < n_hold else 'margin'} is the constraint)")
    if binding >= 0.01:
        gross_yr = binding * mean_p * mult * 12
        net_yr = binding * net * mult * 12
        print(f"    gross  ${gross_yr:,.0f}/yr = {gross_yr/account*100:.1f}% "
              f"of account")
        print(f"    NET    ${net_yr:,.0f}/yr = {net_yr/account*100:.1f}% "
              f"of account")
    return dict(binding=binding, net=net, worst_c=worst_c, mean=mean_p,
                n_dd=n_dd, n_hold=n_hold)


#: Declared, not tuned. Approximate average 3-month T-bill over 2004-2026 and
#: approximate S&P dividend yield over the same window. Both are shown as a
#: sensitivity below rather than relied on as point estimates.
CASH_RATE = 0.02
DIV_YIELD = 0.02


def risk_matched(eq_monthly, net_vp, carry_dd, max_dd, cash, div=None):
    """Both sides scaled to lose the SAME fraction in their own worst
    observed drawdown, over the same window. Returns a dict of annual
    fractions of account.

    Return-on-account at a fixed drawdown budget is SIZE-INVARIANT on both
    sides: double the position and both the return and the drawdown double.
    A bigger account does not improve this number. It only makes the
    contract granularity workable.
    """
    div = DIV_YIELD if div is None else div
    r = eq_monthly.pct_change().dropna()
    yrs = len(r) / 12.0
    cum = (1 + r).cumprod()
    eq_dd = float((cum / cum.cummax() - 1).min())
    eq_price = float(cum.iloc[-1]) ** (1 / yrs) - 1
    eq_excess = eq_price + div - cash
    return dict(eq_price=eq_price, eq_dd=eq_dd, eq_excess=eq_excess,
                eq_sized=eq_excess * (max_dd / abs(eq_dd)),
                carry=12.0 * net_vp / abs(carry_dd) * max_dd,
                months=len(r))


def diagnose(p, a, out):
    """When the drawdowns happened, how long they lasted, and whether the
    risk-matched return beats simply owning the index over the SAME window."""
    import numpy as np, pandas as pd

    eps = drawdown_episodes(p)
    print("\n\n  THE FIVE WORST DRAWDOWNS -- depth is not the only cost")
    print(f"    {'from':>9}{'trough':>9}{'depth':>9}{'to trough':>11}"
          f"{'to recover':>12}")
    print("    " + "-" * 50)
    for e in eps[:5]:
        rec = f"{e['to_recover']} mo" if e["to_recover"] else "NOT YET"
        print(f"    {format(e['start'], '%Y-%m'):>9}"
              f"{format(e['trough'], '%Y-%m'):>9}"
              f"{e['depth']:>9.2f}{str(e['to_trough']) + ' mo':>11}"
              f"{rec:>12}")
    uw = underwater_share(p)
    print(f"\n    {uw*100:.0f}% of all months were spent below a previous "
          f"peak.")
    done = [e["to_recover"] for e in eps if e["to_recover"]]
    if done:
        print(f"    Longest completed wait back to even: {max(done)} months.")
    if any(e["to_recover"] is None for e in eps):
        print("    One drawdown is still open at the end of the sample -- "
              "its recovery")
        print("    time is unknown, not zero.")

    #: The comparison DESIGN_BRIEF.md has used to reject everything else,
    #: run over the IDENTICAL window rather than against a remembered number.
    print("\n  AGAINST OWNING THE INDEX, SAME WINDOW, SAME DRAWDOWN BUDGET")
    try:
        import vrp_budget as VR
        spx = VR.oanda_daily(os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "data"))
    except Exception as exc:                                  # noqa: BLE001
        print(f"    skipped: no SPX series available ({exc})")
        return
    m = spx.resample("ME").last().dropna()
    m = m.loc[(m.index >= p.index[0]) & (m.index <= p.index[-1])]
    if len(m) < 60:
        print(f"    skipped: only {len(m)} overlapping months")
        return
    base = risk_matched(m, out["VXM"]["net"], out["VXM"]["worst_c"],
                        a.max_dd, CASH_RATE)
    print(f"    SPX proxy {m.index[0]:%Y-%m} -> {m.index[-1]:%Y-%m}   "
          f"price return {base['eq_price']*100:.1f}%/yr   worst drawdown "
          f"{base['eq_dd']*100:.1f}%")
    print(f"\n    {'cash':>6}{'index excess':>15}{'sized to budget':>18}"
          f"{'VIX carry':>12}{'winner':>10}")
    print("    " + "-" * 61)
    for cash in (0.00, CASH_RATE, 0.04):
        k = risk_matched(m, out["VXM"]["net"], out["VXM"]["worst_c"],
                         a.max_dd, cash)
        win = "carry" if k["carry"] > k["eq_sized"] else "index"
        print(f"    {cash*100:>5.0f}%{k['eq_excess']*100:>14.1f}%"
              f"{k['eq_sized']*100:>17.1f}%{k['carry']*100:>11.1f}%"
              f"{win:>10}")
    print(f"    Index excess = price return + {DIV_YIELD*100:.0f}% dividends "
          f"- cash, then scaled")
    print(f"    to lose {a.max_dd*100:.0f}% in its own worst drawdown. VIX "
          f"carry is already an excess")
    print("    return: the collateral earns cash on top, on both sides.")
    print("    Neither worst drawdown is a bound. Equity's is drawn from a "
          "far longer")
    print("    history than 22 years; this window happens to contain it.")


def self_test():
    import numpy as np, pandas as pd
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}" +
              (f"   {detail}" if detail else ""))

    print(f"vix_carry_budget.py v{VERSION} self-test\n")

    print("worst_drawdown measures PEAK TO TROUGH, not a run of red months")
    #: Planted to break the weaker definition. A "longest consecutive run of
    #: negative months" reads this as -18 and stops at the +1. The account is
    #: down 31 from its peak when the -15 lands, and 31 is what the broker
    #: measures. If this ever returns -18 again, sizing is 1.7x too large.
    p = pd.Series([1, 1, -10, -8, 1, 1, -15, 2, 1],
                  index=pd.date_range("2020-01-31", periods=9, freq="ME"))
    w, r = worst_drawdown(p)
    check("a small recovery inside a collapse does NOT reset the drawdown",
          abs(w + 31) < 1e-9 and r == 5, f"worst {w}, {r} months")
    check("the weaker consecutive-run answer is rejected", abs(w + 18) > 1e-9,
          f"{w}")
    p2 = pd.Series([1, -20, 5, 5, -3],
                   index=pd.date_range("2020-01-31", periods=5, freq="ME"))
    w2, _ = worst_drawdown(p2)
    check("an isolated loss is found too", abs(w2 + 20) < 1e-9, f"{w2}")
    p3 = pd.Series([1.0] * 6, index=pd.date_range("2020-01-31", periods=6,
                                                  freq="ME"))
    check("an all-positive series has no drawdown",
          worst_drawdown(p3)[0] == 0.0)
    #: recovery to a NEW peak must start the next drawdown from scratch
    p4 = pd.Series([-5, 20, -7],
                   index=pd.date_range("2020-01-31", periods=3, freq="ME"))
    check("a full recovery resets the peak", abs(worst_drawdown(p4)[0] + 7)
          < 1e-9, f"{worst_drawdown(p4)[0]}")

    print("\ndrawdown episodes are found, dated and ranked")

    def S(v):
        return pd.Series([float(x) for x in v],
                         index=pd.date_range("2020-01-31", periods=len(v),
                                             freq="ME"))
    e1 = drawdown_episodes(S([1, -3, 1, 1, 1, -5, 2, 2, 2]))
    check("two separate episodes, deepest first",
          len(e1) == 2 and abs(e1[0]["depth"] + 5) < 1e-9
          and abs(e1[1]["depth"] + 3) < 1e-9,
          f"{[round(e['depth'], 2) for e in e1]}")
    check("a recovered episode reports how long it took",
          e1[0]["to_recover"] == 3 and e1[0]["to_trough"] == 1,
          f"trough {e1[0]['to_trough']}, recover {e1[0]['to_recover']}")
    #: Planted so that the WORST MONTH and the WORST DRAWDOWN disagree.
    #: A budget that sizes on the worst month would allow 17% more here.
    g = S([-6, 6, -2, -3, -2, 1])
    eg = drawdown_episodes(g)
    check("a slow grind outranks a single worse month",
          abs(eg[0]["depth"] + 7) < 1e-9 and eg[0]["to_trough"] == 3
          and abs(float(g.min()) + 6) < 1e-9,
          f"grind {eg[0]['depth']:.0f} over {eg[0]['to_trough']} mo vs "
          f"worst month {float(g.min()):.0f}")
    check("a drawdown still open at the end reports NOT YET",
          eg[0]["to_recover"] is None, f"{eg[0]['to_recover']}")
    #: Designed to fail the un-clipped version, which starts its running
    #: peak at the first observation and loses the opening decline entirely.
    e0 = drawdown_episodes(S([-4, 9]))
    check("a drawdown starting on the FIRST month is not invisible",
          len(e0) == 1 and abs(e0[0]["depth"] + 4) < 1e-9,
          f"{[round(e['depth'], 2) for e in e0]}")
    #: two independent implementations must agree
    for name, s in (("mixed", S([1, -3, 1, 1, 1, -5, 2, 2, 2])),
                    ("grind", g), ("opening", S([-4, 9]))):
        eps = drawdown_episodes(s)
        check(f"episode depth matches worst_drawdown ({name})",
              abs(min(e["depth"] for e in eps) - worst_drawdown(s)[0]) < 1e-9,
              f"{min(e['depth'] for e in eps):.2f} vs "
              f"{worst_drawdown(s)[0]:.2f}")
    check("an all-positive series is never underwater",
          underwater_share(S([1] * 5)) == 0.0)
    check("underwater share counts the recovery months too",
          abs(underwater_share(S([1, -3, 1, 1, 1])) - 0.6) < 1e-9,
          f"{underwater_share(S([1, -3, 1, 1, 1])):.2f}")

    print("\ncontract arithmetic")
    check("VXM is one tenth of VX",
          CONTRACTS["VXM"]["mult"] * 10 == CONTRACTS["VX"]["mult"])
    check("a VX tick is $50", CONTRACTS["VX"]["tick"]
          * CONTRACTS["VX"]["mult"] == 50.0)
    check("a VXM tick is $5", CONTRACTS["VXM"]["tick"]
          * CONTRACTS["VXM"]["mult"] == 5.0)

    print("\nsizing responds to the inputs, and the gates can fail")
    real = pd.Series(np.concatenate([np.full(200, 0.88), [-23.93, -13.02]]),
                     index=pd.date_range("2004-03-31", periods=202,
                                         freq="ME"))
    a = report(real, 10_000, "VXM", 2, MARGIN_NORMAL_VXM,
               MARGIN_STRESS_MULT, 0.30)
    b = report(real, 100_000, "VXM", 2, MARGIN_NORMAL_VXM,
               MARGIN_STRESS_MULT, 0.30)
    check("a 10x bigger account supports a bigger position",
          b["binding"] > a["binding"], f"{a['binding']:.2f} vs "
                                       f"{b['binding']:.2f}")
    c = report(real, 10_000, "VXM", 6, MARGIN_NORMAL_VXM,
               MARGIN_STRESS_MULT, 0.30)
    check("a 3x wider roll cuts the net premium",
          c["net"] < a["net"], f"{c['net']:+.2f} vs {a['net']:+.2f}")
    check("the worst drawdown is worse than the worst month",
          abs(a["worst_c"]) > 23.93, f"{a['worst_c']:.2f}")

    print("\nthe binding constraint is identified")
    tight = report(real, 10_000, "VXM", 2, MARGIN_NORMAL_VXM, 6.0, 0.30)
    check("a harsher margin regime reduces the size that can be HELD",
          tight["n_hold"] < a["n_hold"],
          f"{tight['n_hold']:.2f} vs {a['n_hold']:.2f}")
    #: The hold limit here is 0.97 contracts. An earlier version read the
    #: limit off the printed grid (0.5, 1, 2, ...), rounded it down to 0.5
    #: and reported margin as the binding constraint when drawdown was.
    check("the hold limit is exact, not rounded to a printed row",
          abs(tight["n_hold"] - 0.5) > 1e-6
          and abs(tight["n_hold"] - 1.0) > 1e-6,
          f"{tight['n_hold']:.4f}")
    check("with margin at 6x the drawdown still binds first",
          abs(tight["binding"] - tight["n_dd"]) < 1e-9,
          f"binding {tight['binding']:.2f}, dd {tight['n_dd']:.2f}, "
          f"hold {tight['n_hold']:.2f}")
    #: and a regime where margin genuinely wins, so the branch is exercised
    spiral = report(real, 10_000, "VXM", 2, MARGIN_NORMAL_VXM, 20.0, 0.30)
    check("at 20x margin the spiral binds before the drawdown does",
          spiral["n_hold"] < spiral["n_dd"]
          and abs(spiral["binding"] - spiral["n_hold"]) < 1e-9,
          f"hold {spiral['n_hold']:.2f} vs dd {spiral['n_dd']:.2f}")
    big = report(real, 10_000, "VX", 2, MARGIN_NORMAL_VXM,
                 MARGIN_STRESS_MULT, 0.30)
    check("the full-size contract is unusable on a small account",
          big["binding"] < 0.2, f"{big['binding']:.2f} contracts")

    print("\nthe risk-matched comparison, and it can name either winner")
    #: A clean 10%/yr index with a -50% drawdown. At a 30% budget it is held
    #: at 0.6 weight, so 10 + 2 div - 2 cash = 10% excess -> 6.0% of account.
    idx = pd.date_range("2004-03-31", periods=121, freq="ME")
    lin = np.linspace(0.0, 1.0, 121)              # ndarray, NOT a Series:
    #: a Series carries its own RangeIndex, and passing index=idx then
    #: REINDEXES rather than relabels, silently producing 121 NaNs.
    eq = pd.Series(100 * (1 + 0.10) ** (lin * 10), index=idx)
    eq.iloc[60:] = eq.iloc[60:] * 0.5             # a -50% step drawdown
    k = risk_matched(eq, 0.78, -47.57, 0.30, 0.02)
    check("the synthetic index is not silently all-NaN",
          k["months"] == 120 and np.isfinite(k["eq_price"]),
          f"{k['months']} months, price {k['eq_price']*100:.1f}%/yr")
    check("the index drawdown is measured, not assumed",
          abs(k["eq_dd"] + 0.50) < 0.02, f"{k['eq_dd']*100:.1f}%")
    check("carry return-on-account is 12 x net / worst dd x budget",
          abs(k["carry"] - 12 * 0.78 / 47.57 * 0.30) < 1e-12,
          f"{k['carry']*100:.2f}%")
    #: The gate has to be able to say "index". Give equity a drawdown so
    #: shallow that the same budget buys a huge weight, and check it flips.
    calm = pd.Series(100 * (1 + 0.10) ** (lin * 10), index=idx)
    calm.iloc[60:] = calm.iloc[60:] * 0.95        # only -5%
    k2 = risk_matched(calm, 0.78, -47.57, 0.30, 0.02)
    check("a shallower index drawdown flips the winner to the index",
          k2["eq_sized"] > k2["carry"] and k["eq_sized"] < k["carry"],
          f"calm {k2['eq_sized']*100:.0f}% vs carry {k2['carry']*100:.1f}%")
    check("a higher cash rate lowers the index excess, not the carry",
          risk_matched(eq, 0.78, -47.57, 0.30, 0.06)["eq_sized"]
          < k["eq_sized"]
          and risk_matched(eq, 0.78, -47.57, 0.30, 0.06)["carry"]
          == k["carry"])
    #: size-invariance is the claim the conclusion rests on
    check("return-on-account does not improve with a bigger position",
          abs(risk_matched(eq, 7.8, -475.7, 0.30, 0.02)["carry"]
              - k["carry"]) < 1e-12)

    print("\na flat commission hurts the small contract ten times harder")
    m_free = report(real, 10_000, "VXM", 2, MARGIN_NORMAL_VXM,
                    MARGIN_STRESS_MULT, 0.30, 0.0)
    m_comm = report(real, 10_000, "VXM", 2, MARGIN_NORMAL_VXM,
                    MARGIN_STRESS_MULT, 0.30, 1.50)
    v_comm = report(real, 10_000, "VX", 2, MARGIN_NORMAL_VXM,
                    MARGIN_STRESS_MULT, 0.30, 1.50)
    v_free = report(real, 10_000, "VX", 2, MARGIN_NORMAL_VXM,
                    MARGIN_STRESS_MULT, 0.30, 0.0)
    hit_m, hit_v = m_free["net"] - m_comm["net"], v_free["net"] - v_comm["net"]
    check("commission reduces the net premium", hit_m > 0, f"{hit_m:.4f}")
    check("in vol points it costs the mini 10x what it costs the full size",
          abs(hit_m / hit_v - 10.0) < 1e-6, f"{hit_m/hit_v:.2f}x")

    print("\nno strategy is simulated")
    import vix_carry_budget as _self
    bad = [x for x in dir(_self) if not x.startswith("_") and any(
        w in x.lower() for w in ("signal", "entry", "backtest", "equity_"))]
    check("no signal / entry / backtest function", bad == [], f"{bad}")

    print(f"\n{'ALL PASS' if ok else 'FAILURES ABOVE'}")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vx1")
    ap.add_argument("--vx2")
    ap.add_argument("--tv-dir", nargs="?", const="~/Downloads")
    ap.add_argument("--account", type=float, default=10_000.0)
    ap.add_argument("--roll-ticks", type=float, default=2.0,
                    help="ticks paid per round trip: 1 tick each leg")
    ap.add_argument("--margin-vxm", type=float, default=MARGIN_NORMAL_VXM)
    ap.add_argument("--stress-mult", type=float, default=MARGIN_STRESS_MULT)
    ap.add_argument("--max-dd", type=float, default=MAX_DD)
    ap.add_argument("--commission", type=float, default=1.50,
                    help="$ per contract per fill; 2 fills per monthly roll")
    ap.add_argument("--diagnose", action="store_true",
                    help="drawdown episodes and the risk-matched equity "
                         "comparison")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())

    if a.tv_dir:
        import glob
        base = os.path.expanduser(a.tv_dir)
        def find(tag):
            hits = [h for h in glob.glob(os.path.join(base, "*.csv"))
                    if tag.lower() in os.path.basename(h).lower()]
            if not hits:
                raise SystemExit(f"  no *{tag}*.csv in {base}")
            return max(hits, key=os.path.getmtime)
        a.vx1, a.vx2 = find("VX1"), find("VX2")
    if not (a.vx1 and a.vx2):
        raise SystemExit("  need --vx1/--vx2 or --tv-dir")

    print(f"vix_carry_budget.py v{VERSION}   "
          f"SIZING A MEASURED PREMIUM, NO STRATEGY\n")
    near, far = VC.load_csv(a.vx1, "VX1"), VC.load_csv(a.vx2, "VX2")
    p = premium_series(near, far)
    print(f"\n  {len(p)} monthly premium observations "
          f"({p.index[0]:%Y-%m} -> {p.index[-1]:%Y-%m})")
    print(f"  account ${a.account:,.0f}   max drawdown "
          f"{a.max_dd*100:.0f}%   roll {a.roll_ticks:.0f} ticks")

    out = {}
    for c in ("VXM", "VX"):
        out[c] = report(p, a.account, c, a.roll_ticks, a.margin_vxm,
                        a.stress_mult, a.max_dd, a.commission)

    print("\n\n  ROLL-COST SENSITIVITY (VXM)")
    print(f"    {'ticks':>7}{'net vol pts':>14}{'% of gross':>13}")
    print("    " + "-" * 34)
    mean_p = float(p.mean())
    for t in (1, 2, 3, 4, 6):
        roll = t * CONTRACTS["VXM"]["tick"]
        print(f"    {t:>7.0f}{mean_p-roll:>14.2f}{roll/mean_p*100:>12.0f}%")
    print("    VXM's nearest month trades ~1 tick wide and can reach 3.")
    print("    Both legs pay, so 2 ticks is the optimistic case and 6 the bad "
          "one.")

    if a.diagnose:
        diagnose(p, a, out)

    print("\n  WHAT THIS BUDGET CANNOT SEE")
    print("    Margin numbers are ESTIMATES. SPAN margin on a volatility")
    print("      product rises with volatility, and the exchange can raise it")
    print("      intraday. Verify with the broker before believing any size")
    print("      above.")
    print("    The worst run is the worst OBSERVED run in 22 years. It is not")
    print("      a bound. 2008 and 2020 were not the largest possible shocks.")
    print("    VXM lists only 2-3 months, so a roll has fewer alternatives if")
    print("      the front is dislocated.")
    print("    No slippage beyond the quoted spread, and the quoted spread is")
    print("      widest in exactly the months that produce the worst runs.")


if __name__ == "__main__":
    main()
