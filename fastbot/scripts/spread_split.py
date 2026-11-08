#!/usr/bin/env python3
"""PREREGISTRATION_v3 — does the dealer's spread tell you which shocks revert?

v1 faded every 3-sigma bar and lost, sign-consistent across seven years, and
concluded "these are information, not inventory". That pools two populations
microstructure theory says behave differently:

    informed print    -> dealer widens hard and stays wide -> price CONTINUES
    inventory print   -> dealer widens briefly, then eases -> price REVERTS

The dealer knows which is which and says so, by how much they widen:

    q_t = spread_t / median(spread over bars t-20 .. t-1)

H1  among 3-sigma bars, LOW-q shocks revert MORE than HIGH-q shocks
H2  the low-q half, faded, is tradeable on its own

The PRIMARY statistic is the DIFFERENCE between the halves, not either level:
it holds constant the drift, cost regime and era effects both halves share.

Zero new free parameters. Shock threshold, vol window, hold, session and
limits are all inherited from PREREGISTRATION_v1 frozen. The split is at the
median precisely so there is no cutoff to tune.

NO spread gate -- see PREREGISTRATION_v3 section 4. Gating on cost/vol would
censor the high-q arm, which is the arm this test needs.

    python spread_split.py --self-test
    python spread_split.py --instruments SPX500_USD,US30_USD --window fit
"""

from __future__ import annotations

import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine as E                                   # noqa: E402

VERSION = "1.0"
Q_WINDOW = 20          # bars of trailing spread for the q baseline
GATE1_T = 2.0
GATE2_SHARPE = 0.76
MIN_PER_HALF = 200


def q_ratio(D):
    """Spread on bar t relative to the instrument's own recent normal.

    Uses bars t-20..t-1 only, shifted, so bar t's own spread never enters its
    own baseline. That shift is the entire causality surface of this file and
    is probed in the self-test.
    """
    import numpy as np, pandas as pd
    s = pd.Series(D["spread"])
    base = s.rolling(Q_WINDOW).median().shift(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        q = (s / base).to_numpy()
    return q


def shocks(D):
    """v1's entry list, unchanged, minus the spread gate. Returns (trades, q)."""
    import numpy as np
    z, cv, valid, in_ses = E.signal(D)
    q = q_ratio(D)
    ok = valid & np.isfinite(q) & (q > 0)

    n = len(z)
    fire = ok & (np.abs(z) >= E.K_SIGMA)
    out, busy, per_day = [], -1, {}
    for i in np.flatnonzero(fire):
        j, k = i + 1, i + 1 + E.H_HOLD
        if k >= n or j <= busy:
            continue
        if not (in_ses[j] and in_ses[k]):
            continue
        if D["day"][j] != D["day"][k]:
            continue
        d = D["day"][j]
        if per_day.get(d, 0) >= E.MAX_PER_DAY:
            continue
        out.append((j, k, -1 if z[i] > 0 else 1, float(q[i]), int(D["year"][i])))
        busy = k
        per_day[d] = per_day.get(d, 0) + 1
    return out


def evaluate(D, trades):
    """Net return per trade, and the q/year labels that go with it."""
    import numpy as np
    rets = E.pnl(D, [(j, k, sd) for j, k, sd, _, _ in trades])
    q = np.array([t[3] for t in trades])
    yr = np.array([t[4] for t in trades])
    return rets, q, yr


def welch(a, b):
    """t on the difference of two means, unequal variance."""
    import numpy as np
    if len(a) < 2 or len(b) < 2:
        return float("nan"), float("nan")
    diff = float(np.mean(a) - np.mean(b))
    se = math.sqrt(np.var(a, ddof=1) / len(a) + np.var(b, ddof=1) / len(b))
    return diff, (diff / se if se > 0 else float("nan"))


def split_at_median(rets, q, yr):
    import numpy as np
    cut = float(np.median(q))
    lo = q <= cut
    return cut, (rets[lo], yr[lo]), (rets[~lo], yr[~lo])


# ------------------------------------------------------------------ tests

def _synth(years=6, rev_lo=0.0, rev_hi=0.0, seed=0, q_random=False):
    """Session-shaped M5 bars where the SPREAD carries the information.

    Built in TWO passes, and the second pass is the point.

    Pass 1 plants shocks and their reversion. Pass 2 re-detects |z|>=3 on the
    finished path and assigns a spread to EVERY detected bar -- including bars
    the engine finds that were never planted.

    The one-pass version was wrong in a way that inverted the result. A 24-bar
    MAD is a noisy volatility estimate, so bars well inside the planted-shock
    size still reach |z|>=3 by themselves; roughly half of all trades were
    unplanted. Those carry a baseline spread, so q~1 put ALL of them in the
    LOW arm, loading it with cost-only trades while the high arm stayed pure.
    That flipped the sign of a correctly-detected effect. Assigning unplanted
    detections a random lo/hi spread makes them dilute both arms equally --
    which is also the more honest model, since real markets certainly contain
    shocks that do neither.
    """
    import numpy as np, pandas as pd

    rng = np.random.default_rng(seed)
    days = pd.bdate_range("2014-01-02", periods=int(252 * years), tz=E.TZ)
    parts = [pd.date_range(d + pd.Timedelta(hours=E.SESSION[0]),
                           d + pd.Timedelta(hours=E.SESSION[1]),
                           freq="5min", inclusive="left", tz=E.TZ)
             for d in days]
    t = parts[0].append(parts[1:])
    n = len(t)
    tu = t.tz_convert("UTC")
    consec = np.concatenate([[False],
                             np.diff(tu.to_numpy()) /
                             np.timedelta64(1, "s") == 300])

    sd = 3.5e-4 * math.sqrt(5)
    base_spread = 0.6e-4
    LOW, HIGH = 1.15, 3.0

    # ---- pass 1: plant shocks and reversion
    r = rng.normal(0, sd, n)
    planted = {}
    for idx in np.flatnonzero(rng.random(n) < 0.004):
        if idx + 1 + E.H_HOLD >= n or idx < Q_WINDOW + 2:
            continue
        lo = bool(rng.random() < 0.5)
        r[idx] += rng.choice([-1, 1]) * 4.5 * sd
        alpha = rev_lo if lo else rev_hi
        if alpha:
            r[idx + 1: idx + 1 + E.H_HOLD] -= alpha * r[idx] / E.H_HOLD
        planted[int(idx)] = lo

    mid_c = 10000 * np.exp(np.cumsum(r))
    mid_o = np.concatenate([[mid_c[0]], mid_c[:-1]])

    # ---- pass 2: give every DETECTED shock a spread, planted or not
    spread = np.full(n, base_spread) * rng.uniform(0.95, 1.05, n)
    probe = dict(mid_c=mid_c, spread=spread, consec=consec,
                 hour=t.hour.to_numpy())
    z, _, valid, _ = E.signal(probe)
    for idx in np.flatnonzero(valid & (np.abs(z) >= E.K_SIGMA)):
        lo = planted.get(int(idx), bool(rng.random() < 0.5))
        if q_random:
            lo = bool(rng.random() < 0.5)
        spread[idx] = base_spread * (LOW if lo else HIGH)

    half = mid_o * spread / 2
    return dict(
        t=tu, local=t, bid_o=mid_o - half, ask_o=mid_o + half,
        mid_c=mid_c, mid_o=mid_o, spread=spread, consec=consec,
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

    print(f"spread_split.py v{VERSION} self-test\n")
    print(f"inherited frozen: N={E.N_VOL} k={E.K_SIGMA} H={E.H_HOLD} "
          f"max={E.MAX_PER_DAY}/day   q window={Q_WINDOW}\n")

    print("A. q is computed causally")
    A = _synth(years=3, rev_lo=0.4, seed=5)
    B = {k: (v.copy() if hasattr(v, "copy") else v) for k, v in A.items()}
    M = len(B["spread"]) // 2
    B["spread"] = B["spread"].copy()
    # Must be a NON-uniform perturbation. q is spread / median(spread), so
    # multiplying the whole tail by a constant cancels top and bottom and
    # leaves q identical -- the first version of this control did that and
    # could not fail. That cancellation is a real and desirable property of
    # q (it is regime-neutral by construction, which is what lets one median
    # split span a window where the raw spread falls 3x), but it makes a
    # uniform scaling useless as a perturbation.
    rngB = np.random.default_rng(4242)
    B["spread"][M:] *= rngB.uniform(1.5, 9.0, len(B["spread"]) - M)
    qa, qb = q_ratio(A), q_ratio(B)
    check("rewriting the future leaves every past q unchanged",
          np.allclose(np.nan_to_num(qa[:M]), np.nan_to_num(qb[:M])))
    check("the future really changed -- the control can fail",
          not np.allclose(np.nan_to_num(qa[M + Q_WINDOW + 2:]),
                          np.nan_to_num(qb[M + Q_WINDOW + 2:])))
    check("a bar's own spread never enters its own baseline",
          abs(q_ratio({"spread": np.concatenate(
              [np.full(Q_WINDOW, 1e-4), [5e-4]])})[-1] - 5.0) < 1e-9)

    C2 = {k: (v.copy() if hasattr(v, "copy") else v) for k, v in A.items()}
    C2["spread"] = A["spread"] * 5.0
    check("q is regime-neutral: scaling ALL spreads leaves q unchanged",
          np.allclose(np.nan_to_num(q_ratio(A)), np.nan_to_num(q_ratio(C2))),
          "this is why one median split spans a 3x cost regime")

    print("\nB. it detects the planted mechanism")
    D = _synth(years=6, rev_lo=0.45, rev_hi=-0.45, seed=1)
    tr = shocks(D)
    rets, q, yr = evaluate(D, tr)
    cut, (rl, yl), (rh, yh) = split_at_median(rets, q, yr)
    diff, t = welch(rl, rh)
    qs = np.array([t[3] for t in tr])
    check("q is bimodal -- every detected shock got a spread assigned",
          float(((qs > 1.6) & (qs < 2.5)).mean()) < 0.05,
          f"{float(((qs>1.6)&(qs<2.5)).mean())*100:.1f}% between the modes")
    check("and the split is near 50/50, so neither arm is loaded",
          0.35 < float((qs <= 1.6).mean()) < 0.65,
          f"{float((qs<=1.6).mean())*100:.0f}% low-q")
    check("both halves are populated", len(rl) > 100 and len(rh) > 100,
          f"{len(rl)} vs {len(rh)}")
    check("the median split is balanced",
          abs(len(rl) - len(rh)) <= max(2, 0.1 * len(rets)),
          f"{len(rl)}/{len(rh)}")
    check("low-q reverts more than high-q, significantly",
          diff > 0 and t >= 3.0, f"diff {diff*1e4:+.2f}bp  t {t:+.2f}")

    print("\nC. it returns NOTHING when the spread carries no information")
    D0 = _synth(years=6, rev_lo=0.45, rev_hi=-0.45, seed=1, q_random=True)
    r0, q0, y0 = evaluate(D0, shocks(D0))
    _, (rl0, _), (rh0, _) = split_at_median(r0, q0, y0)
    d0, t0 = welch(rl0, rh0)
    check("an uninformative spread gives no difference -- gate fires",
          abs(t0) < 2.0, f"diff {d0*1e4:+.2f}bp  t {t0:+.2f}")
    check("and the informative case really was different",
          abs(t) > abs(t0) + 1.0, f"{t:+.2f} vs {t0:+.2f}")

    print("\nD. it detects the mechanism REVERSED")
    Dr = _synth(years=6, rev_lo=-0.45, rev_hi=0.45, seed=1)
    rr, qr, yr2 = evaluate(Dr, shocks(Dr))
    _, (rlr, _), (rhr, _) = split_at_median(rr, qr, yr2)
    dr, tr_ = welch(rlr, rhr)
    check("planting the opposite gives a NEGATIVE difference",
          dr < 0 and tr_ <= -3.0, f"diff {dr*1e4:+.2f}bp  t {tr_:+.2f}")

    print("\nE. no-effect control")
    Dn = _synth(years=6, rev_lo=0.0, rev_hi=0.0, seed=3)
    rn, qn, yn = evaluate(Dn, shocks(Dn))
    _, (rln, _), (rhn, _) = split_at_median(rn, qn, yn)
    dn, tn = welch(rln, rhn)
    check("no planted reversion anywhere -> no difference",
          abs(tn) < 2.0, f"diff {dn*1e4:+.2f}bp  t {tn:+.2f}")

    print("\nF. constraints still bind (inherited from v1)")
    js = [j for j, _, _, _, _ in tr]
    ks = [k for _, k, _, _, _ in tr]
    check("non-overlapping",
          all(js[i + 1] > ks[i] for i in range(len(tr) - 1)))
    check("hold is exactly H bars",
          all(k - j == E.H_HOLD for j, k, _, _, _ in tr))
    from collections import Counter
    pd_ = Counter(D["day"][j] for j, _, _, _, _ in tr)
    check(f"<= {E.MAX_PER_DAY} round trips/day", max(pd_.values()) <= E.MAX_PER_DAY)
    check("cost is charged -- gross beats net",
          float(np.mean([D["mid_o"][k] / D["mid_o"][j] - 1 for j, k, s, _, _
                         in tr if s > 0])) >
          float(np.mean([r for r, (_, _, s, _, _) in zip(rets, tr) if s > 0])))

    print(f"\n{'ALL PASS' if ok else 'FAILURES ABOVE'}")
    return 0 if ok else 1


# ------------------------------------------------------------------ main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=os.path.normpath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "data")))
    ap.add_argument("--instruments", default="SPX500_USD,US30_USD")
    ap.add_argument("--granularity", default="M5")
    ap.add_argument("--window", choices=sorted(E.WINDOWS), default="fit")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--diagnose", action="store_true",
                    help="did the splitter have any power? Measurement check "
                         "on the SAME bars -- re-specifies nothing.")
    a = ap.parse_args()

    if a.self_test:
        sys.exit(self_test())

    import numpy as np
    lo, hi = E.WINDOWS[a.window]
    print(f"spread_split.py v{VERSION}   PREREGISTRATION_v3")
    print(f"  inherited frozen: N={E.N_VOL} k={E.K_SIGMA} H={E.H_HOLD} "
          f"max={E.MAX_PER_DAY}/day   q window={Q_WINDOW}")
    print(f"  no spread gate (v3 section 4)   window '{a.window}' "
          f"{lo} -> {hi}\n")

    pooled_lo, pooled_hi, per_ins = [], [], {}
    for ins in [x.strip().upper() for x in a.instruments.split(",")]:
        D = E.slice_window(E.load_bars(a.data_dir, ins, a.granularity), lo, hi)
        tr = shocks(D)
        rets, q, yr = evaluate(D, tr)
        if len(rets) < 20:
            print(f"{ins}: only {len(rets)} trades -- skipped")
            continue
        cut, (rl, yl), (rh, yh) = split_at_median(rets, q, yr)
        diff, t = welch(rl, rh)
        years = (D["local"][-1] - D["local"][0]).days / 365.25
        sl = E.stats(rl, years)
        sh = E.stats(rh, years)
        per_ins[ins] = dict(diff=diff, t=t, cut=cut, n=len(rets),
                            lo=sl, hi=sh, rl=rl, rh=rh, yl=yl, yh=yh)
        print(f"{ins}   {len(rets):,} shocks, q split at {cut:.2f}")
        print(f"    {'':<10}{'n':>7}{'mean bp':>10}{'net Sharpe':>13}")
        print(f"    {'low q':<10}{len(rl):>7}{sl['mean']*1e4:>10.2f}"
              f"{sl['sharpe']:>13.3f}")
        print(f"    {'high q':<10}{len(rh):>7}{sh['mean']*1e4:>10.2f}"
              f"{sh['sharpe']:>13.3f}")
        print(f"    DIFFERENCE {diff*1e4:+.2f}bp   t {t:+.2f}\n")
        pooled_lo.append(rl)
        pooled_hi.append(rh)

    if len(per_ins) < 1:
        return
    PL, PH = np.concatenate(pooled_lo), np.concatenate(pooled_hi)
    pdiff, pt = welch(PL, PH)

    if a.diagnose:
        # ------------------------------------------------------------------
        # A NULL FROM A SPLITTER THAT DOES NOT SPLIT IS NOT EVIDENCE.
        #
        # Same class as "a gate never observed to fail has not been tested".
        # Before the Gate 1 rejection is read as "the mechanism is absent",
        # this asks whether the mechanism was OBSERVABLE at M5 at all:
        # does the dealer visibly widen on a 3-sigma bar on this feed?
        # Pre-declared in PREREGISTRATION_v3 section 8.
        # ------------------------------------------------------------------
        print("\n" + "=" * 66)
        print("MEASUREMENT DIAGNOSTIC -- could this test see anything?")
        for ins in per_ins:
            D = E.slice_window(E.load_bars(a.data_dir, ins, a.granularity),
                               lo, hi)
            qq = q_ratio(D)
            z, _, valid, in_ses = E.signal(D)
            sh = valid & (np.abs(z) >= E.K_SIGMA)
            nm = valid & (np.abs(z) < 1.0)
            qs = qq[sh & np.isfinite(qq)]
            print(f"\n  {ins}")
            print(f"    q at shock bars: "
                  + "  ".join(f"p{int(p*100)}={np.quantile(qs,p):.3f}"
                              for p in (0.05, 0.25, 0.5, 0.75, 0.95)))
            tie = float((np.abs(qs - 1.0) < 1e-9).mean())
            print(f"    exactly 1.000:   {tie*100:.1f}% of shock bars")
            print(f"    spread at shock  {np.median(D['spread'][sh])*1e4:.3f}bp"
                  f"   at quiet bars {np.median(D['spread'][nm])*1e4:.3f}bp"
                  f"   ratio {np.median(D['spread'][sh])/np.median(D['spread'][nm]):.3f}")
            uniq = np.unique(np.round(D["spread"][in_ses] * 1e6, 3))
            print(f"    distinct spread values in session: {len(uniq):,}")
            print(f"    bar-to-bar spread CV: "
                  f"{float(np.nanstd(D['spread'][in_ses])/np.nanmean(D['spread'][in_ses])):.3f}")
        print("\n  If the shock/quiet spread ratio is ~1.00 the dealer does "
              "not visibly")
        print("  widen at M5, and Gate 1 tested nothing. v3 s8 pre-declared "
              "M1 as the")
        print("  response -- a MEASUREMENT change, not a re-specification.")

    print("=" * 66)
    print(f"POOLED   low-q n={len(PL):,}  high-q n={len(PH):,}")
    print(f"  difference {pdiff*1e4:+.2f}bp per trade   t {pt:+.2f}")

    signs = []
    allyr = np.concatenate([per_ins[i]["yl"] for i in per_ins])
    allyr_h = np.concatenate([per_ins[i]["yh"] for i in per_ins])
    for y in sorted(set(allyr.tolist())):
        al, ah = PL[allyr == y], PH[allyr_h == y]
        if len(al) < 10 or len(ah) < 10:
            continue
        d, _ = welch(al, ah)
        signs.append(d > 0)
        print(f"    {y}  diff {d*1e4:+7.2f}bp   n {len(al):>4}/{len(ah):<4}")

    print("\nGATE 1 -- the mechanism")
    g1 = [
        (f"pooled t >= {GATE1_T}", pt >= GATE1_T),
        ("difference positive", pdiff > 0),
        ("sign agrees on both instruments",
         all(v["diff"] > 0 for v in per_ins.values()) and len(per_ins) >= 2),
        (f">= {MIN_PER_HALF} trades per half",
         len(PL) >= MIN_PER_HALF and len(PH) >= MIN_PER_HALF),
        (">= 5 of 7 years agree", sum(signs) >= 5),
    ]
    for name, good in g1:
        print(f"  [{'PASS' if good else 'FAIL'}] {name}")

    if all(g for _, g in g1):
        print("\nGATE 2 -- tradeability of the low-q half")
        yrs = 7.0
        s = E.stats(PL, yrs)
        good = s["sharpe"] >= GATE2_SHARPE
        print(f"  low-q net Sharpe {s['sharpe']:+.3f} vs {GATE2_SHARPE}")
        print(f"  [{'PASS' if good else 'FAIL'}] tradeable")
        if not good:
            print("\n  Mechanism real, not tradeable. Record it and STOP.")
            print("  This is the crypto-funding outcome (v3 section 6) and it")
            print("  must not be promoted by relaxing anything.")
    else:
        print("\nGATE 1 FAILED -> reject. No re-splitting on another quantile,")
        print("no other q window, no other H. See PREREGISTRATION_v3 s6.")


if __name__ == "__main__":
    main()
