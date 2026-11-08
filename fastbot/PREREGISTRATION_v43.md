# PREREGISTRATION v43 — the variance risk premium, hedged, on SPX options (ORATS)

Frozen 2026-09-27, **before any option price has been seen.** The data is not yet bought.
Scripts: scripts/orats_pull.py v1.0 (fetch, on Dave's Mac), scripts/vrp_v43.py (harness, written after the field probe; it may not change anything below).

I am not a financial adviser. This is a measurement, not a recommendation. Selling options can lose far more than the premium collected; the hedge defines the loss here, and that is the point of the test.

## 1. Question
RESULT_VRP (2026-08-17) measured the premium as real at 10σ, but unhedged it was worse than equity beta: Sharpe +0.32, skew −6.7, and March 2020 erased 9.7 years of gains. The published tradeable form sells the at-the-money straddle and buys protection. **Is the hedged version better than simply owning the index, net of the quoted spread, across 2007–2026, including 2008, 2020 and 2025-04?**

## 2. Strategy (fixed now)
- **Underlying:** SPX index options (European, cash-settled). XSP, the one-tenth-size version a retail account can hold, prices the same per unit; its wider spreads are covered by stress costs in §4.
- **Cycle:** monthly.
  - **Entry:** the first trading day after each standard monthly expiry, at ORATS' near-close snapshot.
  - **Target expiry:** the next standard monthly expiry (third Friday; Thursday when Friday is a holiday).
- **Primary structure, P (iron butterfly, fully defined risk):**
  - sell 1 call and 1 put at the strike nearest the underlying price (ATM);
  - buy 1 put at the strike nearest 0.85 × underlying and 1 call at the strike nearest 1.15 × underlying.
- **Hold to expiry.** Settlement uses the SPX price ORATS reports for the expiry date. This approximates AM settlement; the error is overnight noise, unbiased on average, and is stated as a caveat.
- **Costs:** sell at the bid, buy at the ask, plus $1.50 per contract per side. No exit cost (cash settlement).
- **Unit of return:** P&L ÷ (underlying × 100) at entry, i.e. per unit of notional. Excess over T-bills is not needed for the comparison, because both sides are measured on the same notional.

## 3. Reported, gating nothing (same data, same months)
- **U:** unhedged short straddle, which should reproduce RESULT_VRP's picture.
- **Q:** the Quantpedia form, short straddle plus a long 15% out-of-the-money put, with the call side naked.
- **Wing plateau:** P with wings at 10% and 20%.
- **Benchmark B:** SPX buy-and-hold over the same months (underlying at entry → underlying at the next entry).

## 4. Gates (P, the primary)
1. **G1 edge:** mean monthly net P&L > 0 with t ≥ 2.0, **and** annualised Sharpe ≥ 0.46. That is the 2/√19 detectability bar from COST_BUDGET.
2. **G2 beats beta:** P's Sharpe ≥ B's Sharpe over the same months.
3. **G3 tail:** P's worst month is no worse than its defined maximum loss (a sanity check on the data and code). P's maximum drawdown is smaller than B's.
4. **G4 eras:** P's net mean > 0 in each of 2007–2012 (includes 2008), 2013–2019, and 2020–2026 (includes 2020, 2022 and 2025-04).
5. **G5 plateau:** the 10% and 20% wing versions also have net mean > 0.
6. **G6 cost stress:** P stays > 0 when the entry cost is doubled (approximating XSP spreads).

**PASS needs all of G1–G6.** A PASS earns a forward (paper) record with its own pre-registration. **It does not justify live trading on its own.**

## 5. Budget and economics, before the data
- **Sample:** about 230 monthly cycles, 2007–2026. At that size an annualised Sharpe of 0.46 is roughly the t = 2 line.
- **Data cost:** one month of the ORATS Delayed Data API at $199 (historical end-of-day strikes by ticker back to 2007) covers the pull. The $599 archive of all symbols is the alternative, but it is about 500 GB.
- **Account arithmetic (XSP):**
  - One iron butterfly at SPX 7,700 carries about $77k notional.
  - Maximum loss is about (the 15% wing width, $115.5 × 100 = $11.6k) minus the credit collected.
  - Holding one contract with a reserve for two maximum losses needs roughly $20–25k.
  - At a hoped-for 5–10% a year on that capital, the $199 data cost is repaid within a year. Ongoing data ($99–199/month) would need about $25–50k to pay for itself.
- **Access:** OANDA and Kraken offer no listed options. A live version needs an options broker (for example, Interactive Brokers). No account is opened as part of this test.

## 6. Blind spots
- The near-close snapshot is not a fill. Real fills on wide spreads can be worse, which is why G6 exists.
- AM settlement is approximated, early-exercise risk is nil (European options), and dividends are embedded in the option prices.
- One structure, one tenor. Weekly or 0DTE versions are not tested.

## 7. One run, after the data passes its integrity check. No change of structure, wings, dates or gates.
