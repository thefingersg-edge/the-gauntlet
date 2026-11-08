"""
G1 — the gate before any portfolio work: does the new instrument set actually
lift the effective sample size?

    N_eff = N / (1 + (N-1) * mean pairwise correlation)

The eleven-market test set sits at N_eff 2.7 on asset returns and 3.5 on
strategy returns. Under equicorrelation the ceiling for that cluster is 1/rho
~ 4.8 however many similar markets are added -- which is why the two volatility
replications moved it DOWN. Portfolio construction on 3 effective markets is not
portfolio construction.

Run this before `PREREGISTRATION_PORTFOLIO.md`. If N_eff does not clear the
threshold stated there, the portfolio question is answered without running it.
"""
from __future__ import annotations
import os, sys, glob
import numpy as np
import pandas as pd
import core
from c1_agreement import agreement

SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GATE_NEFF = 6.0          # pre-registered in PREREGISTRATION_PORTFOLIO.md


def build_missing_daily() -> list[str]:
    """Resample any *_oanda_h1.csv that has no daily file yet.

    R4: delegates to make_daily.build so the trading-day boundary is defined
    in exactly one place. The previous inline copy used resample("1D"), which
    is the UTC-midnight boundary that manufactured the Sunday stub bars.
    """
    import make_daily
    made = []
    for mkt in make_daily.all_available():
        if os.path.exists(os.path.join(core.DATA, f"{mkt}_d1.csv")):
            continue
        msg = make_daily.build(mkt, min_days=500)
        print(f"  {msg}")
        if "skipped" not in msg and "MISSING" not in msg:
            made.append(mkt)
    return made


def neff_bootstrap(S: pd.DataFrame, n_boot=2000, mean_block=63, seed=20260911):
    """R1: the gate reported N_eff 6.01 against a 6.00 threshold and called it
    a PASS. At that point dN_eff/drho_bar = -34.4, so 0.01 of N_eff is a
    correlation difference of 0.0003 — the gate has no resolution at its own
    threshold. A point estimate cannot answer this; the interval can.

    Stationary block bootstrap over ROWS (markets are the fixed population)."""
    rng = np.random.default_rng(seed)
    X = S.dropna(how="all")
    N = len(X)
    out = np.empty(n_boot)
    for b in range(n_boot):
        idx, j = [], 0
        while j < N:
            st = rng.integers(0, N)
            L = max(1, rng.geometric(1 / mean_block))
            idx += [(st + k) % N for k in range(min(L, N - j))]
            j += L
        C = X.iloc[np.array(idx[:N])].corr(min_periods=500)
        C = C.dropna(how="all").dropna(axis=1, how="all")
        _, ne = neff(C)
        out[b] = ne
    return out


def neff(C: pd.DataFrame) -> tuple[float, float]:
    n = C.shape[0]
    if n < 2:
        return np.nan, np.nan
    rbar = (C.values.sum() - n) / (n * (n - 1))
    return rbar, n / (1 + (n - 1) * rbar)


def strategy_returns(markets: list[str]) -> pd.DataFrame:
    out = {}
    for m in markets:
        df = core.load(m)
        out[m] = (np.sign(agreement(df["close"])).shift(1) * df["ret"]).rename(m)
    return pd.concat(out.values(), axis=1, sort=False)


def main():
    print("Building daily bars for any new instruments")
    build_missing_daily()

    all_mkts = sorted(os.path.basename(p).replace("_d1.csv", "")
                      for p in glob.glob(os.path.join(core.DATA, "*_d1.csv")))
    new = [m for m in all_mkts if m not in core.MARKETS]
    print(f"\n{len(core.MARKETS)} original + {len(new)} new = {len(all_mkts)} markets")
    if new:
        print("  new:", ", ".join(new))

    for label, mkts in (("original 11", core.MARKETS), ("all markets", all_mkts)):
        if len(mkts) < 2:
            continue
        A = pd.concat([core.load(m)["ret"].rename(m) for m in mkts],
                      axis=1, sort=False)
        S = strategy_returns(mkts)
        print(f"\n{'='*78}\n{label} ({len(mkts)})\n{'='*78}")
        for what, X in (("asset returns", A), ("strategy returns", S)):
            # pairwise-complete: the new markets have shorter histories
            C = X.corr(min_periods=500)
            rbar, ne = neff(C.dropna(how="all").dropna(axis=1, how="all"))
            print(f"  {what:<18} mean rho {rbar:+.3f}   N_eff {ne:.2f} of {C.shape[0]}"
                  f"   ceiling {1/rbar:.1f}" if rbar > 0 else
                  f"  {what:<18} mean rho {rbar:+.3f}   N_eff {ne:.2f}")

    if new:
        S = strategy_returns(all_mkts)
        C = S.corr(min_periods=500)
        rbar, ne = neff(C)
        print(f"\n{'='*78}")
        print(f"GATE: N_eff on strategy returns = {ne:.2f}   "
              f"[pre-registered threshold: >= {GATE_NEFF}]")
        print("  bootstrapping the gate (R1) — a point estimate 0.01 above a "
              "threshold is not a pass...")
        bs = neff_bootstrap(S)
        lo, hi = np.nanpercentile(bs, [5, 95])
        frac = float(np.nanmean(bs >= GATE_NEFF))
        print(f"  stationary block bootstrap: median {np.nanmedian(bs):.2f}, "
              f"5th-95th {lo:.2f} - {hi:.2f}")
        print(f"  fraction of draws clearing {GATE_NEFF}: {100*frac:.1f}%")
        verdict = (ne >= GATE_NEFF) and (lo >= GATE_NEFF)
        print("PASS — N_eff clears the threshold on the point estimate AND the "
              "5th percentile" if verdict else
              f"FAIL — the interval does not clear {GATE_NEFF}. The point estimate "
              f"of {ne:.2f} has no resolution at this threshold; the new markets "
              "did not buy enough independence to make portfolio construction "
              "deliver what the diversification argument promises, and saying so "
              "is the result.")
        # which of the new ones actually helped
        print("\nmean correlation of each new market against the original eleven:")
        for m in new:
            r = C.loc[m, [k for k in core.MARKETS if k in C.columns]].mean()
            print(f"  {m:<12} {r:+.3f}" + ("   <- genuinely outside the cluster"
                                           if abs(r) < 0.10 else ""))
        C.to_csv("g1_strategy_corr.csv")


if __name__ == "__main__":
    main()
