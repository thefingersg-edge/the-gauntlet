# PREREGISTRATION v5 — FX carry, and how much of it OANDA keeps

```
WRITTEN:  2026-08-19, BEFORE any financing rate has been read
STATUS:   FROZEN. One run. No sweeps, no sign flips, no re-specification.
VENUE:    OANDA, the account already open. Token stays on the local machine.
GAP:      AUDIT.md called this "the largest accessible gap in the entire
          record" -- carry is a forty-year documented premium and no test
          across silver15, pineport or fastbot has ever touched it.
```

---

## 1. Hypothesis and mechanism

**H1.** High-interest-rate currencies do not depreciate enough to offset
their interest advantage. Holding the high-yielder against the low-yielder
therefore earns the differential, and that differential is a **risk
premium** — payment for bearing the risk that carry unwinds violently,
which it periodically does (2008, the 2015 CHF break, the 2024 JPY
unwind).

This is the same class as the variance premium and the VIX term structure:
paid to bear, not paid to predict. It is the fourth such test and the
first that needs no new venue, no new broker, and no data purchase.

**The question is not whether the premium exists.** Forty years of
literature say it does. The question is the one this project is built for:
**how much of it survives a retail financing spread.**

## 2. The identity that makes Phase 0 decisive

OANDA quotes a long and a short financing rate for every instrument. If
its formula is the standard one — the interest differential, less a flat
administrative charge applied against you on both sides — then

```
longRate  =  D - m
shortRate = -D - m
```

from which **both unknowns fall out of OANDA's own two published numbers**:

```
D = (longRate - shortRate) / 2      the true differential
m = -(longRate + shortRate) / 2     the broker's take, per side
```

No external interest-rate data is needed to recover either. That makes the
cost budget a single API call.

**This model is not assumed, it is tested.** If `m` is a flat
administrative charge it should be roughly CONSTANT across instruments.
Phase 0 reports its dispersion, and a wildly varying `m` falsifies the
model — in which case the decomposition above is wrong and nothing derived
from it may be used.

## 3. My prediction, recorded so it can be scored

**I predict Phase 0 survives and Gate B fails.**

Reasoning: a flat administrative charge of roughly half a percent a side
is modest against the 3–4 point differentials currently available between
USD and the low-yielders, so the broker probably does not eat the whole
premium — which is a change from the last two tests. But carry's history
splits hard by era: strong before 2008, close to dead through 2010–2020
when every major rate sat near zero and there was no differential to
harvest, and revived from 2022 as the Fed hiked against a static Bank of
Japan. **A premium that only exists when rates diverge cannot keep its
sign through an era when they did not.**

Scored against my record: I have now been right on the verdict and wrong
on the mechanism twice (`RESULT_VIXCURVE`, `RESULT_KRAKENBASIS`). This
prediction names the mechanism explicitly so that failure mode is visible.

## 4. Phase 0 — the broker's take, and its veto

Runs locally with the existing OANDA token. **Read-only endpoints. No
order is ever placed by any file in this project.**

Restricted to genuine FX pairs. Index and metal CFDs have a financing cost
but no interest differential to earn — a long gold position pays carry, it
does not collect it — so they are reported for the markup measurement and
excluded from the carry gate.

**Gate 0.** For at least one FX pair,

```
(|D| - m) / annualised volatility  >=  0.40
```

This is the carry-to-volatility ratio, and it is an **upper bound on the
achievable Sharpe**: it credits the position with the entire net
differential and charges it nothing for spot drift, which on average
partially offsets carry, or for the crash risk that is the premium's whole
reason for existing. 0.40 is `DESIGN_BRIEF`'s equity-beta bar, unchanged.

**If the upper bound is below 0.40 for every available pair, no amount of
history can rescue it and this stops.** That is the cleanest possible
rejection: the premium net of the broker is arithmetically too small to
reach the bar before a single day of price data is examined.

**A units guard, because this one would be catastrophic and silent.**
Financing rates may be quoted annually or daily; reading a daily rate as
annual understates by 365×, and the reverse overstates by the same. Any FX
pair showing `|D| > 20%` fails a sanity check and stops the run. Majors do
not have twenty-point differentials.

## 5. Phase 1 — only if Phase 0 survives

Daily OANDA candles for the surviving pairs, and one policy-rate series
per currency involved, downloaded once as `DGS3MO` was.

```
position   long the high-yielder against the low-yielder, held,
           rebalanced quarterly on the rate ranking
return     spot return + realised differential - m - spread costs
benchmark  Sharpe, against DESIGN_BRIEF's 0.40 equity-beta bar
```

**Gate A.** Net Sharpe ≥ **0.40** after markup and spread.

**Gate B.** Net return positive in **every era** — three equal thirds of
the sample. This is the criterion that rejected fourteen price conditions
and twenty-five indicators, that the VIX curve passed, and that the crypto
basis failed.

**Gate C.** ≥ 10 years, ≥ 3 years per era.

**Gate D.** The capital gate, and on this project's recent record the one
that decides things. Size to survive the **worst observed carry unwind**
within a 30% account drawdown, and report the return on **total capital**.
Gate A is applied after it, exactly as in v4.

## 6. Kill conditions

- **Gate 0 fails** → stop. The differential net of the broker is too small
  and history is irrelevant.
- **The markup model is falsified** (dispersion of `m` too wide) → stop,
  and report that OANDA's financing cannot be decomposed this way. Do not
  substitute an assumed markup.
- **Gate A or Gate B fails** → stop. No "only trade carry when the
  differential exceeds X", no "only the best pair in hindsight", no
  switching to a different rebalancing frequency. Each is a sweep.
- **No sign flip.** If carry pays negatively, the reverse trade is not
  tested.
- **Pairs are not selected on outcome.** The universe is every FX pair the
  account quotes, fixed before any return is computed.

## 7. What this will not see

- **Financing rates today, applied to history.** Phase 1 must assume `m`
  has been roughly stable. It is measurable only at a point in time, and
  if OANDA's charge has widened over the years the historical net return
  is overstated. This is a real limitation and cannot be fixed from
  available data.
- **The crash itself.** The worst carry unwinds happen over days, and Gate
  D uses daily closes. `RESULT_VIXDAILY` established at some cost that the
  worst single day in a sample can be invisible at coarser resolution.
- **Gap risk and weekend risk**, which is where carry unwinds actually
  hurt a leveraged retail position.
- **Whether the quoted financing is what gets charged.** Only a live
  position's transaction history would show that.

## 8. Self-test requirements

Per the standing rule — *a gate that has never been observed to fail has
not been tested* — each of these must be shown failing on a planted case:

1. planted long/short rates must recover `D` and `m` exactly
2. a set of rates with **wildly dispersed** `m` must falsify the model
3. a pair whose carry-to-vol sits just under 0.40 must **fail Gate 0**,
   and one just over must pass
4. a **daily** rate read as annual must trip the units guard
5. an index or metal CFD must be **excluded** from the carry gate
6. a return series positive overall but negative in one era must fail
   Gate B
7. the probe must place no orders — asserted by inspecting the module
   namespace, not by grepping its own source

## 9. Scoreboard entering this test

**Twenty-one investigations. Seventeen rejections, one
measured-but-unreachable premium, one headline that dissolved on
decomposition, one real premium whose edge vanished at daily resolution,
one real premium consumed by its own margin requirement.**

The only thing that has beaten equity beta here is still equity beta.
