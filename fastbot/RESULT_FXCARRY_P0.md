# Phase 0 — OANDA keeps a quarter of the carry at best, and all of it on a third of the book

```
RUN:      2026-08-19
METHOD:   fx_carry_probe.py v1.2, PREREGISTRATION_v5 Phase 0. COST ONLY.
DATA:     68 FX pairs quoting a financing rate, 5 years of daily closes
VERDICT:  PROCEED, on a technicality worth reading carefully. Four pairs of
          sixty-eight clear the bar, three of them Turkish lira crosses
          where the bound is worthless.
```

---

## 1. The headline

```
median markup                   1.095% per side  =  2.19%/yr round trip
best "kept by broker"           24%   (TRY_JPY)
median across the 68 pairs      ~52%
pairs where the fee exceeds
  the ENTIRE differential       22 of 68
```

**On twenty-two of sixty-eight pairs there is no carry to harvest in either
direction.** Long pays `D − m`, short pays `−D − m`; when `|D| < m` both are
negative. A third of OANDA's FX book is a pure cost whichever way you face.

On the four pairs most people actually trade:

| pair | gross D | markup | net | net/vol | broker keeps |
|---|---|---|---|---|---|
| USD_JPY | 2.81% | 1.02% | 1.80% | 0.18 | 36% |
| USD_CAD | 1.54% | 1.06% | 0.48% | 0.08 | 69% |
| EUR_USD | 1.45% | 1.01% | 0.44% | 0.06 | 70% |
| AUD_USD | 0.55% | 1.04% | **−0.49%** | −0.05 | 190% |
| GBP_USD | 0.04% | 1.01% | **−0.98%** | −0.12 | 2900% |

## 2. The fee is not flat, and that matters

`model_holds()` passed — interquartile spread 0.29 points around a 1.095%
median — and it passed **for the wrong reason.** The middle 50% of the
universe are majors, all charged about 1.05%. Sorting by differential shows
the real structure:

```
pairs with |D| >= 3%    median markup = 27% OF THE DIFFERENTIAL
pairs with |D| <  3%    median markup = 1.10% FLAT
```

So the charge is approximately **max(1.05% flat, ~26% of |D|)** — a floor
plus a proportional take. **You cannot outgrow it by finding a bigger
differential.** Above about 4% the broker simply takes a quarter.

This does not affect the decomposition: `D` and `m` come out of `longRate`
and `shortRate` by identity whatever functional form `m` has. What it
falsifies is my *description* of `m` as a flat administrative fee, and it
means the model test I wrote was too weak to see a two-regime charge.

## 3. Gate 0 passed. Read how.

```
[PASS] best carry-to-vol ratio: 1.23 on EUR_TRY   (bar 0.40)
```

Only four pairs of sixty-eight clear 0.40, and three are lira crosses:

```
EUR_TRY  1.23      TRY_JPY  1.22      USD_TRY  1.21      GBP_CHF  0.41
```

**The bound is worthless on exactly those three.** The carry trade in
EUR_TRY is to be *short* the pair — buy lira — collecting 22.3% a year. The
lira has depreciated against the euro at roughly 30–38% a year over the
sample. The ratio's denominator is the standard deviation of log returns,
which **excludes the mean drift entirely**, so a currency in one-way
structural decline registers 18.1% volatility and a spectacular carry score
while losing money every quarter.

`fx_carry_probe.py` prints exactly this warning above the table, which is
the right behaviour, but a gate that passes on a number it simultaneously
disclaims is not doing its job.

**The one thing that rescues the verdict: GBP_CHF clears the bar without
them, at 0.41.** So PROCEED does not depend on the lira. But 0.41 against a
0.40 bar is razor-thin, and it is an **upper** bound — it charges nothing
for drift and nothing for the crash risk the premium exists to pay for.

## 4. A latent hole in Gate 0, recorded before it bites

Volatility normalisation is invalid for **pegged** currencies. EUR_DKK
shows 0.2% volatility and USD_HKD 0.8%, because both are pegged. Realised
volatility does not measure peg-break risk, and dividing by a near-zero
denominator manufactures enormous ratios.

Here it changed nothing — both pairs have negligible or negative net carry.
But had EUR_DKK offered 1% of net carry, its ratio would have been **5.0**
and it would have topped the table on the strength of a risk that has not
happened yet. That is January 2015 in the Swiss franc, exactly.

## 5. Scoring the prediction

§3 said: *"I predict Phase 0 survives and Gate B fails."*

**Phase 0 survived** — correct, and it is the first of the three recent
tests where the broker did not eat the whole premium outright.

**The markup estimate was wrong by more than double.** I wrote *"a flat
administrative charge of roughly half a percent a side"*. It is 1.095%, and
it is not flat. Against the 3–4 point differentials I cited as the reason
for optimism, OANDA takes 26–27%.

Gate B is not yet tested.

## 6. The honest reading

**The premium exists and the broker has priced it carefully.** A 24–27%
take on any differential worth having is not an accident; it is a fee set
by someone who knows precisely what the position is worth.

Of sixty-eight pairs: twenty-two have no carry in either direction, and
sixty-four fail an upper bound that flatters them. The survivors are three
currencies in structural decline and one major at 0.41.

Phase 1 is warranted because the pre-registration says so and because
GBP_CHF clears the bar on its own. It is not warranted by optimism.

## 7. Scoreboard

**Twenty-two investigations. Phase 0 of the twenty-second has passed; the
strategy has not.**
