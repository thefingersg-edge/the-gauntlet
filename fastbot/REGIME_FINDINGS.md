# The budget, with nothing assumed

Run 2026-08-17 on NAS100_USD M5, 1,458,154 bars. **Supersedes §3–4 of
COST_BUDGET.md**, which scaled volatility from M15 by `sqrt` of time and used
a single nine-week spread from 2026. Both are now measured directly, per year
and per hour.

---

## 1. Both terms move, and they move against each other

| | range across years | |
|---|---|---|
| in-session spread | 0.35 → 3.76bp | **10.8×** |
| in-session vol/min | 1.65 → 5.64bp | **3.4×** |

2012–13 were wide-spread, low-volatility years. 2020 and 2022 were the
reverse — 2022 pairs a 0.42bp spread with 5.64bp/min, giving cost/vol of
**0.03** at a five-minute hold. A single blended number for the whole history
would describe no year in it.

This is why the trade-only-when-the-spread-clears rule is a **consequence of
the budget rather than a fitted parameter**. The 0.15 threshold was set in
silver15's `screen_universe.py` before any of this data existed.

## 2. The sample, settled

| era | verdict |
|---|---|
| 2005–2011 | **excluded** — no spread in feed |
| 2012–2013 | 60m+ holds only (cost/vol 0.59–0.64 at 5m) |
| 2014–2017 | reachable at 5m, comfortable at 15m |
| **2018–2026** | **comfortable at 5m** (cost/vol 0.03–0.13) |

**Usable sample: 2014–2026, 12.6 years.** Detectability bar `2/sqrt(12.6)` =
**0.56**.

Note 2014–2017 are not thrown away. At 15-minute holds their cost/vol is
0.14–0.24 — the era does not support a 5-minute hold, and a spread-gated bot
would simply hold longer there. That is the rule doing its job, and it keeps
four years of sample that truncation would have spent.

## 3. The hurdle, recomputed

**Final figures, exchange-local hours** (see §5 — the UTC version of this
table was smeared by DST). Session 09:00–16:00 America/New_York, 7 hours:
spread 0.436bp, vol 3.59bp/min, annualised session volatility **11.7%**.

> ## ⚠ THE TABLE BELOW IS WRONG — SUPERSEDED BY `PREREGISTRATION_v1.1.md` §2
>
> It divided the annual cost by the **asset's** session volatility, which is
> only right for a bot in the market every minute of the session. This one
> holds 30 minutes 4 times a day — ~2 hours of 7 — so its own volatility is
> far lower, and the drag was understated by ~1.9×. It also made drag scale
> linearly in trade count; it scales as `sqrt(N)`.
>
> Correct form: **`drag = cost/vol(H) × sqrt(trades per year)`**, giving
> **0.70** at 4 round trips/day, not 0.38. Found while coding the engine,
> before any backtest. Left visible rather than edited away.

```
cost drag (Sharpe) = round trips/yr x spread / annualised vol      <- WRONG
required gross     = cost drag + detectability bar
```

| round trips/day | cost drag | + full sample (12.6y) | + holdout only (5.6y) |
|---|---|---|---|
| 1 | 0.09 | ~~0.66~~ | ~~0.94~~ |
| 2 | 0.19 | ~~0.75~~ | ~~1.03~~ |
| **4** | 0.38 | ~~0.94~~ | ~~1.22~~ |
| 6 | 0.57 | ~~1.13~~ | ~~1.41~~ |
| 12 | 1.13 | ~~1.69~~ | ~~1.98~~ |

The middle column is what the strategy must produce gross to be *profitable
and provable* on the full sample. The right-hand column is the harder and more
honest number: what it must produce **inside the held-out window alone** for
that window to confirm it at 2σ.

**At 4 round trips a day the bot needs a gross Sharpe of 0.96, and 1.24 in the
holdout.** For scale, 1.0 is a good systematic strategy. This is demanding but
it is not the 50-Sharpe absurdity that FX at 5 minutes required.

Note this is worse than COST_BUDGET.md's 0.70, for two reasons that are both
corrections rather than bad luck: the comfortable session is 6 hours, not the
9 the M15 blend suggested (so annualised session vol is lower), and the usable
sample is 12.6 years, not 21.6.

## 4. Design, ready to pre-register

```
instrument    NAS100_USD (OANDA)
bar           M5
session       09:30-16:00 America/New_York
round trips   <= 4/day          -> hold ~90 min average
spread gate   enter only when measured cost/vol(hold) <= 0.15
overnight     flat -> financing is zero by construction
cost charged  the spread on the bar, per bar. Never a constant.
FIT           2014-01-01 -> 2020-12-31   (7.0y)
HELD OUT      2021-01-01 -> 2026-08-17   (5.6y)  DO NOT OPEN
```

## 5. One correction still outstanding: DST

The hour table above buckets by **UTC**, and the US cash session shifts by an
hour in UTC twice a year. The smearing is visible in the output:

```
13:00 UTC   1.07bp     <- summer session, winter pre-market, blended
14:00 UTC   0.44bp     <- in session under both
...
19:00 UTC   0.40bp     <- in session under both
20:00 UTC   1.00bp     <- summer close, winter still open, blended
```

Hours 13 and 20 are not a genuine cost gradient; they are an average of two
different states. Roughly two hours a day of potentially usable session is
being obscured.

`regime_profile.py` now buckets in `America/New_York` by default. **Applied,
and the smearing resolved:**

```
09:00 ET   0.88bp   3.73bp/min   0.11   comfortable  (contains the pre-open half-hour)
10:00 ET   0.41bp   4.83bp/min   0.04   comfortable
...
15:00 ET   0.40bp   3.44bp/min   0.05   comfortable
16:00 ET   1.15bp   1.34bp/min   0.39   out
17:00 ET   -- no data --                 OANDA daily rollover break
```

The comfortable window came out at **7 clean hours** rather than the 6 the UTC
buckets showed, so the DST correction recovered an hour of session.

**It did not, however, move the hurdle.** I predicted it would lower it; it
lowered it from 0.96 to 0.94, which is nothing. The longer session raises
annualised volatility by `sqrt(7/6)`, but including 09:00 ET — 0.88bp, because
half that hour is pre-open — raises mean spread by almost exactly as much. The
prediction was directionally right and materially wrong.

Worth more than the correction itself: **the hurdle is insensitive to where
the session boundary is drawn.** Trading 09:30–16:00 instead of 09:00–16:00
gives 0.93 against 0.94. A number that barely moves when a design choice moves
is not a fitted number — the same plateau-versus-spike logic `sweep.py` applies
to parameters, applied to a session definition.

> This is the same trap `GOLD_V6_OOS.md` recorded from the other side —
> *"TradingView's chart grid does not shift on US DST the way the OANDA
> session does"* — and it cost that project exact trade-by-trade parity. Worth
> noticing that it reappeared here in a completely different piece of code.

## 6. What is still not established

Unchanged, and still the thing most likely to end this:

**No evidence that any signal exists on NAS100 at these horizons.**
`DESIGN_BRIEF.md` found 0 of 14 price conditions and 0 of 25 indicators
sign-consistent across eras at intraday horizons. Everything done so far has
established what the bot may *spend*. It has not found anything to spend it
on, and that is where all eleven silver15 families and both pineport versions
died.

Also outstanding: quoted spread is a floor, not execution cost. Slippage,
requotes and rejections on a dealer-priced CFD are unmeasured and only
observable live.
