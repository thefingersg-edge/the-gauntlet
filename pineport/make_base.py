#!/usr/bin/env python3
"""Build a neutral starting config for a NEW instrument.

WHY THIS EXISTS

The SPX500 staged run was started from `gold_15m_live_current.json` because it
was the only 15m config to hand. It carried `use_macro_filter=True` with
`rate_filter_mode='replace'` -- the gold 10-year TIPS real-yield gate -- plus
gold's ADX-short and volatility-short filters. `train_staged.py` searches the
six PARAMETER groups and never touches filter SWITCHES, so all of it stayed on
for the whole run and the parameters were fitted around a macro variable that
has nothing to do with an equity index. It was not cosmetic: the gold filter
moved the unseen-window Sharpe by 0.28 in one direction and 0.24 in the other.

Starting from another instrument's tuned config is the problem. This starts
from the dataclass defaults instead and turns OFF everything instrument-
specific, so a search begins from a neutral position and has to earn each
addition.

WHAT IT SWITCHES OFF, AND WHY

  use_macro_filter / rate_filter_mode   FRED real yield -- a GOLD driver
  use_adx_filter (+short)               a filter, not a signal; earn it later
  use_volatility_filter (+short)        same
  use_sma_filter / use_ema_filter       same
  use_ladder                            the profit ladder measured near-inert
                                        on gold (-0.11% CAGR when removed) and
                                        its dollar rungs are price-scale bound

WHAT IT LEAVES ON

  the three entry triggers and the squeeze, because those ARE the strategy.

Stops are carried across as MULTIPLES of median ATR taken from a reference
config that works, not copied as percentages. Gold's 2.95% stop is 24.6x its
median 15m ATR; the same geometry on SPX500 is 2.538%. Percentage constants
have broken four times in this tree, always the same way.

    python make_base.py --csv spx500usd_oanda_m15.csv --out configs/spx500_clean_base.json
    python make_base.py --csv spx500usd_oanda_m15.csv --state-triggers --long-only
"""
from __future__ import annotations

import argparse
import dataclasses as dc
import json
import os
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data import _normalise, _read_csv                # noqa: E402
from strategy import Params                           # noqa: E402
import pine_ta as ta                                  # noqa: E402

#: Switched off in a neutral base. Each is a filter or an instrument-specific
#: macro input; the search can turn them on later if they earn it.
OFF = ["use_macro_filter", "use_adx_filter", "use_adx_filter_short",
       "use_volatility_filter", "use_volatility_filter_short",
       "use_sma_filter", "use_ema_filter", "short_regime_filter",
       "use_ladder"]


def median_atr_pct(df: pd.DataFrame) -> float:
    """Median ATR% measured on DAILY bars, whatever timeframe the file is.

    Measuring on native bars is not timeframe-independent: ATR(14) on 4h bars
    is ~3.6x ATR(14) on 15m bars purely because the bar is bigger. Carrying a
    multiple calibrated on 15m onto 4h then inflates the stop by the bar-size
    ratio -- it produced 10.7% and 21.8% stops for SPX500 4h, which would never
    be hit.

    A stop has to survive the HOLDING PERIOD, not one bar, and the holding
    period is measured in days regardless of how the chart is drawn. So the
    volatility reference is resampled to daily first, which makes the multiple
    transfer across timeframes -- the same instrument should get the same stop
    at 5m and at 4h.
    """
    d = df.resample("1D").agg({"high": "max", "low": "min", "close": "last"}).dropna()
    atr = ta.atr(d["high"], d["low"], d["close"], 14)
    return float((atr / d["close"]).median() * 100)


def vol_scaled_stops(df: pd.DataFrame, ref_cfg: dict, ref_df: pd.DataFrame) -> dict:
    """Carry the RISK GEOMETRY of a working config onto a new instrument.

    Each stop is expressed as a multiple of the REFERENCE instrument's median
    ATR%, then re-applied at the new instrument's median ATR%. Copying the
    percentages transfers nothing; copying the ATR multiple transfers the
    thing that actually matters -- how much normal movement the stop absorbs
    before it fires.

    Deriving the multiple rather than naming it matters. A first version of
    this used a hardcoded 4x because that felt like a sensible stop. Gold's
    working stops are 24.6x median ATR, so that default produced SPX500 stops
    six times too tight -- 0.413% where 2.538% matches gold's geometry. A
    number I invented would have silently defined the strategy.
    """
    a_new, a_ref = median_atr_pct(df), median_atr_pct(ref_df)
    out, mult = {}, {}
    for k in ("sl_percent_long", "limit_percent_long",
              "sl_percent_short", "limit_percent_short"):
        m = float(ref_cfg[k]) / a_ref
        mult[k] = m
        out[k] = round(m * a_new, 3)
    return out, {"atr_new": a_new, "atr_ref": a_ref, "mult": mult}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--reference-config", default="configs/gold_15m_live_current.json",
                    help="a config KNOWN to work, whose stop-to-ATR ratios are "
                         "carried across. Its percentages are not copied; the "
                         "multiples of ITS instrument's median ATR are.")
    ap.add_argument("--reference-csv", default="xauusd_oanda_m15.csv",
                    help="the instrument --reference-config was fitted on")
    ap.add_argument("--state-triggers", action="store_true",
                    help="RSI > level / close < band instead of crossovers")
    ap.add_argument("--long-only", action="store_true")
    ap.add_argument("--trigger-tolerance", type=int, default=0)
    a = ap.parse_args()

    df = _normalise(_read_csv(a.csv))
    cfg = {f.name: getattr(Params(), f.name) for f in dc.fields(Params())}
    for k in OFF:
        cfg[k] = False
    cfg["rate_filter_mode"] = "off"
    cfg["ladder_mode"] = "percent"          # scale-free even when re-enabled
    cfg["trigger_tolerance"] = a.trigger_tolerance
    if a.state_triggers:
        cfg.update(rsi_state=True, bb_state=True,
                   lsma_state=True, ssma_state=True)
    if a.long_only:
        cfg["allow_shorts"] = False

    ref_cfg = json.load(open(a.reference_config))
    ref_df = _normalise(_read_csv(a.reference_csv))
    st, info = vol_scaled_stops(df, ref_cfg, ref_df)
    cfg.update(st)
    atr_pct = info["atr_new"]

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    json.dump(cfg, open(a.out, "w"), indent=2, default=str)

    print(f"\nwrote {a.out}")
    print(f"  from {os.path.basename(a.csv)}   {len(df):,} bars   "
          f"{df.index[0].date()} .. {df.index[-1].date()}")
    print(f"  median ATR(14) = {atr_pct:.4f}% of price")
    print(f"\n  switched OFF (must be earned, not inherited):")
    print("    " + ", ".join(OFF))
    print(f"  reference {os.path.basename(a.reference_config)} on "
          f"{os.path.basename(a.reference_csv)}, median ATR {info['atr_ref']:.4f}%")
    print(f"\n  stops, carrying the reference's ATR multiples onto this instrument:")
    print(f"    {'param':<24}{'ref %':>8}{'= xATR':>9}{'-> here':>10}")
    for k in ("sl_percent_long", "limit_percent_long",
              "sl_percent_short", "limit_percent_short"):
        print(f"    {k:<24}{float(ref_cfg[k]):>8.3f}{info['mult'][k]:>8.1f}x"
              f"{cfg[k]:>9.3f}%")
    print(f"\n  triggers: {'STATE (> / <)' if a.state_triggers else 'crossover'}"
          f"   shorts: {'off' if a.long_only else 'on'}"
          f"   tolerance: {a.trigger_tolerance}")
    print("\n  NOTE: the slippage used at training time is a separate decision.")
    print("  Measure it, do not guess:")
    print("    fetch_oanda.py --instrument <INST> --granularity D --price B --out bid.csv")
    print("    fetch_oanda.py --instrument <INST> --granularity D --price A --out ask.csv")
    print("  then difference the closes; half the median spread is the per-fill cost.\n")


if __name__ == "__main__":
    main()
