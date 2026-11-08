# Pre-registration — what does OANDA's `BCO_USD` price series represent?

**Registered:** 2026-10-11 21:19 BST (20:19 UTC), before any comparison series is pulled.
**Subject:** the construction of OANDA's Brent CFD price, to settle the open
question in `FINDINGS_FINANCING_RATES.md` §5: is the −46.10%/yr "benchmark" on
the rate card the futures curve, and does the price series itself roll?
**Status:** a measurement of the vehicle, not a strategy test. No signal is
tested, no family is reopened, nothing here can produce a "pass" for any
trading rule (standing rules 2, 4, 5).

Replaces HANDOVER_2026-10-11 §2.4's plan (BCO vs EIA Dated Brent via FRED):
FRED is blocked from both the cloud sandbox and the Cowork VM, and the
front/second-month futures comparison below answers the construction question
more directly than spot does.

---

## 1. Data (fixed now)

From the TradingView connector, daily bars, the same count for each:

- `OANDA:BCOUSD` — OANDA's Brent CFD, as TradingView receives it.
- `ICEEUR:BRN1!` — ICE Brent front-month continuous (unadjusted).
- `ICEEUR:BRN2!` — ICE Brent second-month continuous (unadjusted).

Count: 750 bars (~3 years, ~36 contract rolls). Raw JSON saved unedited under
`pineport/data/brent_series/raw/`. Aligned on calendar date; days missing from
any series are dropped, not filled.

**Feed check (gate 0):** TradingView's `OANDA:BCOUSD` daily close is compared
with the on-disk OANDA feed `bcousd_oanda_h4.csv` over the overlap (ends
2026-08-07), using the H4 bar closing nearest the TV daily close. If the median
absolute difference exceeds 0.10 USD, the TV series is not our feed and the
result is reported as "not established" for the panel.

Known noise, stated in advance: OANDA's daily close (17:00 New York) and ICE's
settlement (~19:30 London) are ~2.5 h apart. That timing gap adds noise to
every difference below; it cannot create a sawtooth locked to roll dates.

## 2. Definitions

- `s(t) = BRN2 − BRN1` (curve spread; negative = backwardation).
- `d1(t) = BCO − BRN1`, `d2(t) = BCO − BRN2`.
- **Roll day:** a day on which `BRN1` switches contract, detected as
  `|BRN1(t) − BRN2(t−1)| < |BRN1(t) − BRN1(t−1)|` with `|s(t−1)| > 0.05`.
  Sanity: 10–14 detected per year, else detection is reported as failed and
  roll days are taken from the ICE expiry rule (last business day of the
  second month before delivery).
- **Roll gap:** `g = s(t−1)` on each roll day.

## 3. Hypotheses and decision rules (frozen)

**H-front — BCO tracks the front month and rolls when ICE rolls.**
Holds if median `|d1|` < 0.25 × median `|s|` AND the roll-day regression
slope (below) is in [−0.3, 0.3].

**H-second — BCO tracks the second month.**
Holds if median `|d2|` < 0.25 × median `|s|`.

**H-synthetic — BCO is a continuous, non-jumping series (spot-like or
pre-rolled), with the roll carried in financing instead of in the price.**
Roll-day regression: `Δd1 = a + b·(−g) + e` over all roll days.
Holds if b is in [0.7, 1.3] (BCO does not jump when BRN1 does).

**H-own-roll — BCO rolls on its own calendar.** Holds if, on non-roll days,
the count of days with `|Δd1|` > 4 × MAD of `Δd1` exceeds 3× the count
expected under normality, clustered at roughly monthly spacing.

If none holds, the verdict is "construction not identified" with the
statistics reported. More than one holding is reported as such.

**Curve check (independent of the above).** The card's implied benchmark
(−46.10%/yr, measured 2026-10-11) is compared with the annualised M1→M2 roll
yield from the latest five daily bars: `12 × mean(s/BRN1)` × 100.
"The financing line is the futures curve" is **supported** if the two agree
within ±12 percentage points, **not supported** otherwise. (Annualising a
one-month spread is crude; the band is wide on purpose and fixed now.)

## 4. What each outcome means for the tree (stated now)

- **H-synthetic + curve supported:** price changes alone understate a long's
  return and overstate a short's by roughly the roll yield. Every BCO result
  in the 21-CFD panel that ignored financing is mis-stated by that term.
  Financing is a real, unpriced component, as §5 of the rate-card findings
  feared.
- **H-front:** the price already contains the roll jumps. Financing at the
  curve rate would then double-count, which would be a broker anomaly worth
  checking against a real statement before anything else.
- **H-second / H-own-roll:** as H-front, with the roll on a different date.

Whatever the outcome, **no historical panel result is rescored here**: that
would need front/second-month settlements back to 2005, which are not free,
and the handover's judgement stands that buying them is not worth it while
all twelve directional families have failed regardless.

## 5. What is not allowed after the data is seen

No change to the thresholds, the bar count, the roll detector or the
alignment. If gate 0 fails, the run stops there.
