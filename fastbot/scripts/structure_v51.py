#!/usr/bin/env python3
"""PREREGISTRATION_v51 -- BOS / CHoCH with a swing-width robustness gate.
Definitions live in struct15.py (pinned). Trade: enter open of bar j+1 in the break direction,
exit close of bar j+16 (4h); cost one full quoted spread at the entry bar; drop if the window spans
> 8 calendar hours. SEs clustered by UTC entry date, pooled over SPX500, NAS100, UK100, XAUUSD.
I am not a financial adviser. This is a measurement, not a recommendation."""
import hashlib, sys, os
import numpy as np
from premarket_factor import regress, tstat
from struct15 import load15, structure_events, STEMS

VERSION = "1.0"
PINS = {"../PREREGISTRATION_v51.md": "c57bd85d9dc52da50fd600c95482050852a9480a305e463611825948f7b0cca5",
        "struct15.py": "a162ce2a0eb39525ce7e2fb96ecf8f33aa5509a218eb6d424d18b268fbc7f6ef"}
END = np.datetime64("2026-09-26T00:00"); T = 2.24; H = 16; KS = (2, 3, 4, 5)
ERAS = ((2005, 2012), (2013, 2019), (2020, 2026))


def data(stem, hourly=False):
    d = load15(stem); m = d["t"] < END; d = {k: v[m] for k, v in d.items()}
    if hourly:
        g = d["t"].astype("datetime64[h]"); u, s = np.unique(g, return_index=True); e = np.r_[s[1:], len(g)]
        d = dict(t=u.astype("datetime64[m]"), o=d["o"][s], c=d["c"][e - 1], h=np.maximum.reduceat(d["h"], s),
                 l=np.minimum.reduceat(d["l"], s), spr=d["spr"][s])
    return d


def drift(d, H):
    n = len(d["c"]); i = np.arange(n - H); r = (d["c"][i + H - 1] / d["o"][i] - 1) * 1e4
    span = (d["t"][i + H - 1] - d["t"][i]).astype("int64"); ok = span <= 480
    yr = d["t"][i].astype("datetime64[Y]").astype(int) + 1970; mu = {}
    for y in np.unique(yr[ok]): mu[int(y)] = float(r[ok & (yr == y)].mean())
    return mu


def trades(stem, d, k, H=H, mu=None):
    ev = structure_events(d["h"], d["l"], d["c"], k); n = len(d["c"]); out = []
    for j, kind, s in ev:
        a, b = j + 1, j + H
        if b >= n or (d["t"][b] - d["t"][a]).astype("int64") > 480: continue
        g = s * (d["c"][b] / d["o"][a] - 1) * 1e4
        y = int(str(d["t"][a])[:4])
        out.append((stem, kind, s, str(d["t"][a])[:10], y, g, g - d["spr"][a], g - s * mu.get(y, 0.0)))
    return out


def mean_t(rows, col):
    if len(rows) < 30: return float("nan"), float("nan"), len(rows)
    y = np.array([r[col] for r in rows]); b, V = regress(y, np.ones((len(y), 1)), [r[3] for r in rows])
    return b[0], tstat(b, V, 0), len(y)


def main():
    for f, h in PINS.items():
        if hashlib.sha256(open(f, "rb").read()).hexdigest() != h: sys.exit(f"{f} changed -- refused")
    print(f"structure_v51.py v{VERSION}   PREREGISTRATION_v51 (c57bd85d…) and struct15.py (a162ce2a…) match\n"
          "  I am not a financial adviser. This is a measurement, not a recommendation.\n")
    D = {s: data(s) for s in STEMS}; MU = {s: drift(D[s], H) for s in STEMS}
    # self-test 1: causality -- events computed on truncated data equal the full-data events up to the cut
    d = D["spx500usd"]; cut = 60000
    full = [e for e in structure_events(d["h"], d["l"], d["c"], 3) if e[0] < cut]
    part = structure_events(d["h"][:cut], d["l"][:cut], d["c"][:cut], 3)
    caus = full == part
    ALL = {k: sum((trades(s, D[s], k, mu=MU[s]) for s in STEMS), []) for k in KS}
    # self-test 2: gate machinery
    ch3 = [r for r in ALL[3] if r[1] == "CHOCH"]
    up = [r[:6] + (r[6] + 5.0, r[7]) for r in ch3]; dn = [r[:6] + (-abs(r[6]), r[7]) for r in ch3]
    gm = mean_t(up, 6)[1] >= T and not (mean_t(dn, 6)[0] > 0)
    print(f"  self-test: causality (truncated == full events) {'OK' if caus else 'BROKEN'};  planted +5 bp passes, planted loss fails: {'OK' if gm else 'BROKEN'}")
    if not (caus and gm): sys.exit("self-test broken -- no verdict")

    verdict = {}
    for S in ("CHOCH", "BOS"):
        print(f"\n  ===== {S} =====")
        g1 = g2 = True
        for k in KS:
            rs = [r for r in ALL[k] if r[1] == S]
            mn, tn, n = mean_t(rs, 6); mg, tg, _ = mean_t(rs, 5); me, te, _ = mean_t(rs, 7)
            ok1 = mn > 0 and tn >= T; ok2 = me > 0; g1 &= ok1; g2 &= ok2
            print(f"    k={k}: n {n:6d}  gross {mg:+6.2f} (t {tg:+5.2f})  net {mn:+6.2f} (t {tn:+5.2f})  excess {me:+6.2f} (t {te:+5.2f})"
                  f"   G1 {'ok' if ok1 else 'x'}  G2 {'ok' if ok2 else 'x'}")
        rs3 = [r for r in ALL[3] if r[1] == S]
        er = [mean_t([r for r in rs3 if lo <= r[4] <= hi], 6) for lo, hi in ERAS]
        g3 = all(e[0] > 0 for e in er)
        print("    G3 eras (k=3 net): " + "  ".join(f"{lo}-{hi % 100:02d} {e[0]:+.2f} (t {e[1]:+.2f}, n {e[2]})" for (lo, hi), e in zip(ERAS, er))
              + f"  -> {'ok' if g3 else 'x'}")
        ins = [mean_t([r for r in rs3 if r[0] == s], 6) for s in STEMS]
        g4 = sum(e[0] > 0 for e in ins) >= 3
        print("    G4 instruments (k=3 net): " + "  ".join(f"{s[:6]} {e[0]:+.2f} (t {e[1]:+.2f})" for s, e in zip(STEMS, ins))
              + f"  -> {'ok' if g4 else 'x'}")
        verdict[S] = (g1, g2, g3, g4)
        print(f"    {S}: G1 {'PASS' if g1 else 'FAIL'}  G2 {'PASS' if g2 else 'FAIL'}  G3 {'PASS' if g3 else 'FAIL'}  G4 {'PASS' if g4 else 'FAIL'}"
              f"  -> {'PASS' if all(verdict[S]) else 'FAIL'}")

    print("\n  reported (no gates):")
    for S in ("CHOCH", "BOS"):
        rs3 = [r for r in ALL[3] if r[1] == S]
        L = mean_t([r for r in rs3 if r[2] == 1], 6); Sh = mean_t([r for r in rs3 if r[2] == -1], 6)
        print(f"    {S} k=3 longs net {L[0]:+.2f} (t {L[1]:+.2f})   shorts net {Sh[0]:+.2f} (t {Sh[1]:+.2f})")
    # confirmed CHoCH: a BOS in the same direction that follows a CHoCH (the first BOS after it)
    for k in (3,):
        conf = []
        for s in STEMS:
            ev = structure_events(D[s]["h"], D[s]["l"], D[s]["c"], k); last = None
            for j, kind, dr in ev:
                if kind == "CHOCH": last = dr
                elif kind == "BOS" and last == dr:
                    conf.append(j); last = None
            dd = D[s]; n = len(dd["c"])
            conf_tr = []
        # compute trades for confirmed BOS
        rows = []
        for s in STEMS:
            dd = D[s]; ev = structure_events(dd["h"], dd["l"], dd["c"], k); last = None; n = len(dd["c"])
            for j, kind, dr in ev:
                if kind == "CHOCH": last = dr; continue
                if last == dr:
                    a, b = j + 1, j + H; last = None
                    if b < n and (dd["t"][b] - dd["t"][a]).astype("int64") <= 480:
                        g = dr * (dd["c"][b] / dd["o"][a] - 1) * 1e4; rows.append((s, "C", dr, str(dd["t"][a])[:10], 0, g, g - dd["spr"][a]))
                else: last = None
        m = mean_t(rows, 6); print(f"    confirmed CHoCH (first same-direction BOS after it), k=3: net {m[0]:+.2f} (t {m[1]:+.2f}, n {m[2]})")
    # 1h bars, k=3
    for S in ("CHOCH", "BOS"):
        rows = []
        for s in STEMS:
            dh = data(s, hourly=True); rows += [r for r in trades(s, dh, 3, H=4, mu=drift(dh, 4)) if r[1] == S]
        m = mean_t(rows, 6); print(f"    1h bars {S} k=3, 4h hold: net {m[0]:+.2f} (t {m[1]:+.2f}, n {m[2]})")
    # random-entry control: same count/direction per instrument at random bars, k=3 CHOCH
    rng = np.random.default_rng(0); rows = []
    for s in STEMS:
        dd = D[s]; n = len(dd["c"]); rs = [r for r in ALL[3] if r[1] == "CHOCH" and r[0] == s]
        for r in rs:
            while True:
                a = int(rng.integers(0, n - H)); b = a + H - 1
                if (dd["t"][b] - dd["t"][a]).astype("int64") <= 480: break
            g = r[2] * (dd["c"][b] / dd["o"][a] - 1) * 1e4; rows.append((s, "R", r[2], str(dd["t"][a])[:10], 0, g, g - dd["spr"][a]))
    m = mean_t(rows, 6); print(f"    random-entry control (CHoCH count/direction), net {m[0]:+.2f} (t {m[1]:+.2f})")
    print(f"\n  VERDICTS  CHoCH {'PASS' if all(verdict['CHOCH']) else 'FAIL'}   BOS {'PASS' if all(verdict['BOS']) else 'FAIL'}")


if __name__ == "__main__":
    main()
