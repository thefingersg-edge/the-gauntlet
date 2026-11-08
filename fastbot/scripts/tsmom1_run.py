#!/usr/bin/env python3
"""TSMOM1 harness (PREREGISTRATION_TSMOM1). One run.  python3 tsmom1_run.py   (also used by TSMOM2 with --markets)
I am not a financial adviser. This is a measurement, not a recommendation."""
import os, sys, csv, math, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tf1_run import load_ohlc
import engine as E
FB = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."); END = pd.Timestamp("2026-09-26", tz="UTC")
ERAS = ((2006, 2012), (2013, 2019), (2020, 2026)); TARGET = 0.10; CAP = 3.0
def daily(inst, data_dir):
    D = load_ohlc(data_dir, inst, "15m", 900)
    df = pd.DataFrame({"C": D["C"], "spr": D["spread"]}, index=D["t"]); df = df[df.index < END]
    loc = df.index.tz_convert(E.TZ); df = df[(loc.hour == 15) & (loc.minute == 45) & (loc.weekday < 5)]
    df.index = df.index.tz_convert(E.TZ).normalize().tz_localize(None); return df[~df.index.duplicated()]
def policy():
    return {r["month"]: float(r["rate_pct"]) / 100 for r in csv.DictReader(open(os.path.join(FB, "data", "policy_rates.csv"))) if r["currency"] == "USD"}
def run_market(df, lookback_m, pol, financing=True):
    c = df["C"]; r = c.pct_change().fillna(0.0); var = (r ** 2).ewm(com=60).mean(); sig = np.sqrt(var * 252)
    me = c.groupby([c.index.year, c.index.month]).tail(1).index          # month-end trading days
    w_target = pd.Series(np.nan, index=c.index)
    for d in me:
        past = c[:d]; i0 = past.index.searchsorted(d - pd.DateOffset(months=lookback_m))
        if i0 == 0 or sig[d] <= 0: continue
        s = np.sign(past.iloc[-1] / past.iloc[i0 - 1] - 1); w_target[d] = float(np.clip(s * TARGET / sig[d], -CAP, CAP))
    w = w_target.ffill().shift(1).fillna(0.0)                # set at month-end close, traded at next day's close
    held = w.shift(1).fillna(0.0)                             # position earning day t's return
    gross = held * r
    trade_cost = (w - held).abs() * df["spr"] / 2
    days = pd.Series(c.index, index=c.index).diff().dt.days.fillna(1)
    rate = pd.Series([pol.get(d.strftime("%Y-%m"), 0.02) for d in c.index], index=c.index)
    fin = np.where(held > 0, -held * (rate + 0.025), -held * (rate - 0.025)) * days / 365 if financing else 0.0
    return gross - trade_cost + fin, gross
def stats(x):
    x = x[x.index >= "2006-01-01"]; yrs = len(x) / 252; sh = x.mean() / x.std() * math.sqrt(252) if x.std() > 0 else float("nan")
    eq = (1 + x).cumprod(); dd = (eq / eq.cummax() - 1).min()
    return sh, sh * math.sqrt(yrs), x.mean() * 252, dd, yrs
def main():
    mk = sys.argv[sys.argv.index("--markets") + 1].split(",") if "--markets" in sys.argv else ["XAU_USD", "SPX500_USD", "NAS100_USD"]
    tag = sys.argv[sys.argv.index("--tag") + 1] if "--tag" in sys.argv else "tsmom1"
    log = os.path.join(FB, "data", f"run_{tag}.log")
    if os.path.exists(log): sys.exit("already run")
    OUT = []; P = lambda s="": (print(s, flush=True), OUT.append(s))
    P(f"tsmom1_run.py  {tag}  markets {','.join(mk)}\n  I am not a financial adviser. This is a measurement, not a recommendation.\n")
    pol = policy(); DF = {m: daily(m, os.path.join(FB, "data", "v24")) for m in mk}
    idx = sorted(set.intersection(*[set(d.index) for d in DF.values()])); DF = {m: d.loc[idx] for m, d in DF.items()}
    res = {}
    for L in (12, 3, 1):
        nets = {m: run_market(DF[m], L, pol)[0] for m in mk}; res[L] = (pd.concat(nets, axis=1).mean(axis=1), nets)
    port, nets = res[12]; sh, t, ann, dd, yrs = stats(port)
    g1 = t >= 2.0; er = [port[(port.index.year >= a) & (port.index.year <= b)].sum() for a, b in ERAS]; g2 = all(e > 0 for e in er)
    P(f"  portfolio (12-month lookback, net): Sharpe {sh:+.2f} (t {t:+.2f}, {yrs:.1f} yrs), return {ann*100:+.1f}%/yr, worst drawdown {dd*100:.1f}%  -> G1 {'PASS' if g1 else 'FAIL'}")
    P("  G2 net by era: " + "  ".join(f"{a}-{b % 100:02d} {e*100:+.1f}%" for (a, b), e in zip(ERAS, er)) + f"  -> {'PASS' if g2 else 'FAIL'}")
    P("\n  reported:")
    for L in (3, 1):
        s_ = stats(res[L][0]); P(f"    lookback {L:>2}m portfolio: Sharpe {s_[0]:+.2f} (t {s_[1]:+.2f})")
    for m in mk:
        s_ = stats(nets[m]); g = stats(run_market(DF[m], 12, pol, financing=False)[0]); P(f"    {m:<11} 12m: net Sharpe {s_[0]:+.2f} (t {s_[1]:+.2f}), no financing {g[0]:+.2f}, drawdown {s_[3]*100:.0f}%")
    bh = {}
    for m in mk:
        c = DF[m]["C"]; r = c.pct_change().fillna(0); sig = np.sqrt((r ** 2).ewm(com=60).mean() * 252); w = np.clip(TARGET / sig, 0, CAP).shift(2).fillna(0)
        rate = pd.Series([pol.get(d.strftime("%Y-%m"), 0.02) for d in c.index], index=c.index); days = pd.Series(c.index, index=c.index).diff().dt.days.fillna(1)
        bh[m] = w * r - (w.diff().abs() * DF[m]["spr"] / 2).fillna(0) - w * (rate + 0.025) * days / 365
    b = stats(pd.concat(bh, axis=1).mean(axis=1)); P(f"    equal-risk buy-and-hold, same costs: Sharpe {b[0]:+.2f} (t {b[1]:+.2f}), drawdown {b[3]*100:.0f}%")
    P(f"\n  VERDICT {tag.upper()} G1 {'P' if g1 else 'F'} G2 {'P' if g2 else 'F'} -> {'PASS' if g1 and g2 else 'FAIL'}")
    open(log, "w").write("\n".join(OUT) + "\n")
if __name__ == "__main__": main()
