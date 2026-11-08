"""
C2 — verification for C1.

The candidate (|A| as a size) failed its pre-registered gates. What the run DID
surface is volatility targeting again, so that is now held to the same standard
rather than being claimed as a win:

  1. paired per-market differences — does each ingredient actually add?
  2. shuffled-scale null — same leverage distribution, wrong timing
  3. plateau vs spike across the vol window and target
  4. lookahead audit on the winning rule
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import core
from c1_agreement import agreement, stats, VOL_TARGET, VOL_WIN, LEV_CAP, NULL_LAG

COST = 1.0


def rules(df, vol_win=VOL_WIN, target=VOL_TARGET, cap=LEV_CAP):
    close, ret = df["close"], df["ret"]
    A = agreement(close)
    sA = np.sign(A).astype(float)
    vol = ret.rolling(vol_win).std() * np.sqrt(core.ppy(ret))
    scale = (target / vol).clip(upper=cap)
    return dict(
        agree_sign_only=sA,
        agree_linear=A.astype(float),
        voltgt_agree_sign=(sA * scale).astype(float),
        null_shuffled_scale=(sA * scale.shift(NULL_LAG)).astype(float),
        const_scale_matched=(sA * scale.mean()).astype(float),
    )


def per_market_sharpe(fn=rules, **kw) -> pd.DataFrame:
    out = {}
    for m in core.MARKETS:
        df = core.load(m)
        out[m] = {k: stats(p, df["ret"], COST)["sharpe"] for k, p in fn(df, **kw).items()}
    return pd.DataFrame(out).T


def paired(P: pd.DataFrame, a: str, b: str) -> str:
    d = (P[a] - P[b]).dropna()
    se = d.std() / np.sqrt(len(d))
    return (f"  {a} - {b}:  mean {d.mean():+.3f}  SE {se:.3f}  "
            f"t {d.mean()/se:+.2f}  wins {int((d>0).sum())}/{len(d)}")


def main():
    P = per_market_sharpe()
    print("=" * 90)
    print("1-2. Per-market Sharpe, and what each ingredient adds")
    print("=" * 90)
    print(P.to_string(float_format=lambda x: f"{x:+.3f}"))
    print()
    print(paired(P, "voltgt_agree_sign", "agree_sign_only"))
    print(paired(P, "voltgt_agree_sign", "null_shuffled_scale"))
    print(paired(P, "voltgt_agree_sign", "const_scale_matched"))
    print(paired(P, "agree_linear", "agree_sign_only"))
    print("  (const_scale_matched applies the SAME average leverage with no timing —")
    print("   Sharpe is scale-invariant, so it must equal agree_sign_only; a sanity check)")

    print("\n" + "=" * 90)
    print("3. Plateau or spike — vol-target rule across its two parameters")
    print("=" * 90)
    rows = []
    for win in (20, 40, 60, 120, 250):
        r = {"vol_window": win}
        for tgt in (0.05, 0.10, 0.15, 0.20):
            P2 = per_market_sharpe(vol_win=win, target=tgt)
            ports = []
            for m in core.MARKETS:
                df = core.load(m)
                ports.append(stats(rules(df, vol_win=win, target=tgt)["voltgt_agree_sign"],
                                   df["ret"], COST)["series"].rename(m))
            r[f"tgt{int(tgt*100)}"] = core.sharpe(pd.concat(ports, axis=1).mean(axis=1))
        rows.append(r)
    t = pd.DataFrame(rows)
    print(t.to_string(index=False, float_format=lambda x: f"{x:+.3f}"))
    span = t[[c for c in t.columns if c.startswith("tgt")]].values
    print(f"\n  spread across all 20 settings: {span.min():+.3f} to {span.max():+.3f} "
          f"(range {span.max()-span.min():.3f})")
    print("  a PLATEAU is a small range with no isolated peak; a SPIKE is one cell "
          "well above its neighbours")

    print("\n" + "=" * 90)
    print("4. Lookahead audit — one extra bar of delay on the winning rule")
    print("=" * 90)
    for m in ("xauusd", "spx500usd", "eurusd"):
        df = core.load(m)
        p = rules(df)["voltgt_agree_sign"]
        a = stats(p, df["ret"], COST)["sharpe"]
        b = stats(p.shift(1), df["ret"], COST)["sharpe"]
        print(f"  {m:<10} as run {a:+.3f}   one bar later {b:+.3f}   delta {b-a:+.3f}")
    P.to_csv("c2_per_market.csv")
    t.to_csv("c2_plateau.csv", index=False)


if __name__ == "__main__":
    main()
