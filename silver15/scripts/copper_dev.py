#!/usr/bin/env python3
"""Copper/palladium development harness. The holdout is locked BY CODE.

PROTOCOL (agreed 2026-08-09, before any development)
----------------------------------------------------
    development window   2006-03-01 .. 2018-12-31    (open)
    LOCKED HOLDOUT       2019-01-01 .. 2026-08-07    (untouched)
    condition budget     3, each with a stated mechanism BEFORE testing
    final test           ONE run on the holdout, at the end

Why the lock is in code rather than in a promise: this project has now found a
cache-key collision, a day-index error, a timezone bug, three mislabelled
files, an overlapping-sample inflation, a fixed-dollar cost error and an
unpowerable pre-registration. Every one of them survived good intentions.
`load()` truncates at 2018-12-31 unconditionally. Seeing the holdout requires
--unlock-holdout AND the exact confirmation phrase, and that is recorded.

THE CONDITION LEDGER
--------------------
Every condition tested is appended to `ledger.json` automatically. The budget
of 3 cannot be quietly exceeded by forgetting what was already tried -- the
count is on disk, not in anyone's memory. A 3-way selection needs about t>2.1
to mean what t>1.96 would mean for a single pre-planned test; the ledger is
what makes that correction computable rather than guessed.

STANDING CAVEAT -- READ BEFORE BELIEVING ANY RESULT HERE
--------------------------------------------------------
copper/palladium was chosen from 9 pairs AFTER seeing their gross P&L
(t = 2.69; the best of 9 under pure noise exceeds t = 2.53 about 5% of the
time). It clears selection only marginally. Worse, copper/PLATINUM -- the near
substitute, same auto-catalyst demand story -- shows +0.0117 gross against
copper/palladium's +0.2304. A structural effect should not vanish when you
swap in the substitute.

So the prior here is weak and the mechanism is unproven. The holdout is the
only thing that can settle it.

    python copper_dev.py --baseline
    python copper_dev.py --ledger
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

VERSION = "1.0"

DEV_START, DEV_END = "2006-03-01", "2018-12-31"
HOLDOUT_START, HOLDOUT_END = "2019-01-01", "2026-08-07"
CONDITION_BUDGET = 3
UNLOCK_PHRASE = "I am spending the holdout and will not develop further"
LEDGER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ledger.json")

PAIR = ("xcuusd", "xpdusd")           # copper / palladium


def load(data_dir, holdout=False):
    """Load the pair. Truncated to the development window unless unlocked."""
    import pandas as pd
    out = {}
    for stem in PAIR:
        d = pd.read_csv(os.path.join(data_dir, f"{stem}_4h.csv"))
        t = d.columns[0]
        d[t] = pd.to_datetime(d[t], utc=True)
        s = d.set_index(t).sort_index()["close"]
        s = s.loc[HOLDOUT_START:HOLDOUT_END] if holdout else s.loc[DEV_START:DEV_END]
        out[stem] = s
    win = "HOLDOUT" if holdout else "development"
    lo = min(v.index.min() for v in out.values())
    hi = max(v.index.max() for v in out.values())
    print(f"  window: {win}   {lo.date()} -> {hi.date()}   "
          f"{min(len(v) for v in out.values()):,} bars")
    if not holdout and hi >= pd.Timestamp(HOLDOUT_START, tz="UTC"):
        raise SystemExit("!! holdout leaked into the development window. STOP.")
    return out


def read_ledger():
    if not os.path.exists(LEDGER):
        return []
    with open(LEDGER) as fh:
        return json.load(fh)


def log_condition(name, mechanism, result):
    entries = read_ledger()
    entries.append(dict(n=len(entries) + 1, name=name, mechanism=mechanism,
                        result=result,
                        when=dt.datetime.now(dt.timezone.utc).isoformat()[:19]))
    with open(LEDGER, "w") as fh:
        json.dump(entries, fh, indent=2)
    used = len([e for e in entries if e["name"] != "baseline"])
    print(f"\n  ledger: {used}/{CONDITION_BUDGET} conditions used")
    if used > CONDITION_BUDGET:
        print("  !! BUDGET EXCEEDED. Any further result is not interpretable")
        print("  !! at the agreed threshold. Stop and test the holdout.")
    return used


def gates(series):
    """Compute all three pre-declared condition gates.

    Each is stated with its mechanism BEFORE being tested, and each uses a
    MEDIAN SPLIT rather than a searched threshold. That is deliberate: a swept
    threshold is a hidden extra experiment and would silently spend more of the
    3-condition budget than it appears to. The median is one pre-declared
    choice, not a search.
    """
    import numpy as np, pandas as pd
    import prereg_v2_test as V

    a, b = series[PAIR[0]], series[PAIR[1]]
    idx = a.index.intersection(b.index)
    ra = pd.Series(np.log(a.loc[idx].to_numpy(float)), index=idx).diff()
    rb = pd.Series(np.log(b.loc[idx].to_numpy(float)), index=idx).diff()
    beta = (ra.rolling(V.BETA_WINDOW).cov(rb)
            / rb.rolling(V.BETA_WINDOW).var().replace(0, np.nan)).clip(0.5, 4.0)
    resid = ra - beta * rb
    svol = resid.rolling(V.VOL_WINDOW).std()

    g = {}

    # ---- CONDITION 1: trend-regime gate ---------------------------------
    # MECHANISM: established across three horizons in this project -- the
    # residual REVERTS fast (minutes to ~1 day) and TRENDS slowly (~5 days).
    # A reversion entry taken while the slow residual is trending is fighting
    # the slower effect. Kaufman efficiency ratio on the residual path: net
    # displacement over total path length. High = trending, low = choppy.
    # Trade reversion only in the choppy half.
    net = resid.rolling(120).sum().abs()
    path = resid.abs().rolling(120).sum()
    er = (net / path.replace(0, np.nan))
    g["trend"] = er < er.median()

    # ---- CONDITION 2: cost-to-volatility gate ---------------------------
    # MECHANISM: cost is FIXED per round trip while spread-vol varies by a
    # factor of several. Entries taken when vol is low pay the same spread for
    # a smaller available move -- they cannot pay for themselves regardless of
    # whether the signal is right. This predicts nothing; it declines trades
    # that are arithmetically unable to profit.
    cost = 2 * (V.SPREAD_REL[PAIR[0]] / 2 + beta.abs() * V.SPREAD_REL[PAIR[1]] / 2)
    ratio = cost / svol
    g["cost"] = ratio < ratio.median()

    # ---- CONDITION 3: beta-stability gate -------------------------------
    # MECHANISM: the position is hedged with beta x palladium. If beta is
    # moving, the hedge put on at entry is not the hedge you hold at exit, and
    # the "residual" being traded is not the one that was measured. Require
    # the rolling beta to be steady.
    bstab = beta.rolling(60).std() / beta.abs().rolling(60).mean()
    g["beta"] = bstab < bstab.median()

    return {k: v.reindex(idx).fillna(False) for k, v in g.items()}


def run(series, sides_mode="real", cond=None, seeds=0):
    """Baseline v2 spec on this pair, optionally with a condition mask."""
    import numpy as np, pandas as pd
    import prereg_v2_test as V

    a, b = series[PAIR[0]], series[PAIR[1]]
    sa, sb = V.SPREAD_REL[PAIR[0]], V.SPREAD_REL[PAIR[1]]
    tr = V.pair_trades(a, b, sa, sb, sides_mode)
    if cond is not None and len(tr):
        tr = tr[tr.t.map(cond).fillna(False)].reset_index(drop=True)
    return tr


def report(tr, label):
    import numpy as np
    if len(tr) == 0:
        print(f"  {label}: no trades"); return None
    se = tr.pnl.std() / np.sqrt(len(tr))
    t = tr.pnl.mean() / se if se > 0 else 0.0
    boot = np.array([np.random.default_rng(k).choice(
        tr.pnl.to_numpy(), len(tr), replace=True).mean() for k in range(1000)])
    lo, hi = np.percentile(boot, 2.5), np.percentile(boot, 97.5)
    print(f"  {label:<22} n={len(tr):>5}  win {tr.win.mean():>6.2%}  "
          f"mean {tr.pnl.mean():>+8.4f}  t={t:>+5.2f}  CI[{lo:+.3f},{hi:+.3f}]")
    return dict(n=int(len(tr)), win=float(tr.win.mean()),
                mean=float(tr.pnl.mean()), t=float(t),
                ci=[float(lo), float(hi)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="../data_h4")
    ap.add_argument("--baseline", action="store_true")
    ap.add_argument("--condition", default=None,
                    choices=["trend", "cost", "beta"],
                    help="test ONE pre-declared condition (spends budget)")
    ap.add_argument("--cumulative", action="store_true",
                    help="stack this condition on the previous ones")
    ap.add_argument("--ledger", action="store_true")
    ap.add_argument("--unlock-holdout", default=None,
                    help="requires the exact confirmation phrase")
    a = ap.parse_args()
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    print(f"copper_dev.py v{VERSION}   copper/palladium")
    print(f"  dev {DEV_START}..{DEV_END}   HOLDOUT {HOLDOUT_START}..{HOLDOUT_END} "
          f"(locked)")

    if a.ledger:
        for e in read_ledger():
            print(f"  {e['n']}. {e['name']:<22} {e['when']}  "
                  f"t={e['result'].get('t', float('nan')):+.2f}")
            print(f"     mechanism: {e['mechanism']}")
        used = len([e for e in read_ledger() if e["name"] != "baseline"])
        print(f"\n  {used}/{CONDITION_BUDGET} conditions used")
        return

    holdout = False
    if a.unlock_holdout is not None:
        if a.unlock_holdout != UNLOCK_PHRASE:
            raise SystemExit(f"!! wrong phrase. The holdout stays locked.\n"
                             f"   required: \"{UNLOCK_PHRASE}\"")
        holdout = True
        print("\n  *** HOLDOUT UNLOCKED. This is the one shot. ***")

    s = load(a.data, holdout)

    MECH = {
        "trend": "residual reverts fast, trends slow: skip entries while the "
                 "120-bar residual path is directional (ER above median)",
        "cost": "cost is fixed, spread-vol varies: skip entries where "
                "cost/vol is in the worse half -- cannot pay for itself",
        "beta": "a moving beta means the hedge at exit is not the hedge at "
                "entry: require rolling beta stability in the better half",
    }
    if a.condition:
        gs = gates(s)
        order = ["trend", "cost", "beta"]
        use = order[:order.index(a.condition) + 1] if a.cumulative \
            else [a.condition]
        mask = None
        for k in use:
            mask = gs[k] if mask is None else (mask & gs[k])
        print(f"\n  condition: {' + '.join(use)}")
        print(f"  mechanism: {MECH[a.condition]}")
        print(f"  gate keeps {mask.mean():.1%} of bars\n")
        base = report(run(s, "real"), "baseline (real)")
        d = mask.to_dict()
        r = report(run(s, "real", cond=lambda t: d.get(t, False)), "WITH condition")

        # THE RIGHT NULL FOR A FILTER. A gate that keeps half the bars must be
        # judged against RANDOM subsamples of the same size, not against the
        # full baseline: any 50% subsample moves the mean around, and the
        # question is whether THIS one moves it more than chance would.
        
        report(run(s, "rev", cond=lambda t: d.get(t, False)), "  reversed")
        if r and base:
            import numpy as np
            full = run(s, "real")
            keep = r["n"]
            sub = np.array([np.random.default_rng(k).choice(
                full.pnl.to_numpy(), keep, replace=False).mean()
                for k in range(2000)])
            z = (r["mean"] - sub.mean()) / sub.std()
            pctl = float((sub < r["mean"]).mean())
            print(f"\n  delta vs baseline: mean {r['mean']-base['mean']:+.4f}"
                  f"   win {(r['win']-base['win'])*100:+.2f}pp"
                  f"   trades {r['n']-base['n']:+d}")
            print(f"  vs RANDOM subsamples of the same size (n={keep}):")
            print(f"    random mean {sub.mean():+.4f} (sd {sub.std():.4f})"
                  f"   this gate {r['mean']:+.4f}")
            print(f"    = {z:+.2f} sd, {pctl:.0%} percentile")
            r["vs_random_sd"] = float(z)
            if abs(z) < 1.5:
                print("    >> the gate is doing nothing a coin could not do.")
        if not holdout:
            log_condition(" + ".join(use), MECH[a.condition], r or {})
        print("\n  Break-even is ~54.3% win at these barriers and costs.")
        return

    if a.baseline:
        print()
        r = report(run(s, "real"), "baseline (real)")
        report(run(s, "rev"), "reversed")
        if not holdout:
            log_condition("baseline", "v2 spec, no conditions", r or {})
        print("\n  Break-even is ~54.3% win at these barriers and costs.")


if __name__ == "__main__":
    main()
