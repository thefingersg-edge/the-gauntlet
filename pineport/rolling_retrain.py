#!/usr/bin/env python3
"""Retrain on the trailing N years, trade the next month, roll, repeat.

THE QUESTION

Every test in this project so far has fitted ONE window and scored ONE holdout.
That answers "does a fixed parameter set generalise", and the answer has been
no. It does not answer the question you would actually face: if you re-fit on
the last three years every month and trade the following month, what do you
get? Those differ. A non-stationary edge can be worthless to a frozen config
and still be harvestable by someone who re-fits often enough.

HOW IT AVOIDS FOOLING ITSELF

* NO LOOKAHEAD. The training window ends the instant before the test month
  opens. Parameters chosen in the search have never touched the month scored.

* WARM-UP IS NOT TEST DATA. Indicators need history, so the strategy is run
  over train+test together, but only the equity change ACROSS THE TEST MONTH is
  recorded. Running the one-month slice standalone would start every indicator
  cold and score warm-up noise instead of the strategy.

* THREE NULLS, because "it made money" is not a finding on a rising market:

      buy and hold   did the effort beat owning the thing?
      frozen         one config fitted once at the start and never touched --
                     isolates the value of RE-FITTING from the value of the
                     strategy
      random         parameters drawn from the same ranges with no search at
                     all. If monthly retraining cannot beat random draws, the
                     retraining is theatre.

* THE DISTRIBUTION, not the total. A stitched equity curve hides that one month
  carried everything. Percent of months positive and the worst month are
  reported alongside.

COST. Each month is a full parameter search, so this is the most expensive
thing in the repo. One greedy pass at 100 samples over a 3-year 4H window is
~600 evaluations, about 13s on 7 workers, so ~100 months is roughly 20 minutes.
Checkpointed per month.

    python rolling_retrain.py --csv xauusd_oanda_h4.csv  --tf H4 --samples 100
    python rolling_retrain.py --csv nas100usd_oanda_h4.csv --tf H4 --slippage 2.0 \
        --ladder-mode percent --start 2016-01-01
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import train_tf as T                                   # noqa: E402
from broker import BrokerConfig                        # noqa: E402
from data import _normalise, _read_csv                 # noqa: E402
from metrics import compute_metrics                    # noqa: E402
from strategy import Params, run_strategy              # noqa: E402
import fetch_fred                                      # noqa: E402

CAPITAL = 6000.0


def window_return(df: pd.DataFrame, cfg: dict, t0, t1, slip: float,
                  rates, warm=None) -> tuple[float, int]:
    """Equity change across [t0, t1) only, with everything before t0 as warm-up.

    `warm` bounds how far back the warm-up starts. The first version sliced
    df[:t1] -- the ENTIRE history every month, three times over, which at 15m
    meant simulating ~480k bars to score one month. The result is a RATIO of
    equity at t1 to equity at t0, so the absolute starting point is irrelevant
    provided indicators and position state are warm by t0; the training window
    itself is already orders of magnitude more history than the longest
    lookback needs.
    """
    seg = df[warm:t1] if warm is not None else df[:t1]
    if len(seg) < 50:
        return np.nan, 0
    res = run_strategy(seg, Params(**cfg),
                       BrokerConfig(CAPITAL, 1.0, slippage_points=slip), rates=rates)
    eq = res.equity
    pre = eq[eq.index < t0]
    test = eq[(eq.index >= t0) & (eq.index < t1)]
    if not len(test) or not len(pre) or pre.iloc[-1] <= 0:
        return np.nan, 0
    n = int(((res.trades["entry_time"] >= t0)
             & (res.trades["entry_time"] < t1)).sum()) if len(res.trades) else 0
    return float(test.iloc[-1] / pre.iloc[-1] - 1), n


def fit(csv: str, t_lo, t_hi, scale: float, stop_scale: float, samples: int,
        workers: int, slip: float, objective: str, seed: int, rates,
        frac: float = 0.6) -> dict:
    """One greedy pass over the groups on the training window.

    The window is set through `_init`'s own start/end arguments rather than by
    assigning `_DF` directly. That matters because `search()` hands `_ARGS` to
    the worker-pool initialiser: a hand-set frame is invisible to spawned
    workers, and blanking `_ARGS` makes them die in `_init(*None)`. Going
    through `_init` means every worker reconstructs exactly this window.
    """
    T._DF = None
    # END BOUND MUST BE EXCLUSIVE. `_init` slices with d[:end], and pandas
    # date-string slicing includes the WHOLE of that day -- so passing
    # "2025-06-01" pulled the 21:00 Sunday-open bar into training even though
    # it belongs to the test month. One bar in 4,644, but it is still the
    # search seeing data it is about to be scored on. Backing off one second
    # makes the two windows genuinely disjoint.
    T._init(csv, str(pd.Timestamp(t_lo).date()), scale, stop_scale,
            (pd.Timestamp(t_hi) - pd.Timedelta(seconds=1)).isoformat())
    cur = json.load(open(T.BASE_CFG))
    base = T.evaluate(cur, slippage=slip)
    # See train_tf.trade_floor: 0.25 permitted a 4x drop in activity, which is
    # what filled the rolling test with configs that sit out whole months.
    floor = T.trade_floor(base["trades"], frac, len(T._DF), T._TF, min_abs=10)
    for g in T.ORDER:
        spec, fixed = T.GROUPS[g]
        cand, r, score = T.search(cur, fixed, T.scaled(spec), floor, samples,
                                  seed + hash(g) % 9973, workers, objective, slip)
        prev = T.evaluate(cur, slippage=slip)[objective]
        if np.isfinite(score) and (not np.isfinite(prev) or r[objective] > prev):
            cur = {**cur, **fixed, **cand}
    return cur


def random_cfg(rng: np.random.Generator, floor: int = 0, slip: float = 0.0,
               tries: int = 10) -> dict:
    """Parameters drawn from the same ranges, with NO search. The null.

    MUST CLEAR THE SAME TRADE FLOOR the search clears. A first version drew
    freely and returned exactly 0.00% in 10 of 11 months -- the draws produced
    NO TRADES, so the "null" was a cash balance and beating it proved only that
    the strategy traded at all. Redrawing until the config actually trades makes
    this the comparison it was meant to be: same ranges, same activity level,
    no search. Call this while the module frame is still the TRAINING window,
    so the floor check never touches the test month.
    """
    best, best_n = None, -1
    for _ in range(max(1, tries)):
        cur = json.load(open(T.BASE_CFG))
        for g in T.ORDER:
            spec, fixed = T.GROUPS[g]
            cur = {**cur, **fixed,
                   **{n: (int(rng.integers(lo, hi + 1)) if i else float(rng.uniform(lo, hi)))
                      for n, lo, hi, i in T.scaled(spec)}}
        if floor <= 0:
            return cur
        n = T.evaluate(cur, slippage=slip)["trades"]
        if n > best_n:
            best, best_n = cur, n
        if n >= floor:
            return cur
    return best


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", required=True)
    ap.add_argument("--tf", required=True, choices=sorted(T.TF_MINUTES))
    ap.add_argument("--train-years", type=float, default=3.0)
    ap.add_argument("--test-months", type=int, default=1)
    ap.add_argument("--start", default=None, help="first TEST month")
    ap.add_argument("--samples", type=int, default=100)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) - 1))
    ap.add_argument("--slippage", type=float, default=0.25)
    ap.add_argument("--objective", default="calmar")
    ap.add_argument("--ladder-mode", default="dollars", choices=sorted(T.LADDER_SPECS))
    ap.add_argument("--length-scale", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--min-trade-frac", type=float, default=0.6,
                    help="candidates (and the random null) must take at least "
                         "this fraction of the baseline's trades on the "
                         "training window. Was 0.25, which let the search "
                         "pick configs that sat out 27%% of test months.")
    ap.add_argument("--stop-scale", type=float, default=None,
                    help="multiplier on stop%% ranges; default 1.0 (range used "
                         "as written, 0.01-6.00%%)")
    ap.add_argument("--random-tries", type=int, default=10,
                    help="how many random draws to make per month looking for "
                         "one that clears the trade floor. Each costs a full "
                         "evaluation, so with --skip-retrain this becomes the "
                         "dominant cost. 0 disables the redraw (the null then "
                         "often takes no trades and is not a fair comparison).")
    ap.add_argument("--skip-retrain", action="store_true",
                    help="score frozen / random / buy-and-hold ONLY, no "
                         "parameter search. The search is ~95%% of the runtime "
                         "and feeds only the `retrained` arm, so if the "
                         "question is 'does this config hold up month by "
                         "month against the nulls', this answers it in "
                         "minutes instead of hours. Requires --base.")
    ap.add_argument("--base", help="config to start each search from AND to use "
                                   "as the frozen arm. Without it, `frozen` is "
                                   "whatever the FIRST month happened to fit, "
                                   "which is a weak and run-dependent control. "
                                   "Point this at a config you actually care "
                                   "about and `frozen` becomes the real "
                                   "question: is re-fitting better than just "
                                   "keeping this?")
    a = ap.parse_args()
    if a.base:
        if not os.path.exists(a.base):
            raise SystemExit(f"--base {a.base} not found")
        T.BASE_CFG = a.base
    if a.skip_retrain and not a.base:
        raise SystemExit("--skip-retrain needs --base: there is nothing to "
                         "freeze without a config to freeze.")

    T.set_ladder_mode(a.ladder_mode)
    T._MAXLEN, T._TF = 25_000, a.tf
    ratio = T.TF_MINUTES["H4"] / T.TF_MINUTES[a.tf]
    scale = ratio * a.length_scale
    # 1.0, matching train_tf.py. The old 1/sqrt(ratio) put M15 stops in a
    # 0.125-2.5% box that excluded the ~2.95%/6.00% both working configs use.
    stop_scale = a.stop_scale if a.stop_scale is not None else 1.0
    T._SCALE, T._STOPSCALE = scale, stop_scale

    df = _normalise(_read_csv(a.csv))
    rates = (fetch_fred.load_daily_series("dfii10.csv")
             if os.path.exists("dfii10.csv") else None)
    # THE CHECKPOINT KEY MUST CARRY THE SETTINGS. Keyed on csv+tf alone, a
    # --train-years 5 run would silently load the 3-year run's cached months and
    # report them as 5-year results -- so a "window length doesn't matter"
    # conclusion would be manufactured by the cache rather than measured.
    # Exactly the failure search_robustness.py had with --samples.
    # Readable stem for recognition; hash over the FULL namespace plus the
    # search space for correctness. Each hand-added component below was itself
    # a bug found after the fact -- --samples, --train-years, --skip-retrain,
    # --base, --min-trade-frac, --seed. The hash removes the need to remember.
    fp, settings = T.settings_fingerprint(a)
    tag = (f"{os.path.basename(a.csv).replace('.csv','')}_{a.tf}_roll"
           f"_tr{a.train_years:g}y_te{a.test_months}m"
           f"_s{a.samples}_{a.objective}_sl{a.slippage:g}"
           + f"_f{a.min_trade_frac:g}"
           + (f"_b{os.path.basename(a.base).replace('.json','')}" if a.base else "")
           + ("_norefit" if a.skip_retrain else "")
           + f"_{fp}")
    out = f"results/{tag}"
    T.guard_settings(out, settings)

    first = (pd.Timestamp(a.start, tz="UTC") if a.start
             else df.index[0] + pd.DateOffset(years=a.train_years))
    first = max(first, df.index[0] + pd.DateOffset(years=a.train_years))
    months = pd.date_range(first.normalize().replace(day=1), df.index[-1],
                           freq=f"{a.test_months}MS", tz="UTC")
    months = [m for m in months if m + pd.DateOffset(months=a.test_months) <= df.index[-1]]

    print(f"\nROLLING RETRAIN  {tag}   {len(months)} test windows")
    print(f"  train {a.train_years:g}y -> test {a.test_months}m, rolling   "
          f"{months[0].date()} .. {months[-1].date()}")
    print(f"  {a.samples} samples/group, 1 pass, objective {a.objective}, "
          f"slippage {a.slippage:g}, ladder {a.ladder_mode}")
    print("=" * 96)

    # With --base, `frozen` is that config held constant for the whole run --
    # never re-fitted, not even once. That makes the `vs frozen` row the
    # question worth asking: does monthly re-fitting beat simply keeping the
    # config you already have?
    frozen = json.load(open(a.base)) if a.base else None
    rng = np.random.default_rng(a.seed)
    rows = []
    t_start = time.time()
    for k, m in enumerate(months):
        path = f"{out}/{m.date()}.json"
        if os.path.exists(path):
            rows.append(json.load(open(path)))
            continue
        t0, t1 = m, m + pd.DateOffset(months=a.test_months)
        t_lo = t0 - pd.DateOffset(years=a.train_years)
        if len(df[t_lo:t0]) < 200:
            continue
        if a.skip_retrain:
            # No search. The random draw still needs the TRAINING window in
            # place for its trade-count floor, so build it the same way `fit`
            # would have, just without optimising anything on it.
            T._DF = None
            T._init(a.csv, str(pd.Timestamp(t_lo).date()), scale, stop_scale,
                    (pd.Timestamp(t0) - pd.Timedelta(seconds=1)).isoformat())
            cfg = frozen
        else:
            cfg = fit(a.csv, t_lo, t0, scale, stop_scale, a.samples, a.workers,
                      a.slippage, a.objective, a.seed + k, rates,
                      a.min_trade_frac)
        if frozen is None:
            frozen = cfg          # fitted ONCE, at the first window, never again
        # Drawn while _DF is STILL the training window, so the floor check
        # cannot see the month being scored.
        # Same floor as the search, so the null is held to the same activity
        # standard. Using a laxer one here would let the null go quiet and
        # make the strategy look good purely by comparison.
        floor_n = T.trade_floor(
            T.evaluate(json.load(open(T.BASE_CFG)), slippage=a.slippage)["trades"],
            a.min_trade_frac, len(T._DF), T._TF, min_abs=10)
        rcfg = random_cfg(rng, floor_n, a.slippage, a.random_tries)
        T._DF, T._RATES = df, rates      # restore full frame for scoring
        r_fit, n_fit = window_return(df, cfg, t0, t1, a.slippage, rates, t_lo)
        r_frz, _ = window_return(df, frozen, t0, t1, a.slippage, rates, t_lo)
        r_rnd, _ = window_return(df, rcfg, t0, t1, a.slippage, rates, t_lo)
        px = df["close"][t0:t1]
        r_bh = float(px.iloc[-1] / px.iloc[0] - 1) if len(px) > 1 else np.nan
        rec = {"month": str(m.date()), "retrained": r_fit, "frozen": r_frz,
               "random": r_rnd, "buyhold": r_bh, "trades": n_fit}
        json.dump(rec, open(path, "w"), indent=2)
        rows.append(rec)
        el = time.time() - t_start
        print(f"  {rec['month']}  retrained {100*r_fit:>7.2f}%  frozen {100*r_frz:>7.2f}%"
              f"  random {100*r_rnd:>7.2f}%  B&H {100*r_bh:>7.2f}%  "
              f"({n_fit} trades) [{el/max(k+1,1):.0f}s/mo]", flush=True)

    r = pd.DataFrame(rows).dropna(subset=["retrained"])
    r.to_csv(f"{out}/summary.csv", index=False)
    print("\n  RESULTS   " + f"{len(r)} test months")
    print("  " + "=" * 92)
    print(f"  {'series':<14}{'total%':>10}{'ann%':>9}{'mean/mo%':>11}"
          f"{'median%':>10}{'% up':>8}{'worst%':>9}{'best%':>9}{'maxDD%':>9}")
    print("  " + "-" * 92)
    yrs = len(r) * a.test_months / 12
    for col in ("retrained", "frozen", "random", "buyhold"):
        x = r[col].dropna()
        if not len(x):
            continue
        eq = (1 + x).cumprod()
        tot = 100 * (eq.iloc[-1] - 1)
        ann = 100 * (eq.iloc[-1] ** (1 / yrs) - 1) if eq.iloc[-1] > 0 else np.nan
        dd = 100 * ((eq / eq.cummax()) - 1).min()
        print(f"  {col:<14}{tot:>10.1f}{ann:>9.2f}{100*x.mean():>11.2f}"
              f"{100*x.median():>10.2f}{100*(x > 0).mean():>8.1f}"
              f"{100*x.min():>9.2f}{100*x.max():>9.2f}{dd:>9.1f}")

    print("\n  DID MONTHLY RETRAINING EARN ITS KEEP?")
    print("  " + "=" * 92)
    for other in ("frozen", "random", "buyhold"):
        d = (r["retrained"] - r[other]).dropna()
        if not len(d):
            continue
        # Paired t on monthly differences: same months, same market, so the
        # pairing removes most of the common market move and the test is about
        # the DIFFERENCE, not about whether the market went up.
        se = d.std(ddof=1) / np.sqrt(len(d))
        t = d.mean() / se if se > 0 else np.nan
        print(f"  vs {other:<10} mean diff {100*d.mean():>+7.3f}%/mo   "
              f"beat it in {100*(d > 0).mean():>4.1f}% of months   "
              f"t = {t:>+5.2f}  {'SIGNIFICANT' if abs(t) > 2 else 'not significant'}")
    print(f"\n  wrote {out}/summary.csv\n")


if __name__ == "__main__":
    main()
