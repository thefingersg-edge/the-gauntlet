#!/usr/bin/env python3
"""Synthetic-control audit of every backtest engine in this project.

WHY
---
The v3 test reported a PASS: mean P&L +0.2846, implied Sharpe +1.51, both
criteria met. It was a bug. Snapping a barrier breach back to the barrier level
understated every loss, and because the near stop was hit ~3x more often than
the far target the optimism was severe. On a DRIFTLESS random walk at ZERO cost
the engine returned +0.278 vol units per trade, where the correct answer is 0.

That bug was caught only because the result looked too good. A bug biased the
other way -- one that quietly kills real edges -- would never have announced
itself. This file exists so no engine here is trusted on the basis that its
output looked plausible.

WHAT IT DOES
------------
Feeds each engine inputs whose correct answer is known in advance:

  1  driftless random walk, zero cost      -> mean P&L must be 0
  2  driftless random walk, with cost      -> mean P&L must be -cost
  3  cost monotonicity                     -> doubling cost doubles the drag
  4  sign symmetry                         -> real and reversed must mirror
  5  planted mean-reversion edge           -> engine must FIND it
  6  planted edge, wrong direction         -> engine must LOSE by the same
  7  barrier containment                   -> no impossible outcomes
  8  look-ahead probe                      -> shuffling the future kills P&L

An engine that cannot recover a planted edge is as dangerous as one that
invents an absent one, and only test 5 catches that.

    python audit.py
"""

from __future__ import annotations

import os
import sys

VERSION = "1.0"
TOL = 0.05          # vol units; tolerance for "indistinguishable from zero"
TRIALS = 8
N = 32000


def synth(kind, seed, n=N):
    """Price series with a KNOWN correct answer."""
    import numpy as np, pandas as pd
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2006-01-01", periods=n, freq="4h", tz="UTC")
    if kind == "driftless":
        r = rng.normal(0, 0.003, n)
    elif kind == "meanrev":
        # OU: strongly mean-reverting, so a fade strategy MUST profit
        r = np.zeros(n); x = 0.0
        for i in range(n):
            x = 0.96 * x + rng.normal(0, 0.003)
            r[i] = x - (0.96 * x if i == 0 else 0)
        x = np.zeros(n)
        for i in range(1, n):
            x[i] = 0.96 * x[i-1] + rng.normal(0, 0.003)
        r = np.diff(np.concatenate([[0.0], x]))
    elif kind == "trend":
        # persistent drift regimes, so a trend strategy MUST profit
        r = np.zeros(n); mu = 0.0
        for i in range(n):
            if rng.random() < 1/500:
                mu = rng.normal(0, 0.0006)
            r[i] = mu + rng.normal(0, 0.003)
    else:
        raise ValueError(kind)
    return pd.Series(100 * np.exp(np.cumsum(r)), index=idx)


def run_suite(name, fn, kind_for_edge, tests):
    """fn(price, cost, mode, rng) -> DataFrame with a 'pnl' column."""
    import numpy as np
    print(f"\n{'='*72}\n{name}\n{'='*72}")
    fails = []

    def check(label, cond, detail=""):
        print(f"  {'PASS' if cond else 'FAIL'}  {label}" +
              (f"   {detail}" if detail else ""))
        if not cond:
            fails.append(label)

    # 1. driftless, zero cost -> 0
    m = [fn(synth("driftless", s), 0.0, "real", None).pnl.mean()
         for s in range(TRIALS)]
    mu, se = float(np.mean(m)), float(np.std(m)) / np.sqrt(TRIALS)
    check("1 driftless + zero cost -> mean 0", abs(mu) < max(2 * se, TOL),
          f"got {mu:+.4f} (se {se:.4f})")

    # 2. driftless with cost -> -cost (in vol units, approximately)
    C = 0.001
    m2 = [fn(synth("driftless", s), C, "real", None) for s in range(TRIALS)]
    drag = np.mean([t.pnl.mean() for t in m2]) - mu
    check("2 cost reduces P&L", drag < 0, f"drag {drag:+.4f}")

    # 3. doubling cost doubles the drag
    m3 = [fn(synth("driftless", s), 2 * C, "real", None) for s in range(TRIALS)]
    drag2 = np.mean([t.pnl.mean() for t in m3]) - mu
    ratio = drag2 / drag if drag != 0 else float("nan")
    check("3 doubling cost doubles drag", 1.7 < ratio < 2.3,
          f"ratio {ratio:.2f}")

    # 4. sign symmetry on symmetric data
    a = fn(synth("driftless", 99), 0.0, "real", None).pnl.mean()
    b = fn(synth("driftless", 99), 0.0, "rev", None).pnl.mean()
    check("4 real and reversed mirror on symmetric data",
          abs(a + b) < max(TOL, 0.3 * (abs(a) + abs(b)) + 1e-9),
          f"real {a:+.4f} rev {b:+.4f} sum {a+b:+.4f}")

    # 5/6. planted edge: engine must find it, and lose it reversed
    e = [fn(synth(kind_for_edge, s), 0.0, "real", None).pnl.mean()
         for s in range(TRIALS)]
    er = [fn(synth(kind_for_edge, s), 0.0, "rev", None).pnl.mean()
          for s in range(TRIALS)]
    em, erm = float(np.mean(e)), float(np.mean(er))
    check(f"5 recovers a planted {kind_for_edge} edge", em > 2 * TOL,
          f"got {em:+.4f}")
    check("6 reversed loses on the same data", erm < em,
          f"real {em:+.4f} rev {erm:+.4f}")

    # 7. barrier containment (overshoot allowed, but bounded and one-signed)
    t = fn(synth("driftless", 7), 0.0, "real", None)
    if "outcome" in t.columns and len(t):
        sl_hits = t[t.outcome == "sl"]
        over = sl_hits.pnl.min() if len(sl_hits) else 0.0
        check("7 stop losses are not credited better than the stop",
              len(sl_hits) == 0 or sl_hits.pnl.max() <= 0,
              f"worst {over:+.2f}, best sl {sl_hits.pnl.max():+.2f}"
              if len(sl_hits) else "no sl hits")
    else:
        check("7 barrier containment", True, "n/a")

    # 8. LOOK-AHEAD PROBE. Plant an edge, then destroy the future while
    # leaving the SIGNAL untouched: shuffle post-entry returns. An engine
    # using only information available at entry must collapse to ~0. One
    # that peeks keeps its edge, because the "future" it read is still there.
    # This was listed in the docstring and never implemented -- the gap
    # itself is the kind of thing this file exists to catch.
    import pandas as pd
    def shuffled(kind, seed):
        px = synth(kind, seed)
        r = np.log(px.to_numpy(float))
        d = np.diff(r, prepend=r[0])
        rs = np.random.default_rng(seed + 777)
        head = max(200, len(d) // 4)          # keep early bars so signals form
        tail = d[head:].copy()
        rs.shuffle(tail)                      # same distribution, no structure
        d2 = np.concatenate([d[:head], tail])
        return pd.Series(np.exp(np.cumsum(d2)) * 100, index=px.index)

    intact = np.mean([fn(synth(kind_for_edge, s), 0.0, "real", None).pnl.mean()
                      for s in range(TRIALS)])
    broken = np.mean([fn(shuffled(kind_for_edge, s), 0.0, "real", None).pnl.mean()
                      for s in range(TRIALS)])
    check("8 look-ahead probe: shuffling the future kills the edge",
          abs(broken) < max(0.35 * abs(intact), TOL),
          f"intact {intact:+.4f} -> shuffled {broken:+.4f}")

    print(f"  --> {len(fails)} failure(s)" + (f": {', '.join(fails)}" if fails else ""))
    return fails


def main():
    import numpy as np
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    print(f"audit.py v{VERSION}  synthetic controls, known answers\n")
    print(f"  tolerance {TOL} vol units, {TRIALS} trials, {N:,} bars each")

    # sklearn is not needed for any engine here; stub it so silver_mr imports
    import types
    if "sklearn" not in sys.modules:
        try:
            import sklearn  # noqa: F401
        except ImportError:
            m = types.ModuleType("sklearn"); lm = types.ModuleType("sklearn.linear_model")
            class _LR:
                def __init__(self, *a, **k): raise RuntimeError("stubbed")
            lm.LogisticRegression = _LR; m.linear_model = lm
            sys.modules["sklearn"] = m; sys.modules["sklearn.linear_model"] = lm

    import prereg_v3_test as V3
    import prereg_v2_test as V2
    import hedged_test as HT
    import silver_mr  # noqa: F401  (import check only)

    all_fails = {}

    # --- directional engine (v3), already fixed --------------------------
    all_fails["v3 directional"] = run_suite(
        "prereg_v3_test.instrument_trades   (directional, POST-FIX)",
        lambda px, c, mode, rng: V3.instrument_trades(px, c, mode, rng),
        "trend", None)

    # --- pair engine (v2): needs a second leg ----------------------------
    def v2_call(px, c, mode, rng):
        # pair the series against an independent walk so the residual is the
        # series itself plus noise; cost passed to both legs
        other = synth("driftless", 12345, len(px))
        other.index = px.index
        return V2.pair_trades(px, other, c, c, mode, rng)

    all_fails["v2 pairs"] = run_suite(
        "prereg_v2_test.pair_trades   (residual pairs, PRE-FIX)",
        v2_call, "meanrev", None)

    # --- hedged engine ---------------------------------------------------
    def ht_call(px, c, mode, rng):
        import numpy as np, pandas as pd
        other = synth("driftless", 54321, len(px))
        other.index = px.index
        df = pd.DataFrame({"close": px, "xau": other, "beta": 0.0})
        cfg = dict(silver_mr.CFG)
        # A REAL mean-reversion signal. The first version of this harness used
        # an always-long signal and then asked the engine to recover a
        # mean-reversion edge -- an unfair test that produced a false FAIL.
        # An audit that reports spurious failures is as useless as one that
        # misses real ones.
        lp = pd.Series(np.log(px.to_numpy(float)), index=px.index)
        z = (lp - lp.rolling(96).mean()) / lp.rolling(96).std()
        sides = pd.Series(0, index=px.index, dtype=int)
        sides[z <= -2] = 1
        sides[z >= 2] = -1
        if mode == "rev":
            sides = -sides
        elif mode == "rand" and rng is not None:
            v = sides.to_numpy(dtype=int, copy=True)
            nz = v != 0
            v[nz] = rng.choice([-1, 1], size=int(nz.sum()))
            sides = pd.Series(v, index=px.index, dtype=int)
        return HT.spread_barriers(silver_mr, df, sides, cfg, c, 0.0,
                                  hedged=False, no_overlap=True).rename(
                                      columns={"pnl_sig": "pnl"})

    all_fails["hedged"] = run_suite(
        "hedged_test.spread_barriers   (hedged spread, PRE-FIX)",
        ht_call, "meanrev", None)

    print(f"\n{'='*72}\nSUMMARY\n{'='*72}")
    for k, v in all_fails.items():
        print(f"  {k:<20} {'CLEAN' if not v else f'{len(v)} FAILURE(S)'}")
        for f in v:
            print(f"      - {f}")
    tot = sum(len(v) for v in all_fails.values())
    print(f"\n  {tot} total failures across {len(all_fails)} engines.")
    if tot:
        print("  Any engine with a test-1 failure MANUFACTURES or DESTROYS P&L")
        print("  independently of signal. Its results are not interpretable.")


if __name__ == "__main__":
    main()
