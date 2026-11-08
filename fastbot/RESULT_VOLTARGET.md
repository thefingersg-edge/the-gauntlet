# Volatility targeting — it controls risk, it does not add return

```
RUN:      2026-08-19
METHOD:   equity_cost.py v1.0 (Phase 0) + vol_target.py v1.1,
          PREREGISTRATION_v6. ONE RUN.
DATA:     6,721 daily SPX closes 2005-01-02 -> 2026-08-17;
          DGS3MO at 81% coverage of return days
VERDICT:  REJECTED on Gate B. Gate A fails levered and passes unlevered;
          Gate C passes everywhere and by a wide margin. The drawdown
          result is real. The Sharpe result is not.
```

---

## 1. The result

| | cap 2.0× | cap 1.0× |
|---|---|---|
| **Gate A** Sharpe beats B&H in ≥5 of 6 | **FAIL** — 4 of 6 | **PASS** — 6 of 6 |
| **Gate B** improvement in every era | **FAIL** | **FAIL** |
| **Gate C** drawdown not worse | PASS | PASS |

Gate B fails in both. Per §7 this stops.

## 2. My leverage prediction was exactly backwards

§3 said:

> **I further predict the leverage cap binds.** The improvement will
> require going above 1× in calm periods; capped at 1×, the strategy will
> deliver lower return with only marginally better Sharpe.

Capped at 1× it delivers lower return — 3.7% against 4.0% — and that half
is right. Everything else is wrong. **Unlevered is the version that
works:** 6 of 6 against 4 of 6, and the best delta rises from +0.05 to
+0.07.

Gate D shows why, and it is the reason the gate was pre-registered:

```
2018-02   weight entering 1.50-2.00x    index moved  -9.4%
2020-03   weight entering 0.77-1.62x    index moved -43.8%
2024-08   weight entering 0.90-1.73x    index moved  -4.3%
```

Calm invites leverage and calm is what precedes a vol shock. The rule
levers into precisely the conditions that precede its worst days. That is
not a tuning problem — it is what inverse-vol scaling *does*.

## 3. The era pattern, which is the actual finding

```
 20d 10%   +0.14  -0.11  -0.10
 20d 15%   +0.13  -0.11  -0.05
 60d 10%   +0.01  -0.08  -0.08
 60d 15%   +0.00  -0.10  -0.10
120d 10%   -0.01  -0.02  -0.13
120d 15%   -0.02  -0.06  -0.15
```

**Fourteen of eighteen era cells are negative.** Every setting is negative
in both of the last two eras. What positive there is sits in 2005–2012 and
only for the short lookbacks.

§2 argued this test is strict here on a stated basis, and the argument
holds up:

> Volatility clustering is a mechanical statistical property of price
> series, not a payment for bearing a risk. It has no economic reason to
> switch off for a decade.

It switched off. **Vol targeting helped through 2008 and has hurt in every
era since.** The mechanism is coherent: 2008 was a slow-building crisis
with persistently elevated volatility, which is what an inverse-vol rule is
built for. 2018, 2020 and 2024 were V-shaped — the rule de-risks after the
fall and re-risks after the recovery, selling the bottom and buying back
higher, twice.

## 4. What the corrected rate file moved, and my reasoning about it was wrong

The provisional run defaulted 82% of the sample to a flat 2%. I argued the
correction would hurt eras 2 and 3, because the strategy earns cash on its
(1−w) leg through the zero-rate years and buy-and-hold has no cash leg.

Eras 2 and 3 barely moved. **Era 1 fell for every single setting**, two of
them flipping negative:

| setting | era 1 before → after | eras 2+3 before → after |
|---|---|---|
| 20/10 | +0.17 → **+0.14** | −0.24 → −0.21 |
| 60/10 | +0.05 → **+0.01** | −0.17 → −0.16 |
| 120/10 | +0.03 → **−0.01** | −0.15 → −0.15 |

The reason is leverage, not the cash leg. Era 1 opens with the calm of
2005–2007, when the rule was levered **above** 1×, and a levered position
is hurt by a *higher* funding rate. The 2% default was too **low** for
those years, not too high.

Right conclusion — Gate B fails wider, 14 negative cells against 12 — and
the wrong mechanism, for the fourth time in this project. Recorded the same
way as the others.

## 5. The one result that is robust

```
buy-and-hold maximum drawdown      -56.9%
targeted, cap 2.0x                 -27.0% to -44.5%
targeted, cap 1.0x                 -27.2% to -40.8%
```

**Gate C passed in all twelve configurations, by twelve to thirty
points.** Unlike the Sharpe improvement, this holds across every setting,
both caps, and every era.

That is a precise and useful finding, and it is not the one the
hypothesis claimed:

> **Volatility targeting is a risk-control tool that works. It is not a
> return-enhancement tool that works.**

At 20d/10% unlevered it delivers 3.7% excess at 9.9% volatility against
buy-and-hold's roughly 5% at 19%. Less return, much less risk, a modestly
better ratio that does not survive era testing, and a drawdown almost half
as deep that does.

If the objective were "hold equities and be less likely to capitulate at
the bottom", this does that reliably. If the objective is "beat equity
beta", it does not.

## 6. Phase 0 — what equity beta costs here

```
funding 3.65% + markup 2.50% = 6.15%/yr to hold a long index CFD
                             = 65% of a 9.5% equity total return
```

The markup on indices is **2.50% per side**, more than double the 1.05%
OANDA charges on FX majors. In Sharpe terms on 16% volatility: an index
fund returns 5.85% excess for about **0.37**; the same exposure as an OANDA
CFD returns 3.35% for **0.21**, or 0.09 if dividend adjustments are not
credited.

The benchmark does not move — an index fund is available to anyone, and
that is the fair "what else could you do with the money" comparison. What
this establishes is that **OANDA is not where you would hold equity beta**,
which is worth knowing after twenty-three investigations of comparing
things to it.

Whether dividends are credited on an index CFD is a contract term worth
about two points a year and should be confirmed with the broker.

## 7. Verdict

**Rejected as a return strategy. Retained as a risk observation.**

The pre-registration asked whether equity beta can be made to beat itself.
On Sharpe, across a twenty-one year sample and six pre-declared settings,
it cannot — and the improvement that does appear is concentrated in the one
crisis whose shape suited the rule.

On drawdown it can, robustly, and at the cost of return. That is not an
edge. It is a preference about which risks to carry, and it should be
called that.

## 8. Scoreboard

**Twenty-three investigations. Nineteen rejections, one
measured-but-unreachable premium, one headline that dissolved on
decomposition, one real premium whose edge vanished at daily resolution,
one real premium consumed by its own margin requirement.**

The only thing that has beaten equity beta here is still equity beta —
and Phase 0 established that even that is not purchasable at the assumed
price through the accounts this project was built around.
