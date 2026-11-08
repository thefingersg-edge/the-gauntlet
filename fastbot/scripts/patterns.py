#!/usr/bin/env python3
"""PREREGISTRATION_v2 — the twenty bar patterns, forty tests, one screen.

Externally sourced and fully specified before any of it touched this data.
Every threshold is frozen in PREREGISTRATION_v2 section 3 and none is swept.

    ENTRY  stop at the pattern bar's high (long) / low (short), next bar only
    FILL   only if that bar trades through. price = max(trigger, open) for a
           long -- a gap through the trigger fills at the OPEN, never the
           better of the two
    EXIT   open of the bar H=6 later, same as v1
    COST   the actual measured spread on the actual bar
    LIMITS non-overlapping per pattern, <= 4 round trips/day, in-session only

The screen is a filter, not a verdict: 40 tests at an uncorrected 2-sigma bar
produce ~0.9 false positives by chance. Advancing patterns must confirm on
instruments never used. See PREREGISTRATION_v2 section 5.

    python patterns.py --self-test
    python patterns.py --instrument NAS100_USD --window fit
"""

from __future__ import annotations

import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine as E                                    # noqa: E402

VERSION = "1.0"
SCREEN_SHARPE = 0.76
MIN_TRADES = 200
MIN_YEAR_SIGN = 6


# ------------------------------------------------------------------ data

def load_ohlc(data_dir, instrument, gran="M5"):
    """Full mid OHLC plus the bid/ask opens fills are priced from."""
    import numpy as np, pandas as pd
    stem = instrument.replace("_", "").lower()
    suf = {"M1": "1m", "M5": "5m", "M15": "15m"}[gran]
    step = {"M1": 60, "M5": 300, "M15": 900}[gran]

    F = {}
    for side in ("bid", "ask"):
        p = os.path.join(data_dir, f"{stem}_{side}_{suf}.csv")
        if not os.path.exists(p):
            raise SystemExit(f"missing {os.path.basename(p)}")
        d = pd.read_csv(p)
        d.columns = ["t", "open", "high", "low", "close", "volume"]
        d["t"] = pd.to_datetime(d["t"], utc=True)
        F[side] = d.drop_duplicates("t").set_index("t")

    idx = F["bid"].index.intersection(F["ask"].index).sort_values()
    b, a = F["bid"].loc[idx], F["ask"].loc[idx]
    m = {k: (b[k].to_numpy(float) + a[k].to_numpy(float)) / 2
         for k in ("open", "high", "low", "close")}
    local = idx.tz_convert(E.TZ)
    dt = np.diff(idx.to_numpy()) / np.timedelta64(1, "s")
    return dict(
        t=idx, local=local, O=m["open"], H=m["high"], L=m["low"],
        C=m["close"], V=b["volume"].to_numpy(float),
        spread=(a["close"].to_numpy(float) - b["close"].to_numpy(float))
        / m["close"],
        consec=np.concatenate([[False], dt == step]),
        hour=local.hour.to_numpy(), year=local.year.to_numpy(),
        day=local.normalize().to_numpy())


# ------------------------------------------------------------------ patterns

def detect(D):
    """Every pattern, as a dict of name -> (bull_mask, bear_mask).

    Bidirectional patterns return the SAME mask twice; the direction then
    comes from which side of the bar breaks first, handled in `trades()`.
    All thresholds are frozen by PREREGISTRATION_v2 section 3.
    """
    import numpy as np, pandas as pd
    O, H, L, C, V = D["O"], D["H"], D["L"], D["C"], D["V"]
    rng = H - L
    body = np.abs(C - O)
    up, dn = C > O, C < O

    def sh(x, k):
        return np.concatenate([np.full(k, np.nan), x[:-k].astype(float)])

    def shb(x, k):
        return np.concatenate([np.zeros(k, bool), x[:-k]])

    r1 = np.maximum(sh(rng, 1), 1e-12)
    vmed = pd.Series(V).rolling(20).median().shift(1).to_numpy()
    rmed = pd.Series(rng).rolling(20).median().shift(1).to_numpy()
    nr7 = rng <= pd.Series(rng).rolling(7).min().to_numpy()

    P = {}
    P["reversal_bar"] = ((L < sh(L, 1)) & (C > sh(C, 1)),
                         (H > sh(H, 1)) & (C < sh(C, 1)))
    P["key_reversal"] = ((O < sh(L, 1)) & (C > sh(H, 1)),
                         (O > sh(H, 1)) & (C < sh(L, 1)))
    P["exhaustion"] = (
        (O < sh(L, 1)) & (H < sh(L, 1)) & (C >= L + 0.75 * rng) & (V > vmed),
        (O > sh(H, 1)) & (L > sh(H, 1)) & (C <= L + 0.25 * rng) & (V > vmed))
    P["pin_bar"] = ((np.minimum(O, C) - L >= 0.66 * rng) & (rng > 0),
                    (H - np.maximum(O, C) >= 0.66 * rng) & (rng > 0))
    P["two_bar_rev"] = (
        (sh(C, 1) <= sh(L, 1) + 0.33 * r1) & (C >= L + 0.67 * rng),
        (sh(C, 1) >= sh(L, 1) + 0.67 * r1) & (C <= L + 0.33 * rng))
    P["three_bar_rev"] = (
        shb(dn, 2) & (sh(H, 1) < sh(H, 2)) & (sh(L, 1) < sh(L, 2))
        & (L > sh(L, 1)) & (C > sh(H, 1)),
        shb(up, 2) & (sh(H, 1) > sh(H, 2)) & (sh(L, 1) > sh(L, 2))
        & (H < sh(H, 1)) & (C < sh(L, 1)))
    P["three_bar_pull"] = (
        shb(dn, 3) & shb(dn, 2) & shb(dn, 1) & up,
        shb(up, 3) & shb(up, 2) & shb(up, 1) & dn)
    inside = (H < sh(H, 1)) & (L > sh(L, 1))
    P["inside_bar"] = (inside, inside)
    outside = (H > sh(H, 1)) & (L < sh(L, 1))
    P["outside_bar"] = (outside, outside)
    P["nr7"] = (nr7, nr7)
    P["engulfing"] = (
        shb(dn, 1) & up & (O <= sh(C, 1)) & (C >= sh(O, 1)),
        shb(up, 1) & dn & (O >= sh(C, 1)) & (C <= sh(O, 1)))
    b1 = np.maximum(sh(body, 1), 1e-12)
    P["harami"] = (
        shb(dn, 1) & (body < 0.5 * b1) & (np.maximum(O, C) <= sh(O, 1))
        & (np.minimum(O, C) >= sh(C, 1)),
        shb(up, 1) & (body < 0.5 * b1) & (np.maximum(O, C) <= sh(C, 1))
        & (np.minimum(O, C) >= sh(O, 1)))
    P["hammer"] = (
        (np.minimum(O, C) - L >= 2 * body) & (H - np.maximum(O, C)
                                              <= 0.25 * rng) & (rng > 0),
        (H - np.maximum(O, C) >= 2 * body) & (np.minimum(O, C) - L
                                              <= 0.25 * rng) & (rng > 0))
    P["marubozu"] = ((body >= 0.9 * rng) & up & (rng > 0),
                     (body >= 0.9 * rng) & dn & (rng > 0))
    doji = (body <= 0.1 * rng) & (rng > 0)
    P["doji"] = (doji, doji)
    P["morning_star"] = (
        shb(dn, 2) & (sh(body, 1) <= 0.3 * sh(body, 2)) & up
        & (C >= sh(O, 2) - 0.5 * sh(body, 2)),
        shb(up, 2) & (sh(body, 1) <= 0.3 * sh(body, 2)) & dn
        & (C <= sh(O, 2) + 0.5 * sh(body, 2)))
    P["three_soldiers"] = (
        shb(up, 2) & shb(up, 1) & up & (C > sh(C, 1)) & (sh(C, 1) > sh(C, 2))
        & (O > sh(O, 1)) & (O < sh(C, 1)),
        shb(dn, 2) & shb(dn, 1) & dn & (C < sh(C, 1)) & (sh(C, 1) < sh(C, 2))
        & (O < sh(O, 1)) & (O > sh(C, 1)))
    wide = (rng >= 2 * rmed)
    P["wide_range"] = (wide & (C >= L + 0.5 * rng), wide & (C <= L + 0.5 * rng))
    P["gap_bar"] = ((O > sh(H, 1)), (O < sh(L, 1)))
    first = D["hour"] == E.SESSION[0]
    firstbar = first & ~shb(first, 1)
    P["opening_range"] = (firstbar, firstbar)

    BIDIRECTIONAL = {"inside_bar", "outside_bar", "nr7", "doji",
                     "wide_range", "gap_bar", "opening_range"}
    for k in P:
        P[k] = (np.nan_to_num(P[k][0], nan=0).astype(bool),
                np.nan_to_num(P[k][1], nan=0).astype(bool))
    return P, BIDIRECTIONAL


# ------------------------------------------------------------------ engine

def trades(D, mask, side):
    """Stop entry on the bar after the pattern. side +1 long, -1 short."""
    import numpy as np
    n = len(D["C"])
    in_ses = (D["hour"] >= E.SESSION[0]) & (D["hour"] < E.SESSION[1])
    ok = mask & in_ses & D["consec"]

    out, busy, per_day = [], -1, {}
    for i in np.flatnonzero(ok):
        j, k = i + 1, i + 1 + E.H_HOLD
        if k >= n or j <= busy or not (in_ses[j] and in_ses[k]):
            continue
        if D["day"][j] != D["day"][k] or D["day"][i] != D["day"][j]:
            continue
        trig = D["H"][i] if side > 0 else D["L"][i]
        hit = (D["H"][j] >= trig) if side > 0 else (D["L"][j] <= trig)
        if not hit:
            continue
        # a gap through the trigger fills at the OPEN, never the better price
        fill = max(trig, D["O"][j]) if side > 0 else min(trig, D["O"][j])
        d = D["day"][j]
        if per_day.get(d, 0) >= E.MAX_PER_DAY:
            continue
        out.append((j, k, side, fill))
        busy = k
        per_day[d] = per_day.get(d, 0) + 1
    return out


def pnl(D, tr):
    import numpy as np
    if not tr:
        return np.array([]), np.array([])
    r, yr = [], []
    for j, k, sd, fill in tr:
        ent = fill * (1 + sd * D["spread"][j] / 2)
        ex = D["O"][k] * (1 - sd * D["spread"][k] / 2)
        r.append(sd * (ex - ent) / ent)
        yr.append(D["year"][j])
    return np.array(r), np.array(yr)


def screen(D, label=""):
    import numpy as np
    P, BI = detect(D)
    years = (D["local"][-1] - D["local"][0]).days / 365.25
    rows = []
    for name, (bull, bear) in P.items():
        for dirn, mask in ((+1, bull), (-1, bear)):
            tr = trades(D, mask, dirn)
            r, yr = pnl(D, tr)
            if len(r) < 2:
                continue
            st = E.stats(r, years)
            sign = []
            for y in sorted(set(yr.tolist())):
                v = r[yr == y]
                if len(v) >= 5:
                    sign.append(np.mean(v) > 0)
            agree = max(sum(sign), len(sign) - sum(sign)) if sign else 0
            rows.append(dict(
                name=name, dir="long" if dirn > 0 else "short",
                n=len(r), per_day=len(r) / max(years * 252, 1),
                mean=st["mean"], sharpe=st["sharpe"],
                agree=agree, of=len(sign), bi=name in BI))
    rows.sort(key=lambda x: -(x["sharpe"] if x["sharpe"] == x["sharpe"]
                              else -9))
    return rows


# ------------------------------------------------------------------ tests

def _bars(seq):
    """Build a D from a list of (o,h,l,c,v) inside one session."""
    import numpy as np, pandas as pd
    n = len(seq)
    t = pd.date_range("2019-03-04 09:00", periods=n, freq="5min", tz=E.TZ)
    a = np.array(seq, float)
    return dict(
        t=t.tz_convert("UTC"), local=t,
        O=a[:, 0], H=a[:, 1], L=a[:, 2], C=a[:, 3], V=a[:, 4],
        spread=np.full(n, 1e-4), consec=np.concatenate([[False],
                                                        np.ones(n - 1, bool)]),
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

    print(f"patterns.py v{VERSION} self-test\n")

    # (o, h, l, c, v). Each case: a sequence that MUST fire the named
    # pattern on its last bar, and one that must NOT.
    base = (100, 101, 99, 100, 100)
    CASES = {
        "reversal_bar": ([base, (100, 101, 98, 100.5, 100)],
                         [base, (100, 101, 99.5, 99, 100)]),
        "key_reversal": ([base, (98.5, 102, 98, 101.5, 100)],
                         [base, (99.5, 101, 99, 100.5, 100)]),
        "pin_bar":      ([base, (100, 100.2, 97, 100, 100)],
                         [base, (100, 101, 99, 100, 100)]),
        "inside_bar":   ([base, (100, 100.5, 99.5, 100, 100)],
                         [base, (100, 102, 98, 100, 100)]),
        "outside_bar":  ([base, (100, 102, 98, 100, 100)],
                         [base, (100, 100.5, 99.5, 100, 100)]),
        "engulfing":    ([(101, 101.5, 99.5, 99.5, 100),
                          (99.4, 102, 99.3, 101.5, 100)],
                         [(101, 101.5, 99.5, 99.5, 100),
                          (100, 100.6, 99.8, 100.4, 100)]),
        "marubozu":     ([base, (99, 101.05, 98.95, 101, 100)],
                         [base, (100, 102, 98, 100.5, 100)]),
        "doji":         ([base, (100, 101, 99, 100.05, 100)],
                         [base, (100, 101, 99, 100.9, 100)]),
        "gap_bar":      ([base, (102, 103, 101.5, 102.5, 100)],
                         [base, (100.5, 101, 99.5, 100.2, 100)]),
        "three_bar_pull": ([(100, 101, 99, 99, 100), (99, 100, 98, 98, 100),
                            (98, 99, 97, 97, 100), (97, 99, 96.9, 98.5, 100)],
                           [(100, 101, 99, 99, 100), (99, 100, 98, 98, 100),
                            (98, 99, 97, 98.5, 100),
                            (98.5, 99.5, 97, 99, 100)]),
    }
    print("each pattern fires on its own case and NOT on a near miss")
    for name, (yes, no) in CASES.items():
        Py, _ = detect(_bars([base] * 8 + yes))
        Pn, _ = detect(_bars([base] * 8 + no))
        fires = bool(Py[name][0][-1])
        quiet = not bool(Pn[name][0][-1])
        check(f"{name:<16} fires / stays quiet", fires and quiet,
              "" if (fires and quiet) else
              f"fires={fires} quiet_on_near_miss={quiet}")

    print("\nevery pattern is detectable at all (none is dead code)")
    rng = np.random.default_rng(0)
    n = 60_000
    px = 100 * np.exp(np.cumsum(rng.normal(0, 3e-4, n)))
    # Opens must GAP from the prior close, or four patterns are unreachable.
    # The first version set open[t] = close[t-1] exactly, so key_reversal,
    # exhaustion, gap_bar and three_soldiers could never fire -- and the
    # look-ahead control compared two all-False arrays and passed vacuously.
    # Real bars do not open exactly on the prior close.
    op = np.concatenate([[px[0]], px[:-1]]) * (1 + rng.normal(0, 1.5e-4, n))
    hi = np.maximum(px, op) + np.abs(rng.normal(0, 0.05, n))
    lo = np.minimum(px, op) - np.abs(rng.normal(0, 0.05, n))
    import pandas as pd
    t = pd.date_range("2019-01-02 09:00", periods=n, freq="5min", tz=E.TZ)
    D = dict(t=t.tz_convert("UTC"), local=t, O=op, H=hi, L=lo, C=px,
             V=rng.integers(1, 500, n).astype(float),
             spread=np.full(n, 1e-4),
             consec=np.concatenate([[False], np.ones(n - 1, bool)]),
             hour=t.hour.to_numpy(), year=t.year.to_numpy(),
             day=t.normalize().to_numpy())
    P, BI = detect(D)
    dead = [k for k, (b, s) in P.items() if b.sum() == 0 or s.sum() == 0]
    check("no pattern never fires on random data", dead == [], f"{dead}")

    print("\nfills are conservative")
    # needs >= 8 + 2 + H_HOLD bars or the exit index falls off the end and
    # the trade is silently dropped -- which is what "filled at None" was.
    seq = ([base] * 8 + [(100, 101, 99, 100, 100),
                         (103, 104, 102.5, 103.5, 100)]
           + [(103.5, 104, 103, 103.5, 100)] * (E.H_HOLD + 1))
    Dg = _bars(seq)
    mask = np.zeros(len(seq), bool); mask[8] = True
    tr = trades(Dg, mask, +1)
    check("a gap through the trigger fills at the OPEN, not the trigger",
          len(tr) == 1 and abs(tr[0][3] - 103.0) < 1e-9,
          f"filled at {tr[0][3] if tr else None}")
    seq2 = ([base] * 8 + [(100, 101, 99, 100, 100),
                          (99.5, 100.5, 99, 100, 100)]
            + [base] * (E.H_HOLD + 1))
    m2 = np.zeros(len(seq2), bool); m2[8] = True
    tr2 = trades(_bars(seq2), m2, +1)
    check("no fill when the next bar never reaches the trigger",
          len(tr2) == 0, f"{len(tr2)} fills")

    print("\ncost and causality")
    trs = trades(D, P["inside_bar"][0], +1)
    r, _ = pnl(D, trs)
    gross = np.array([(D["O"][k] - f) / f for _, k, _, f in trs])
    check("net is below gross -- the spread is charged",
          float(np.mean(r)) < float(np.mean(gross)),
          f"{np.mean(r)*1e4:+.3f}bp vs {np.mean(gross)*1e4:+.3f}bp")
    D2 = {k: (v.copy() if hasattr(v, "copy") else v) for k, v in D.items()}
    M = n // 2
    # Perturb each BAR by its own factor, not the whole tail by one constant.
    # Every pattern here is a comparison BETWEEN bars, so scaling all four
    # series by a single constant leaves every one of them identical -- the
    # first version did that and the control passed vacuously. Same
    # cancellation that broke the q look-ahead control in spread_split.py.
    # One factor per bar keeps each bar internally consistent (H >= O,C >= L)
    # while genuinely changing the bar-to-bar relationships.
    f = 1 + rng.normal(0, 0.01, n - M)
    for key in ("O", "H", "L", "C"):
        D2[key] = D2[key].copy()
        D2[key][M:] *= f
    P2, _ = detect(D2)
    check("rewriting the future leaves past detections unchanged",
          np.array_equal(P["inside_bar"][0][:M - 2], P2["inside_bar"][0][:M - 2]))
    check("and the future really changed -- control can fail",
          not np.array_equal(P["gap_bar"][0][M + 2:], P2["gap_bar"][0][M + 2:]))

    print(f"\n{'ALL PASS' if ok else 'FAILURES ABOVE'}")
    return 0 if ok else 1


# ------------------------------------------------------------------ main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=os.path.normpath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "data")))
    ap.add_argument("--instrument", default="NAS100_USD")
    ap.add_argument("--granularity", default="M5")
    ap.add_argument("--window", choices=sorted(E.WINDOWS), default="fit")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--diagnose", action="store_true",
                    help="matched random-entry benchmark: do the PATTERNS "
                         "add anything over the execution model?")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())

    lo, hi = E.WINDOWS[a.window]
    print(f"patterns.py v{VERSION}   PREREGISTRATION_v2")
    print(f"  {a.instrument} {a.granularity}   '{a.window}' {lo} -> {hi}")
    print(f"  H={E.H_HOLD} bars, <= {E.MAX_PER_DAY}/day, "
          f"session {E.SESSION[0]:02d}-{E.SESSION[1]:02d} {E.TZ}\n")

    D = E.slice_window(load_ohlc(a.data_dir, a.instrument, a.granularity),
                       lo, hi)
    rows = screen(D)

    print(f"{'pattern':<18}{'dir':>6}{'n':>7}{'/day':>7}{'mean bp':>10}"
          f"{'Sharpe':>9}{'yr sign':>9}  advance")
    print("-" * 78)
    adv = []
    for r in rows:
        good = (r["sharpe"] >= SCREEN_SHARPE and r["n"] >= MIN_TRADES
                and r["per_day"] <= E.MAX_PER_DAY
                and r["agree"] >= MIN_YEAR_SIGN)
        if good:
            adv.append(r)
        print(f"{r['name']:<18}{r['dir']:>6}{r['n']:>7,}{r['per_day']:>7.2f}"
              f"{r['mean']*1e4:>10.2f}{r['sharpe']:>9.3f}"
              f"{r['agree']:>5}/{r['of']:<3}  {'YES' if good else ''}")

    if a.diagnose:
        # ------------------------------------------------------------------
        # 40 of 40 negative is not a null -- under a coin flip that is
        # p = 9e-13. Something systematic is driving every test the same way,
        # and the patterns share almost nothing with each other. What they DO
        # share is the execution model: a stop entry on the break of the
        # prior bar's extreme, held 30 minutes.
        #
        # So: run that execution model on RANDOM bars. If the patterns match
        # the random benchmark, the patterns contribute nothing and the whole
        # table is measuring stop-entries plus index drift minus cost.
        # Compares MEAN PER TRADE, not Sharpe, because Sharpe confounds the
        # trade count and the counts here vary 80x.
        # ------------------------------------------------------------------
        import numpy as np
        rng = np.random.default_rng(0)
        n = len(D["C"])
        print("\n" + "=" * 78)
        print("MATCHED RANDOM-ENTRY BENCHMARK -- same execution, no pattern")
        bench = {}
        for dirn, lbl in ((+1, "long"), (-1, "short")):
            draws = []
            for s_ in range(5):
                m = np.random.default_rng(100 + s_).random(n) < 0.06
                r_, _ = pnl(D, trades(D, m, dirn))
                if len(r_) > 50:
                    draws.append(r_)
            allr = np.concatenate(draws) if draws else np.array([])
            bench[dirn] = allr
            print(f"  random {lbl:<6} n={len(allr):>7,}  "
                  f"mean {np.mean(allr)*1e4:+.2f}bp  "
                  f"sd {np.std(allr, ddof=1)*1e4:.1f}bp")
        print("\n  pattern mean MINUS matched random mean:")
        print(f"  {'pattern':<18}{'dir':>6}{'pattern bp':>12}"
              f"{'random bp':>11}{'excess':>9}{'t':>8}")
        print("  " + "-" * 66)
        beats = 0
        for r in rows:
            dirn = 1 if r["dir"] == "long" else -1
            b = bench[dirn]
            if len(b) < 2:
                continue
            # recompute the pattern's own return series for a Welch t
            P, _ = detect(D)
            mask = P[r["name"]][0 if dirn > 0 else 1]
            pr, _ = pnl(D, trades(D, mask, dirn))
            if len(pr) < 2:
                continue
            ex = float(np.mean(pr) - np.mean(b))
            se = math.sqrt(np.var(pr, ddof=1) / len(pr)
                           + np.var(b, ddof=1) / len(b))
            t = ex / se if se > 0 else float("nan")
            beats += ex > 0
            print(f"  {r['name']:<18}{r['dir']:>6}{np.mean(pr)*1e4:>12.2f}"
                  f"{np.mean(b)*1e4:>11.2f}{ex*1e4:>9.2f}{t:>8.2f}")
        print(f"\n  patterns beating their own random benchmark: "
              f"{beats} of {len(rows)}")
        print("  If that is near half and no |t| is large, the patterns add")
        print("  nothing and the table measures execution + drift - cost.")

    print(f"\n  tests run: {len(rows)}   advancing: {len(adv)}")
    print(f"  expected by chance at this bar: ~{len(rows)*0.022:.1f}")
    if not adv:
        print("\n  NOTHING ADVANCES -> the family is rejected. No "
              "re-quantification\n  of thresholds, no eleventh pattern, no "
              "other H. (v2 section 6.)")
    elif len(adv) > 4:
        print("\n  MORE THAN FOUR ADVANCED -> treat with MORE suspicion, not "
              "less.\n  That is a common factor or a bug, not five "
              "discoveries. (v2 s6.)")
    else:
        print("\n  Confirm on SPX500_USD and US30_USD before believing any of "
              "it.")
        for r in adv:
            print(f"    python patterns.py --instrument SPX500_USD "
                  f"--window fit   # check {r['name']} {r['dir']}")


if __name__ == "__main__":
    main()
