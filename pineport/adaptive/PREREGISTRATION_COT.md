# Pre-registration — K1, hedging pressure from CFTC COT

Written 2026-09-03, before any COT data is joined to any return.

## Why this one matters more than the others

Every test in this project so far — A through J — has been computed from
price. Parts E and F used implied-volatility indices, which are still a
price. **K1 is the first test in the project whose predictor is not a price
at all.** It is a count of who is holding what.

That makes it the only remaining candidate that could fail for a genuinely
different reason than everything before it.

## Published evidence

Fernandez-Perez, Fuertes and Miffre, hedging pressure across asset classes,
1992-2016. Signal = net short position of *hedgers* (commercials), averaged
over a **12-month** lookback — deliberately slow, to strip seasonal
production swings and short-horizon speculator noise.

| asset class | ann. return | Sharpe |
|---|---|---|
| commodities | 3.71% | 0.506 |
| equities | 4.46% | 0.486 |
| currencies | 1.77% | 0.375 |
| fixed income | -0.70% | **-0.238** |

Panel logit t: commodities 2.98, currencies 1.71, equities 0.13.

Read honestly, that table is weaker than its headline. Equities have a
respectable Sharpe but a t of 0.13. Fixed income is negative. A mechanism
that works in three classes and reverses in a fourth is not a law, and the
published Sharpes are gross of the CFD funding this project now charges.

Prior recorded in advance: **moderate for commodities, low elsewhere.**

## Data

CFTC Commitments of Traders, legacy futures-only report, via the public
Socrata endpoint. Free, weekly, back to 1986.

**Reporting lag is a hard constraint.** The report is a *Tuesday* snapshot
published the following *Friday* at 15:30 ET. A backtest that stamps the
Tuesday value on Tuesday is looking ahead by three days. Fixed rule: the
Tuesday-dated observation may first be used on the **following Monday's
open**, i.e. lag the series to the first trading day strictly after
publication, then shift one more bar for the standard execution model. This
is asserted in code, not left to a comment.

## Market mapping

Of our 21, these have a CFTC-reported underlying:

    cornusd CORN | wheatusd WHEAT-SRW | sugarusd SUGAR NO. 11
    natgasusd NATURAL GAS | xauusd GOLD | xagusd SILVER
    xcuusd COPPER | xptusd PLATINUM | spx500usd E-MINI S&P 500
    nas100usd NASDAQ-100 | usb10yusd 10-YEAR T-NOTES
    eurusd EURO FX | gbpusd BRITISH POUND | audusd AUSTRALIAN DOLLAR
    usdjpy JAPANESE YEN* | usdcad CANADIAN DOLLAR*

Excluded, no CFTC report: eurgbp, eurjpy (crosses), de30eur, de10ybeur
(Eurex), bcousd (ICE Europe).

    ADDENDUM 2026-09-03, recorded rather than acted on. Contract discovery
    turned up "BRENT LAST DAY - NEW YORK MERCANTILE EXCHANGE", 238 weeks from
    2022-02-08. So the clause above is factually wrong: a CFTC-reported Brent
    contract does exist. It is NOT being added. Two reasons, in order of
    weight: (1) it is the NYMEX last-day-financial contract, not the ICE
    Brent our bcousd CFD references -- different settlement, so the original
    "different instrument" reasoning survives the factual correction; (2) it
    starts 2022-02-08, giving 4.6 years against the 25+ the rest of the panel
    has, so it would join the cross-section only at the very end and change
    the panel width mid-sample.

    Adding a market to a universe after inspecting the data is how a panel
    gets tuned. If bcousd is ever wanted, it belongs in a fresh
    pre-registration with the short sample declared up front.

## Contract lineages — resolved 2026-09-03, before any join to returns

CFTC renames contracts rather than backfilling them, so each market is a
CHAIN of names across three generations: IMM -> CME around 2000-08, a second
pass 2003-12, and a large standardisation on 2022-02-08. A single hardcoded
name silently returns whichever era it covers.

The first fetch attempt did exactly that: gbpusd came back as 238 weeks
(2022 onward only), and natgasusd, spx500usd, nas100usd, usb10yusd and
xcuusd all stopped dead at 2022-02-01. Four of those five still had over
1,000 weeks, so a row-count threshold did not catch it -- the check that
does is comparing each series' END date against the newest in the run.

Two successors shared no word at all with their predecessors
(NATURAL GAS -> NAT GAS NYME, 10-YEAR U.S. TREASURY NOTES -> UST 10Y NOTE)
and were therefore unreachable by keyword search. They were found by asking
which contracts have their first report on exactly 2022-02-08 -- a rename
cohort all starts the same day.

Resolved week counts, all ending 2026-08-25:

    xauusd 1931 | xagusd 1931 | xptusd 1931 | cornusd 1932 | wheatusd 1932
    usdjpy 1932 | usdcad 1932 | usb10yusd 1932 | gbpusd ~1931 | sugarusd 1929
    xcuusd ~1926 | audusd 1795 | natgasusd 1828 | spx500usd 1506
    eurusd 1443 | nas100usd 1418

The cluster at 1931-1932 is the length of a complete 1986-2026 series, and
the short ones are short for contract-launch reasons: AUD 1987, NG 1990,
E-mini SPX 1997, euro 1999, E-mini NDX 1999.

Two near-miss exclusions worth recording, because either would have produced
a plausible-looking wrong answer rather than an error:

- **WHEAT - KANSAS CITY BOARD OF TRADE** has the identical 1,269 weeks over
  the identical span as the CBOT contract. wheatusd is pinned to CBOT soft
  red winter by exact prefix; a keyword match would have merged two
  different wheats.
- **ULTRA UST 10Y - CHICAGO BOARD OF TRADE** sits immediately beside
  UST 10Y NOTE in the same rename cohort and is a different contract with a
  different deliverable basket.

    * SIGN TRAP. CME quotes JPY/USD and CAD/USD. Our CFDs are USD/JPY and
      USD/CAD. The COT net position must be sign-flipped for these two.
      Getting this wrong flips the signal on exactly two markets and would
      look like a plausible weak result. Asserted in code by checking that
      the COT-implied spot direction correlates positively with the inverted
      CFD return over the full sample before any test is run.

That leaves **16 markets**, and by the same block logic as everywhere else
their N_eff will be well under 16. Report it.

## Signal

    HP = - (commercial_long - commercial_short) / open_interest
    S  = 12-month trailing mean of HP

Positive S = hedgers net short = the published prediction is positive
expected return. Position = cross-sectional z-score of S each week,
dollar-neutral, unit gross — the same construction as J1, so the two are
comparable and neither gets a bespoke portfolio.

Secondary specification: time-series sign of S per market. Reported, not
scored, unless the cross-sectional version passes.

## Pass criteria — fixed in advance

1. Sharpe >= **0.29** (3 x the 0.096 noise floor for ~108 market-years).
2. Sign consistent across E1/E2/E3.
3. Beats the destroyed-timing null (signal lagged 750 bars) at the 95th
   percentile of a stationary block bootstrap.
4. Holds at 3bp cost.
5. Plateau in the lookback: 9, 12 and 18 month averages keep the same sign.
6. **Class check.** The published result is not uniform — it reverses in
   fixed income. Report commodities, FX and equity-index sub-baskets
   separately. If the whole-panel result is carried by one sub-basket, say
   so and treat the panel number as uninformative.

## Traps

- **Look-ahead via the lag rule.** Stated above; the single most likely way
  to manufacture a false pass here.
- **Open interest as denominator.** OI is contemporaneous with the position,
  so no look-ahead, but it moves with price. Run the mirror check: rank on
  1/OI alone. If that reproduces the result the signal is an OI tilt.
- **CFD is not the future.** GAUNTLET 4.6 again, and it cuts both ways here.
  The positions are in the futures; we would hold a CFD referencing the same
  underlying. Basis and funding differ. A pass is a reason to price futures
  access, not to trade the CFD on the strength of the futures result.
- **Revisions.** CFTC restates. Whether the vendor series is
  as-first-published or as-revised is unknown; assume revised, and note that
  this biases *towards* a false pass.

## Kill condition

If S fails criterion 1 in the cross-sectional specification and the
commodities sub-basket alone also fails, positioning data is closed for this
universe. We would not then move on to the disaggregated or
traders-in-financial-futures reports looking for a version that works.

## Standing

If K1 fails, then across A-K this project has tested price-based trend,
price-based state conditioning, chart shapes, candlestick patterns,
implied-volatility conditioning, real-yield macro, cross-market agreement,
portfolio construction, microstructure stratification, cross-sectional
ranking, and non-price positioning — and found nothing above the noise
floor. That is the point at which the correct conclusion is that this
universe, at this cost structure, through this vehicle, does not support a
systematic edge we can find, and the remaining honest options are to change
the vehicle or stop.
