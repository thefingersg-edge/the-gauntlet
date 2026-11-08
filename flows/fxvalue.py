#!/usr/bin/env python3
"""fxvalue.py -- FLOWS-13, implements PREREGISTRATION_FXVALUE.md.  --self-test | --check-inputs | --run
Implementation readings fixed before the run: quarterly CPIs (AUD, NZD) are used from
the second month after their quarter ends; the euro's price level and short rate are
Germany's to 1998-12 and the euro area's after, chained on growth rates."""
from __future__ import annotations
import argparse, io, json, os, sys
import numpy as np
import pandas as pd
import common as C

NAME = "FXVALUE"
LR = os.path.join(C.FDATA, "longrun")
CCY = ["EUR", "JPY", "GBP", "CHF", "CAD", "AUD", "NZD", "SEK", "NOK"]
ISO = {"JPY": "JP", "GBP": "GB", "CHF": "CH", "CAD": "CA", "AUD": "AU", "NZD": "NZ", "SEK": "SE", "NOK": "NO"}
SPOT = {"JPY": ("DEXJPUS", -1), "GBP": ("DEXUSUK", 1), "CHF": ("DEXSZUS", -1), "CAD": ("DEXCAUS", -1),
        "AUD": ("DEXUSAL", 1), "NZD": ("DEXUSNZ", 1), "SEK": ("DEXSDUS", -1), "NOK": ("DEXNOUS", -1)}
THIRDS = (("1990-2002", "1990-01-01", "2002-12-31"), ("2003-2014", "2003-01-01", "2014-12-31"), ("2015-2026", "2015-01-01", "2026-08-31"))
LOG, RES = (os.path.join(C.FDATA, f) for f in ("fxvalue_run.log", "fxvalue_result.json"))


def s(name) -> pd.Series:
    p = os.path.join(LR, f"{name}.csv")
    if not os.path.exists(p):
        return None
    d = pd.read_csv(p, parse_dates=["date"]).set_index("date")["value"].astype(float)
    return d[d.index <= C.END]


def mend(x: pd.Series) -> pd.Series:
    m = x.groupby(x.index.to_period("M")).last(); m.index = m.index.to_timestamp(); return m


def chain(old: pd.Series, new: pd.Series, at="1999-01-01") -> pd.Series:
    """Level series: `old` to before `at`, then `new`'s growth from `at` on."""
    old, new = old.dropna(), new.dropna()
    base = old[old.index < at].iloc[-1]; g = new[new.index >= at]
    prev_new = new[new.index < at]
    ref = prev_new.iloc[-1] if len(prev_new) else g.iloc[0]
    return pd.concat([old[old.index < at], base * g / ref])


def bis(area):
    """Amendment A1: BIS WS_LONG_CPI, lagged as registered (monthly +1 month;
    quarterly usable from the second month after the quarter ends)."""
    p = os.path.join(LR, f"BISCPI_{area}.csv")
    if not os.path.exists(p):
        return None
    d = pd.read_csv(p, dtype=str)
    v = d["value"].astype(float)
    if d["period"].str.contains("Q").any():
        per = pd.PeriodIndex(d["period"].str.replace("-", ""), freq="Q")
        idx = per.to_timestamp(how="start") + pd.DateOffset(months=4)       # Q1 (Jan) -> usable from May
        return pd.Series(v.to_numpy(), index=idx).resample("MS").ffill()
    idx = pd.PeriodIndex(d["period"], freq="M").to_timestamp()
    return pd.Series(v.to_numpy(), index=idx).shift(1, freq="MS")


FILLED = {}


def rate_of(c3, c2):
    a, b = s(f"IR3TIB01{c3}M156N"), s(f"IRSTCI01{c3}M156N")
    x = a.combine_first(b) if a is not None and b is not None else (a if a is not None else b)
    if x is None:
        return None
    x = x.resample("MS").last()
    full = x.reindex(pd.date_range(x.index[0], "2026-08-01", freq="MS"))
    f = full.ffill(limit=8)
    FILLED[c2] = int(f.notna().sum() - full.notna().sum())
    return f


def build():
    """Amendment A1 inputs (BIS CPI, FRED EXGEUS, spliced short rates)."""
    need = []
    spot = {}
    eur_new, dem = s("DEXUSEU"), s("EXGEUS")
    if eur_new is None or dem is None:
        need.append("DEXUSEU/EXGEUS")
    else:
        spot["EUR"] = pd.concat([mend(1.95583 / dem[dem.index < "1999-01-01"]), mend(eur_new)])
    for c, (sid, sg) in SPOT.items():
        x = s(sid)
        if x is None: need.append(sid); continue
        spot[c] = mend(x if sg > 0 else 1.0 / x)
    area = {"JPY": "JP", "GBP": "GB", "CHF": "CH", "CAD": "CA", "AUD": "AU", "NZD": "NZ", "SEK": "SE", "NOK": "NO"}
    cpi = {}
    for c in CCY:
        if c == "EUR":
            de, xm = bis("DE"), bis("XM")
            if de is None or xm is None: need.append("BIS CPI DE/XM"); continue
            cpi[c] = chain(de, xm, at="1999-02-01")          # lagged index: Jan-1999 data usable from Feb
        else:
            x = bis(area[c])
            if x is None: need.append(f"BIS CPI {area[c]}"); continue
            cpi[c] = x
    usl = bis("US")
    rate = {}
    for c in CCY:
        if c == "EUR":
            de, ez = rate_of("DE", "DEM"), rate_of("EZ", "EUR")
            if de is None or ez is None: need.append("EUR rate"); continue
            rate[c] = pd.concat([de[de.index < "1999-01-01"], ez[ez.index >= "1999-01-01"]])
        else:
            x = rate_of(ISO[c], c)
            if x is None: need.append(f"rate {c}"); continue
            rate[c] = x
    tb = s("TB3MS")
    if usl is None or tb is None: need.append("BIS CPI US/TB3MS")
    if need:
        raise SystemExit(f"STOP: missing inputs {need} -- FLOWS-13 is void for want of data (amendment A1)")
    idx = pd.date_range("1971-01-01", "2026-08-01", freq="MS")
    S = pd.DataFrame({c: spot[c].reindex(idx) for c in CCY})
    P = pd.DataFrame({c: cpi[c].reindex(idx) for c in CCY})
    I = pd.DataFrame({c: rate[c].reindex(idx) for c in CCY})
    return S, P, I, usl.reindex(idx), tb.reindex(idx)


def build_base_unused():
    need = []
    spot = {}
    eur_new, dem = s("DEXUSEU"), s("DEXGEUS")
    if eur_new is None or dem is None:
        need.append("DEXUSEU/DEXGEUS")
    else:
        spot["EUR"] = mend(pd.concat([(1.95583 / dem)[dem.index < "1999-01-04"], eur_new]))
    for c, (sid, sg) in SPOT.items():
        x = s(sid)
        if x is None: need.append(sid); continue
        spot[c] = mend(x if sg > 0 else 1.0 / x)
    us = s("CPIAUCSL")
    cpi = {}
    for c in CCY:
        if c == "EUR":
            de, ez = s("CPALTT01DEM661N"), (s("CPALTT01EZM661N") if s("CPALTT01EZM661N") is not None else s("CP0000EZ19M086NEST"))
            if de is None or ez is None: need.append("EUR CPI"); continue
            cpi[c] = chain(de, ez).shift(1, freq="MS")
        elif c in ("AUD", "NZD"):
            q = s(f"CPALTT01{ISO[c]}Q661N")
            if q is None: need.append(f"CPALTT01{ISO[c]}Q661N"); continue
            q.index = q.index + pd.DateOffset(months=4)              # Q1 (dated Jan) usable from May
            cpi[c] = q.resample("MS").ffill()
        else:
            x = s(f"CPALTT01{ISO[c]}M661N")
            if x is None: need.append(f"CPALTT01{ISO[c]}M661N"); continue
            cpi[c] = x.shift(1, freq="MS")
    usl = us.shift(1, freq="MS") if us is not None else None
    rate = {}
    for c in CCY:
        if c == "EUR":
            de = s("IR3TIB01DEM156N") if s("IR3TIB01DEM156N") is not None else s("IRSTCI01DEM156N")
            ez = s("IR3TIB01EZM156N") if s("IR3TIB01EZM156N") is not None else s("IRSTCI01EZM156N")
            if de is None or ez is None: need.append("EUR rate"); continue
            rate[c] = pd.concat([de[de.index < "1999-01-01"], ez[ez.index >= "1999-01-01"]])
        else:
            x = s(f"IR3TIB01{ISO[c]}M156N")
            x = x if x is not None else s(f"IRSTCI01{ISO[c]}M156N")
            if x is None: need.append(f"rate {c}"); continue
            rate[c] = x
    tb = s("TB3MS")
    if us is None or tb is None: need.append("CPIAUCSL/TB3MS")
    if need:
        raise SystemExit(f"STOP: missing inputs {need} -- an amendment is needed before this test can run")
    idx = pd.date_range("1971-01-01", "2026-08-01", freq="MS")
    S = pd.DataFrame({c: spot[c].reindex(idx) for c in CCY})
    P = pd.DataFrame({c: cpi[c].reindex(idx) for c in CCY})
    I = pd.DataFrame({c: rate[c].reindex(idx) for c in CCY})
    Pu, Iu = usl.reindex(idx), tb.reindex(idx)
    return S, P, I, Pu, Iu


def portfolio(S, P, I, Pu, Iu, start="1990-01-01"):
    q = np.log(S) + np.log(P).sub(np.log(Pu), axis=0)
    val = -(q - q.shift(60))
    spot_ret = S.shift(-1) / S - 1                                       # held t -> t+1
    carry = I.sub(Iu, axis=0) / 1200.0
    exc = spot_ret + carry
    rows, prev_w = [], pd.Series(0.0, index=S.columns)
    for t in val.index:
        v = val.loc[t]
        if t < pd.Timestamp(start) or v.isna().any() or exc.loc[t].isna().any():
            continue
        rk = v.sort_values()
        w = pd.Series(0.0, index=S.columns); w[rk.index[-3:]] = 1 / 3; w[rk.index[:3]] = -1 / 3
        rows.append(dict(date=t + pd.offsets.MonthBegin(1), exc=float((w * exc.loc[t]).sum()),
                         spot=float((w * spot_ret.loc[t]).sum()), turnover=float((w - prev_w).abs().sum())))
        prev_w = w
    return pd.DataFrame(rows).set_index("date")


def nw(x, lags=3):
    b, se, t, n = C.ols_nw(np.asarray(x, float), np.ones((len(x), 1)), lags)
    return float(b[0]), float(t[0]), int(n)


def run():
    buf = io.StringIO()
    def say(*a):
        print(*a); print(*a, file=buf)
    pin = C.check_pin(NAME); C.check_pin("FXVALUE_A1")
    pf = portfolio(*build())
    say(f"FLOWS-13 FXVALUE  prereg {pin[:16]} + A1  months {len(pf)} {pf.index[0].date()}..{pf.index[-1].date()}  rate months carried forward: {FILLED}")
    m, t, n = nw(pf["exc"])
    say(f"\n  G1 long-short excess {m*100:+.3f}%/month (ann {m*1200:+.2f}%)  t {t:+.2f}  Sharpe {pf['exc'].mean()/pf['exc'].std()*np.sqrt(12):+.2f}")
    th = {}
    for lab, a, b in THIRDS:
        th[lab] = dict(zip(("mean", "t", "n"), nw(pf.loc[(pf.index >= a) & (pf.index <= b), "exc"])))
        say(f"  {lab}: {th[lab]['mean']*100:+.3f}% t {th[lab]['t']:+.2f}")
    ms, ts, _ = nw(pf["spot"]); say(f"  G3 spot-only {ms*100:+.3f}% t {ts:+.2f}")
    net = pf["exc"] - 0.0002 * pf["turnover"] - 0.01 / 12
    mn, tn, _ = nw(net); say(f"  G4 net {mn*100:+.3f}%/month t {tn:+.2f} (mean turnover {pf['turnover'].mean():.2f})")
    G = {"G1": m > 0 and t >= 2.0, "G2": all(v["mean"] > 0 for v in th.values()) and th["2015-2026"]["mean"] >= 0.5 * m,
         "G3": ms > 0, "G4": mn > 0}
    kill = [k for k, gg in (("K1", "G1"), ("K2", "G2"), ("K3", "G4")) if not G[gg]]
    res = {"pin": pin, "mean": m, "t": t, "thirds": th, "spot": ms, "net": mn, "gates": G,
           "verdict": "DEAD " + ",".join(kill) if kill else ("PASS" if G["G3"] else "PASS but carry-driven (G3)")}
    say("\n  " + "  ".join(f"{k} {'PASS' if v else 'FAIL'}" for k, v in G.items()) + f"   VERDICT: {res['verdict']}")
    open(LOG, "w").write(buf.getvalue()); json.dump(res, open(RES, "w"), indent=1, default=float)
    return 0


def check_inputs():
    print(f"prereg {C.check_pin(NAME)[:16]} OK")
    S, P, I, Pu, Iu = build()
    full = (S.notna() & P.notna() & I.notna()).all(axis=1)
    print(f"all nine currencies with spot, CPI and rate from {full[full].index[0].date()}; value needs +60 months")
    return 0


def self_test():
    ok = True
    def check(n, c):
        nonlocal ok; print(f"  {'PASS' if c else 'FAIL'}  {n}"); ok = ok and bool(c)
    idx = pd.date_range("1980-01-01", "2026-08-01", freq="MS")
    rng = np.random.default_rng(8)
    k = len(CCY)
    # mean-reverting real rates: cheap currencies (low q vs 5y ago) appreciate
    q = np.zeros((len(idx), k)); eps = rng.normal(0, 0.02, (len(idx), k))
    for i in range(1, len(idx)):
        q[i] = q[i - 1] + eps[i] - 0.03 * (q[i - 1] - (q[i - 61] if i > 60 else 0))
    S = pd.DataFrame(np.exp(q), index=idx, columns=CCY)
    P = pd.DataFrame(1.0, index=idx, columns=CCY); I = pd.DataFrame(2.0, index=idx, columns=CCY)
    Pu = pd.Series(1.0, index=idx); Iu = pd.Series(2.0, index=idx)
    pf = portfolio(S, P, I, Pu, Iu)
    m, t, _ = nw(pf["exc"])
    check(f"planted value reversion is found (t {t:+.1f})", m > 0 and t > 2)
    check("equal rates: excess return == spot return", np.allclose(pf["exc"], pf["spot"]))
    a = pd.Series([1.0, 2.0], index=pd.to_datetime(["1998-12-01", "1999-01-01"]))
    b = pd.Series([50.0, 55.0], index=pd.to_datetime(["1998-12-01", "1999-01-01"]))
    ch = chain(a, b)
    check("chain: old level then new growth", abs(ch.iloc[-1] - 1.0 * 55 / 50) < 1e-12 and ch.iloc[0] == 1.0)
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); g = ap.add_mutually_exclusive_group(required=True)
    for f in ("--self-test", "--check-inputs", "--run"): g.add_argument(f, action="store_true")
    a = ap.parse_args()
    sys.exit(self_test() if a.self_test else check_inputs() if a.check_inputs else run())
