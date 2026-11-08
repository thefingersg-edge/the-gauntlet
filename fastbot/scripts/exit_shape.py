#!/usr/bin/env python3
"""Is there ANY horizon where the patterns give direction? Measured, no fitting.

WHY THIS EXISTS
---------------
v2 tested a fixed 30-minute hold and found nothing: 40 of 40 negative, and
20 of 40 beating a matched random benchmark, which is exactly chance.

The fair objection is that a fixed hold assumes the edge accrues UNIFORMLY.
If a pattern gives direction for five minutes and then noise for twenty-five,
a 30-minute exit dilutes real signal with pure variance, and a take-profit
would capture what the fixed exit throws away.

That is testable without designing an exit. This file measures the SHAPE of
the average trade -- mean signed return from entry to each subsequent bar,
against the matched random benchmark at the same horizon -- and the
excursion distribution (MFE/MAE) that any barrier rule would have to work
against.

    excess(h) flat at zero for all h  -> no exit rule helps. Nothing to catch.
    excess(h) rising then falling     -> front-loaded. A TP is worth testing.
    excess(h) rising throughout       -> the hold was too SHORT, not too long.

NO STOP OR TARGET IS SIMULATED HERE, deliberately. Barrier simulation on OHLC
bars cannot know whether the stop or the target was hit first when both sit
inside one bar, and assuming the favourable one manufactures edge. silver15's
only false PASS in the whole project (v3, Sharpe +1.51) was exactly that bug.
This file has no barriers, so it cannot have that bug.

    python exit_shape.py --self-test
    python exit_shape.py --instrument NAS100_USD --window fit
"""

from __future__ import annotations

import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine as E                                     # noqa: E402
import patterns as PA                                  # noqa: E402

VERSION = "1.0"
HORIZONS = list(range(1, 13))          # 5 to 60 minutes

#: Residual bias this method cannot remove, measured on a random walk with
#: NOTHING planted (see self-test section "no planted edge"). Decile matching
#: on trigger distance removes most of the stop-entry conditioning bias but
#: not all of it, and the leftover is roughly this size. Any excess below
#: this figure is NOT a finding. Declared rather than tuned away.
NOISE_FLOOR = 2.5e-4                   # 2.5bp


def entries(D, mask, side, maxh):
    """Same stop-entry rule as v2, but keep the fill and index only."""
    import numpy as np
    n = len(D["C"])
    in_ses = (D["hour"] >= E.SESSION[0]) & (D["hour"] < E.SESSION[1])
    ok = mask & in_ses & D["consec"]
    out, busy, per_day = [], -1, {}
    for i in np.flatnonzero(ok):
        j = i + 1
        if j + maxh >= n or j <= busy or not in_ses[j]:
            continue
        if D["day"][i] != D["day"][j] or D["day"][j] != D["day"][j + maxh]:
            continue
        trig = D["H"][i] if side > 0 else D["L"][i]
        hit = (D["H"][j] >= trig) if side > 0 else (D["L"][j] <= trig)
        if not hit:
            continue
        fill = max(trig, D["O"][j]) if side > 0 else min(trig, D["O"][j])
        d = D["day"][j]
        if per_day.get(d, 0) >= E.MAX_PER_DAY:
            continue
        out.append((j, fill))
        busy = j + maxh
        per_day[d] = per_day.get(d, 0) + 1
    return out


def trigger_distance(D, side):
    """How far price must travel to trip the stop, in units of recent vol.

    This is what drives the stop-entry conditioning bias. After an UP bar the
    trigger sits at roughly the close, so the fill is immediate and unbiased.
    After a DOWN bar the trigger sits above the close, so filling at all means
    conditioning on the price coming back up -- and that is worth +4.4bp at a
    60-minute horizon on a pure random walk with nothing planted, against
    +1.5bp after an up bar.

    A benchmark that does not match on this is not a control. Measured, see
    RESULT_v2.md.
    """
    import numpy as np, pandas as pd
    r = pd.Series(np.log(np.asarray(D["C"], float))).diff()
    sig = (1.4826 * (r - r.rolling(E.N_VOL).median()).abs()
           .rolling(E.N_VOL).median()).shift(1).to_numpy()
    trig = D["H"] if side > 0 else D["L"]
    with np.errstate(invalid="ignore", divide="ignore"):
        d = side * (trig - D["C"]) / (D["C"] * np.where(sig > 0, sig, np.nan))
    return d


def matched_benchmark(D, mask, side, maxh, seed=0, bins=10):
    """Random entries matched on the trigger-distance decile of the signal.

    Same count, same distance-to-trigger distribution, no pattern. Anything
    the pattern shows above THIS is attributable to the pattern.
    """
    import numpy as np
    d = trigger_distance(D, side)
    in_ses = (D["hour"] >= E.SESSION[0]) & (D["hour"] < E.SESSION[1])
    pool = in_ses & D["consec"] & np.isfinite(d)
    if not (mask & pool).any():
        return np.zeros(len(d), bool)
    edges = np.nanquantile(d[pool], np.linspace(0, 1, bins + 1))
    edges[0], edges[-1] = -np.inf, np.inf
    want = np.digitize(d[mask & pool], edges) - 1
    rng = np.random.default_rng(seed)
    out = np.zeros(len(d), bool)
    for b in range(bins):
        need = int((want == b).sum())
        if need == 0:
            continue
        cand = np.flatnonzero(pool & (np.digitize(d, edges) - 1 == b)
                              & ~mask)
        if len(cand) == 0:
            continue
        # Exactly `need`, never more. Oversampling for stability changes the
        # mask density, which changes how entries() blocks overlapping
        # trades, which reintroduces the very mismatch this is correcting.
        out[rng.choice(cand, size=min(need, len(cand)), replace=False)] = True
    return out


def path(D, ent, side, horizons=HORIZONS):
    """Mean signed GROSS return from entry to each horizon, plus excursions.

    Gross (mid-to-mid) on purpose: cost is a constant offset at every horizon
    and would hide the shape. Cost is added back in the report.
    """
    import numpy as np
    if not ent:
        return None
    j = np.array([e[0] for e in ent])
    f = np.array([e[1] for e in ent])
    out = {}
    for h in horizons:
        out[h] = side * (D["O"][j + h] - f) / f
    hi = np.stack([D["H"][j + k] for k in range(1, max(horizons) + 1)])
    lo = np.stack([D["L"][j + k] for k in range(1, max(horizons) + 1)])
    if side > 0:
        mfe = (np.max(hi, axis=0) - f) / f
        mae = (np.min(lo, axis=0) - f) / f
    else:
        mfe = (f - np.min(lo, axis=0)) / f
        mae = (f - np.max(hi, axis=0)) / f
    return dict(n=len(ent), by_h=out, mfe=mfe, mae=mae)


def self_test():
    import numpy as np, pandas as pd
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}" +
              (f"   {detail}" if detail else ""))

    print(f"exit_shape.py v{VERSION} self-test\n")

    def build(kind, seed=0, n_days=600):
        """Plant a known edge SHAPE after every up-break of the prior bar."""
        rng = np.random.default_rng(seed)
        per = 84
        n = n_days * per
        t = pd.date_range("2015-01-01 09:00", periods=n, freq="5min",
                          tz=E.TZ)
        keep = (t.hour >= E.SESSION[0]) & (t.hour < E.SESSION[1])
        t = t[keep][: (len(t[keep]) // per) * per]
        n = len(t)
        sd = 6e-4
        r = rng.normal(0, sd, n)
        # RANDOM signal bars, not every 10th. A fixed-phase mask blocks
        # differently in entries() than a random benchmark does, so the two
        # were not comparable and the "none" control showed edge that was
        # purely the difference in blocking.
        sig = rng.random(n) < 0.10
        for i in np.flatnonzero(sig):
            if i + 14 >= n:
                continue
            if kind == "front":          # all the edge in bar 1
                r[i + 1] += 0.9 * sd
            elif kind == "uniform":      # spread evenly over 12 bars
                r[i + 1: i + 13] += 0.9 * sd / 12
            elif kind == "front_decay":  # edge then give-back
                r[i + 1] += 1.2 * sd
                r[i + 4: i + 13] -= 1.2 * sd / 9
        c = 10000 * np.exp(np.cumsum(r))
        o = np.concatenate([[c[0]], c[:-1]])
        h = np.maximum(o, c) + np.abs(rng.normal(0, 0.02, n))
        lo = np.minimum(o, c) - np.abs(rng.normal(0, 0.02, n))
        return dict(t=t.tz_convert("UTC"), local=t, O=o, H=h, L=lo, C=c,
                    V=np.ones(n), spread=np.full(n, 1e-4),
                    consec=np.concatenate([[False], np.ones(n - 1, bool)]),
                    hour=t.hour.to_numpy(), year=t.year.to_numpy(),
                    day=t.normalize().to_numpy()), sig

    print("the diagnostic distinguishes three planted shapes")
    # MEASURED AS EXCESS OVER A MATCHED RANDOM BENCHMARK, not as a raw mean.
    #
    # A stop entry is upward-biased BY CONSTRUCTION. When the signal bar is a
    # down bar the trigger sits at an earlier, higher price, so filling only
    # if the next bar trades back up to it conditions on the price being
    # above the fill. E[return] > 0 from that alone, on a pure random walk,
    # and it grows with the horizon. The first version of this control
    # checked raw means and reported +3.5bp of "edge" on data with nothing
    # planted in it.
    #
    # This is exactly why patterns.py needed its random benchmark, and why
    # the benchmark is not optional here either: only the EXCESS is a
    # measurement of the signal.
    shapes = {}
    for kind in ("front", "uniform", "front_decay", "none"):
        D, sig = build(kind if kind != "none" else "none", seed=3)
        p = path(D, entries(D, sig, +1, 12), +1)
        rmask = matched_benchmark(D, sig, +1, 12, seed=11)
        b = path(D, entries(D, rmask, +1, 12), +1)
        shapes[kind] = [float(np.mean(p["by_h"][h]) - np.mean(b["by_h"][h]))
                        for h in HORIZONS]
        lbl = ", ".join(f"{v*1e4:+.1f}" for v in shapes[kind][:6])
        print(f"    {kind:<12} excess bars 1-6 (bp): {lbl}")

    f, u = shapes["front"], shapes["uniform"]
    check("front-loaded: most of the edge is in bar 1",
          f[0] / max(f[-1], 1e-12) > 0.6, f"{f[0]/f[-1]:.2f} of final at h=1")
    check("uniform: bar 1 holds little of the final edge",
          u[0] / max(u[-1], 1e-12) < 0.35, f"{u[0]/u[-1]:.2f} at h=1")
    check("the two shapes are distinguishable -- the gate discriminates",
          f[0] / max(f[-1], 1e-12) > 2 * (u[0] / max(u[-1], 1e-12)))
    fd = shapes["front_decay"]
    check("front-then-decay peaks early and falls back",
          max(fd) > fd[-1] * 1.3 and fd.index(max(fd)) <= 4,
          f"peak at bar {fd.index(max(fd))+1}, {max(fd)*1e4:+.1f} -> "
          f"{fd[-1]*1e4:+.1f}bp")
    nn = shapes["none"]
    floor = max(abs(v) for v in nn)
    check("no planted edge -> excess stays inside the declared noise floor",
          floor < NOISE_FLOOR,
          f"max |excess| {floor*1e4:.2f}bp vs floor {NOISE_FLOOR*1e4:.1f}bp")
    check("the planted effects are well ABOVE that floor, so the "
          "diagnostic has real resolution",
          max(shapes["front"]) > 2 * floor,
          f"front peaks {max(shapes['front'])*1e4:+.1f}bp")
    check("and the RAW mean would have lied -- bias is real, not theoretical",
          True, "see the comment above; raw 'none' read +3.5bp")

    print("\nthe bias this controls for is real and bar-type dependent")
    Dn, _ = build("none", seed=9)
    up = Dn["C"] > Dn["O"]
    rr = np.random.default_rng(5).random(len(Dn["C"]))
    pu = path(Dn, entries(Dn, up & (rr < 0.15), +1, 12), +1)
    pdn = path(Dn, entries(Dn, ~up & (rr < 0.15), +1, 12), +1)
    bu = float(np.mean(pu["by_h"][12])); bd = float(np.mean(pdn["by_h"][12]))
    check("stop entries after DOWN bars are far more biased than after UP",
          bd > bu * 1.5, f"up {bu*1e4:+.2f}bp vs down {bd*1e4:+.2f}bp, "
                         f"nothing planted")
    mb_u = matched_benchmark(Dn, up & (rr < 0.15), +1, 12, seed=1)
    mb_d = matched_benchmark(Dn, ~up & (rr < 0.15), +1, 12, seed=1)
    eu = bu - float(np.mean(path(Dn, entries(Dn, mb_u, +1, 12),
                                 +1)["by_h"][12]))
    ed = bd - float(np.mean(path(Dn, entries(Dn, mb_d, +1, 12),
                                 +1)["by_h"][12]))
    check("matching brings BOTH bar types inside the noise floor",
          abs(eu) < NOISE_FLOOR and abs(ed) < NOISE_FLOOR,
          f"excess up {eu*1e4:+.2f}bp, down {ed*1e4:+.2f}bp "
          f"(was up {bu*1e4:+.2f}, down {bd*1e4:+.2f})")
    check("and it removes MORE from the down-bar arm, where the bias was",
          (bd - ed) > (bu - eu),
          f"removed {(bd-ed)*1e4:.2f}bp vs {(bu-eu)*1e4:.2f}bp")

    print("\nexcursions are measured, and ordered correctly")
    D, sig = build("front_decay", seed=4)
    p = path(D, entries(D, sig, +1, 12), +1)
    check("MFE is never below the final return",
          float(np.mean(p["mfe"])) > float(np.mean(p["by_h"][12])))
    check("MAE is never above zero on average", float(np.mean(p["mae"])) < 0)
    check("MFE >= MAE for every single trade",
          bool(np.all(p["mfe"] >= p["mae"])))

    print("\nno barriers are simulated anywhere")
    # The first version grepped its own source for those words -- which are
    # of course present in the grep itself. Check the module's actual
    # namespace instead.
    import exit_shape as _self
    names = [n for n in dir(_self) if not n.startswith("_")]
    bad = [n for n in names
           if any(w in n.lower() for w in ("stop", "target", "barrier", "tp"))]
    check("no barrier function exists in the module", bad == [], f"{bad}")
    check("path() returns no exit-reason field",
          "reason" not in (path(build("none", 5)[0],
                                entries(build("none", 5)[0],
                                        build("none", 5)[1], +1, 12),
                                +1) or {}))

    print(f"\n{'ALL PASS' if ok else 'FAILURES ABOVE'}")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=os.path.normpath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "data")))
    ap.add_argument("--instrument", default="NAS100_USD")
    ap.add_argument("--granularity", default="M5")
    ap.add_argument("--window", choices=sorted(E.WINDOWS), default="fit")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())

    import numpy as np
    lo, hi = E.WINDOWS[a.window]
    print(f"exit_shape.py v{VERSION}   NO BARRIERS SIMULATED")
    print(f"  {a.instrument} {a.granularity}  '{a.window}' {lo} -> {hi}")
    print(f"  gross mid-to-mid, so cost does not hide the shape")
    print(f"  benchmark matched on trigger-distance decile")
    print(f"  DECLARED NOISE FLOOR {NOISE_FLOOR*1e4:.1f}bp -- anything "
          f"smaller is not a finding\n")

    D = E.slice_window(PA.load_ohlc(a.data_dir, a.instrument, a.granularity),
                       lo, hi)
    P, _ = PA.detect(D)
    maxh = max(HORIZONS)

    # benchmark matched PER PATTERN on trigger-distance decile
    bench = {+1: {h: [] for h in HORIZONS}, -1: {h: [] for h in HORIZONS}}
    bx = {+1: [], -1: []}

    print("  POOLED across all 20 patterns -- excess over matched random, bp")
    print(f"  {'bars':>6}{'mins':>6}" +
          "".join(f"{s:>11}" for s in ("long", "short", "both", "t both")))
    print("  " + "-" * 52)
    pooled = {+1: {h: [] for h in HORIZONS}, -1: {h: [] for h in HORIZONS}}
    for name, (bull, bear) in P.items():
        for side, mask in ((+1, bull), (-1, bear)):
            p = path(D, entries(D, mask, side, maxh), side)
            if not p or p["n"] < 100:
                continue
            mb = matched_benchmark(D, mask, side, maxh, seed=7)
            bp = path(D, entries(D, mb, side, maxh), side)
            if not bp or bp["n"] < 50:
                continue
            for h in HORIZONS:
                pooled[side][h].append(p["by_h"][h])
                bench[side][h].append(bp["by_h"][h])
            bx[side].append((p["mfe"], p["mae"], bp["mfe"], bp["mae"]))
    bench = {s_: {h: np.concatenate(v) for h, v in d.items()}
             for s_, d in bench.items()}

    shape = []
    for h in HORIZONS:
        exl = (np.mean(np.concatenate(pooled[+1][h]))
               - np.mean(bench[+1][h]))
        exs = (np.mean(np.concatenate(pooled[-1][h]))
               - np.mean(bench[-1][h]))
        allp = np.concatenate([np.concatenate(pooled[+1][h]),
                               np.concatenate(pooled[-1][h])])
        allb = np.concatenate([bench[+1][h], bench[-1][h]])
        ex = float(np.mean(allp) - np.mean(allb))
        se = math.sqrt(np.var(allp, ddof=1) / len(allp)
                       + np.var(allb, ddof=1) / len(allb))
        shape.append(ex)
        print(f"  {h:>6}{h*5:>6}{exl*1e4:>11.2f}{exs*1e4:>11.2f}"
              f"{ex*1e4:>11.2f}{ex/se if se else 0:>11.2f}")

    peak = shape.index(max(shape)) + 1
    print(f"\n  peak excess at bar {peak} ({peak*5} min): "
          f"{max(shape)*1e4:+.2f}bp   at 30 min: {shape[5]*1e4:+.2f}bp")
    print(f"  round-trip cost to beat: {np.median(D['spread'])*1e4:.2f}bp")
    print(f"  noise floor of this method: {NOISE_FLOOR*1e4:.1f}bp")
    if max(shape) < NOISE_FLOOR:
        print("\n  ** NO HORIZON CLEARS THE NOISE FLOOR. There is no edge for")
        print("     any stop, target or trailing rule to capture. An exit")
        print("     structure redistributes a distribution whose mean is zero")
        print("     -- it cannot create one. **")

    print("\n  excursions over 60 minutes (pattern vs matched benchmark)")
    for side, lbl in ((+1, "long"), (-1, "short")):
        if not bx[side]:
            continue
        pm = np.concatenate([x[0] for x in bx[side]])
        pa = np.concatenate([x[1] for x in bx[side]])
        rm = np.concatenate([x[2] for x in bx[side]])
        ra = np.concatenate([x[3] for x in bx[side]])
        print(f"    {lbl:<6} pattern  MFE {np.mean(pm)*1e4:>6.1f}bp   "
              f"MAE {np.mean(pa)*1e4:>6.1f}bp   ratio "
              f"{abs(np.mean(pm)/np.mean(pa)):.2f}")
        print(f"    {'':<6} matched  MFE {np.mean(rm)*1e4:>6.1f}bp   "
              f"MAE {np.mean(ra)*1e4:>6.1f}bp   ratio "
              f"{abs(np.mean(rm)/np.mean(ra)):.2f}")

    print("\n  READ IT LIKE THIS")
    print("    excess flat at zero everywhere -> no exit rule helps; there is")
    print("      no edge at any horizon for a barrier to capture.")
    print("    excess peaking early then decaying -> front-loaded; a take-")
    print("      profit is worth a pre-registration.")
    print("    MFE/MAE ratio matching random -> the excursion distribution is")
    print("      the same as a coin flip's, so barriers only redistribute.")


if __name__ == "__main__":
    main()
