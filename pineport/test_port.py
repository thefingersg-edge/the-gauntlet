"""Tests for the Pine port.

Indicator tests check against values derived by hand from Pine's published
formulas, not against another Python TA library -- the point is to catch the
places where the common Python implementations disagree with TradingView.

Run with:  python3 test_port.py
"""

from __future__ import annotations

import sys
import traceback

import numpy as np
import pandas as pd

import pine_ta as ta
from broker import BrokerConfig, PineBroker
from data import security_lookahead_off
from strategy import Params, compute_indicators, run_strategy
from synth import make_bars

FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}  {detail}")
        FAILURES.append(name)


def approx(a, b, tol=1e-9) -> bool:
    return bool(np.isclose(a, b, rtol=tol, atol=tol, equal_nan=True))


# ==========================================================================
# indicators
# ==========================================================================

def test_rma_seed() -> None:
    print("\nrma / Wilder smoothing")
    s = pd.Series([1.0, 2, 3, 4, 5, 6, 7, 8])
    r = ta.rma(s, 3)
    # Warm-up is NaN until a full window exists, then seeded with SMA(3).
    check("rma NaN before full window", bool(r.iloc[:2].isna().all()))
    check("rma seed == sma(3)", approx(r.iloc[2], 2.0), f"got {r.iloc[2]}")
    # then alpha = 1/3:  x[3]=4 -> 4/3 + 2*(2/3) = 2.6666...
    check("rma step 1", approx(r.iloc[3], 4 / 3 + 2.0 * 2 / 3), f"got {r.iloc[3]}")
    check("rma step 2", approx(r.iloc[4], 5 / 3 + r.iloc[3] * 2 / 3), f"got {r.iloc[4]}")


def test_rsi_degenerate() -> None:
    print("\nrsi")
    s = pd.Series([100.0, 101, 100, 102, 102, 99])
    r1 = ta.rsi(s, 1)
    # length 1 -> alpha 1 -> pure up/down indicator
    check("rsi(1) up bar == 100", approx(r1.iloc[1], 100.0), f"got {r1.iloc[1]}")
    check("rsi(1) down bar == 0", approx(r1.iloc[2], 0.0), f"got {r1.iloc[2]}")
    check("rsi(1) unchanged bar is NaN (Pine na)", bool(np.isnan(r1.iloc[4])),
          f"got {r1.iloc[4]}")

    # A monotonically rising series must pin RSI at 100 for any length.
    up = pd.Series(np.arange(1.0, 40.0))
    check("rsi(14) monotone up == 100", approx(ta.rsi(up, 14).iloc[-1], 100.0))
    check("rsi(14) monotone down == 0",
          approx(ta.rsi(up[::-1].reset_index(drop=True), 14).iloc[-1], 0.0))


def test_stdev_population() -> None:
    print("\nstdev")
    s = pd.Series([2.0, 4, 4, 4, 5, 5, 7, 9])
    v = ta.stdev(s, 8).iloc[-1]
    check("stdev is population (ddof=0)", approx(v, 2.0), f"got {v}")
    check("stdev != sample stdev", not approx(v, float(s.std(ddof=1))))


def test_vwma() -> None:
    print("\nvwma")
    src = pd.Series([10.0, 20, 30])
    vol = pd.Series([1.0, 1, 2])
    v = ta.vwma(src, vol, 3).iloc[-1]
    check("vwma weighted correctly", approx(v, (10 + 20 + 60) / 4.0), f"got {v}")

    zero = ta.vwma(src, pd.Series([0.0, 0, 0]), 3).iloc[-1]
    check("vwma with zero volume is NaN", bool(np.isnan(zero)), f"got {zero}")


def test_true_range_and_atr() -> None:
    print("\ntr / atr")
    h = pd.Series([10.0, 12, 11])
    l = pd.Series([8.0, 9, 7])
    c = pd.Series([9.0, 11, 8])
    tr = ta.true_range(h, l, c)
    check("first tr == high-low (handle_na)", approx(tr.iloc[0], 2.0), f"got {tr.iloc[0]}")
    check("tr uses prev close", approx(tr.iloc[1], 3.0), f"got {tr.iloc[1]}")
    check("tr picks widest leg", approx(tr.iloc[2], 4.0), f"got {tr.iloc[2]}")
    check("atr == rma(tr)", approx(ta.atr(h, l, c, 2).iloc[-1],
                                   ta.rma(tr, 2).iloc[-1]))


def test_linreg() -> None:
    print("\nlinreg")
    # A perfectly linear series: the regression endpoint is the series value.
    s = pd.Series(np.arange(0.0, 20.0) * 3.0 + 5.0)
    v = ta.linreg(s, 10, 0).iloc[-1]
    check("linreg on a line returns the endpoint", approx(v, s.iloc[-1], 1e-9),
          f"got {v} vs {s.iloc[-1]}")
    # offset shifts back along the fitted line
    v1 = ta.linreg(s, 10, 1).iloc[-1]
    check("linreg offset=1 steps back one slope unit", approx(v1, s.iloc[-1] - 3.0),
          f"got {v1}")
    check("linreg NaN before full window", bool(ta.linreg(s, 10, 0).iloc[:9].isna().all()))


def test_dmi_bounds() -> None:
    print("\ndmi / adx")
    df = make_bars(600, seed=3)
    plus, minus, adx = ta.dmi(df["high"], df["low"], df["close"], 6, 20)
    valid = adx.dropna()
    check("adx has values", len(valid) > 300, f"got {len(valid)}")
    check("adx within 0..100", bool((valid >= 0).all() and (valid <= 100).all()),
          f"range {valid.min():.2f}..{valid.max():.2f}")
    check("+DI/-DI non-negative",
          bool((plus.dropna() >= 0).all() and (minus.dropna() >= 0).all()))

    # A clean uptrend should drive ADX high and +DI above -DI.
    n = 200
    up = pd.Series(np.arange(n, dtype=float))
    p2, m2, a2 = ta.dmi(up + 1, up - 1, up, 6, 20)
    check("trending series -> +DI > -DI", bool(p2.iloc[-1] > m2.iloc[-1]))
    check("trending series -> high ADX", bool(a2.iloc[-1] > 60), f"got {a2.iloc[-1]:.1f}")


def test_crossings() -> None:
    print("\ncrossover / crossunder / barssince")
    a = pd.Series([1.0, 2, 3, 2, 1])
    b = pd.Series([2.0, 2, 2, 2, 2])
    xo = ta.crossover(a, b)
    xu = ta.crossunder(a, b)
    check("crossover fires once on the crossing bar",
          list(xo) == [False, False, True, False, False], f"got {list(xo)}")
    check("crossunder fires once", list(xu) == [False, False, False, False, True],
          f"got {list(xu)}")
    check("equal-to-equal is not a cross", not bool(xo.iloc[1]))

    bs = ta.barssince(pd.Series([False, True, False, False, True, False]))
    check("barssince NaN before first true", bool(np.isnan(bs.iloc[0])))
    check("barssince 0 on the true bar", approx(bs.iloc[1], 0))
    check("barssince counts up", approx(bs.iloc[3], 2))
    check("barssince resets", approx(bs.iloc[4], 0))


def test_htf_no_lookahead() -> None:
    print("\nrequest.security lookahead_off")
    df = make_bars(400, seed=11)
    htf_close = security_lookahead_off(df, "4h", lambda h: h["close"])

    from data import resample_ohlcv
    h4 = resample_ohlcv(df, "4h")

    # Take a base bar in the middle of a 4H bucket and confirm the value it
    # sees belongs to the PREVIOUS completed 4H bar, not the forming one.
    bucket = df.index.floor("4h")
    probe = 100
    this_bucket = bucket[probe]
    pos = h4.index.get_loc(this_bucket)
    expected = h4["close"].iloc[pos - 1]
    check("htf value comes from the previous closed bar",
          approx(htf_close.iloc[probe], expected),
          f"got {htf_close.iloc[probe]} expected {expected}")

    # Strongest form of the test: the value on any base bar must never equal the
    # close of a 4H bar that has not finished yet.
    forming = pd.Series(h4["close"].reindex(bucket).to_numpy(), index=df.index)
    leaked = (htf_close.notna() & forming.notna()
              & np.isclose(htf_close.to_numpy(), forming.to_numpy())
              & (bucket != df.index))
    check("no future 4H close leaks into base bars", int(leaked.sum()) == 0,
          f"{int(leaked.sum())} leaked bars")

    first_bucket_bars = (bucket == bucket[0]).sum()
    check("first 4H bucket has no HTF value",
          bool(htf_close.iloc[:first_bucket_bars].isna().all()))


# ==========================================================================
# broker
# ==========================================================================

def _bars(rows) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=len(rows), freq="1h", tz="UTC")
    return pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx)


def test_broker_next_bar_fill() -> None:
    print("\nbroker: entry latency")
    df = _bars([[100, 101, 99, 100], [102, 103, 101, 102], [104, 105, 103, 104]])
    b = PineBroker(BrokerConfig(initial_capital=1000))

    b.process_bar(0, df.index[0], *df.iloc[0])
    b.mark_to_market(df.iloc[0]["close"])
    b.submit_entry(1, 1)                       # signal at close of bar 0
    check("no position on the signal bar", b.position_size == 0)

    b.process_bar(1, df.index[1], *df.iloc[1])
    check("filled on the next bar", b.position_size == 1)
    check("filled at the next bar's OPEN, not the signal close",
          approx(b.entry_price, 102.0), f"got {b.entry_price}")


def test_broker_stop_fill_and_gap() -> None:
    print("\nbroker: stop fills")
    df = _bars([[100, 101, 99, 100], [100, 101, 99, 100],
                [100, 101, 95, 96], [90, 91, 85, 86]])
    b = PineBroker(BrokerConfig(initial_capital=1000))
    b.process_bar(0, df.index[0], *df.iloc[0]); b.mark_to_market(100)
    b.submit_entry(1, 1)
    b.process_bar(1, df.index[1], *df.iloc[1]); b.mark_to_market(100)
    b.set_exit(stop=97.0)
    b.process_bar(2, df.index[2], *df.iloc[2])
    check("stop fills at the stop price when touched intrabar",
          len(b.trades) == 1 and approx(b.trades[0].exit_price, 97.0),
          f"got {b.trades[0].exit_price if b.trades else 'no trade'}")

    # gap case: bar opens below the stop -> fill at the open, worse than stop
    b2 = PineBroker(BrokerConfig(initial_capital=1000))
    b2.process_bar(0, df.index[0], *df.iloc[0]); b2.mark_to_market(100)
    b2.submit_entry(1, 1)
    b2.process_bar(1, df.index[1], *df.iloc[1]); b2.mark_to_market(100)
    b2.set_exit(stop=97.0)
    b2.process_bar(3, df.index[3], *df.iloc[3])
    check("gap through the stop fills at the open",
          len(b2.trades) == 1 and approx(b2.trades[0].exit_price, 90.0),
          f"got {b2.trades[0].exit_price if b2.trades else 'no trade'}")


def test_broker_pyramiding_and_reversal() -> None:
    print("\nbroker: pyramiding=0 and reversals")
    df = _bars([[100, 101, 99, 100]] * 5)
    b = PineBroker(BrokerConfig(initial_capital=1000))
    b.process_bar(0, df.index[0], *df.iloc[0]); b.mark_to_market(100)
    b.submit_entry(1, 1)
    b.process_bar(1, df.index[1], *df.iloc[1]); b.mark_to_market(100)
    b.submit_entry(1, 1)                       # same direction -> rejected
    b.process_bar(2, df.index[2], *df.iloc[2]); b.mark_to_market(100)
    check("same-direction entry rejected (pyramiding=0)", b.position_size == 1,
          f"got {b.position_size}")

    b.submit_entry(-1, 1)                      # opposite -> reverse
    b.process_bar(3, df.index[3], *df.iloc[3]); b.mark_to_market(100)
    check("opposite entry reverses the position", b.position_size == -1,
          f"got {b.position_size}")
    check("reversal books the closing trade", len(b.trades) == 1)
    check("reversal exit reason recorded",
          bool(b.trades and b.trades[0].exit_reason == "reverse"))


def test_broker_pnl_and_costs() -> None:
    print("\nbroker: P&L, point value, costs")
    df = _bars([[100, 101, 99, 100], [100, 110, 99, 105], [110, 115, 105, 112]])
    b = PineBroker(BrokerConfig(initial_capital=1000, point_value=10.0))
    b.process_bar(0, df.index[0], *df.iloc[0]); b.mark_to_market(100)
    b.submit_entry(1, 2)
    b.process_bar(1, df.index[1], *df.iloc[1]); b.mark_to_market(105)
    b.set_exit(stop=108.0)
    b.process_bar(2, df.index[2], *df.iloc[2])
    t = b.trades[0]
    # Entry at 100 (open of bar 1). Bar 2 opens at 110, above the 108 stop, then
    # trades down to 105 -- so the stop is touched, not gapped, and fills at 108.
    check("pnl = (exit-entry) * qty * pointvalue",
          approx(t.pnl, (108 - 100) * 2 * 10.0), f"got {t.pnl}")
    check("equity reflects realised pnl", approx(b.equity, 1000 + t.pnl),
          f"got {b.equity}")

    b3 = PineBroker(BrokerConfig(initial_capital=1000, slippage_points=0.5))
    b3.process_bar(0, df.index[0], *df.iloc[0]); b3.mark_to_market(100)
    b3.submit_entry(1, 1)
    b3.process_bar(1, df.index[1], *df.iloc[1])
    check("slippage worsens the long entry", approx(b3.entry_price, 100.5),
          f"got {b3.entry_price}")


def test_no_entry_bar_stop() -> None:
    print("\nbroker: entry bar carries no stop")
    # Bar 1 is the entry bar and dives well below any plausible stop; because the
    # script has not yet seen the position, no exit order exists during it.
    df = _bars([[100, 101, 99, 100], [100, 101, 80, 100], [100, 101, 99, 100]])
    b = PineBroker(BrokerConfig(initial_capital=1000))
    b.process_bar(0, df.index[0], *df.iloc[0]); b.mark_to_market(100)
    b.submit_entry(1, 1)
    b.process_bar(1, df.index[1], *df.iloc[1]); b.mark_to_market(100)
    check("no exit on the entry bar", len(b.trades) == 0 and b.position_size == 1)


# ==========================================================================
# strategy
# ==========================================================================

def test_strategy_runs() -> None:
    print("\nstrategy: end to end")
    df = make_bars(4000, seed=5)
    res = run_strategy(df, Params(), BrokerConfig(initial_capital=4000))
    check("produced an equity curve", len(res.equity) == len(df))
    check("equity starts at initial capital", approx(res.equity.iloc[0], 4000.0),
          f"got {res.equity.iloc[0]}")
    check("no NaN in equity", bool(res.equity.notna().all()))
    print(f"        trades={len(res.trades)} "
          f"final_equity={res.equity.iloc[-1]:,.2f}")

    if not res.trades.empty:
        t = res.trades
        check("all trades closed", bool((t["exit_bar"] >= 0).all()))
        check("exit is at or after entry", bool((t["exit_bar"] >= t["entry_bar"]).all()))
        check("no overlapping trades",
              bool((t["entry_bar"].iloc[1:].to_numpy()
                    >= t["exit_bar"].iloc[:-1].to_numpy()).all()),
              "a trade opened before the previous one closed")
        check("mae <= 0 <= mfe",
              bool((t["mae"] <= 1e-9).all() and (t["mfe"] >= -1e-9).all()))


def test_long_stop_is_trailing_and_ratchets() -> None:
    print("\nstrategy: long stop ratchet")
    df = make_bars(3000, seed=5)
    res = run_strategy(df, Params(), BrokerConfig(initial_capital=4000))
    d = res.diagnostics
    pos = d["position"].to_numpy()
    stop = d["price_stop_long"].to_numpy()

    violations = 0
    for i in range(1, len(pos)):
        if pos[i] > 0 and pos[i - 1] > 0 and stop[i] < stop[i - 1] - 1e-9:
            violations += 1
    check("long stop never moves down while in position", violations == 0,
          f"{violations} downward moves")

    in_long = pos > 0
    if in_long.any():
        check("long stop sits below price while long",
              bool((stop[in_long] < df["close"].to_numpy()[in_long] + 1e-9).all()))


def test_short_stop_ratchets_down() -> None:
    print("\nstrategy: short stop ratchet")
    df = make_bars(3000, seed=17)
    res = run_strategy(df, Params(), BrokerConfig(initial_capital=4000))
    d = res.diagnostics
    pos = d["position"].to_numpy()
    stop = d["price_stop_short"].to_numpy()
    violations = sum(
        1 for i in range(1, len(pos))
        if pos[i] < 0 and pos[i - 1] < 0 and stop[i] > stop[i - 1] + 1e-9
    )
    check("short stop never moves up while in position", violations == 0,
          f"{violations} upward moves")


def test_signals_use_only_past_information() -> None:
    print("\nstrategy: no lookahead in signals")
    df = make_bars(2500, seed=23)
    full = compute_indicators(df, Params())

    # Recomputing on a truncated history must not change earlier signal values.
    cut = 2000
    trunc = compute_indicators(df.iloc[:cut], Params())
    warm = 1200          # skip the 942-bar KC warm-up region
    a = full["long_signal"].iloc[warm:cut].to_numpy()
    b = trunc["long_signal"].iloc[warm:cut].to_numpy()
    check("long signals unchanged when future bars are removed",
          bool((a == b).all()), f"{int((a != b).sum())} differing bars")

    a = full["short_signal"].iloc[warm:cut].to_numpy()
    b = trunc["short_signal"].iloc[warm:cut].to_numpy()
    check("short signals unchanged when future bars are removed",
          bool((a == b).all()), f"{int((a != b).sum())} differing bars")


def test_determinism() -> None:
    print("\nstrategy: determinism")
    df = make_bars(2000, seed=31)
    r1 = run_strategy(df, Params(), BrokerConfig(initial_capital=4000))
    r2 = run_strategy(df, Params(), BrokerConfig(initial_capital=4000))
    check("two runs agree exactly",
          approx(r1.equity.iloc[-1], r2.equity.iloc[-1]) and len(r1.trades) == len(r2.trades))


def test_unix_epoch_time_parsing() -> None:
    """TradingView exports `time` as integer epoch seconds, not ISO text."""
    print("\ndata: TradingView epoch timestamps")
    from data import parse_time_column

    secs = pd.Series([1778691600, 1778695200, 1778698800])
    parsed = parse_time_column(secs)
    check("epoch seconds parsed as seconds, not nanoseconds",
          parsed.iloc[0].year == 2026, f"got {parsed.iloc[0]}")
    check("bar spacing preserved",
          (parsed.diff().dropna() == pd.Timedelta(hours=1)).all())

    ms = pd.Series([1778691600000, 1778695200000])
    check("epoch milliseconds detected",
          parse_time_column(ms).iloc[0].year == 2026,
          f"got {parse_time_column(ms).iloc[0]}")

    iso = pd.Series(["2026-05-13 17:00:00", "2026-05-13 18:00:00"])
    check("ISO strings still parse", parse_time_column(iso).iloc[0].year == 2026)


def test_assume_squeeze_on_is_signal_neutral() -> None:
    """`assume_squeeze_on` must not change any signal on a warmed-up bar.

    The flag exists so short chart exports can be verified without the 942-bar
    `sqzOn` warm-up. That is only legitimate because `sqzOn` is true on every
    warmed-up bar; this test is what makes the shortcut safe to rely on.
    """
    print("\nstrategy: assume_squeeze_on changes nothing once warm")
    df = make_bars(4000, seed=42)
    a = compute_indicators(df, Params())
    b = compute_indicators(df, Params(assume_squeeze_on=True))

    warm = a["lower_kc"].notna() & a["upper_kc"].notna()
    check("sqzOn is true on every warmed-up bar",
          bool(a.loc[warm, "sqz_on"].all()),
          f"{int((~a.loc[warm, 'sqz_on']).sum())} warmed-up bars had sqzOn false")
    for key in ("sqz_up", "sqz_down", "long_signal", "short_signal"):
        same = (a.loc[warm, key].fillna(False) == b.loc[warm, key].fillna(False)).all()
        check(f"{key} identical on warmed-up bars", bool(same))

    # And it must NOT be a blanket disable: valL > 0 has to keep rejecting.
    rejected = int((b["sqz_up"].fillna(False) != (b["val_l"].notna())).sum())
    check("valL > 0 still rejects signals under the shortcut",
          bool((~b.loc[b["val_l"].notna(), "sqz_up"]).any()),
          "sqz_up was true everywhere, so the linreg test stopped filtering")
    _ = rejected


def test_quirks_are_reproduced() -> None:
    """Lock in the surprising behaviours so a later 'cleanup' cannot hide them."""
    print("\nstrategy: documented quirks still present")
    df = make_bars(3000, seed=5)
    p = Params()
    ind = compute_indicators(df, p)

    # Measured only over bars where the 942-length Keltner has warmed up;
    # before that the comparison is against NaN and is trivially False.
    warm = ind["lower_kc"].notna() & ind["upper_kc"].notna()
    sqz_rate = float(ind.loc[warm, "sqz_on"].fillna(False).mean())
    check("QUIRK: sqzOn is effectively always true once warmed up", sqz_rate > 0.99,
          f"sqzOn true on {100*sqz_rate:.1f}% of warmed-up bars")
    # Note the precise claim: sqzOn contributes nothing, so sqzUp reduces to the
    # linreg test. The linreg test itself is NOT inert -- it rejects real
    # signals, verified against TradingView on 2026-07-27.
    check("QUIRK: sqzOn contributes nothing; valL alone decides sqzUp",
          bool((ind.loc[warm, "sqz_up"] == (ind.loc[warm, "val_l"] > 0)).all()),
          "sqz_up differs from the raw linreg test, so sqzOn does bind somewhere")

    valid = ind[["lower_bb", "lower_kc"]].dropna()
    check("QUIRK: lower Keltner sits far below the lower Bollinger",
          bool((valid["lower_kc"] < valid["lower_bb"]).all()))

    val_s = ind["val_s"].dropna()
    check("QUIRK: valS is nowhere near the 960 short threshold",
          bool((val_s.abs() < 960).all()),
          f"max |valS| = {val_s.abs().max():.1f}")

    res = run_strategy(df, p, BrokerConfig(initial_capital=4000))
    if not res.trades.empty:
        reasons = set(res.trades["exit_reason"])
        check("QUIRK: no trade ever exits on the limit leg",
              "limit" not in reasons, f"reasons seen: {reasons}")


# ==========================================================================

def main() -> int:
    tests = [
        test_rma_seed, test_rsi_degenerate, test_stdev_population, test_vwma,
        test_true_range_and_atr, test_linreg, test_dmi_bounds, test_crossings,
        test_htf_no_lookahead,
        test_broker_next_bar_fill, test_broker_stop_fill_and_gap,
        test_broker_pyramiding_and_reversal, test_broker_pnl_and_costs,
        test_no_entry_bar_stop,
        test_strategy_runs, test_long_stop_is_trailing_and_ratchets,
        test_short_stop_ratchets_down, test_signals_use_only_past_information,
        test_determinism, test_unix_epoch_time_parsing,
        test_assume_squeeze_on_is_signal_neutral, test_quirks_are_reproduced,
    ]
    for t in tests:
        try:
            t()
        except Exception:
            print(f"  ERROR in {t.__name__}")
            traceback.print_exc()
            FAILURES.append(t.__name__)

    print("\n" + "=" * 60)
    if FAILURES:
        print(f"{len(FAILURES)} FAILED: {', '.join(FAILURES)}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
