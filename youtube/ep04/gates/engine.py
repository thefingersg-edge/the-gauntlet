#!/usr/bin/env python3
"""Gate engine for episodes 4/5 — one implementation, six strategies.

Every arm is scored by THIS file. No per-arm special-casing, no arm's own
cost model, no arm's own split. An arm's self-reported figures are a claim
to be checked, never a result.

Execution model, applied identically to every arm:
    signals are computed from bar t's CLOSE
    orders fill at bar t+1's OPEN (or the stated limit/stop price)
    nothing reads a value unknown at the signal bar

Costs, applied identically to every arm:
    round-trip spread, per market, charged once per trade
    financing at 2.5%/365 on notional per CALENDAR day held, both
    directions -- the OANDA markup convention already used in
    pineport/carry_cost.py

    *** THE SPREAD TABLE BELOW NEEDS DAVE'S SIGN-OFF BEFORE ANY RESULT
        COUNTS. It is the single number that decides several arms. ***
"""
from __future__ import annotations
import os, sys
from dataclasses import dataclass
import numpy as np
import pandas as pd

HOME = os.path.expanduser("~")
DATA = os.path.join(HOME, "mnt", "Claude", "pineport", "adaptive", "data")

MARKETS = ["eurusd", "gbpusd", "usdjpy", "usdcad", "audusd", "eurgbp", "eurjpy",
           "xauusd", "xagusd", "xptusd", "xcuusd",
           "spx500usd", "nas100usd", "de30eur",
           "bcousd", "natgasusd",
           "usb10yusd", "de10ybeur",
           "cornusd", "wheatusd", "sugarusd"]

# fixed in PREREGISTRATION.md section 4, before any gate was run
ERAS = {
    "E1": ("2005-01-01", "2012-03-31"),
    "E2": ("2012-04-01", "2019-06-30"),
    "E3": ("2019-07-01", "2026-08-31"),
}

# MEASURED round-trip spread, as a FRACTION of price.
# Source: OANDA's own bid and ask hourly candle streams, 2024-01 to 2026-11,
# median of (ask-bid)/mid over 07:00-21:00 UTC, doubled for a round trip.
# See measure_spread.py and ../COST_MODEL.md.
#
# This REPLACES a table that was copied verbatim from ARM B's own generated
# cost assumptions -- i.e. one contestant's guess used to judge the other
# five. The measured figures differ from that guess in BOTH directions:
# index spreads were overstated by 2-2.6x, soft commodities understated by
# up to 1.9x. Neither error was deliberate and both are now gone.
SPREAD_RT = {
    "eurusd": 0.00028, "gbpusd": 0.00028, "usdjpy": 0.00021,
    "usdcad": 0.00026, "audusd": 0.00039, "eurgbp": 0.00032,
    "eurjpy": 0.00028,
    "xauusd": 0.00032, "xagusd": 0.00124, "xptusd": 0.00333,
    "xcuusd": 0.00079,
    "spx500usd": 0.00015, "nas100usd": 0.00016, "de30eur": 0.00022,
    "bcousd": 0.00088, "natgasusd": 0.00435,
    "usb10yusd": 0.00046, "de10ybeur": 0.00023,
    "cornusd": 0.00464, "wheatusd": 0.00373, "sugarusd": 0.00289,
}

# ---------------------------------------------------------------- v2 costs
# ENGINE_COSTS_v2, partial. Written 2026-11-07 from ARM G's cost spec, but
# IMPLEMENTED HERE, not by the arm that wrote it: a subject of the study does
# not write the code that scores it.
#
# FUTURES-BASED CFDs: the futures roll sits in OANDA's financing line, not in
# the price. Brent's implied benchmark is -46.1%/yr -- a long EARNS ~43.6%,
# a short PAYS ~48.6% (pineport/FINDINGS_FINANCING_RATES.md, measured
# 2026-10-11). We charge a flat 2.5%, which is wrong by two orders of
# magnitude AND the wrong sign for longs. No F1/F2 history exists here to
# price it properly, so these instruments are marked UNPRICED: their results
# are reported and excluded from any tradeable claim, per ENGINE_COSTS_v2
# section 2.4. Brent is measured; the other five are presumed by analogy and
# flagged for the same reason.
UNPRICED = {"bcousd", "natgasusd", "cornusd", "wheatusd", "sugarusd", "xcuusd"}

# OANDA's markup is a constant 2.50% on indices and Brent; metals are the
# outlier at 1.19%, because they are priced off the pair's rate differential.
MARKUP = {m: 0.0119 for m in ("xauusd", "xagusd", "xptusd")}
DEFAULT_MARKUP = 0.025

# OANDA's convention: long pays (b + m), short RECEIVES (b - m), where b is
# the overnight rate of the instrument's currency. v1 charged only m, in both
# directions, so longs were undercharged by b and shorts under-credited by b.
#
# USD benchmark: Fed funds effective (FRED DFF), monthly, 2004-12 to 2026-11.
# Validated against the rate cards -- DFF today is 3.88%, which is exactly the
# implied b on the SPX500 and NAS100 cards (FINDINGS_FINANCING_RATES.md).
# Monthly resolution is adequate: DFF is a policy rate and is piecewise
# constant between FOMC moves.
#
# EUR IS NOT IMPLEMENTED. No euro overnight series was reachable (FRED timed
# out from the Mac; no clean series on the TradingView connector). de30eur and
# de10ybeur therefore still carry markup-only financing, and that is stated
# wherever their figures appear.
_USD_CCY = {"eurusd", "gbpusd", "usdjpy", "usdcad", "audusd", "eurgbp", "eurjpy",
            "xauusd", "xagusd", "xptusd", "xcuusd", "spx500usd", "nas100usd",
            "bcousd", "natgasusd", "usb10yusd", "cornusd", "wheatusd", "sugarusd"}
NO_BENCHMARK = {"de30eur", "de10ybeur"}          # EUR, not yet sourced

_rates = None
def benchmark(mkt: str, when) -> float:
    """Annual benchmark rate as a fraction, or 0.0 where not sourced."""
    global _rates
    if mkt in NO_BENCHMARK:
        return 0.0
    if _rates is None:
        import os
        f = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "rates_usd_dff_monthly.csv")
        _rates = pd.read_csv(f, parse_dates=["time"]).set_index("time")["rate_pct"] / 100.0
    v = _rates.asof(pd.Timestamp(when))
    return float(v) if np.isfinite(v) else 0.0

FINANCING_ANNUAL = 0.025          # OANDA markup, per carry_cost.py
EFFECT_SIZE_MIN = 0.002           # gate 3: 0.2% per trade after costs
SAMPLE_MIN = 200                  # gate 4
BREADTH_MIN = 14                  # gate 2, of 21
ROBUST_FRACTION = 0.80            # gate 5
ROBUST_PCT = 0.25                 # gate 5: uniform +/-25% of each parameter's
                                  # own value, all arms, fixed 2026-11-02
                                  # before any arm but F part A was run


# ---------------------------------------------------------------- data

_cache: dict[str, pd.DataFrame] = {}

def load(mkt: str) -> pd.DataFrame:
    if mkt not in _cache:
        df = pd.read_csv(os.path.join(DATA, f"{mkt}_d1.csv"), parse_dates=["time"])
        df = df.set_index("time").sort_index()
        df = df[~df.index.duplicated(keep="first")]
        _cache[mkt] = df
    return _cache[mkt]


def era_of(ts) -> str:
    ts = pd.Timestamp(ts)
    for name, (a, b) in ERAS.items():
        if pd.Timestamp(a, tz="UTC") <= ts <= pd.Timestamp(b, tz="UTC"):
            return name
    return "OUT"


# ---------------------------------------------------------------- trades

@dataclass
class Trade:
    market: str
    direction: int          # +1 long, -1 short
    entry_date: pd.Timestamp
    exit_date: pd.Timestamp
    entry_px: float
    exit_px: float
    reason: str = ""

    @property
    def gross(self) -> float:
        """signed return on notional, before costs"""
        return self.direction * (self.exit_px / self.entry_px - 1.0)

    @property
    def nights(self) -> int:
        # calendar nights held, counted by date boundaries crossed -- not by
        # elapsed hours. A 16:00 -> 09:00 overnight hold is ONE night even
        # though it is 17 hours; a Friday 16:00 -> Monday 09:00 hold is three.
        return max(0, (self.exit_date.date() - self.entry_date.date()).days)

    def cost(self) -> float:
        spread = SPREAD_RT[self.market]
        # v2 partial: the markup is per instrument. The BENCHMARK half of the
        # charge (long pays b+m, short receives b-m) still needs an overnight
        # rate series and is not yet applied -- see ENGINE_COSTS_v2 section 1.
        m = MARKUP.get(self.market, DEFAULT_MARKUP)
        b = benchmark(self.market, self.entry_date)
        # long pays b + m ; short receives b - m, i.e. is charged m - b
        rate = (b + m) if self.direction > 0 else (m - b)
        fin = rate * self.nights / 365.0
        return spread + fin

    @property
    def unpriced(self) -> bool:
        return self.market in UNPRICED

    @property
    def net(self) -> float:
        return self.gross - self.cost()

    @property
    def era(self) -> str:
        return era_of(self.entry_date)


# ---------------------------------------------------------------- gates

def _mean(xs):
    xs = [x for x in xs if np.isfinite(x)]
    return float(np.mean(xs)) if xs else np.nan


def g1_sign_consistency(trades: list[Trade]) -> dict:
    by = {e: [t.net for t in trades if t.era == e] for e in ERAS}
    means = {e: _mean(v) for e, v in by.items()}
    counts = {e: len(v) for e, v in by.items()}
    signs = [np.sign(m) for m in means.values() if np.isfinite(m)]
    ok = len(signs) == 3 and (all(s > 0 for s in signs) or all(s < 0 for s in signs))
    return {"gate": "1 SIGN CONSISTENCY", "pass": bool(ok),
            "by_era": {e: round(m, 5) for e, m in means.items()},
            "n_by_era": counts}


def g2_breadth(trades: list[Trade]) -> dict:
    """Breadth is counted twice: over everything, and over instruments whose
    financing we can actually price. Only the second may be quoted as a
    tradeable result (ENGINE_COSTS_v2 section 5)."""
    traded = sorted({t.market for t in trades})
    agree = {m: _mean([t.net for t in trades if t.market == m]) for m in traded}
    pos = sum(1 for v in agree.values() if np.isfinite(v) and v > 0)
    priced = [m for m in traded if m not in UNPRICED]
    pos_p = sum(1 for m in priced if np.isfinite(agree[m]) and agree[m] > 0)
    return {"gate": "2 BREADTH", "pass": pos >= BREADTH_MIN,
            "positive": pos, "traded": len(traded), "universe": len(MARKETS),
            "positive_priced_only": f"{pos_p} of {len(priced)}",
            "unpriced_excluded": sorted(set(traded) & UNPRICED) or "none",
            "per_market": {m: (f"{agree[m]:+.5f}" + (" UNPRICED" if m in UNPRICED else ""))
                           for m in traded}}


def g3_effect_size(trades: list[Trade]) -> dict:
    m = _mean([t.net for t in trades])
    return {"gate": "3 EFFECT SIZE", "pass": bool(np.isfinite(m) and m >= EFFECT_SIZE_MIN),
            "mean_net_per_trade": round(m, 5),
            "mean_gross_per_trade": round(_mean([t.gross for t in trades]), 5),
            "mean_cost_per_trade": round(_mean([t.cost() for t in trades]), 5),
            "threshold": EFFECT_SIZE_MIN}


def g4_sample(trades: list[Trade]) -> dict:
    return {"gate": "4 SAMPLE", "pass": len(trades) >= SAMPLE_MIN,
            "n": len(trades), "threshold": SAMPLE_MIN}


def g6_matched_control(trades: list[Trade], seed: int = 20261102,
                       prior_win: int = 20, n_ctrl: int = 50) -> dict:
    """Each trade is compared with same-market, same-era bars in the same
    (prior-return decile x volatility decile) cell, held the same number of
    bars, charged the same costs. Adapted from the implementation already
    used in pineport/adaptive/o1_kalman.py."""
    rng = np.random.default_rng(seed)
    edges = []
    by_mkt: dict[str, list[Trade]] = {}
    for t in trades:
        by_mkt.setdefault(t.market, []).append(t)

    for mkt, ts in by_mkt.items():
        df = load(mkt)
        c = df["close"]
        idx = df.index
        prior = (c / c.shift(prior_win) - 1.0).to_numpy()
        vol = c.pct_change().rolling(prior_win).std().to_numpy()
        era = np.array([era_of(x) for x in idx])
        pd_dec = pd.qcut(pd.Series(prior), 10, labels=False, duplicates="drop").to_numpy()
        vd_dec = pd.qcut(pd.Series(vol), 10, labels=False, duplicates="drop").to_numpy()
        cv = c.to_numpy()
        pos = {d: i for i, d in enumerate(idx)}
        in_trade = np.zeros(len(idx), dtype=bool)
        for t in ts:
            i, j = pos.get(t.entry_date), pos.get(t.exit_date)
            if i is not None and j is not None:
                in_trade[i:j + 1] = True

        for t in ts:
            i = pos.get(t.entry_date); j = pos.get(t.exit_date)
            if i is None or j is None:
                continue
            h = j - i
            if h <= 0:
                continue
            cell = ((era == era[i]) & (pd_dec == pd_dec[i]) & (vd_dec == vd_dec[i])
                    & ~in_trade & np.isfinite(cv))
            cand = np.flatnonzero(cell)
            cand = cand[(cand + h) < len(cv)]
            if len(cand) == 0:
                continue
            pick = rng.choice(cand, size=min(n_ctrl, len(cand)), replace=False)
            ctrl_gross = t.direction * np.mean(cv[pick + h] / cv[pick] - 1.0)
            ctrl_net = ctrl_gross - t.cost()      # same costs, same horizon
            edges.append(t.net - ctrl_net)

    e = _mean(edges)
    cover = len(edges) / len(trades) if trades else 0.0
    out = {"gate": "6 MATCHED CONTROL",
           "edge_vs_control": round(e, 5), "n_matched": len(edges),
           "coverage": f"{cover:.0%} of {len(trades)} trades"}
    if cover < 0.50:
        # A strategy that is in the market almost all the time leaves too few
        # non-trade bars to match against, so the control pool is a biased
        # remnant rather than a comparison. Reported as not determinable and
        # counted as not cleared -- we cannot confirm an edge over control.
        out["pass"] = False
        out["note"] = ("NOT DETERMINABLE: too few trades could be matched. "
                       "An always-in-market strategy leaves no control bars.")
    else:
        out["pass"] = bool(np.isfinite(e) and e > 0)
    return out


def summarise(name: str, trades: list[Trade], gates: list[dict]) -> str:
    cleared = sum(1 for g in gates if g["pass"])
    out = [f"\n=== {name} — cleared {cleared} of {len(gates)} ===",
           f"    trades {len(trades)}  markets {len({t.market for t in trades})}"]
    for g in gates:
        out.append(f"  [{'PASS' if g['pass'] else 'FAIL'}] {g['gate']}")
        for k, v in g.items():
            if k not in ("gate", "pass"):
                out.append(f"          {k}: {v}")
    return "\n".join(out)


def g5_robustness(run_fn, params: dict, base_net: float,
                  skip: tuple = ()) -> dict:
    """Uniform rule: every parameter perturbed by +/-ROBUST_PCT of its own
    value, rounded to a valid value. `skip` names hypothesis-defining
    parameters held fixed in the SECONDARY run (see GATES_ARM_C.md)."""
    if not np.isfinite(base_net) or base_net <= 0:
        # An edge that is zero or negative cannot be robust. Perturbing it
        # produces ratios that are arithmetically meaningless (a less-negative
        # result scores as a "larger fraction" of a negative base), so the
        # gate is reported as inapplicable and counted as not cleared.
        return {"gate": "5 ROBUSTNESS", "pass": False,
                "rule": f"+/-{ROBUST_PCT:.0%} of each parameter's value",
                "base_net_per_trade": round(base_net, 5),
                "note": "not applicable: base edge is not positive"}
    rows, worst = [], None
    for k, v0 in params.items():
        if k in skip:
            continue
        for sgn in (-1, +1):
            v = v0 * (1.0 + sgn * ROBUST_PCT)
            v = int(round(v)) if isinstance(v0, int) else round(v, 6)
            if v <= 0 or v == v0:
                continue
            m = _mean([t.net for t in run_fn({k: v})])
            frac = m / base_net if base_net else float("nan")
            rows.append((k, v, round(m, 5), round(frac, 3)))
            if worst is None or frac < worst[3]:
                worst = (k, v, round(m, 5), round(frac, 3))
    return {"gate": "5 ROBUSTNESS", "pass": bool(worst and worst[3] >= ROBUST_FRACTION),
            "rule": f"+/-{ROBUST_PCT:.0%} of each parameter's value",
            "base_net_per_trade": round(base_net, 5),
            "worst": (f"{worst[0]}={worst[1]} -> {worst[2]} "
                      f"({worst[3]:.0%} of base)") if worst else None,
            "all": rows}
