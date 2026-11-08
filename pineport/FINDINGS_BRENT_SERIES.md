VERDICT: REGISTERED PROCEDURE — construction NOT IDENTIFIED (both of its roll calendars were wrong about TradingView's BRN1!); curve check SUPPORTED (−35.9%/yr vs card −46.1%). DIAGNOSTIC (not registered) — BCO_USD is a continuous, non-rolling, spot-like series (roll slope b = 0.91 ± 0.16); the roll is carried in financing, so every BCO price-only result omits a term of roughly the curve's roll yield.

# Findings — what OANDA's `BCO_USD` price series represents

**Run:** 2026-10-11, under `PREREGISTRATION_BRENT_SERIES.md` (registered 20:19
UTC the same evening, before any comparison data was pulled).
**Script:** `brent_series.py`. **Data:** `data/brent_series/raw/` (TradingView
JSON, unedited) → `data/brent_series/aligned.csv`.
**Status:** a measurement of the vehicle. No strategy is tested or rescored.

---

## 1. The registered result, as registered

| check | result | registered bar | outcome |
|---|---|---|---|
| Gate 0: TV `OANDA:BCOUSD` vs on-disk `bcousd_oanda_h4.csv` | median \|diff\| **0.0000** over 704 days | ≤ 0.10 | **PASS** — TV's series is our feed |
| Roll detector | 279 "rolls" = 96/yr | 10–14/yr | **FAILED** → ICE-expiry fallback |
| Fallback roll days (1st trading day of month) | 35 = 12.1/yr | — | used |
| median \|d1\| / median \|s\| | 0.498 / 0.580 = **0.86×** | < 0.25× | H-front no |
| median \|d2\| / median \|s\| | 1.058 / 0.580 = **1.82×** | < 0.25× | H-second no |
| Roll-day slope b (fallback days) | **−0.06** (se 0.06) | [0.7, 1.3] synth; [−0.3, 0.3] front | neither (front fails its median test) |
| Non-roll \|Δd1\| > 4 MAD | 74 of 713 vs 5.0 expected | > 3× expected **and** monthly clustering | count part holds; clustering not met (§3) |
| Curve check (last 5 days) | **−35.9%/yr** vs card −46.10% | within ±12 pp | **SUPPORTED** |

**Registered verdict: construction not identified.** That verdict is correct on
its own terms and is not overturned below. The reason it failed is specific and
is what the diagnostic addresses: **both registered roll calendars were wrong
about TradingView's continuous contract.**

- The detector (`|BRN1(t) − BRN2(t−1)| < |BRN1(t) − BRN1(t−1)|`) fires on noise
  whenever the curve is flat relative to a day's move. That was foreseeable and
  is why the registration included a sanity range and a fallback.
- The fallback assumed `BRN1!` switches at ICE expiry. It doesn't (§2). On the
  fallback's month-start days both legs of `d1` belong to the same contract, so
  b ≈ 0 there tells you nothing about construction.

## 2. What TradingView's `BRN1!` actually does (checked, not assumed)

Against the individual contracts:

| contract | ICE expiry | last day `BRN1!` = it | first day `BRN1!` = next |
|---|---|---|---|
| BRNM2024 (Jun 24) | 2024-04-30 | 2024-04-23 | 2024-04-24 |
| BRNV2026 (Oct 26) | 2026-08-28 (31st a UK bank holiday) | 2026-08-21 | 2026-08-24 |
| BRNX2026 (Nov 26) | 2026-09-30 | 2026-09-23 | 2026-09-24 |

`BRN1!` is **unadjusted** (it matches each contract to the cent) and rolls on the
**5th-from-last UK business day of the month**, five trading days before expiry.
`BRN2!` matched the next contract exactly on every day checked.

## 3. DIAGNOSTIC — not registered, thresholds unchanged

Roll days taken from that calendar, using the futures series only (BCO never
used to place them): 34 roll days, 2023-12-21 → 2026-09-24.

- **Roll-day slope b = 0.907 (se 0.161), R² 0.50, intercept +0.04.** Inside the
  registered H-synthetic band [0.7, 1.3]; H-front's band excludes it by over 3 se.
  When the front month jumps by the roll gap, BCO does not.
- On those days, BCO's move against the *new* front contract's own move:
  median \|diff\| **0.28**, i.e. the size of the timing noise. BCO keeps moving
  with the market straight through the switch.
- Worked example, 2026-09-24: roll gap −g = **+4.96**, Δd1 = **+4.97**.
- **No roll calendar of OANDA's own:** after removing TradingView's rolls, the 74
  large Δd1 days spread across **18 months** and evenly across positions in the
  month (no pile-up at any trading-day-before-month-end), with **33 in Mar–May
  2026**. That's fat-tailed noise from the ~2.5 h close mismatch in a violent
  market, not a roll schedule. The 4-MAD normal benchmark was always going to
  overcount on oil returns.
- **Where BCO sits:** on clearly backwardated days (s < −0.5, n = 441), median
  `d1 / |s|` = **0.68**. BCO is above the front month by about two-thirds of the
  M1–M2 spread, i.e. extrapolated toward spot, which is what a spot-referenced
  CFD looks like in backwardation.

## 4. What this means for the tree

**`BCO_USD` is a continuous, spot-like price, and the futures roll lives in the
financing line, not the price.** Both halves now have evidence: the price
doesn't jump at rolls (diagnostic, b = 0.91), and the financing rate matches the
curve (registered curve check, within 10 pp). FINDINGS_FINANCING_RATES §5's worry
is confirmed in its stronger form.

Consequences, stated at the level the evidence supports:

1. **Every BCO result computed from price changes alone omits a term of roughly
   the curve's roll yield, with opposite signs for longs and shorts.** Over this
   sample, annualised M1→M2: **2024 −8.2%/yr, 2025 −10.5%/yr, 2026 −33.8%/yr**
   (backwardated on 711 of 717 days). In backwardation a long earns it and a
   short pays it. Contango eras (2009, 2015, 2020 in the long panel) flip the sign.
2. **Scale:** even the calm-year figure (~8–10%/yr) exceeds every directional
   effect in `PROGRAMME.md`, which are measured in bp per trade.
3. **Not shown:** that OANDA's *historical* financing followed the curve before
   today. Only today's card was measured. The 2005–2023 panel cannot be
   corrected without both historical curve data and confirmation of OANDA's past
   practice.
4. **No panel result is rescored.** As registered: rescoring needs front/second
   settlements back to 2005, which aren't free, and every directional family has
   already failed without this term. What changes is how a *future* commodity
   result must be costed: **price P&L + financing at the curve rate**, never
   price alone.
5. **The same structure is presumed, not measured,** for copper, natural gas,
   wheat, corn and sugar in the panel. This test covered Brent only.

## 5. Errors caught in this run

- The registration's timestamp was first written as 16:20 BST, a guess. It was
  corrected to the real file time (20:19 UTC) before any data was pulled.
- The fallback roll days were nearly accepted at face value. b = −0.06 looked
  like a clean H-front-ish answer, and the "own-roll" outliers looked like a
  finding. The check that caught it was looking at the raw rows at month-ends
  and seeing no gap where an unadjusted front month must have one. Same shape as
  the handover's §3 list: a regression of real numbers almost became a claim
  about a mechanism while one unchecked input (when the reference series rolls)
  did all the work.

*Not financial advice. Everything here is measurement, not recommendation.*
