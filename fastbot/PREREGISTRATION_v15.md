# PREREGISTRATION v15 — does OANDA pass carry through at all?

```
WRITTEN:  2026-09-04, BEFORE any OANDA FX financing rate has been read
STATUS:   FROZEN
SUBJECT:  whether a cross-sectional FX carry premium is reachable
          through OANDA, measured on the cost side only
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.**

---

## 1. Why this is the first thing to measure, not the last

`FINDINGS.md` rule 2, now five for five: **nothing died of absence,
everything died of access.** VRP's hedge did not exist, the VIX term
structure vanished at daily resolution, Kraken's inverse contract had no
bid, its quarterly traded 4 BTC in a month, and the pre-FOMC drift ended
in 2015.

Carry is the archetypal risk premium — you are paid an interest
differential and occasionally destroyed in a crash, which is rule 3's
category and the one that survives. **But the premium is quoted in
interbank terms and this account is not an interbank participant.** What
reaches a retail CFD account is the differential after OANDA marks up
both sides.

So the question is not "does carry work". It is **"how much of it
arrives", and it is answerable before a single position is modelled.**

## 2. The decomposition

For an instrument XXX_YYY, OANDA publishes `financing.longRate` and
`financing.shortRate` as annualised rates. If the broker quotes a
reference differential `d` with a half-spread `s` on each side:

```
longRate  =  d - s
shortRate = -d - s

  =>   d = (longRate - shortRate) / 2        the implied differential
       s = -(longRate + shortRate) / 2       the broker's cut, per side
```

`d` should equal `r_XXX − r_YYY`. Validated on SPX500_USD, where it
returned d = −3.65%/yr and s = 2.50%/yr against a 3.87% three-month
bill — a sane reference and a large but plausible cut.

**What a carry position actually nets, per year, on the receiving
side:**

```
net = |d| - s          and         pass-through = (|d| - s) / |d|
```

**If s ≥ |d| the pair pays negative carry in BOTH directions.** You pay
to hold it either way, and no amount of skill in choosing the direction
recovers that.

## 3. The chaining test, which needs no external data

The differentials must be internally consistent. Anchoring USD at zero
and reading each currency's implied rate off its USD pair:

```
r_XXX  =  d(XXX_USD)          for every pair quoted against USD
```

then **every cross is predicted**:

```
d_predicted(XXX_YYY) = r_XXX - r_YYY
residual = d_quoted - d_predicted
```

A residual of zero means `d` is a real reference and `s` is the whole
cost. **A non-zero residual means the reference itself is being shaded
per pair — a second markup hiding behind the first, and one that a
naive `s` calculation would miss entirely.**

This is the part most people will not do, and it costs one extra
function.

## 4. The gates, frozen

**Gate A — is anything positive at all.**

```
PASS   at least 5 instruments with net = |d| - s > 0
FAIL   -> the family is closed at this broker, full stop
```

**Gate B — pass-through on the pairs that matter.**
Taken over the ten instruments with the largest |d|.

```
PASS   median pass-through >= 50%
FAIL   otherwise
```

50% because the documented cross-sectional carry premium is roughly
4-6%/yr unlevered at Sharpe 0.4-0.6. Halving the return while keeping
**all** of the crash risk takes that to Sharpe 0.2-0.3, which is not
compensation for anything. The threshold is set here, before the numbers
are seen, and it is a judgement about what is worth owning rather than
about what the data will show.

**Gate C — is the reference honest.**

```
PASS   median |residual| over all crosses <= 0.25 %/yr
FAIL   otherwise -> report the shading and treat Gate B's
       pass-through as an UPPER bound, not a measurement
```

**Gate D — the cross-sectional spread.**
The long-short book Dave's stated direction points at: receive on the
top quintile by net carry, pay on the bottom quintile.

```
PASS   net financing on the spread >= 2.0 %/yr
FAIL   otherwise
```

Both legs pay `s`. That is the whole point of measuring it: a
cross-sectional book pays the markup **twice**, which is why the
academic spread and the reachable spread are different numbers.

## 5. Predictions, registered before the call

- **Majors clear Gate A comfortably.** Current policy rates put the
  biggest major differentials around 3-4%/yr and I expect `s` around
  0.5-1.5%, so net positive on several.
- **Gate B is the close one. I expect pass-through of 50-75% on majors
  and lower on EM crosses**, where the differential is larger and the
  markup usually larger still in absolute terms.
- **Gate C: I expect small but non-zero residuals** — under 0.5%/yr —
  concentrated in the crosses rather than the USD pairs.
- **Gate D is the one I expect to fail**, because the spread pays `s`
  on both legs and 2%/yr net is a high bar once it is charged twice.

**If everything passes cleanly I should be suspicious**, because five
consecutive candidates have died at exactly this step and a broker that
passed carry through generously would be an unusual broker.

## 6. Kill conditions

- **The quoted rate is not the charged rate.** These are the rates
  OANDA advertises via the API; what actually posts to the account can
  differ. This measurement is therefore an **upper bound on what
  arrives**, and it is labelled as one. Confirming it against real
  financing transactions on the account is a separate step and is not
  claimed here.
- **A single snapshot is a snapshot.** Financing rates move with policy
  rates. A pass here is a pass *today*, and the run records its
  timestamp so a later re-run is a comparison rather than a replacement.
- **No position, no history, no backtest.** This run touches no price
  series at all. If it tempts anyone into a P&L curve, that is a
  separate pre-registration.
- **One run.** No re-running against a different instrument subset to
  find a pass.

## 7. What each outcome means

| | |
|---|---|
| **A, B, C, D pass** | Cross-sectional carry is reachable here. Then, and only then, the crash-risk question — which is the real cost of carry and is not measured by this document. |
| **A, B pass; D fails** | Directional carry may be reachable; the long-short book is not. A narrower and much less diversified thing than the literature describes. |
| **C fails** | The reference is shaded per pair. Gate B's number becomes an upper bound and the honest pass-through is unknown without external rate data. |
| **A fails** | The family is closed at this broker. Recorded and finished in a day, which is the entire point of screening access first. |

## 8. What this deliberately does not ask

**Whether carry earns its premium.** It is compensation for crash risk
and that risk is real; measuring it needs history and a drawdown study,
and is worthless if the financing does not arrive in the first place.

**Whether Kraken would be better.** Different venue, different
pre-registration.

**Investigation thirty-one.** The first to run the access screen
*before* the premium study rather than after — which is what five
consecutive deaths at this step have earned.
