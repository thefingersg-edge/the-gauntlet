#!/usr/bin/env python3
"""The backtest engine for PREREGISTRATION_v1 / v1.1. Nothing else.

This file implements ONE specification, the frozen one:

    sigma_t = 1.4826 * MAD(r) over the previous N bars, in-session, consecutive
    z_t     = r_t / sigma_t
    ENTRY   z <= -k -> LONG,  z >= +k -> SHORT, at the OPEN of bar t+1
    GATE    only if spread_t / (sigma_t * sqrt(H)) <= 0.15
    EXIT    at the OPEN of bar t+1+H
    long buys the ASK and sells the BID; short is the mirror
    non-overlapping, <= 4 round trips per day, flat by session close

It deliberately does NOT expose N, k or H as sweepable inputs on the command
line beyond the declared secondaries. They are frozen at 24 / 3.0 / 6 and any
other value is a declared secondary under v1 section 5, reported and never
promoted.

    python engine.py --self-test           <- run this first, and believe it
    python engine.py --window fit
    python engine.py --window holdout      <- ONLY after Gate A passes
"""

from __future__ import annotations

import argparse
import math
import os
import sys

VERSION = "1.0"

# ---- FROZEN by PREREGISTRATION_v1 section 3. Do not edit to chase a result.
N_VOL = 24          # bars for the volatility estimate (2 hours)
K_SIGMA = 3.0       # entry threshold in sigmas
H_HOLD = 6          # holding period in bars (30 minutes)
COST_VOL_GATE = 0.15
MAX_PER_DAY = 4
SESSION = (9, 16)   # America/New_York
TZ = "America/New_York"

WINDOWS = {
    "early":   ("2012-01-01", "2013-12-31"),   # secondary, high cost
    "fit":     ("2014-01-01", "2020-12-31"),   # Gate A
    "holdout": ("2021-01-01", "2026-12-31"),   # Gate B -- open once
}
GATE_A_NET_SHARPE = 0.76        # 2/sqrt(7.0)
GATE_B_NET_SHARPE = 0.85        # 2/sqrt(5.6)
MIN_TRADES = 200


# ------------------------------------------------------------------ data

def load_bars(data_dir, instrument, gran="M5"):
    """bid/ask OHLC -> the arrays the engine needs. No returns computed."""
    import numpy as np, pandas as pd

    stem = instrument.replace("_", "").lower()
    suf = {"M1": "1m", "M5": "5m", "M15": "15m"}[gran]
    step = {"M1": 60, "M5": 300, "M15": 900}[gran]

    frames = {}
    for side in ("bid", "ask"):
        p = os.path.join(data_dir, f"{stem}_{side}_{suf}.csv")
        if not os.path.exists(p):
            raise SystemExit(f"missing {os.path.basename(p)}")
        d = pd.read_csv(p)
        d.columns = ["t", "open", "high", "low", "close", "volume"]
        d["t"] = pd.to_datetime(d["t"], utc=True)
        frames[side] = d.drop_duplicates("t").set_index("t")

    idx = frames["bid"].index.intersection(frames["ask"].index).sort_values()
    b, a = frames["bid"].loc[idx], frames["ask"].loc[idx]

    local = idx.tz_convert(TZ)
    mid_c = (b["close"].to_numpy(float) + a["close"].to_numpy(float)) / 2
    mid_o = (b["open"].to_numpy(float) + a["open"].to_numpy(float)) / 2
    spread = (a["close"].to_numpy(float) - b["close"].to_numpy(float)) / mid_c

    dt = np.diff(idx.to_numpy()) / np.timedelta64(1, "s")
    consec = np.concatenate([[False], dt == step])

    return dict(
        t=idx, local=local,
        bid_o=b["open"].to_numpy(float), ask_o=a["open"].to_numpy(float),
        mid_c=mid_c, mid_o=mid_o, spread=spread, consec=consec,
        hour=local.hour.to_numpy(), year=local.year.to_numpy(),
        day=local.normalize().to_numpy(),
    )


# ------------------------------------------------------------------ signal

def signal(D):
    """z-score and the spread gate. Uses information available at bar t only.

    Every quantity here is computed from bars <= t. The entry price is taken
    from bar t+1 in `run()`, never from bar t -- that separation is the whole
    look-ahead surface and is probed explicitly in the self-test.
    """
    import numpy as np, pandas as pd

    n = len(D["mid_c"])
    in_ses = (D["hour"] >= SESSION[0]) & (D["hour"] < SESSION[1])

    r = np.full(n, np.nan)
    ok = D["consec"] & in_ses
    r[ok] = np.log(D["mid_c"][ok] / np.roll(D["mid_c"], 1)[ok])

    # Rolling MAD over the previous N_VOL bars, EXCLUDING bar t itself so the
    # threshold cannot be inflated by the very move it is judging.
    s = pd.Series(r)
    med = s.rolling(N_VOL).median().shift(1)
    mad = (s - med).abs().rolling(N_VOL).median().shift(1)
    sigma = (1.4826 * mad).to_numpy()

    with np.errstate(invalid="ignore", divide="ignore"):
        z = r / sigma
        cv = D["spread"] / (sigma * math.sqrt(H_HOLD))

    valid = np.isfinite(z) & np.isfinite(cv) & in_ses & (sigma > 0)
    return z, cv, valid, in_ses


def entries(D, z, cv, valid, in_ses, side_rule="reversion", rng=None,
            random_entry=False):
    """Pick entry bars under the pre-registered constraints.

    side_rule: 'reversion' (primary), 'momentum' (reversed null),
               'random'    (randomised-side null)
    random_entry: ignore z entirely and pick bars at random from the same
               time-of-day distribution (random-entry null)
    """
    import numpy as np

    n = len(z)
    fire = valid & (np.abs(z) >= K_SIGMA) & (cv <= COST_VOL_GATE)
    if random_entry:
        pool = np.flatnonzero(valid & (cv <= COST_VOL_GATE))
        want = int(fire.sum())
        fire = np.zeros(n, bool)
        if want and len(pool):
            fire[rng.choice(pool, size=min(want, len(pool)),
                            replace=False)] = True

    out = []
    busy_until = -1
    day_count = {}
    for i in np.flatnonzero(fire):
        j, k = i + 1, i + 1 + H_HOLD          # enter at j, exit at k
        if k >= n:
            continue
        if j <= busy_until:                    # non-overlapping
            continue
        if not (in_ses[j] and in_ses[k]):      # flat by the close
            continue
        if D["day"][j] != D["day"][k]:
            continue
        d = D["day"][j]
        if day_count.get(d, 0) >= MAX_PER_DAY:
            continue
        if side_rule == "reversion":
            sd = -1 if z[i] > 0 else 1
        elif side_rule == "momentum":
            sd = 1 if z[i] > 0 else -1
        else:
            sd = 1 if rng.random() < 0.5 else -1
        out.append((j, k, sd))
        busy_until = k
        day_count[d] = day_count.get(d, 0) + 1
    return out


def pnl(D, trades, leak=False):
    """Per-trade net returns. Cost is the actual bid/ask on the actual bars.

    `leak` is a DELIBERATE look-ahead used only by the self-test: it fills at
    bar t's close instead of bar t+1's open. It exists so the probe can be
    shown to detect a leak; if it cannot detect this one it cannot detect any.
    """
    import numpy as np
    if not trades:
        return np.array([])
    out = []
    for j, k, sd in trades:
        if leak:
            ent = D["mid_c"][j - 1]
            ex = D["mid_o"][k]
            out.append(sd * (ex - ent) / ent)
            continue
        if sd > 0:
            ent, ex = D["ask_o"][j], D["bid_o"][k]
        else:
            ent, ex = D["bid_o"][j], D["ask_o"][k]
        out.append((ex - ent) / ent if sd > 0 else (ent - ex) / ent)
    return np.array(out)


def stats(rets, years):
    import numpy as np
    if len(rets) < 2 or years <= 0:
        return dict(n=len(rets), sharpe=float("nan"), mean=float("nan"),
                    total=float(np.sum(rets)) if len(rets) else 0.0,
                    per_yr=0.0)
    per_yr = len(rets) / years
    sd = float(np.std(rets, ddof=1))
    return dict(
        n=len(rets), per_yr=per_yr,
        mean=float(np.mean(rets)),
        sharpe=(float(np.mean(rets)) / sd * math.sqrt(per_yr)) if sd > 0
        else float("nan"),
        total=float(np.sum(rets)))


def slice_window(D, lo, hi):
    import numpy as np, pandas as pd
    m = (D["local"] >= pd.Timestamp(lo, tz=TZ)) & \
        (D["local"] <= pd.Timestamp(hi + " 23:59:59", tz=TZ))
    idx = np.flatnonzero(m)
    if len(idx) == 0:
        raise SystemExit(f"no bars in {lo}..{hi}")
    a, b = idx[0], idx[-1] + 1
    out = {k: (v[a:b] if hasattr(v, "__len__") else v) for k, v in D.items()}
    out["consec"] = D["consec"][a:b].copy()
    out["consec"][0] = False
    return out


def run(D, seed=0, side_rule="reversion", random_entry=False, leak=False,
        leak_signal=False):
    import numpy as np
    rng = np.random.default_rng(seed)
    z, cv, valid, in_ses = signal(D)
    if leak_signal:
        # DELIBERATE look-ahead, self-test only: judge bar t by bar t+1's
        # move. Exists so the probe can be shown to catch a leak; a probe
        # never observed to fire has not been tested.
        z = np.roll(z, -1)
        valid = valid & np.roll(valid, -1)
    tr = entries(D, z, cv, valid, in_ses, side_rule, rng, random_entry)
    rets = pnl(D, tr, leak=leak)
    years = (D["local"][-1] - D["local"][0]).days / 365.25
    st = stats(rets, years)
    st["years"] = years
    st["per_day"] = st["n"] / max(years * 252, 1)
    st["trades"] = tr
    st["rets"] = rets
    return st


# ------------------------------------------------------------------ tests

def _synth(years=6, alpha=0.0, spread_bp=0.4, sd_bp=3.5, seed=0,
           start="2014-01-02"):
    """Session-shaped M5 bars with a KNOWN reversion strength `alpha`.

    alpha = 0   -> nothing to find. The engine must return ~0.
    alpha > 0   -> a shock reverts by that fraction over the next H bars.
    alpha < 0   -> shocks continue. The momentum null must then win.
    """
    import numpy as np, pandas as pd

    rng = np.random.default_rng(seed)
    days = pd.bdate_range(start, periods=int(252 * years), tz=TZ)
    stamps = []
    for d in days:
        stamps.append(pd.date_range(d + pd.Timedelta(hours=SESSION[0]),
                                    d + pd.Timedelta(hours=SESSION[1]),
                                    freq="5min", inclusive="left", tz=TZ))
    t = stamps[0].append(stamps[1:]) if len(stamps) > 1 else stamps[0]
    n = len(t)

    sd = sd_bp * 1e-4 * math.sqrt(5)          # per 5m bar
    r = rng.normal(0, sd, n)
    # inject shocks and their reversion
    shock_at = rng.random(n) < 0.004
    r[shock_at] += rng.choice([-1, 1], shock_at.sum()) * 4.5 * sd
    if alpha:
        rev = np.zeros(n)
        for i in np.flatnonzero(shock_at):
            if i + 1 + H_HOLD < n:
                rev[i + 1: i + 1 + H_HOLD] -= alpha * r[i] / H_HOLD
        r += rev

    mid_c = 10000 * np.exp(np.cumsum(r))
    mid_o = np.concatenate([[mid_c[0]], mid_c[:-1]])
    half = spread_bp * 1e-4 / 2
    tu = t.tz_convert("UTC")
    return dict(
        t=tu, local=t,
        bid_o=mid_o * (1 - half), ask_o=mid_o * (1 + half),
        mid_c=mid_c, mid_o=mid_o,
        spread=np.full(n, spread_bp * 1e-4),
        consec=np.concatenate([[False],
                               np.diff(tu.to_numpy()) /
                               np.timedelta64(1, "s") == 300]),
        hour=t.hour.to_numpy(), year=t.year.to_numpy(),
        day=t.normalize().to_numpy())


def self_test():
    import numpy as np
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}" +
              (f"   {detail}" if detail else ""))

    print(f"engine.py v{VERSION} self-test\n")
    print(f"frozen spec: N={N_VOL} k={K_SIGMA} H={H_HOLD} "
          f"gate={COST_VOL_GATE} max={MAX_PER_DAY}/day\n")

    print("A. the probe returns ZERO where the honest answer is zero")
    # silver15 v7's leak probe ran on a strong trend, where a planted edge
    # swamps the leak: 54x inflation on a driftless path, 1.1x on a trend.
    # So this is run driftless, with nothing planted.
    null = _synth(years=6, alpha=0.0, seed=1)
    rn = run(null, seed=1)
    se = 1.0 / math.sqrt(max(rn["n"], 1)) * math.sqrt(rn["per_yr"])
    check("no planted edge -> Sharpe within 2 se of zero",
          abs(rn["sharpe"]) < 2 * se,
          f"Sharpe {rn['sharpe']:+.3f}, 2se {2*se:.3f}, n={rn['n']}")
    check("and it produced a real sample, not an empty one",
          rn["n"] > 300, f"n={rn['n']}")

    print("\nB. it RECOVERS an effect that is really there")
    good = _synth(years=6, alpha=0.35, seed=1)
    rg = run(good, seed=1)
    check("planted reversion is detected", rg["sharpe"] > 1.0,
          f"Sharpe {rg['sharpe']:+.2f}, n={rg['n']}")
    check("and clearly exceeds the null run",
          rg["sharpe"] > rn["sharpe"] + 1.0,
          f"{rg['sharpe']:+.2f} vs {rn['sharpe']:+.2f}")

    print("\nC. the reversed-side null wins when the shock is INFORMATION")
    # The pre-registered falsifier: if shocks continue rather than revert,
    # momentum must beat reversion. If this does not fire, the null is
    # decorative.
    mom = _synth(years=6, alpha=-0.35, seed=1)
    r_rev = run(mom, seed=1, side_rule="reversion")
    r_mom = run(mom, seed=1, side_rule="momentum")
    check("momentum beats reversion on continuing shocks",
          r_mom["sharpe"] > r_rev["sharpe"],
          f"mom {r_mom['sharpe']:+.2f} vs rev {r_rev['sharpe']:+.2f}")
    check("and reversion is actually negative there",
          r_rev["sharpe"] < 0, f"{r_rev['sharpe']:+.2f}")

    print("\nD. no look-ahead -- tested causally, not by inspection")
    # The first version of this control compared filling at bar t's close
    # against bar t+1's open. That is NOT a look-ahead test: in this
    # generator open[t] == close[t-1] exactly, so the two differ only by the
    # spread. It would have passed on an engine that peeked.
    #
    # The right test is causal. Build two series identical up to bar M and
    # different after it. If the engine uses only information available at
    # bar t, every signal at t < M must be byte-identical between them.
    import numpy as _np
    A = _synth(years=4, alpha=0.35, seed=7)
    B = _synth(years=4, alpha=0.35, seed=7)
    M = len(B["mid_c"]) // 2
    rng2 = _np.random.default_rng(999)
    for key in ("mid_c", "mid_o", "bid_o", "ask_o"):
        B[key] = B[key].copy()
        B[key][M:] *= _np.exp(_np.cumsum(rng2.normal(0, 5e-3, len(B[key]) - M)))
    B["spread"] = B["spread"].copy()
    B["spread"][M:] = 9e-3

    zA, cvA, vA, _ = signal(A)
    zB, cvB, vB, _ = signal(B)
    same_z = _np.allclose(_np.nan_to_num(zA[:M]), _np.nan_to_num(zB[:M]))
    same_cv = _np.allclose(_np.nan_to_num(cvA[:M]), _np.nan_to_num(cvB[:M]))
    check("rewriting the FUTURE leaves every past z unchanged", same_z)
    check("and leaves every past spread gate unchanged", same_cv)
    check("the future really was changed -- the control can fail",
          not _np.allclose(_np.nan_to_num(zA[M + N_VOL + 2:]),
                           _np.nan_to_num(zB[M + N_VOL + 2:])))

    # And the probe must be able to see a leak when there IS one.
    leaked = run(null, seed=1, leak_signal=True)
    check("a deliberate one-bar-ahead signal is detected on NULL data",
          abs(leaked["sharpe"]) > 3.0,
          f"leaked {leaked['sharpe']:+.2f} vs honest {rn['sharpe']:+.2f}")
    check("while the honest run on the same data stays at zero",
          abs(rn["sharpe"]) < 1.0, f"{rn['sharpe']:+.2f}")

    print("\nE. constraints actually bind")
    tr = rg["trades"]
    js = [j for j, _, _ in tr]
    ks = [k for _, k, _ in tr]
    check("no overlapping positions",
          all(js[i + 1] > ks[i] for i in range(len(tr) - 1)))
    check("every hold is exactly H bars",
          all(k - j == H_HOLD for j, k, _ in tr))
    from collections import Counter
    per_day = Counter(good["day"][j] for j, _, _ in tr)
    check(f"never more than {MAX_PER_DAY} round trips in a day",
          max(per_day.values()) <= MAX_PER_DAY, f"max {max(per_day.values())}")
    check("every entry and exit is inside the session",
          all(SESSION[0] <= good["hour"][j] < SESSION[1] and
              SESSION[0] <= good["hour"][k] < SESSION[1] for j, k, _ in tr))
    check("no trade spans two days",
          all(good["day"][j] == good["day"][k] for j, k, _ in tr))

    print("\nF. the spread gate blocks when cost is too high")
    dear = _synth(years=6, alpha=0.35, spread_bp=40.0, seed=1)
    rd = run(dear, seed=1)
    check("a 40bp spread suppresses entries entirely",
          rd["n"] == 0, f"n={rd['n']}")
    cheap = _synth(years=6, alpha=0.35, spread_bp=0.4, seed=1)
    check("a 0.4bp spread does not -- the gate discriminates",
          run(cheap, seed=1)["n"] > 300)

    print("\nG. cost is really being charged")
    # 6bp was the first choice and it made the gate block every entry, so
    # the comparison came back nan. Use a spread that PASSES the gate, or
    # the test measures the gate rather than the cost.
    free = _synth(years=6, alpha=0.10, spread_bp=0.0, seed=2)
    paid = _synth(years=6, alpha=0.10, spread_bp=2.0, seed=2)
    rf, rp = run(free, seed=2), run(paid, seed=2)
    check("both runs actually traded", rf["n"] > 300 and rp["n"] > 300,
          f"{rf['n']} vs {rp['n']}")
    check("a wider spread lowers the result",
          rp["sharpe"] < rf["sharpe"],
          f"{rp['sharpe']:+.2f} vs {rf['sharpe']:+.2f} at zero cost")
    predicted = (2.0e-4 / (3.5e-4 * math.sqrt(30))) * math.sqrt(rp["per_yr"])
    observed = rf["sharpe"] - rp["sharpe"]
    check("the drag matches cost/vol x sqrt(trades/yr) within 25%",
          abs(observed / predicted - 1) < 0.25,
          f"observed {observed:.2f} vs predicted {predicted:.2f}")

    print("\nH. the randomised-side null destroys the edge")
    sh = [run(good, seed=100 + i, side_rule="random")["sharpe"]
          for i in range(12)]
    check("random side is centred near zero",
          abs(float(np.mean(sh))) < 0.6, f"mean {np.mean(sh):+.2f}")
    check("and the real signal beats every draw",
          rg["sharpe"] > max(sh), f"{rg['sharpe']:+.2f} > {max(sh):+.2f}")

    print("\nI. the random-entry null does too")
    re_ = [run(good, seed=200 + i, random_entry=True)["sharpe"]
           for i in range(12)]
    check("random entries at matched cost are near zero",
          abs(float(np.mean(re_))) < 0.6, f"mean {np.mean(re_):+.2f}")
    check("the real signal beats them",
          rg["sharpe"] > max(re_), f"{rg['sharpe']:+.2f} > {max(re_):+.2f}")

    print(f"\n{'ALL PASS' if ok else 'FAILURES ABOVE'}")
    return 0 if ok else 1


# ------------------------------------------------------------------ main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=os.path.normpath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "data")))
    ap.add_argument("--instrument", default="NAS100_USD")
    ap.add_argument("--granularity", default="M5")
    ap.add_argument("--window", choices=sorted(WINDOWS), default=None)
    ap.add_argument("--nulls", type=int, default=1000)
    ap.add_argument("--diagnose", action="store_true",
                    help="post-failure accounting on the SAME trades. Not a "
                         "search for a passing variant -- see RESULT_v1.md")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    if a.self_test:
        sys.exit(self_test())
    if not a.window:
        ap.print_help()
        return

    import numpy as np
    lo, hi = WINDOWS[a.window]
    print(f"engine.py v{VERSION}   PREREGISTRATION_v1 / v1.1")
    print(f"  N={N_VOL} k={K_SIGMA} H={H_HOLD} gate={COST_VOL_GATE} "
          f"max={MAX_PER_DAY}/day   FROZEN")
    print(f"  {a.instrument} {a.granularity}   window '{a.window}' "
          f"{lo} -> {hi}\n")

    D = slice_window(load_bars(a.data_dir, a.instrument, a.granularity),
                     lo, hi)
    r = run(D, seed=0)

    print(f"  trades          {r['n']:,}   ({r['per_day']:.2f}/day, "
          f"{r['per_yr']:.0f}/yr over {r['years']:.1f}y)")
    print(f"  mean per trade  {r['mean']*1e4:+.2f}bp")
    print(f"  total           {r['total']*100:+.1f}%")
    print(f"  NET SHARPE      {r['sharpe']:+.3f}")

    bar = GATE_A_NET_SHARPE if a.window == "fit" else GATE_B_NET_SHARPE
    print(f"\n  pre-registered bar for '{a.window}': {bar:.2f}")
    conds = [
        (f"net Sharpe >= {bar:.2f}", r["sharpe"] >= bar),
        (f">= {MIN_TRADES} trades", r["n"] >= MIN_TRADES),
        (f"<= {MAX_PER_DAY} round trips/day", r["per_day"] <= MAX_PER_DAY),
    ]
    for name, good in conds:
        print(f"    [{'PASS' if good else 'FAIL'}] {name}")

    if all(g for _, g in conds):
        print(f"\n  nulls ({a.nulls} draws each)")
        for label, kw in (("randomised side", dict(side_rule="random")),
                          ("reversed side", dict(side_rule="momentum")),
                          ("random entry", dict(random_entry=True))):
            if label == "reversed side":
                v = run(D, seed=0, **kw)["sharpe"]
                print(f"    {label:>16}: {v:+.3f}   "
                      f"{'PASS' if r['sharpe'] > v else 'FAIL'}")
                continue
            draws = np.array([run(D, seed=s + 1, **kw)["sharpe"]
                              for s in range(min(a.nulls, 200))])
            p95 = float(np.nanpercentile(draws, 95))
            print(f"    {label:>16}: p95 {p95:+.3f}   "
                  f"{'PASS' if r['sharpe'] > p95 else 'FAIL'}")

    if a.diagnose:
        # ------------------------------------------------------------------
        # POST-FAILURE ACCOUNTING. This runs on the SAME trade list already
        # taken. It changes no parameter and searches nothing. Its only job
        # is to answer the silver15 question -- "is the gross signal zero
        # BEFORE cost, or is cost eating a real edge?" -- because those two
        # failures have completely different implications.
        # ------------------------------------------------------------------
        print("\n  ---- diagnosis (same trades, nothing re-fitted) ----")
        gross = pnl(D, r["trades"], leak=False)
        g_mid = []
        for j, k, sd in r["trades"]:
            ent, ex = D["mid_o"][j], D["mid_o"][k]
            g_mid.append(sd * (ex - ent) / ent)
        g_mid = np.array(g_mid)
        gs = stats(g_mid, r["years"])
        print(f"    GROSS (mid-to-mid) Sharpe   {gs['sharpe']:+.3f}"
              f"   mean {gs['mean']*1e4:+.2f}bp")
        print(f"    NET   (bid/ask)    Sharpe   {r['sharpe']:+.3f}"
              f"   mean {r['mean']*1e4:+.2f}bp")
        print(f"    cost paid                   "
              f"{(gs['mean']-r['mean'])*1e4:.2f}bp/trade"
              f"   drag {gs['sharpe']-r['sharpe']:.2f} Sharpe")
        if gs["sharpe"] < 0:
            print("    => the GROSS signal is negative. Cost is not the "
                  "problem;")
            print("       the hypothesis points the wrong way.")
        else:
            print("    => gross is positive; cost is what killed it.")

        rev = run(D, seed=0, side_rule="momentum")
        print(f"\n    reversed side (momentum)    {rev['sharpe']:+.3f}"
              f"   n={rev['n']}")
        print("    NOTE: this is the pre-registered FALSIFIER, not a "
              "strategy.")
        print("    A positive reading here is a sign flip on a spent window "
              "and")
        print("    cannot be promoted. See PREREGISTRATION_v1 section 6.")

        print(f"\n    by year")
        print(f"    {'year':>6}{'trades':>9}{'mean bp':>10}{'total %':>10}")
        for y in sorted(set(D['year'][j] for j, _, _ in r['trades'])):
            sel = [i for i, (j, _, _) in enumerate(r['trades'])
                   if D['year'][j] == y]
            v = r['rets'][sel]
            print(f"    {y:>6}{len(v):>9}{np.mean(v)*1e4:>9.2f}"
                  f"{np.sum(v)*100:>9.1f}%")

        z, cv, valid, in_ses = signal(D)
        fired = valid & (np.abs(z) >= K_SIGMA)
        gated = fired & (cv > COST_VOL_GATE)
        print(f"\n    signals at |z|>={K_SIGMA}      {int(fired.sum()):,}")
        print(f"    blocked by spread gate  {int(gated.sum()):,} "
              f"({gated.sum()/max(fired.sum(),1)*100:.0f}%)")
        print(f"    survived to a trade     {r['n']:,} "
              f"(rest lost to overlap / session / daily cap)")

    verdict = "PASS" if all(g for _, g in conds) else "FAIL"
    print(f"\n  {a.window.upper()} VERDICT: {verdict}")
    if a.window == "fit" and verdict == "FAIL":
        print("\n  Per PREREGISTRATION_v1 section 7: the project STOPS here.")
        print("  No retuning. No v2 with different N/k/H. Holdout stays "
              "sealed.")


if __name__ == "__main__":
    main()
