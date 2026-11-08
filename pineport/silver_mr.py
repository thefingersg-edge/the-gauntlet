"""
XAGUSD intraday mean-reversion research scaffold.

Primary signal : silver's deviation from gold-implied fair value (rolling-beta residual)
Regime gate    : Kaufman efficiency ratio + vol percentile + session
Meta-model     : logistic regression -> P(trade wins), coefficients exportable to Pine
Labels         : triple barrier (ATR-scaled TP/SL + time stop)
Validation     : purged walk-forward with embargo

Every feature here is computable in Pine v6. No volume-based features (spot CFD
tick volume is broker-specific and will not replicate).

Usage:
    python silver_mr.py --data ./data          # expects xagusd_15m.csv, xauusd_15m.csv, dxy_15m.csv
    python silver_mr.py --synthetic            # runs on generated data to verify the pipeline

CSV format: timestamp,open,high,low,close   (timestamp parseable, UTC)
"""

from __future__ import annotations

import argparse
import os
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

pd.set_option("display.width", 200)

# ----------------------------------------------------------------------------
# CONFIG -- tune these, they are the strategy
# ----------------------------------------------------------------------------

CFG = dict(
    # --- costs (SET THESE FROM YOUR BROKER, they decide everything) ---
    spread_usd      = 0.08,   # full round-trip spread in $/oz. 0.08 = 8 cents.
    slippage_atr    = 0.02,   # extra adverse fill, in ATR units

    # --- primary signal ---
    beta_window     = 96,     # bars for rolling XAG~XAU regression (96 x 15m = 24h)
    resid_z_window  = 96,     # bars for z-scoring the residual
    entry_z         = 2.0,    # fade when |resid_z| exceeds this

    # --- regime gate ---
    er_window       = 20,     # Kaufman efficiency ratio lookback
    er_max          = 0.35,   # only trade when ER below this (choppy = mean-reverting)
    vol_window      = 480,    # bars for vol percentile ranking
    vol_lo          = 0.15,   # skip dead tape
    vol_hi          = 0.90,   # skip crisis tape
    sessions        = [(7, 16)],  # UTC hours [start, end). London+NY overlap.

    # --- barriers ---
    tp_atr          = 1.0,    # take profit in ATR units
    sl_atr          = 1.5,    # stop loss in ATR units  (tp<sl => higher win rate, worse R:R)
    max_hold        = 12,     # time stop, bars
    atr_window      = 14,

    # --- meta-model ---
    prob_threshold  = 0.58,   # only take trades above this P(win)
    n_folds         = 8,      # walk-forward folds

    # --- sizing ---
    risk_per_trade  = 0.01,   # fraction of equity risked to the stop
)

FEATURES = [
    "resid_z", "gsr_z", "dxy_z", "rsi_dev", "er",
    "vol_pct", "dist_ema_atr", "xau_lead", "hour_sin", "hour_cos",
]

# ----------------------------------------------------------------------------
# DATA
# ----------------------------------------------------------------------------

def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    tcol = df.columns[0]
    df[tcol] = pd.to_datetime(df[tcol], utc=True)
    df = df.set_index(tcol).sort_index()
    df.columns = [c.lower() for c in df.columns]
    return df[["open", "high", "low", "close"]]


def make_synthetic(n=60000, seed=7) -> dict:
    """Gold random walk; silver = leveraged gold + mean-reverting idiosyncratic noise.
    This bakes in the edge on purpose, to verify the pipeline finds it."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2019-01-01", periods=n, freq="15min", tz="UTC")

    gold_r = rng.normal(0, 0.0011, n)
    # OU idiosyncratic component -- the thing the strategy is supposed to harvest
    ou = np.zeros(n)
    for i in range(1, n):
        ou[i] = 0.97 * ou[i - 1] + rng.normal(0, 0.0022)
    silver_r = 1.8 * gold_r + np.diff(np.concatenate([[0], ou]))
    dxy_r = -0.3 * gold_r + rng.normal(0, 0.0008, n)

    def to_ohlc(rets, p0):
        close = p0 * np.exp(np.cumsum(rets))
        noise = np.abs(rng.normal(0, 0.0012, len(close))) * close
        return pd.DataFrame(
            {"open": np.concatenate([[p0], close[:-1]]),
             "high": close + noise, "low": close - noise, "close": close},
            index=idx)

    return {"xag": to_ohlc(silver_r, 60.0), "xau": to_ohlc(gold_r, 4000.0),
            "dxy": to_ohlc(dxy_r, 96.0)}


# ----------------------------------------------------------------------------
# FEATURES  (all Pine-replicable)
# ----------------------------------------------------------------------------

def atr(df: pd.DataFrame, n: int) -> pd.Series:
    pc = df["close"].shift(1)
    tr = pd.concat([df["high"] - df["low"],
                    (df["high"] - pc).abs(),
                    (df["low"] - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def rsi(s: pd.Series, n: int = 14) -> pd.Series:
    d = s.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def efficiency_ratio(s: pd.Series, n: int) -> pd.Series:
    """Kaufman ER. Near 1 = clean trend, near 0 = chop. Mean reversion wants low."""
    direction = (s - s.shift(n)).abs()
    volatility = s.diff().abs().rolling(n).sum()
    return direction / volatility.replace(0, np.nan)


def zscore(s: pd.Series, n: int) -> pd.Series:
    return (s - s.rolling(n).mean()) / s.rolling(n).std(ddof=0).replace(0, np.nan)


def build_features(xag, xau, dxy, cfg) -> pd.DataFrame:
    df = pd.DataFrame(index=xag.index)
    df[["open", "high", "low", "close"]] = xag[["open", "high", "low", "close"]]
    df["xau_close"] = xau["close"].reindex(xag.index).ffill()
    df["dxy_close"] = dxy["close"].reindex(xag.index).ffill()

    r_ag = np.log(df["close"]).diff()
    r_au = np.log(df["xau_close"]).diff()
    r_dx = np.log(df["dxy_close"]).diff()

    # --- 1. gold-implied fair value residual (the primary edge) ---
    bw = cfg["beta_window"]
    cov = r_ag.rolling(bw).cov(r_au)
    var = r_au.rolling(bw).var()
    beta = (cov / var.replace(0, np.nan)).clip(0.5, 4.0)
    resid = r_ag - beta * r_au
    # cumulative residual = how far silver has drifted from gold-implied path
    cum_resid = resid.rolling(bw).sum()
    df["beta"] = beta
    df["resid_z"] = zscore(cum_resid, cfg["resid_z_window"])

    # --- 2. gold/silver ratio dislocation ---
    df["gsr_z"] = zscore(df["xau_close"] / df["close"], cfg["resid_z_window"])

    # --- 3. dollar impulse ---
    df["dxy_z"] = zscore(r_dx.rolling(8).sum(), cfg["resid_z_window"])

    # --- 4/5. classic oscillator + regime ---
    df["rsi_dev"] = (rsi(df["close"], 14) - 50) / 50
    df["er"] = efficiency_ratio(df["close"], cfg["er_window"])

    # --- 6. volatility regime (percentile of ATR%) ---
    df["atr"] = atr(df, cfg["atr_window"])
    atr_pct = df["atr"] / df["close"]
    df["vol_pct"] = atr_pct.rolling(cfg["vol_window"]).rank(pct=True)

    # --- 7. stretch from anchor, in ATR units (vol-normalized, so 2019 still informative) ---
    ema = df["close"].ewm(span=48, adjust=False).mean()
    df["dist_ema_atr"] = (df["close"] - ema) / df["atr"].replace(0, np.nan)

    # --- 8. gold lead-lag (gold is more liquid, it moves first) ---
    df["xau_lead"] = r_au.rolling(3).sum() / atr_pct.replace(0, np.nan)

    # --- 9/10. time of day, cyclically encoded ---
    hr = df.index.hour + df.index.minute / 60
    df["hour_sin"] = np.sin(2 * np.pi * hr / 24)
    df["hour_cos"] = np.cos(2 * np.pi * hr / 24)
    df["hour"] = df.index.hour

    return df.replace([np.inf, -np.inf], np.nan)


# ----------------------------------------------------------------------------
# PRIMARY SIGNAL + TRIPLE BARRIER LABELS
# ----------------------------------------------------------------------------

def primary_signal(df, cfg) -> pd.Series:
    """+1 = long (silver cheap vs gold), -1 = short. Regime-gated."""
    in_session = np.zeros(len(df), dtype=bool)
    for lo, hi in cfg["sessions"]:
        in_session |= (df["hour"] >= lo) & (df["hour"] < hi)

    gate = (
        in_session
        & (df["er"] < cfg["er_max"])
        & (df["vol_pct"].between(cfg["vol_lo"], cfg["vol_hi"]))
    )
    sig = pd.Series(0, index=df.index, dtype=int)
    sig[gate & (df["resid_z"] <= -cfg["entry_z"])] = 1
    sig[gate & (df["resid_z"] >= cfg["entry_z"])] = -1
    return sig


def triple_barrier(df, sig, cfg) -> pd.DataFrame:
    """For each signal bar, walk forward to whichever barrier hits first.
    Returns one row per candidate trade."""
    hi, lo, cl, av = (df["high"].values, df["low"].values,
                      df["close"].values, df["atr"].values)
    idxs = np.flatnonzero(sig.values != 0)
    rows = []
    n = len(df)

    for i in idxs:
        if i + 1 >= n or not np.isfinite(av[i]) or av[i] <= 0:
            continue
        side = sig.values[i]
        entry = cl[i] + side * (cfg["spread_usd"] / 2 + cfg["slippage_atr"] * av[i])
        tp = entry + side * cfg["tp_atr"] * av[i]
        sl = entry - side * cfg["sl_atr"] * av[i]

        end = min(i + 1 + cfg["max_hold"], n)
        outcome, exit_px, bars = "time", cl[end - 1], end - 1 - i
        for j in range(i + 1, end):
            hit_sl = (lo[j] <= sl) if side == 1 else (hi[j] >= sl)
            hit_tp = (hi[j] >= tp) if side == 1 else (lo[j] <= tp)
            if hit_sl and hit_tp:          # both in one bar -> assume the worse
                outcome, exit_px, bars = "sl", sl, j - i
                break
            if hit_sl:
                outcome, exit_px, bars = "sl", sl, j - i
                break
            if hit_tp:
                outcome, exit_px, bars = "tp", tp, j - i
                break

        exit_px -= side * cfg["spread_usd"] / 2      # pay the other half on exit
        pnl_atr = side * (exit_px - entry) / av[i]
        rows.append(dict(
            t=df.index[i], i=i, side=side, entry=entry, exit=exit_px,
            atr=av[i], outcome=outcome, bars=bars, pnl_atr=pnl_atr,
            win=int(pnl_atr > 0),
            **{f: df[f].values[i] for f in FEATURES},
        ))

    if not rows:
        return pd.DataFrame(columns=["t", "i", "side", "pnl_atr", "win"] + FEATURES)
    return pd.DataFrame(rows).dropna(subset=FEATURES).reset_index(drop=True)


# ----------------------------------------------------------------------------
# PURGED WALK-FORWARD META-MODEL
# ----------------------------------------------------------------------------

def walk_forward(trades: pd.DataFrame, cfg) -> pd.DataFrame:
    """Train logistic P(win) on past folds only, predict forward.
    Embargo removes trades whose label horizon overlaps the test window."""
    trades = trades.sort_values("i").reset_index(drop=True)
    n = len(trades)
    fold = n // (cfg["n_folds"] + 1)
    if fold < 30:
        raise ValueError(f"only {n} trades -- not enough for {cfg['n_folds']} folds")

    out, coef_log = [], []
    for k in range(1, cfg["n_folds"] + 1):
        tr_end, te_end = k * fold, min((k + 1) * fold, n)
        train, test = trades.iloc[:tr_end].copy(), trades.iloc[tr_end:te_end].copy()

        # embargo: drop train trades still "open" when the test window starts
        cutoff = test["i"].iloc[0]
        train = train[train["i"] + cfg["max_hold"] < cutoff]
        if len(train) < 50 or train["win"].nunique() < 2:
            continue

        mu, sd = train[FEATURES].mean(), train[FEATURES].std(ddof=0).replace(0, 1)
        Xtr = ((train[FEATURES] - mu) / sd).values
        Xte = ((test[FEATURES] - mu) / sd).values

        clf = LogisticRegression(C=0.3, max_iter=2000, class_weight="balanced")
        clf.fit(Xtr, train["win"].values)
        test["p_win"] = clf.predict_proba(Xte)[:, 1]
        test["fold"] = k
        out.append(test)

        coef_log.append(pd.Series(clf.coef_[0], index=FEATURES).to_dict()
                        | {"intercept": clf.intercept_[0], "fold": k})

    oos = pd.concat(out).reset_index(drop=True)
    coefs = pd.DataFrame(coef_log).set_index("fold")
    return oos, coefs, (mu, sd)


# ----------------------------------------------------------------------------
# EVALUATION
# ----------------------------------------------------------------------------

def evaluate(oos, df, cfg, threshold):
    """Fixed-fractional sizing: risk `risk_per_trade` of equity to the stop."""
    sel = oos[oos["p_win"] >= threshold].copy()
    if len(sel) < 10:
        return None

    # pnl in R multiples (R = distance to stop = sl_atr ATRs)
    sel["R"] = sel["pnl_atr"] / cfg["sl_atr"]
    eq = (1 + cfg["risk_per_trade"] * sel["R"]).cumprod()
    peak = eq.cummax()
    max_dd = float((1 - eq / peak).max())

    wins, losses = sel[sel["R"] > 0]["R"], sel[sel["R"] <= 0]["R"]
    pf = wins.sum() / abs(losses.sum()) if len(losses) and losses.sum() != 0 else np.inf

    span_days = (sel["t"].iloc[-1] - sel["t"].iloc[0]).days or 1
    years = span_days / 365.25
    cagr = eq.iloc[-1] ** (1 / years) - 1 if years > 0 else np.nan

    # per-trade Sharpe annualised by trade frequency
    tpy = len(sel) / years
    sharpe = (sel["R"].mean() / sel["R"].std(ddof=0) * np.sqrt(tpy)
              if sel["R"].std(ddof=0) > 0 else np.nan)

    # buy & hold over the same window, same leverage-free basis
    sub = df.loc[sel["t"].iloc[0]:sel["t"].iloc[-1], "close"]
    bh_ret = sub.iloc[-1] / sub.iloc[0] - 1
    bh_dd = float((1 - sub / sub.cummax()).max())

    return dict(
        threshold=threshold, trades=len(sel), trades_per_yr=round(tpy),
        win_rate=round(sel["win"].mean(), 4),
        avg_R=round(sel["R"].mean(), 4),
        profit_factor=round(float(pf), 3),
        total_return=round(float(eq.iloc[-1] - 1), 4),
        cagr=round(float(cagr), 4),
        max_dd=round(max_dd, 4),
        sharpe=round(float(sharpe), 2),
        bh_return=round(float(bh_ret), 4), bh_max_dd=round(bh_dd, 4),
    )


def cost_check(df, cfg):
    """Run this BEFORE anything else. If the spread is a large fraction of your
    target move, no amount of modelling will save the strategy."""
    a = df["atr"].dropna()
    med_atr = float(a.median())
    target = cfg["tp_atr"] * med_atr
    cost = cfg["spread_usd"] + 2 * cfg["slippage_atr"] * med_atr
    ratio = target / cost

    print("-" * 60)
    print("COST VIABILITY CHECK")
    print("-" * 60)
    print(f"  median ATR({cfg['atr_window']})   : ${med_atr:.4f}")
    print(f"  target move (TP)     : ${target:.4f}")
    print(f"  round-trip cost      : ${cost:.4f}")
    print(f"  target / cost        : {ratio:.2f}x", end="  ")
    if ratio < 1.5:
        print("<-- FATAL. Costs eat the edge. Widen TP, or use a slower timeframe.")
    elif ratio < 3:
        print("<-- MARGINAL. Edge must be strong to survive.")
    else:
        print("<-- OK.")
    print("-" * 60 + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=None, help="dir with xagusd_15m.csv etc")
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--tf", default="15m")
    args = ap.parse_args()

    if args.synthetic or not args.data:
        print(">> SYNTHETIC DATA (pipeline check only -- results are meaningless)\n")
        d = make_synthetic()
        xag, xau, dxy = d["xag"], d["xau"], d["dxy"]
    else:
        tf = args.tf
        xag = load_csv(os.path.join(args.data, f"xagusd_{tf}.csv"))
        xau = load_csv(os.path.join(args.data, f"xauusd_{tf}.csv"))

        # Dukascopy publishes no dollar index. EUR is 57.6% of DXY and moves
        # inversely, so 1/EURUSD is a serviceable stand-in for a z-scored
        # feature. Real DXY is preferred when you have it.
        dxy_path = os.path.join(args.data, f"dxy_{tf}.csv")
        eur_path = os.path.join(args.data, f"eurusd_{tf}.csv")
        if os.path.exists(dxy_path):
            dxy = load_csv(dxy_path)
        elif os.path.exists(eur_path):
            e = load_csv(eur_path)
            dxy = pd.DataFrame({
                "open": 1 / e["open"], "high": 1 / e["low"],
                "low": 1 / e["high"], "close": 1 / e["close"]}, index=e.index)
            print("   note: using inverted EURUSD as a DXY proxy")
        else:
            raise SystemExit(f"need {dxy_path} or {eur_path}")
        print(f">> loaded {len(xag):,} XAGUSD bars "
              f"{xag.index[0].date()} -> {xag.index[-1].date()}\n")

    df = build_features(xag, xau, dxy, CFG)
    cost_check(df, CFG)
    sig = primary_signal(df, CFG)
    print(f"primary signals fired : {int((sig != 0).sum()):,} "
          f"({(sig != 0).mean() * 100:.2f}% of bars)")

    trades = triple_barrier(df, sig, CFG)
    if len(trades) < 200:
        print(f"\ncandidate trades: {len(trades)} -- too few to model.\n"
              "  Loosen the gate: lower entry_z, raise er_max, widen the vol band,\n"
              "  or extend the session window. Then re-run.")
        return
    print(f"candidate trades      : {len(trades):,}")
    print(f"raw win rate (no ML)  : {trades['win'].mean():.1%}")
    print(f"raw avg pnl (ATR)     : {trades['pnl_atr'].mean():+.4f}\n")

    oos, coefs, _ = walk_forward(trades, CFG)
    print(f"out-of-sample trades  : {len(oos):,}\n")

    # ---- the win-rate vs drawdown frontier ----
    print("=" * 96)
    print("FRONTIER: P(win) threshold vs win rate / drawdown / return")
    print("=" * 96)
    rows = [evaluate(oos, df, CFG, t) for t in np.arange(0.45, 0.76, 0.025)]
    frontier = pd.DataFrame([r for r in rows if r])
    print(frontier.to_string(index=False))

    print("\n" + "=" * 96)
    print("MEAN LOGISTIC COEFFICIENTS  (paste into Pine -- see silver_mr.pine)")
    print("=" * 96)
    print(coefs.mean().round(4).to_string())
    print("\nCoefficient stability across folds (std -- high = unstable feature):")
    print(coefs.std().round(4).to_string())


if __name__ == "__main__":
    main()
