#!/usr/bin/env python3
"""Walk-forward parameter search, built so it cannot flatter itself.

The danger here is specific and already demonstrated on this data. In
`FINDINGS.md` §5, removing the 4H macro filter produced the best full-sample
result (+252% vs +174%) and the *worst* out-of-sample one. An optimiser
searching thousands of combinations will find dozens of those, and a single
in-sample fit has no way to tell them apart from real improvements.

So this module reports **only out-of-sample numbers**, and surrounds them with
the controls needed to tell whether the search found anything:

1. **Walk-forward.** Parameters are chosen on a training window and scored on
   the *next* window, never seen during selection. The reported equity curve is
   those out-of-sample segments stitched together.

2. **A trade-count floor.** With ~10 trades carrying the profit, a parameter set
   taking five lucky trades can post a spectacular Calmar. Anything below the
   floor scores as -inf rather than winning.

3. **Two nulls.** The optimised result is compared against (a) the untouched
   baseline over the same windows, and (b) *randomly drawn* parameters, chosen
   with no optimisation at all. If optimisation cannot beat random draws out of
   sample, the search is fitting noise -- and that is a result worth having.

4. **The in-sample/out-of-sample gap is printed.** A large gap is the signature
   of overfitting and is reported rather than buried.

Random search is the default rather than Bayesian optimisation, deliberately.
With this few effective observations, a method that concentrates its budget
near apparent optima concentrates it on noise. Random search explores more
evenly and is harder to fool; Optuna is available via --sampler tpe if you want
to compare.

    python optimise.py sensitivity --csv xauusd_1h.csv
    python optimise.py walkforward --csv xauusd_1h.csv --trials 80
    python optimise.py walkforward --csv xauusd_1h.csv --trials 80 --sampler tpe
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import warnings
from dataclasses import replace

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from broker import BrokerConfig                    # noqa: E402
from data import _normalise, _read_csv             # noqa: E402
from metrics import compute_metrics                # noqa: E402
from strategy import Params, run_strategy          # noqa: E402

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")

#: Fixed (non-searched) settings that define the strategy being optimised.
BASE_CONFIGS: dict[str, dict] = {
    # Both code repairs, everything else at the original defaults.
    "repaired": dict(fix_keltner_range=True, fix_long_stop_ratchet=True),

    # Dave's edited script: markUp/lockProfitUp/rangeL all raised to 10000 so
    # the profit ladder can never fire, and the stop/limit percentages widened
    # to 6%. Long-only, since the short leg produces an identical trade list.
    "dave": dict(
        fix_keltner_range=True, fix_long_stop_ratchet=True,
        use_ladder=False,
        sl_percent_long=6.0, limit_percent_long=6.0, r_ratio_long=3.0,
        sl_percent_short=6.0, limit_percent_short=6.0,
        allow_shorts=False,
    ),
}

#: Set from --base.
BASE_PARAMS: dict = BASE_CONFIGS["repaired"]

#: The narrow search space -- parameters selected by MEASURED impact, not by
#: guesswork. Run `optimise.py sensitivity` to regenerate the ranking.
#:
#: Measured Calmar spread on the full sample (baseline 0.456, 138 trades):
#:   bb_stdev_long    0.556   <- dominates; low values take far more trades
#:   sl_percent_long  0.375
#:   bullish_sma      0.349
#:   bb_period_long   0.270
#:   bb_stdev_short   0.133   dropped: affects the short leg, ~18 trades in 20y
#:   vol_long         0.077
#:   adx_threshold    0.073
#:   atr_long         0.069
#:   adx_len          0.062
#:   bb_period_short  0.000   dropped: literally no effect
#:
#: Seven parameters against ~281 trades is about 40 trades each -- thin, but the
#: walk-forward harness is what decides whether even that is too many.
#: (name, low, high, is_integer)
SEARCH_SPACES: dict[str, list[tuple[str, float, float, bool]]] = {
    # Seven parameters. The first walk-forward run used this. Five of the seven
    # failed to converge across folds -- the optimiser was picking noise on
    # those axes.
    "wide7": [
        ("bb_period_long",    8,    30,   True),
        ("bb_stdev_long",     1.2,  3.2,  False),
        ("sl_percent_long",   1.2,  4.5,  False),
        ("bullish_sma",       10,   60,   True),
        ("adx_threshold",     12.0, 38.0, False),
        ("vol_long",          20,   120,  True),
        ("atr_long",          3,    14,   True),
    ],
    # Only the two parameters that (a) rank 1st and 2nd on measured impact and
    # (b) actually converged across folds in the wide7 run. Same trial budget
    # over two dimensions instead of seven is a far denser search, with much
    # less room to fit noise.
    "narrow2": [
        ("bb_stdev_long",     1.2,  3.2,  False),
        ("sl_percent_long",   1.2,  4.5,  False),
    ],

    # LONG-SIDE ONLY. Everything here feeds the long entry or the long exit;
    # nothing short-side is included. Note that the squeeze parameters
    # (kc_length_l, kc_mult, bb_length_l, long_val) are LIVE for the first time
    # -- before FIX 1 the Keltner comparison was always true, so they did
    # nothing and were correctly excluded from earlier searches.
    "long_entry": [
        ("bb_period_long",    8,    40,   True),    # BBlengthL
        ("bb_stdev_long",     1.0,  3.5,  False),   # BBmultL
        ("kc_length_l",       30,   150,  True),    # lengthKCL
        ("kc_mult",           1.0,  4.0,  False),   # multKC
        ("bb_length_l",       2,    20,   True),    # lengthL
        ("long_val",         -30.0, 30.0, False),   # longVal
    ],
    "long_exit": [
        ("sl_percent_long",   2.0,  12.0, False),   # SL_percent_basedL
        ("limit_percent_long", 2.0, 15.0, False),   # L_percent_basedL
        ("r_ratio_long",      1.0,  6.0,  False),   # r_ratioL
        ("flex_up",           0.85, 1.0,  False),   # flexUp
        ("gap_up",            0.97, 1.0,  False),   # gapUp
    ],
    "long_filters": [
        ("bullish_sma",       10,   80,   True),    # bullish SMA (4H macro)
        ("adx_threshold",     10.0, 40.0, False),   # adxVar
        ("adx_len",           4,    20,   True),
        ("atr_long",          3,    20,   True),
        ("vol_long",          20,   140,  True),
    ],
}

#: Active space; set from --space. Module-level so the search helpers can see it.
SEARCH_SPACE: list[tuple[str, float, float, bool]] = SEARCH_SPACES["wide7"]

#: Minimum trades in a window for a score to count. Below this, ratios are noise.
MIN_TRADES_PER_YEAR = 3.0


# --------------------------------------------------------------------------
# scoring
# --------------------------------------------------------------------------

def evaluate(df: pd.DataFrame, params: Params, cfg: BrokerConfig,
             test_start: pd.Timestamp | None = None) -> dict:
    """Run the strategy and score it, optionally only over a test slice.

    When ``test_start`` is given, the strategy still runs over the whole frame
    (so indicators and open positions carry the correct history) but the metrics
    are computed on the test slice alone, with equity rebased to the window
    start. Scoring a window without letting the run warm up through it would
    penalise every parameter set with a long lookback.
    """
    res = run_strategy(df, params, cfg)
    eq, trades = res.equity, res.trades

    if test_start is not None:
        eq = eq[eq.index >= test_start]
        if len(eq) < 10:
            return {"calmar": -np.inf, "trades": 0, "cagr_pct": np.nan,
                    "max_drawdown_pct": np.nan, "sharpe": np.nan}
        eq = eq / eq.iloc[0] * cfg.initial_capital
        if not trades.empty:
            entry = pd.to_datetime(trades["entry_time"], utc=True)
            trades = trades[entry >= test_start]

    m = compute_metrics(eq, trades, cfg.initial_capital)
    m["years"] = max(m.get("years", 0.0), 1e-9)
    return m


def objective(m: dict, min_trades_per_year: float = MIN_TRADES_PER_YEAR) -> float:
    """Calmar, with a trade-count floor.

    Calmar (CAGR / max drawdown) is used rather than Sharpe because it targets
    what this strategy is actually good at -- drawdown control -- and because a
    bar-level Sharpe on an equity curve that is flat 70% of the time rewards
    low exposure, which FINDINGS.md §7 identifies as the binding constraint
    rather than a virtue.

    The floor is the important part. Without it the optimiser's best move is to
    take three trades that happened to work.
    """
    n, years = m.get("trades", 0), m.get("years", 1e-9)
    if n < min_trades_per_year * years or n < 5:
        return -np.inf
    calmar = m.get("calmar", np.nan)
    if calmar is None or not np.isfinite(calmar):
        return -np.inf
    return float(calmar)


# --------------------------------------------------------------------------
# search
# --------------------------------------------------------------------------

def sample_params(rng: np.random.Generator) -> dict:
    out = {}
    for name, lo, hi, is_int in SEARCH_SPACE:
        out[name] = (int(rng.integers(lo, hi + 1)) if is_int
                     else float(rng.uniform(lo, hi)))
    return out


def random_search(df: pd.DataFrame, cfg: BrokerConfig, trials: int,
                  rng: np.random.Generator, test_start=None) -> tuple[dict, float]:
    best, best_score = {}, -np.inf
    for _ in range(trials):
        cand = sample_params(rng)
        m = evaluate(df, Params(**{**BASE_PARAMS, **cand}), cfg, test_start)
        s = objective(m)
        if s > best_score:
            best, best_score = cand, s
    return best, best_score


def tpe_search(df: pd.DataFrame, cfg: BrokerConfig, trials: int,
               seed: int, test_start=None) -> tuple[dict, float]:
    try:
        import optuna
    except ImportError:
        raise SystemExit("optuna not installed:  .venv/bin/python -m pip install optuna")
    optuna.logging.set_verbosity(optuna.logging.WARNING)

    def obj(trial):
        cand = {}
        for name, lo, hi, is_int in SEARCH_SPACE:
            cand[name] = (trial.suggest_int(name, int(lo), int(hi)) if is_int
                          else trial.suggest_float(name, lo, hi))
        s = objective(evaluate(df, Params(**{**BASE_PARAMS, **cand}), cfg, test_start))
        return -1e9 if not np.isfinite(s) else s

    study = optuna.create_study(direction="maximize",
                                sampler=optuna.samplers.TPESampler(seed=seed))
    study.optimize(obj, n_trials=trials, show_progress_bar=False)
    return study.best_params, study.best_value


# --------------------------------------------------------------------------
# walk-forward
# --------------------------------------------------------------------------

def make_folds(df: pd.DataFrame, n_folds: int, train_years: float,
               test_years: float) -> list[tuple]:
    """Rolling train/test windows across the sample."""
    start, end = df.index[0], df.index[-1]
    total = (end - start).days / 365.25
    step = (total - train_years) / n_folds
    if step <= 0:
        raise SystemExit(f"sample is only {total:.1f}y; cannot fit "
                         f"{train_years}y train + {n_folds} folds")

    folds = []
    for i in range(n_folds):
        tr_start = start + pd.Timedelta(days=365.25 * i * step)
        tr_end = tr_start + pd.Timedelta(days=365.25 * train_years)
        te_end = min(tr_end + pd.Timedelta(days=365.25 * test_years), end)
        if (te_end - tr_end).days < 120:
            break
        folds.append((tr_start, tr_end, te_end))
    return folds


#: Set from --space so state files from different search spaces never collide.
SPACE_NAME = "wide7"


def fold_state_path(fold: int) -> str:
    return os.path.join(OUT_DIR, f"wf_{SPACE_NAME}_fold_{fold:02d}.json")


def run_fold(df: pd.DataFrame, cfg: BrokerConfig, fold: int, bounds: tuple,
             trials: int, seed: int) -> dict:
    """Add `trials` more random-search trials to one fold, resuming prior work.

    Each invocation is self-contained and appends to the fold's saved state, so
    a long search can be accumulated across several short runs without losing
    what came before. The RNG is seeded from the trial count already completed,
    so resuming explores new points rather than repeating the same ones.
    """
    tr_start, tr_end, te_end = bounds
    os.makedirs(OUT_DIR, exist_ok=True)
    path = fold_state_path(fold)

    state = {"fold": fold, "trials_done": 0, "best": None, "best_score": -np.inf,
             "train": f"{tr_start:%Y-%m}..{tr_end:%Y-%m}",
             "test": f"{tr_end:%Y-%m}..{te_end:%Y-%m}"}
    if os.path.exists(path):
        with open(path) as fh:
            state.update(json.load(fh))
        if state["best_score"] is None:
            state["best_score"] = -np.inf

    train = df[tr_start:tr_end]
    rng = np.random.default_rng(seed + 1000 * fold + state["trials_done"])

    for _ in range(trials):
        cand = sample_params(rng)
        s = objective(evaluate(train, Params(**{**BASE_PARAMS, **cand}), cfg))
        state["trials_done"] += 1
        if s > state["best_score"]:
            state["best"], state["best_score"] = cand, s

    with open(path, "w") as fh:
        json.dump({k: (None if v == -np.inf else v) for k, v in state.items()},
                  fh, indent=1)
    return state


def fold_score_path(fold: int) -> str:
    return os.path.join(OUT_DIR, f"wf_{SPACE_NAME}_score_{fold:02d}.json")


def score_fold(df: pd.DataFrame, cfg: BrokerConfig, fold: int, bounds: tuple,
               seed: int, n_null: int = 8, cached: bool = True) -> dict:
    """Score a fold's chosen parameters out of sample, against both nulls.

    Results are cached to disk because scoring is itself expensive -- each fold
    needs the optimised run, the baseline run and `n_null` random-parameter runs
    over the combined train+test window.
    """
    if cached and os.path.exists(fold_score_path(fold)):
        with open(fold_score_path(fold)) as fh:
            return json.load(fh)

    tr_start, tr_end, te_end = bounds
    with open(fold_state_path(fold)) as fh:
        state = json.load(fh)
    best = state["best"]
    full = df[tr_start:te_end]

    oos = evaluate(full, Params(**{**BASE_PARAMS, **best}), cfg, test_start=tr_end)
    base = evaluate(full, Params(**BASE_PARAMS), cfg, test_start=tr_end)

    rng = np.random.default_rng(seed + 77 * fold)
    null = []
    for _ in range(n_null):
        m = evaluate(full, Params(**{**BASE_PARAMS, **sample_params(rng)}),
                     cfg, test_start=tr_end)
        null.append(objective(m))
    finite = [s for s in null if np.isfinite(s)]

    def clean(x):
        return None if x is None or not np.isfinite(x) else float(x)

    row = {
        "fold": fold, "train": state["train"], "test": state["test"],
        "trials_done": state["trials_done"],
        "is_calmar": clean(state["best_score"]),
        "oos_calmar": clean(objective(oos)),
        "oos_cagr": clean(oos.get("cagr_pct")),
        "oos_dd": clean(oos.get("max_drawdown_pct")),
        "oos_trades": int(oos.get("trades", 0)),
        "base_calmar": clean(objective(base)),
        "base_cagr": clean(base.get("cagr_pct")),
        "base_trades": int(base.get("trades", 0)),
        "null_calmar_med": clean(np.median(finite)) if finite else None,
        "params": json.dumps({k: round(v, 3) for k, v in best.items()}),
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(fold_score_path(fold), "w") as fh:
        json.dump(row, fh, indent=1)
    return row


def walk_forward(df: pd.DataFrame, cfg: BrokerConfig, trials: int, seed: int,
                 n_folds: int, train_years: float, test_years: float,
                 sampler: str) -> pd.DataFrame:
    folds = make_folds(df, n_folds, train_years, test_years)
    rng = np.random.default_rng(seed)
    rows = []

    print(f"\n{len(folds)} folds, {train_years:g}y train / {test_years:g}y test, "
          f"{trials} trials per fold, sampler={sampler}")
    print("=" * 100)

    for i, (tr_start, tr_end, te_end) in enumerate(folds, 1):
        t0 = time.time()
        train = df[tr_start:tr_end]
        full = df[tr_start:te_end]           # test scored on the tail of this

        if sampler == "tpe":
            best, is_score = tpe_search(train, cfg, trials, seed + i)
        else:
            best, is_score = random_search(train, cfg, trials, rng)

        # Out-of-sample: same params, scored only on the unseen tail.
        oos = evaluate(full, Params(**{**BASE_PARAMS, **best}), cfg, test_start=tr_end)
        base = evaluate(full, Params(**BASE_PARAMS), cfg, test_start=tr_end)

        # Null: parameters drawn at random, no optimisation at all.
        null_scores, null_cagrs = [], []
        for _ in range(12):
            cand = sample_params(rng)
            m = evaluate(full, Params(**{**BASE_PARAMS, **cand}), cfg, test_start=tr_end)
            null_scores.append(objective(m))
            null_cagrs.append(m.get("cagr_pct", np.nan))
        finite = [s for s in null_scores if np.isfinite(s)]

        rows.append({
            "fold": i,
            "train": f"{tr_start:%Y-%m}..{tr_end:%Y-%m}",
            "test": f"{tr_end:%Y-%m}..{te_end:%Y-%m}",
            "is_calmar": is_score,
            "oos_calmar": objective(oos),
            "oos_cagr": oos.get("cagr_pct", np.nan),
            "oos_dd": oos.get("max_drawdown_pct", np.nan),
            "oos_trades": oos.get("trades", 0),
            "base_calmar": objective(base),
            "base_cagr": base.get("cagr_pct", np.nan),
            "null_calmar_med": float(np.median(finite)) if finite else np.nan,
            "null_cagr_med": float(np.nanmedian(null_cagrs)),
            "params": json.dumps({k: round(v, 3) for k, v in best.items()}),
        })
        r = rows[-1]
        print(f"fold {i}  train {r['train']}  test {r['test']}  "
              f"({time.time()-t0:.0f}s)")
        print(f"    in-sample Calmar {r['is_calmar']:>7.3f}   "
              f"OUT-OF-SAMPLE {r['oos_calmar']:>7.3f}   "
              f"baseline {r['base_calmar']:>7.3f}   "
              f"random-params median {r['null_calmar_med']:>7.3f}")
        print(f"    chosen: {r['params']}")

    return pd.DataFrame(rows)


def summarise(res: pd.DataFrame) -> None:
    print("\n" + "=" * 100)
    print("WALK-FORWARD SUMMARY  (out-of-sample only)")
    print("=" * 100)

    opt = res["oos_calmar"].replace(-np.inf, np.nan)
    base = res["base_calmar"].replace(-np.inf, np.nan)
    null = res["null_calmar_med"].replace(-np.inf, np.nan)
    is_ = res["is_calmar"].replace(-np.inf, np.nan)

    print(f"\n{'':<26}{'mean':>10}{'median':>10}{'folds won':>12}")
    print("-" * 60)
    print(f"{'optimised (OOS)':<26}{opt.mean():>10.3f}{opt.median():>10.3f}"
          f"{int((opt > base).sum()):>7}/{len(res)}")
    print(f"{'baseline (no tuning)':<26}{base.mean():>10.3f}{base.median():>10.3f}")
    print(f"{'random params (no search)':<26}{null.mean():>10.3f}{null.median():>10.3f}")

    print(f"\n{'in-sample Calmar (mean)':<30}{is_.mean():>8.3f}")
    print(f"{'out-of-sample Calmar (mean)':<30}{opt.mean():>8.3f}")
    gap = is_.mean() - opt.mean()
    print(f"{'in-sample minus OOS':<30}{gap:>8.3f}")
    if gap > 0:
        print(f"  {100*gap/abs(is_.mean()):.0f}% of the in-sample edge did not "
              f"survive -- the usual overfitting signature.")
    else:
        print("  NEGATIVE gap: out-of-sample scored HIGHER than in-sample.")
        print("  This is not evidence of unusually good generalisation. It means")
        print("  the test windows were simply easier than the training windows --")
        print("  they sit later in a 20-year gold bull market. The in-sample/OOS")
        print("  comparison is uninformative here; the baseline and random-parameter")
        print("  columns are the ones carrying the weight.")

    # Parameter stability. If a parameter matters and the search is finding
    # signal, its chosen value should be similar across folds. Values scattered
    # across the whole range mean the optimiser is picking noise on that axis --
    # which is exactly what happens to the low-impact parameters.
    try:
        chosen = pd.DataFrame([json.loads(p) for p in res["params"]])
    except Exception:                                    # noqa: BLE001
        return
    print("\nParameter stability across folds")
    print("-" * 72)
    print(f"{'parameter':<20}{'min':>9}{'median':>9}{'max':>9}"
          f"{'spread/range':>14}")
    ranges = {n: (lo, hi) for n, lo, hi, _ in SEARCH_SPACE}
    unstable = []
    for col in chosen.columns:
        lo, hi = ranges.get(col, (chosen[col].min(), chosen[col].max()))
        frac = (chosen[col].max() - chosen[col].min()) / max(hi - lo, 1e-9)
        flag = "  <- scattered" if frac > 0.6 else ""
        if frac > 0.6:
            unstable.append(col)
        print(f"{col:<20}{chosen[col].min():>9.2f}{chosen[col].median():>9.2f}"
              f"{chosen[col].max():>9.2f}{frac:>13.0%}{flag}")
    if unstable:
        print(f"\n  {len(unstable)} parameter(s) span most of their range across")
        print(f"  folds: {', '.join(unstable)}.")
        print("  The optimiser is not converging on a value for these, which")
        print("  means it is fitting noise on those axes. They are candidates")
        print("  for removal from the search space -- fewer parameters, less")
        print("  room to overfit, same result.")

    print("\nVerdict")
    print("-" * 60)
    beat_base = int((opt > base).sum())
    beat_null = int((opt > null).sum())
    if opt.mean() > base.mean() and beat_base > len(res) / 2:
        print(f"  Optimised beats the untuned baseline in {beat_base}/{len(res)} folds.")
        if opt.mean() > null.mean() and beat_null > len(res) / 2:
            print(f"  It also beats randomly-drawn parameters in {beat_null}/{len(res)}.")
            print("  The search is finding something that generalises. Modest")
            print("  confidence is warranted -- keep the walk-forward harness for")
            print("  any further change.")
        else:
            print(f"  But it beats RANDOM parameter draws in only {beat_null}/{len(res)}"
                  f" folds.")
            print("  That means the gain comes from the parameter RANGES being")
            print("  reasonable, not from the search finding good values. Pick")
            print("  sensible defaults and stop optimising.")
    else:
        print(f"  Optimised does NOT beat the untuned baseline out of sample "
              f"({beat_base}/{len(res)} folds).")
        print("  The search is fitting noise. This is the expected outcome given")
        print("  ~10 trades carry the profit, and it is a real result: it says")
        print("  tuning these parameters is not where the improvement is.")


# --------------------------------------------------------------------------

def cmd_sensitivity(args) -> None:
    """Rank parameters by how much they actually move the result."""
    df = _normalise(_read_csv(args.csv))
    cfg = BrokerConfig(initial_capital=args.capital, point_value=args.point_value)
    base_m = evaluate(df, Params(**BASE_PARAMS), cfg)
    print(f"baseline: {base_m['trades']} trades  CAGR {base_m['cagr_pct']:.2f}%  "
          f"DD {base_m['max_drawdown_pct']:.2f}%  Calmar {base_m['calmar']:.3f}\n")

    candidates = SEARCH_SPACE + [
        ("adx_len", 4, 14, True), ("atr_long", 3, 14, True),
        ("ssma_length_long", 15, 40, True), ("kc_length_l", 40, 120, True),
        ("rsi_overbought", 10.0, 35.0, False), ("long_val", -20.0, 20.0, False)]
    if args.only:
        wanted = {s.strip() for s in args.only.split(",")}
        candidates = [c for c in candidates if c[0] in wanted]

    rows = []
    for name, lo, hi, is_int in candidates:
        vals = []
        for v in (lo, hi):
            v = int(v) if is_int else float(v)
            m = evaluate(df, Params(**{**BASE_PARAMS, name: v}), cfg)
            vals.append((v, m["trades"], m["calmar"]))
        spread = max(v[2] for v in vals + [(0, 0, base_m["calmar"])]) - \
                 min(v[2] for v in vals + [(0, 0, base_m["calmar"])])
        rows.append({"param": name, "spread": spread,
                     "low_val": vals[0][0], "low_trades": vals[0][1],
                     "low_calmar": round(vals[0][2], 3),
                     "high_val": vals[1][0], "high_trades": vals[1][1],
                     "high_calmar": round(vals[1][2], 3)})

    out = pd.DataFrame(rows).sort_values("spread", ascending=False)
    print("RANKED BY IMPACT ON CALMAR (one-at-a-time)")
    print("-" * 92)
    for _, r in out.iterrows():
        bar = "#" * int(min(r["spread"], 1.5) * 30)
        print(f"  {r['param']:<20}{r['spread']:>7.3f}  "
              f"low {r['low_val']:>6}: {r['low_trades']:>4}t/{r['low_calmar']:>6.3f}   "
              f"high {r['high_val']:>6}: {r['high_trades']:>4}t/{r['high_calmar']:>6.3f}  {bar}")
    os.makedirs(OUT_DIR, exist_ok=True)
    out.to_csv(os.path.join(OUT_DIR, "sensitivity.csv"), index=False)
    print(f"\nwrote sensitivity.csv to {OUT_DIR}")


def cmd_walkforward(args) -> None:
    df = _normalise(_read_csv(args.csv))
    cfg = BrokerConfig(initial_capital=args.capital, point_value=args.point_value)
    folds = make_folds(df, args.folds, args.train_years, args.test_years)

    if args.list_folds:
        print(f"data: {len(df):,} bars  {df.index[0]:%Y-%m-%d} -> {df.index[-1]:%Y-%m-%d}")
        print(f"\n{len(folds)} folds ({args.train_years:g}y train / "
              f"{args.test_years:g}y test):")
        for i, (a, b, c) in enumerate(folds, 1):
            done = 0
            if os.path.exists(fold_state_path(i)):
                with open(fold_state_path(i)) as fh:
                    done = json.load(fh).get("trials_done", 0)
            print(f"  fold {i}  train {a:%Y-%m}..{b:%Y-%m}   test {b:%Y-%m}..{c:%Y-%m}"
                  f"   trials done: {done}")
        return

    if args.score_fold:
        row = score_fold(df, cfg, args.score_fold, folds[args.score_fold - 1],
                         args.seed, cached=False)
        print(f"fold {row['fold']}  test {row['test']}")
        print(f"  in-sample Calmar   {row['is_calmar']}")
        print(f"  OUT-OF-SAMPLE      {row['oos_calmar']}   "
              f"({row['oos_trades']} trades, CAGR {row['oos_cagr']})")
        print(f"  baseline           {row['base_calmar']}   "
              f"({row['base_trades']} trades, CAGR {row['base_cagr']})")
        print(f"  random params med  {row['null_calmar_med']}")
        return

    if args.summarise:
        rows = []
        missing = []
        for i, bounds in enumerate(folds, 1):
            if os.path.exists(fold_score_path(i)):
                rows.append(score_fold(df, cfg, i, bounds, args.seed))
            elif os.path.exists(fold_state_path(i)):
                missing.append(i)
        if missing:
            print(f"folds not yet scored: {missing}\n"
                  f"  run:  --score-fold N   for each")
        if not rows:
            raise SystemExit("no scored folds; run with --score-fold N first")
        res = pd.DataFrame(rows)
        summarise(res)
        res.to_csv(os.path.join(OUT_DIR, "walkforward.csv"), index=False)
        print(f"\nwrote walkforward.csv to {OUT_DIR}")
        return

    if args.fold:
        if not 1 <= args.fold <= len(folds):
            raise SystemExit(f"fold must be 1..{len(folds)}")
        st = run_fold(df, cfg, args.fold, folds[args.fold - 1],
                      args.trials, args.seed)
        print(f"fold {args.fold}  train {st['train']}  test {st['test']}")
        print(f"  trials completed: {st['trials_done']}")
        print(f"  best in-sample Calmar: {st['best_score']:.3f}")
        print(f"  best params: {json.dumps(st['best'])}")
        return

    res = walk_forward(df, cfg, args.trials, args.seed, args.folds,
                       args.train_years, args.test_years, args.sampler)
    summarise(res)
    os.makedirs(OUT_DIR, exist_ok=True)
    res.to_csv(os.path.join(OUT_DIR, "walkforward.csv"), index=False)
    print(f"\nwrote walkforward.csv to {OUT_DIR}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    for name, fn in (("sensitivity", cmd_sensitivity), ("walkforward", cmd_walkforward)):
        p = sub.add_parser(name)
        p.add_argument("--csv", required=True)
        p.add_argument("--capital", type=float, default=4000.0)
        p.add_argument("--point-value", type=float, default=1.0)
        p.add_argument("--space", default="wide7", choices=sorted(SEARCH_SPACES),
                       help="which parameter set to search; state files are "
                            "namespaced so runs never collide")
        p.add_argument("--base", default="repaired", choices=sorted(BASE_CONFIGS),
                       help="fixed settings defining the strategy being tuned")
        p.set_defaults(func=fn)
        if name == "walkforward":
            p.add_argument("--trials", type=int, default=80)
            p.add_argument("--folds", type=int, default=6)
            p.add_argument("--train-years", type=float, default=6.0)
            p.add_argument("--test-years", type=float, default=2.5)
            p.add_argument("--seed", type=int, default=0)
            p.add_argument("--sampler", default="random", choices=["random", "tpe"])
            p.add_argument("--fold", type=int, default=None,
                           help="run/resume a single fold, so a long search can "
                                "be accumulated across short invocations")
            p.add_argument("--score-fold", type=int, default=None,
                           help="score one fold out of sample and cache it")
            p.add_argument("--summarise", action="store_true",
                           help="collate all scored folds")
            p.add_argument("--list-folds", action="store_true")
        else:
            p.add_argument("--only", default=None,
                           help="comma-separated parameter names to test")

    args = ap.parse_args()

    global SEARCH_SPACE, SPACE_NAME, BASE_PARAMS
    space = getattr(args, "space", "wide7")
    base = getattr(args, "base", "repaired")
    SEARCH_SPACE = SEARCH_SPACES[space]
    BASE_PARAMS = BASE_CONFIGS[base]
    SPACE_NAME = f"{base}_{space}"
    print(f"base config : {base}")
    print(f"search space: {space}  ({len(SEARCH_SPACE)} parameters: "
          f"{', '.join(n for n, *_ in SEARCH_SPACE)})")

    args.func(args)


if __name__ == "__main__":
    main()
