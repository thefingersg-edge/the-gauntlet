# Pre-registration — O1: Kalman velocity trend (external replication)

FROZEN: 2026-09-19, before any outcome statistic was computed.
Author of the rules: Dave (relayed from a public video). Author of this document: Claude.
Nothing below may change after the first result is seen. If a declaration here is
wrong, it is corrected BEFORE the run or not at all.

---

## 0. Provenance and prior

This strategy did not arise from our own research. It is the reported winner of a
public "AI trading challenge" run on crypto perpetuals through a prompt-driven
backtest terminal (trader.dev — "prompt-driven strategies, AI-native backtests,
one-click deploys to Bybit, Blofin, Toobit, WeeX"). Reported figures:

    net return   +117%          trades        358
    profit factor  1.44         max drawdown  10.9%
    Sharpe         2.51         timeframe     4h (moved there mid-challenge)

The author states that **1,600 of roughly 2,000 backtests failed immediately**, and
that "99% of amazing back tests will fail on live markets".

That disclosure fixes the search width, so the selection-bias prior can be computed
rather than guessed. The expected maximum Sharpe from N independent zero-edge
strategies over T years is approximately `sqrt(2 ln N) / sqrt(T)`:

    N = 2,000, T = 1.5y  ->  expected best Sharpe from NO edge = 3.18
    claimed Sharpe                                            = 2.51

The reported winner does not clear the threshold its own search width implies. Two
further defects in the selection procedure, both stated by the author:

  - the winner "strangely enough" migrated to the 4h timeframe, which makes
    timeframe a fitted parameter and multiplies the effective search width;
  - candidates were screened on max drawdown < 20%, which is the single most
    path-dependent and most overfittable statistic available.

**Therefore the prior on this strategy is low, and a null result here is the
expected outcome requiring no explanation.** This run exists because the rules are
cheap to test on a panel that is 14x longer and 16x wider than the original, and
because a specific, fully-specified external claim is worth more than a vague one.
A positive result must clear every gate in section 8; nothing less is reportable.

Registered expectation, recorded now: **the primary statistic will not clear G2.**

---

## 1. The specification as given

Verbatim from Dave:

> entry = x2 (velocity) crosses above 0 and close ema(200). Exit = 2x crosses below
> 0 or chandelier stop at peak -4 x atr. Kalman = Q = 0.01, r= 1.0 (both x atr(14)
> squared for scaling). f=[[1,1],[0,1]], observe price only. Size = 40% of equity,
> no pyramiding

### 1.1 Ambiguities resolved by declaration (pre-outcome)

| # | Ambiguity | Declared reading | Why |
|---|---|---|---|
| A1 | "close ema(200)" — operator missing | `close > EMA(200)` | Only reading consistent with a long entry on a rising-velocity cross. |
| A2 | Which ATR for the chandelier | `ATR(14)`, Wilder smoothing, same series as the filter scaling | No second ATR length is specified anywhere in the rules; introducing one would add a free parameter. |
| A3 | "peak" | Highest **high** since and including the entry bar | Standard chandelier definition. |
| A4 | EMA(200) timeframe | Same timeframe as the signal bar | A higher-timeframe EMA would be multi-timeframe, which the source video itself warns against, and adds a fitted parameter. |
| A5 | Long-only or both sides | **Long-only** as written | "crosses above 0" + "close >" is one-sided. The short mirror is a control (section 8, G6), not an alternative specification. |

| A6 | Chandelier ATR: fixed at entry, or trailing? | **Trailing** — ATR(14) of the current bar, recomputed each bar | The standard chandelier definition (LeBeau) uses current ATR. Fixing it at entry would make the stop a constant-distance stop, which is a different rule. Caught on implementation, amended 2026-09-19 BEFORE any code was run and before any outcome existed. |

| A7 | Volatility window for unit-risk normalisation | Trailing realised vol over **378 bars (4h) / 1512 bars (H1)** ~= 63 trading days, **shifted one bar** | R2: an unshifted rolling stat leaks the current bar. Window matched to the 63-day convention used elsewhere in the project. |
| A8 | Is the chandelier level causal? | **Yes.** The stop level for bar t uses the peak through **t-1** and ATR(14) at **t-1** — known before bar t opens. The stop is armed from the bar AFTER the entry fill, with peak initialised to the entry bar's high. | Using bar t's own high in the peak before testing bar t's low is intrabar lookahead and inflates every stop-based backtest. Pine's `strategy.exit` on a current-bar level has exactly this defect. |
| A9 | Exit precedence within one bar | **Velocity exit first.** Signalled at close t-1, it fills at open t, which precedes any intrabar stop touch. | Chronological. (Where the bar gaps through the stop both conventions fill at the open anyway, so this only matters for non-gap bars.) |

| A10 | G4 matched-control cell definition | Era x decile of prior return over **30 bars (4h) / 120 bars (H1)** (~1 trading week) x decile of the same trailing vol used for normalisation (A7). Control bars are bars in the same cell that are not inside a trade; the comparison is mean h-bar forward return, h = the matched trade's realised holding period. | The pre-registration named the three matching axes but not the lookbacks. Fixed here, before the run. |

These readings are fixed. If Dave overrides one, it is overridden before the run.

### 1.2 A note on the ATR scaling — effective parameter count

Q = 0.01 x ATR(14)^2 and R = 1.0 x ATR(14)^2 scale **both** noise covariances by
the same factor. In a linear-Gaussian filter the Kalman gain depends on Q and R
only through their ratio: scaling both by c scales P by c and leaves K, and hence
the state estimate, unchanged. Since the signal is `sign(x2)` — a comparison to
zero — the ATR^2 factor is very nearly a no-op for this strategy. It survives only
as a second-order path effect, because c changes bar to bar while P carries the
previous scale.

Consequences, recorded now:

  - The effective free parameter is **the ratio Q/R = 0.01**, not two parameters.
    One tuning knob is genuinely in this strategy's favour on the overfitting axis,
    and that is worth saying plainly.
  - No post-hoc claim that the ATR^2 scaling is load-bearing can be entertained.
    It is measurable: ablation ABL-4 (section 7) runs the filter with constant
    Q = 0.01, R = 1.0 and no ATR scaling at all. If the two differ materially, the
    difference is the second-order path effect and will be reported as such.

---

## 2. Filter definition (exact)

State `x = [level, velocity]^T`. Per bar, with `a = ATR(14)^2` on the signal timeframe:

    F = [[1, 1],
         [0, 1]]                H = [1, 0]
    Q = 0.01 * a * I2           R = 1.0 * a

    predict:  x' = F x                  P' = F P F^T + Q
    update:   K  = P' H^T / (H P' H^T + R)
              x  = x' + K (z - H x')    P  = (I - K H) P'

where `z` is the bar close. Initialisation, declared:

    x0 = [first close, 0]       P0 = diag(R0, R0)  with R0 from the first valid ATR
    burn-in: first 500 bars of each market discarded (filter transient + EMA200 +
             ATR warm-up); no signal may be taken inside the burn-in.

`x2` is the post-update velocity of the current bar. A "cross above 0" is
`x2[t] > 0 and x2[t-1] <= 0`.

---

## 3. Data

### 3.1 The 4h grid — corrected before this run

`../resampled_h4/` (pre-existing) was built with a naive UTC resample landing bars
on 00/04/08/12/16/20 UTC. OANDA anchors H4 to the **17:00 New York** trading-day
boundary, which moves with US DST:

    EDT (UTC-4):  boundaries at UTC hours  1,  5,  9, 13, 17, 21
    EST (UTC-5):  boundaries at UTC hours  2,  6, 10, 14, 18, 22

The naive grid shares **zero** timestamps with OANDA's native H4 candles. This is
the same error class as R4 on the daily bars, one timeframe down. That directory is
quarantined as `resampled_h4.WRONG-GRID-DO-NOT-USE/` and is not read by anything.

`make_h4.py` (written for this run) rebuilds 4h bars from the H1 feed on the
DST-aware grid, with `MIN_BARS = 4` so only complete blocks are emitted. Validated
against the 11 markets that have native OANDA H4 files:

    11 markets, 316,570 shared bars, 0 OHLC mismatches (0.000%)

Bar boundaries are not cosmetic for this strategy: the entry is a crossing event
and the exit is a stop off a running high. Both are determined by where the bars
are cut.

### 3.2 Sample

Primary: **16 markets**, those whose 4h coverage exceeds 1,100 bars/yr.

    audusd bcousd eurgbp eurjpy eurusd gbpusd nas100usd natgasusd
    spx500usd usb10yusd usdcad usdjpy xagusd xauusd xcuusd xptusd

Excluded, declared now with the reason: **cornusd, de10ybeur, de30eur, sugarusd,
wheatusd** (512-808 bars/yr). These are session-traded, so most 4h blocks are
structurally incomplete — a property of the market's hours, not a data defect. The
1,100 threshold sits in a clean gap (highest excluded 808, lowest included 1,140);
it is set here, before any outcome, and is not revisited.

End date: all markets **truncated at 2026-08-07**, the common end of the H1 feed.
Ten markets were last fetched 2026-08-07, one 2026-08-26, ten 2026-08-29; without
truncation the final three weeks would be an unbalanced panel. Three weeks off a
20-year sample changes nothing material. (GAUNTLET 1.6: the feed is 6 weeks stale
as of today. A refresh is available and would not alter any conclusion here.)

Eras, unchanged from the rest of the project: E1 2005-2012, E2 2012-2019,
E3 2019-2026.

---

## 4. Timeframes — both declared now

    PRIMARY    4h   (matches the claim)
    SECONDARY  H1   (the source moved timeframes mid-search; if the edge is real
                     it should not live at exactly one bar width)

Both are in the declared test family and both are FDR-corrected. This is not
"try both, report the better one" — the 4h result is the headline whatever H1 does.

---

## 5. What is being tested, and what is not

**The signal is tested. The sizing is not.** Sharpe is scale-invariant, so
"40% of equity" does not affect the primary statistic at all. Positions are held at
unit risk, volatility-normalised, so results are comparable with every other family
in this project.

The 40%-of-equity path is computed and reported **descriptively only**, because it
is what produces the headline numbers in the source. Recorded now: 40% notional
with a 4 x ATR stop risks roughly `0.40 x 4 x ATR/price` of equity per trade. On
crypto-like 4h volatility that is approximately **5% of equity per trade** — about
6x the 0.8% used in our own live forward test. The source's +117% return and 10.9%
drawdown are therefore **leverage artefacts, not evidence**. Sharpe is the only one
of the four reported figures that carries information about the signal.

Vehicle (GAUNTLET 4.6): OANDA CFDs, 0.1-unit increments. Any surviving result must
be restated at that granularity before it counts.

---

## 6. Execution conventions

  - Signal evaluated on bar close; entry fills at the **next** bar's open.
  - Chandelier stop checked intrabar. For a long, if `low <= stop` the fill is
    `min(stop, that bar's open)` — a gap through the stop fills at the open, not
    at the stop. Optimistic stop fills are a classic backtest inflator and are
    excluded by construction.
  - Velocity-cross exit fills at the next bar's open.
  - Both exits armed simultaneously; whichever triggers first ends the trade.
  - One unit, no pyramiding, no re-entry on the same bar as an exit.
  - Costs: **0 / 1 / 3 bp** per side. **1 bp is primary.** The source reports ~240
    trades/yr; at that rate 3 bp costs roughly 1.4% a year, which for a 10%-vol
    series is about 0.14 of Sharpe. Cost sensitivity is expected to matter.

---

## 7. Declared test count — fixed now

Inferential family, **12 tests**, BH-FDR applied across all 12:

    T1   4h primary, long-only, 1 bp
    T2   H1 primary, long-only, 1 bp
    T3   4h short mirror
    T4   H1 short mirror
    ABL-1  Kalman velocity cross alone, no EMA(200) filter        (4h, H1)
    ABL-2  EMA(200) filter alone, no Kalman                       (4h, H1)
    ABL-3  velocity-cross exit only, no chandelier                (4h, H1)
    ABL-4  filter with Q=0.01, R=1.0 and NO ATR scaling           (4h, H1)

Descriptive, reported but not inferential: 16 per-market Sharpes per timeframe
(32 total), BH applied within each timeframe; the 40%-of-equity equity curve; cost
sensitivity at 0 and 3 bp; trade count, profit factor, max drawdown per market.

No test outside this list may be added after a result is seen. If one is added
before, this document is amended and the amendment dated.

---

## 8. Gates — thresholds set before the run

| Gate | Test | Pass condition |
|---|---|---|
| **G0** | Pre-registration | This document, frozen before any outcome. **Met.** |
| **G1** | Era sign consistency | T1 Sharpe has the **same sign** in E1, E2 and E3. |
| **G2** | Noise floor | T1 Sharpe > `2 / sqrt(T * N_eff)`, with `N_eff` **measured** on the realised position series (`N_eff = N / (1 + (N-1) * rho_bar)`), not assumed. |
| **G3** | Destroyed timing | Signal lagged **750 bars** must score materially below T1 and be indistinguishable from zero. If the lagged version scores as well, the "edge" is unconditional long exposure plus vol targeting, not the filter. |
| **G4** | Matched control | Beats a control matched on era x prior-return decile x volatility decile. |
| **G5** | Cost | Still positive **and** above the G2 floor at **3 bp**. |
| **G6** | Mirror / dumb version | T1 must beat (a) its own short mirror T3, and (b) **ABL-2**, plain `close > EMA(200)` long-only with no Kalman at all. Failing (b) is fatal: it is what killed M1. |
| **G7** | Vehicle | Restated at OANDA 0.1-unit granularity with floor-not-ceil rounding, still above the G2 floor. |
| **G8** | Inference | Stationary block bootstrap, mean block 63 bars, 10,000 draws; BH-FDR across the 12 declared tests; q < 0.10. |

Additional, given section 0: even a full pass is a **replication under a low prior**,
and will be reported as "survives our gauntlet on 16 markets over 20 years",
never as confirmation of the +117% claim, which is a sizing artefact.

---

## 9. Kill conditions

Any one of these ends the family; no further variants are run:

  1. G1 fails — the sign is not stable across eras.
  2. G6(b) fails — plain EMA(200) long-only does as well or better. The Kalman
     filter would then be decoration on a trend filter.
  3. G3 fails — the 750-bar-lagged signal scores comparably.
  4. G2 fails at 1 bp by more than a factor of two.

## 10. What would change my mind

A pass on G1-G8 with T1 Sharpe above the G2 floor at 3 bp, era signs consistent,
beating both the mirror and plain EMA(200), on 16 markets over 20 years, would be
the first external claim in this project to survive. It would still need the
forward-test treatment before any capital: pre-registered, position-limited, and
run live at 0.1-unit granularity for the ~33 trades needed to distinguish the
result from zero.

---

## 11. Files

    make_h4.py            4h bar builder, DST-aware NY-17:00 grid (new, validated)
    adaptive/data_h4/     21 markets of 4h bars (16 used here)
    o1_kalman.py          the test harness (not yet written)
    FINDINGS_KALMAN.md    results (not yet written)
