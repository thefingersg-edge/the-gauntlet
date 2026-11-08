"""
o1_kalman.py — Kalman velocity trend, external replication.

Pre-registered in PREREGISTRATION_KALMAN.md (frozen 2026-09-19, amendments
A6-A9 added before any code was run). Nothing here may be tuned to an outcome.

    state x = [level, velocity],  F = [[1,1],[0,1]],  H = [1,0]
    Q = 0.01 * ATR(14)^2 * I2,    R = 1.0 * ATR(14)^2
    entry  : x2 crosses above 0 AND close > EMA(200)
    exit   : x2 crosses below 0, OR chandelier at peak - 4*ATR(14)
"""
import os, sys, glob
import numpy as np
import pandas as pd
import core

# ---- frozen parameters -----------------------------------------------------
ATR_N, EMA_N   = 14, 200
CHAND_MULT     = 4.0
Q_SCALE, R_SCALE = 0.01, 1.0
BURN           = 500
COST_BP        = 1.0                     # primary; 0 and 3 are robustness
LAG_NULL       = 750                     # G3 destroyed timing
MIN_BARS_YR    = 1100                    # sample rule (section 3.2)
END            = pd.Timestamp("2026-08-07 23:59:59", tz="UTC")
VOL_WIN        = {"h4": 378, "h1": 1512}   # ~63 trading days (A7)

HERE = os.path.dirname(os.path.abspath(__file__))
SRC  = os.path.dirname(HERE)
H4   = os.path.join(HERE, "data_h4")

# ---- data ------------------------------------------------------------------

def load(mkt: str, tf: str) -> pd.DataFrame:
    p = (os.path.join(H4, f"{mkt}_h4.csv") if tf == "h4"
         else os.path.join(SRC, f"{mkt}_oanda_h1.csv"))
    df = pd.read_csv(p, usecols=["time", "open", "high", "low", "close"])
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df = df.sort_values("time").drop_duplicates("time").set_index("time")
    return df[df.index <= END]


def markets(tf: str) -> list[str]:
    """Section 3.2: >= MIN_BARS_YR bars/yr on the 4h grid. The list is fixed by
    the 4h coverage for BOTH timeframes, so the panel does not change between
    T1 and T2."""
    out = []
    for p in sorted(glob.glob(os.path.join(H4, "*_h4.csv"))):
        m = os.path.basename(p).replace("_h4.csv", "")
        d = load(m, "h4")
        if len(d) < 2:
            continue
        yrs = (d.index[-1] - d.index[0]).days / 365.25
        if yrs > 0 and len(d) / yrs >= MIN_BARS_YR:
            out.append(m)
    return out

# ---- indicators ------------------------------------------------------------

def atr(df: pd.DataFrame, n: int = ATR_N) -> pd.Series:
    """Wilder ATR."""
    pc = df["close"].shift(1)
    tr = pd.concat([df["high"] - df["low"],
                    (df["high"] - pc).abs(),
                    (df["low"] - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()


def ema(s: pd.Series, n: int = EMA_N) -> pd.Series:
    return s.ewm(span=n, adjust=False, min_periods=n).mean()

# ---- the filter ------------------------------------------------------------

def kalman_velocity(close: np.ndarray, a: np.ndarray,
                    q_scale: float = Q_SCALE, r_scale: float = R_SCALE,
                    scale_by_atr: bool = True) -> np.ndarray:
    """Velocity component x2 of the constant-velocity filter.

    P is symmetric so it is carried as (p11, p12, p22) and the 2x2 algebra is
    written out; with F = [[1,1],[0,1]] and Q = q*I2:

        P' = [[p11 + 2p12 + p22 + q, p12 + p22], [p12 + p22, p22 + q]]
        S  = p'11 + R,  k1 = p'11/S,  k2 = p'12/S
        p11 = (1-k1) p'11,  p12 = (1-k1) p'12,  p22 = p'22 - k2 p'12

    NOTE (section 1.2): scaling Q and R by the same ATR^2 leaves K, and hence
    sign(x2), all but unchanged. scale_by_atr=False is ablation ABL-4.
    """
    n  = len(close)
    x2 = np.full(n, np.nan)
    i0 = int(np.argmax(np.isfinite(a)))            # first valid ATR
    if not np.isfinite(a[i0]):
        return x2

    s0 = a[i0] if scale_by_atr else 1.0
    x1, v = close[i0], 0.0
    p11 = p22 = r_scale * s0
    p12 = 0.0
    x2[i0] = 0.0

    for t in range(i0 + 1, n):
        s = (a[t] if scale_by_atr else 1.0)
        if not np.isfinite(s) or s <= 0:
            s = s0
        s0 = s
        q, r = q_scale * s, r_scale * s

        x1, v = x1 + v, v                          # x' = F x
        a11 = p11 + 2.0 * p12 + p22 + q            # P' = F P F^T + Q
        a12 = p12 + p22
        a22 = p22 + q

        S  = a11 + r
        k1 = a11 / S
        k2 = a12 / S
        innov = close[t] - x1
        x1 += k1 * innov
        v  += k2 * innov
        p11 = (1.0 - k1) * a11
        p12 = (1.0 - k1) * a12
        p22 = a22 - k2 * a12
        x2[t] = v
    return x2

# ---- trade simulation ------------------------------------------------------

def simulate(o, h, l, c, entry_sig, exit_sig, atrv, cost_bp=COST_BP,
             chandelier=True, vel_exit=True, mult=CHAND_MULT, direction=1):
    """Bar-level return series for a one-unit, no-pyramiding rule.

    `direction` is +1 for the rule as written (long) and -1 for the G6 mirror.
    The mirror is taken by SIGNING THE RETURN and reflecting the stop, not by
    negating prices: ratio returns are invariant to a sign flip of the price
    series, so price negation silently produces the long result again.

    Conventions (pre-registered, sections 6 and A8/A9):
      entry signal at close t-1  -> fill at open t
      velocity exit at close t-1 -> fill at open t          (checked FIRST)
      chandelier level for bar t = extreme through t-1 -/+ mult * ATR[t-1],
        armed from the bar after entry; a gap through the stop fills at the
        open, never at the stop
    Returns (r, pos, n_trades).
    """
    n = len(c)
    r    = np.zeros(n)
    pos  = np.zeros(n)
    cost = cost_bp / 1e4
    d    = float(direction)
    in_pos, ext, ntr = False, np.nan, 0

    for t in range(1, n):
        if in_pos:
            if vel_exit and exit_sig[t - 1]:                     # A9: first
                r[t] = d * (o[t] / c[t - 1] - 1.0) - cost
                pos[t] = 1.0
                in_pos = False
                continue
            if chandelier and np.isfinite(ext) and np.isfinite(atrv[t - 1]):
                if d > 0:
                    lvl = ext - mult * atrv[t - 1]
                    hit, fill = l[t] <= lvl, min(lvl, o[t])
                else:
                    lvl = ext + mult * atrv[t - 1]
                    hit, fill = h[t] >= lvl, max(lvl, o[t])
                if hit:
                    r[t] = d * (fill / c[t - 1] - 1.0) - cost
                    pos[t] = 1.0
                    in_pos = False
                    continue
            r[t] = d * (c[t] / c[t - 1] - 1.0)
            pos[t] = 1.0
            ext = max(ext, h[t]) if d > 0 else min(ext, l[t])
        else:
            if entry_sig[t - 1]:
                in_pos = True
                ntr += 1
                ext = h[t] if d > 0 else l[t]     # stop armed from t+1 (A8)
                r[t] = d * (c[t] / o[t] - 1.0) - cost
                pos[t] = 1.0
    return r, pos, ntr

# ---- one market, one variant ----------------------------------------------

def run_market(mkt: str, tf: str, *, use_ema=True, use_kalman=True,
               chandelier=True, vel_exit=True, scale_by_atr=True,
               short=False, cost_bp=COST_BP, lag=0) -> pd.Series:
    df = load(mkt, tf)
    if len(df) < BURN + 1000:
        return pd.Series(dtype=float)
    av = atr(df).to_numpy()
    c  = df["close"].to_numpy()
    e  = ema(df["close"]).to_numpy()

    if use_kalman:
        x2 = kalman_velocity(c, av ** 2, scale_by_atr=scale_by_atr)
        up = np.zeros(len(c), bool); dn = np.zeros(len(c), bool)
        f  = np.isfinite(x2)
        up[1:] = f[1:] & f[:-1] & (x2[1:] > 0) & (x2[:-1] <= 0)
        dn[1:] = f[1:] & f[:-1] & (x2[1:] < 0) & (x2[:-1] >= 0)
    else:                                   # ABL-2: EMA cross stands in
        up = np.zeros(len(c), bool); dn = np.zeros(len(c), bool)
        fe = np.isfinite(e)
        up[1:] = fe[1:] & fe[:-1] & (c[1:] > e[1:]) & (c[:-1] <= e[:-1])
        dn[1:] = fe[1:] & fe[:-1] & (c[1:] < e[1:]) & (c[:-1] >= e[:-1])

    if short:                               # G6 mirror: flip the whole rule
        up, dn = dn, up

    ok = (c > e) if (use_ema and not short) else ((c < e) if (use_ema and short)
                                                 else np.ones(len(c), bool))
    ent = up & np.isfinite(e) & ok
    ent[:BURN] = False

    if lag:                                 # G3 destroyed timing
        ent = np.concatenate([np.zeros(lag, bool), ent[:-lag]])
        dn  = np.concatenate([np.zeros(lag, bool), dn[:-lag]])

    o, hi, lo = df["open"].to_numpy(), df["high"].to_numpy(), df["low"].to_numpy()
    r, pos, ntr = simulate(o, hi, lo, c, ent, dn, av, cost_bp,
                           chandelier, vel_exit,
                           direction=-1 if short else 1)

    s = pd.Series(r, index=df.index)
    s.attrs["n_trades"] = ntr
    s.attrs["exposure"] = float(pos.mean())
    return s

# ---- portfolio assembly ----------------------------------------------------

def vol_weight(df: pd.DataFrame, tf: str) -> pd.Series:
    """Trailing realised vol of the market's own bar returns, shifted (A7, R2)."""
    w = VOL_WIN[tf]
    br = df["close"].pct_change()
    v = br.rolling(w, min_periods=int(w * 0.8)).std().shift(1)
    return v.replace(0.0, np.nan)


def build_panel(tf: str, mkts: list[str], **kw) -> pd.DataFrame:
    """One vol-normalised strategy return series per market, aligned."""
    cols = {}
    for m in mkts:
        r = run_market(m, tf, **kw)
        if r.empty:
            continue
        v = vol_weight(load(m, tf), tf).reindex(r.index)
        s = (r / v).replace([np.inf, -np.inf], np.nan)
        s.attrs = r.attrs
        cols[m] = s
    P = pd.DataFrame(cols)
    P.attrs["n_trades"] = {m: cols[m].attrs.get("n_trades", 0) for m in cols}
    return P


def pooled(P: pd.DataFrame) -> pd.Series:
    """Equal-weight across markets, live bars only (R3: min_count, not sum-of-nan)."""
    return P.mean(axis=1).dropna()

# ---- inference -------------------------------------------------------------

def n_eff(P: pd.DataFrame) -> tuple[float, float]:
    """N_eff = N / (1 + (N-1) rho_bar), rho_bar the mean off-diagonal correlation
    of the REALISED strategy returns — measured, never assumed (GAUNTLET 3.2)."""
    C = P.corr(min_periods=250)
    N = C.shape[0]
    if N < 2:
        return float(N), np.nan
    off = C.to_numpy()[~np.eye(N, dtype=bool)]
    rho = float(np.nanmean(off))
    return N / (1.0 + (N - 1) * rho), rho


def noise_floor(r: pd.Series, ne: float) -> float:
    """2 SE on a Sharpe estimate: SE ~ 1/sqrt(T * N_eff)."""
    T = core.years(r)
    return 2.0 / np.sqrt(T * ne) if (T and T > 0 and ne and ne > 0) else np.nan


def era_sharpes(r: pd.Series) -> dict:
    e = core.era_of(pd.DatetimeIndex(r.index))
    return {k: core.sharpe(r[(e == k).to_numpy()]) for k in core.ERAS}


def block_bootstrap(r: pd.Series, mean_block: int = 63, draws: int = 10000,
                    seed: int = 20260919) -> np.ndarray:
    """Stationary block bootstrap of the Sharpe ratio."""
    x = r.dropna().to_numpy()
    n = len(x)
    if n < 500:
        return np.array([])
    rng = np.random.default_rng(seed)
    ppy = core.ppy(r.dropna())
    ar = np.arange(n)
    out = []
    batch = max(1, int(5e6 // n))
    done = 0
    while done < draws:
        b = min(batch, draws - done)
        new = rng.random((b, n)) < (1.0 / mean_block)
        new[:, 0] = True
        seg = np.maximum.accumulate(np.where(new, ar, -1), axis=1)
        base = np.take_along_axis(rng.integers(0, n, size=(b, n)), seg, axis=1)
        s = x[(base + (ar - seg)) % n]
        sd = s.std(axis=1)
        out.append(np.where(sd > 0, s.mean(axis=1) / np.where(sd > 0, sd, 1) * np.sqrt(ppy), np.nan))
        done += b
    return np.concatenate(out)


def bh_fdr(p: np.ndarray) -> np.ndarray:
    """Benjamini-Hochberg q-values."""
    p = np.asarray(p, float)
    ok = np.isfinite(p)
    q = np.full(p.shape, np.nan)
    v = p[ok]
    m = len(v)
    if m == 0:
        return q
    o = np.argsort(v)
    ranked = v[o] * m / np.arange(1, m + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty(m)
    out[o] = np.minimum(ranked, 1.0)
    q[ok] = out
    return q


def boot_p(boot: np.ndarray) -> float:
    """Two-sided bootstrap p for Sharpe != 0, centred on the bootstrap mean."""
    if boot.size == 0:
        return np.nan
    b = boot[np.isfinite(boot)]
    if b.size == 0:
        return np.nan
    return float(2.0 * min((b <= 0).mean(), (b >= 0).mean()))

# ---- G4 matched control ----------------------------------------------------

PRIOR_WIN = {"h4": 30, "h1": 120}          # ~1 trading week (A10)


def matched_control(mkt: str, tf: str, seed: int = 20260919) -> tuple:
    """Mean trade return vs mean forward return of non-trade bars in the same
    (era x prior-return decile x vol decile) cell, over a matched horizon (A10)."""
    df = load(mkt, tf)
    if len(df) < BURN + 1000:
        return (np.nan, np.nan, 0)
    r = run_market(mkt, tf)
    if r.empty:
        return (np.nan, np.nan, 0)

    c = df["close"]
    prior = (c / c.shift(PRIOR_WIN[tf]) - 1.0)
    vol   = vol_weight(df, tf)
    era   = core.era_of(pd.DatetimeIndex(df.index)).to_numpy()
    pd_dec = pd.qcut(prior, 10, labels=False, duplicates="drop").to_numpy()
    vd_dec = pd.qcut(vol,   10, labels=False, duplicates="drop").to_numpy()

    inpos = (r.to_numpy() != 0.0)
    # trade segments from the realised position path
    segs, i, n = [], 0, len(inpos)
    while i < n:
        if inpos[i]:
            j = i
            while j + 1 < n and inpos[j + 1]:
                j += 1
            segs.append((i, j - i + 1))
            i = j + 1
        else:
            i += 1
    if not segs:
        return (np.nan, np.nan, 0)

    cv = c.to_numpy()
    rng = np.random.default_rng(seed)
    tr, ct = [], []
    for s, h in segs:
        if s + h >= n or not np.isfinite(cv[s]) or cv[s] <= 0:
            continue
        tr.append(cv[s + h] / cv[s] - 1.0)
        cell = ((era == era[s]) & (pd_dec == pd_dec[s]) & (vd_dec == vd_dec[s])
                & ~inpos & np.isfinite(cv))
        idx = np.flatnonzero(cell)
        idx = idx[(idx + h) < n]
        if len(idx) == 0:
            continue
        pick = rng.choice(idx, size=min(50, len(idx)), replace=False)
        ct.append(float(np.mean(cv[pick + h] / cv[pick] - 1.0)))
    if not tr or not ct:
        return (np.nan, np.nan, 0)
    return (float(np.mean(tr)), float(np.mean(ct)), len(tr))

# ---- declared test battery -------------------------------------------------

VARIANTS = {
    "T_primary": dict(),
    "T_mirror":  dict(short=True),
    "ABL1_no_ema":       dict(use_ema=False),
    "ABL2_no_kalman":    dict(use_kalman=False),
    "ABL3_no_chandelier": dict(chandelier=False),
    "ABL4_no_atr_scale": dict(scale_by_atr=False),
}


def one(tf: str, mkts: list[str], name: str, kw: dict, boot: bool) -> dict:
    P = build_panel(tf, mkts, **kw)
    r = pooled(P)
    ne, rho = n_eff(P)
    es = era_sharpes(r)
    sh = core.sharpe(r)
    nf = noise_floor(r, ne)
    row = dict(test=name, tf=tf, sharpe=sh, n_eff=ne, rho_bar=rho,
               floor_2se=nf, clears_floor=bool(np.isfinite(sh) and np.isfinite(nf)
                                               and abs(sh) > nf),
               ann_vol=core.ann_vol(r), years=core.years(r), bars=len(r),
               trades=int(sum(P.attrs["n_trades"].values())),
               **{f"era_{k}": v for k, v in es.items()})
    signs = [np.sign(v) for v in es.values() if np.isfinite(v)]
    row["era_consistent"] = bool(len(signs) == 3 and abs(sum(signs)) == 3)
    if boot:
        b = block_bootstrap(r)
        row["boot_med"] = float(np.nanmedian(b)) if b.size else np.nan
        row["boot_p5"]  = float(np.nanpercentile(b, 5)) if b.size else np.nan
        row["boot_p95"] = float(np.nanpercentile(b, 95)) if b.size else np.nan
        row["p"] = boot_p(b)
    return row, P, r


def main(tf: str):
    mkts = markets(tf)
    print(f"O1 Kalman velocity | {tf} | {len(mkts)} markets | "
          f"pre-registered PREREGISTRATION_KALMAN.md\n")
    rows = []
    for name, kw in VARIANTS.items():
        row, P, r = one(tf, mkts, name, kw, boot=(name in ("T_primary", "T_mirror")))
        rows.append(row)
        eras = "/".join(f"{row['era_' + k]:+.2f}" for k in core.ERAS)
        print(f"  {name:20s} Sharpe {row['sharpe']:+.4f}  floor {row['floor_2se']:.4f}  "
              f"N_eff {row['n_eff']:.2f}  eras {eras}  "
              f"{'ERA-OK' if row['era_consistent'] else 'era-flip'}  "
              f"trades {row['trades']}", flush=True)
        if name == "T_primary":
            P.to_csv(f"o1_panel_{tf}.csv")

    # G3 destroyed timing
    row, _, _ = one(tf, mkts, "G3_lag750", dict(lag=LAG_NULL), boot=False)
    rows.append(row); print(f"\n  {'G3_lag750':20s} Sharpe {row['sharpe']:+.4f}  "
                            f"(vs primary {rows[0]['sharpe']:+.4f})")

    # G5 cost sensitivity
    for cb in (0.0, 3.0):
        row, _, _ = one(tf, mkts, f"G5_cost{cb:g}bp", dict(cost_bp=cb), boot=False)
        rows.append(row); print(f"  {f'G5_cost{cb:g}bp':20s} Sharpe {row['sharpe']:+.4f}")

    R = pd.DataFrame(rows)
    R["q"] = np.nan
    fam = R.test.isin(list(VARIANTS))
    if "p" in R.columns:
        R.loc[fam, "q"] = bh_fdr(R.loc[fam, "p"].to_numpy())
    R.to_csv(f"o1_kalman_{tf}.csv", index=False)
    print(f"\nwrote o1_kalman_{tf}.csv and o1_panel_{tf}.csv")
    return R


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "h4")
