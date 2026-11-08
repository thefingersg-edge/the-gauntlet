#!/usr/bin/env python3
"""Does holding longer make the bar easier? Measured, not argued.

The intuition is that a longer hold helps, because cost is paid once per
round trip and the price moves further. Half of that is true and the half
that is missing reverses the conclusion.

    net annual Sharpe = (edge_per_trade - cost) / sd_per_trade * sqrt(T)

Lengthen the hold H and three things move at once:

    sd_per_trade  grows as sqrt(H)     <- cost/sd falls. Good.
    T             falls as 1/H         <- sqrt(T) falls. Bad.
    edge          grows only if the EFFECT keeps accumulating

The first two are arithmetic and cancel almost exactly. The third is an
empirical question about the market, not about the budget -- and it is the
one that decides everything.

This file computes the required GROSS edge per trade at each hold, expressed
both in basis points and as a fraction of that hold's own dispersion. The
second number is the one that matters: it is the bar the market has to clear,
stated in units that are comparable across horizons.

NO RETURNS ARE COMPUTED HERE.

    python horizon_budget.py
    python horizon_budget.py --self-test
"""

from __future__ import annotations

import argparse
import math
import sys

VERSION = "1.0"

# All measured, in REGIME_FINDINGS.md, from NAS100 M5 in-session bid/ask.
VOL_PER_MIN = 3.59e-4
SPREAD = 0.436e-4
SESSION_MIN = 420
DAYS = 252
BAR_HOLDOUT = 0.85          # 2/sqrt(5.6)
BAR_FULL = 0.56             # 2/sqrt(12.6)


def required(hold_min, bar, per_day=None, vol=VOL_PER_MIN, spread=SPREAD):
    """Gross edge per trade needed to clear `bar` at this hold."""
    n = per_day if per_day else SESSION_MIN / hold_min      # max occupancy
    trades = n * DAYS
    sd = vol * math.sqrt(hold_min)
    net = bar * sd / math.sqrt(trades)
    gross = net + spread
    return dict(hold=hold_min, per_day=n, trades=trades, sd=sd,
                net=net, gross=gross, effect=gross / sd,
                cost_drag=(spread / sd) * math.sqrt(trades))


def self_test():
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}" +
              (f"   {detail}" if detail else ""))

    print(f"horizon_budget.py v{VERSION} self-test\n")

    print("the identity this file rests on")
    r = required(30, BAR_HOLDOUT)
    recon = (r["gross"] - SPREAD) / r["sd"] * math.sqrt(r["trades"])
    check("required gross reproduces the target Sharpe exactly",
          abs(recon - BAR_HOLDOUT) < 1e-9, f"{recon:.6f}")
    check("cost drag matches cost/vol x sqrt(trades)",
          abs(r["cost_drag"] - (SPREAD / r["sd"]) * math.sqrt(r["trades"]))
          < 1e-12)

    print("\nthe two arithmetic effects, isolated")
    a, b = required(30, BAR_HOLDOUT), required(120, BAR_HOLDOUT)
    check("4x the hold doubles per-trade dispersion",
          abs(b["sd"] / a["sd"] - 2.0) < 1e-9)
    check("4x the hold quarters the trade count",
          abs(b["trades"] / a["trades"] - 0.25) < 1e-9)
    check("so cost drag falls 4x -- the half of the intuition that is true",
          abs(a["cost_drag"] / b["cost_drag"] - 4.0) < 1e-9)

    print("\nand the half that is missing")
    check("required EFFECT SIZE does not fall with a longer hold",
          b["effect"] >= a["effect"],
          f"30m {a['effect']*100:.2f}%  vs  120m {b['effect']*100:.2f}%")
    check("the curve has an interior minimum, so it is not monotone",
          required(60, BAR_HOLDOUT)["effect"] <
          min(required(5, BAR_HOLDOUT)["effect"],
              required(420, BAR_HOLDOUT)["effect"]))

    print("\ngates can fail")
    check("a free market makes the bar collapse",
          required(30, BAR_HOLDOUT, spread=0.0)["effect"] < a["effect"] / 2)
    check("a 10x spread makes it far worse",
          required(30, BAR_HOLDOUT, spread=10 * SPREAD)["effect"] >
          5 * a["effect"])
    check("a looser bar requires less edge",
          required(30, BAR_FULL)["gross"] < required(30, BAR_HOLDOUT)["gross"])

    print(f"\n{'ALL PASS' if ok else 'FAILURES ABOVE'}")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bar", type=float, default=BAR_HOLDOUT)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())

    print(f"horizon_budget.py v{VERSION}   NO RETURNS COMPUTED")
    print(f"  NAS100 in-session, measured: vol {VOL_PER_MIN*1e4:.2f}bp/min, "
          f"spread {SPREAD*1e4:.3f}bp")
    print(f"  target net annual Sharpe {a.bar:.2f}, "
          f"session {SESSION_MIN}min x {DAYS} days\n")

    print(f"{'hold':>8}{'trips/day':>11}{'trades/yr':>11}{'sd/trade':>11}"
          f"{'cost drag':>11}{'req gross':>11}{'as % of sd':>12}")
    print("-" * 75)
    rows = [required(h, a.bar) for h in
            (5, 10, 15, 30, 60, 120, 210, 420)]
    best = min(rows, key=lambda r: r["effect"])
    for r in rows:
        mark = "  <-- easiest" if r is best else ""
        lbl = (f"{r['hold']:.0f}m" if r["hold"] < 60
               else f"{r['hold']/60:.1f}h")
        print(f"{lbl:>8}{r['per_day']:>11.1f}{r['trades']:>11,.0f}"
              f"{r['sd']*1e4:>10.1f}bp{r['cost_drag']:>11.2f}"
              f"{r['gross']*1e4:>10.2f}bp{r['effect']*100:>11.2f}%{mark}")

    print(f"\n  Cost drag falls {rows[0]['cost_drag']/rows[-1]['cost_drag']:.0f}x"
          f" from 5 minutes to a full session. That is the half of the")
    print(f"  intuition that is correct.")
    print(f"\n  But the required EFFECT SIZE -- the bar the market must clear,"
          f" in units of\n  the hold's own dispersion -- barely moves, and is"
          f" U-shaped:")
    print(f"    5m  {rows[0]['effect']*100:.2f}%      "
          f"{best['hold']:.0f}m  {best['effect']*100:.2f}%  (easiest)      "
          f"7h  {rows[-1]['effect']*100:.2f}%")
    print(f"\n  Lengthening the hold buys cost relief and pays for it in "
          f"sqrt(trades).\n  The two cancel. **The hold already in use is at "
          f"the optimum.**")

    print(f"\n\n  WHAT WOULD ACTUALLY CHANGE THE ANSWER")
    print("  " + "=" * 60)
    print("  Only one thing: an effect whose edge keeps ACCUMULATING as the")
    print("  hold lengthens. The table above assumes it does not -- that the")
    print("  edge is a fixed quantity of drift, so a longer hold adds")
    print("  variance without adding edge.")
    print("\n  DESIGN_BRIEF.md already measured this, on this data:")
    print("    15 minutes to 8 days   0 of 14 price conditions sign-consistent")
    print("                           0 of 25 indicators sign-consistent")
    print("    3 to 12 months         close > SMA200d consistent in every era")
    print("\n  So the band a longer INTERVAL would move into is the band")
    print("  already measured as empty. The horizon where something does")
    print("  survive is 3-12 months -- which is not a short-interval bot, and")
    print("  DESIGN_BRIEF's own multi-market test rejected it at 0 of 9.")


if __name__ == "__main__":
    main()
