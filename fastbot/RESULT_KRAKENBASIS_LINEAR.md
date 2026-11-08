# The first real pass — and exactly how thin it is

```
RUN:      2026-08-25
METHOD:   kraken_collateral.py v1.3 Gate 0 (sourced haircut) ->
          kraken_basis.py --buffer 0.0174 --rf-csv ../data/DGS3MO.csv
DATA:     the SAME 18 quarterly cycles as v4, 2021-08-27 -> 2026-06-26.
          No returns recomputed. One sourced input replacing an assumption.
VERDICT:  PROCEED. Gate A +3.51, Gate B +0.7/+8.0/+2.6, Gate C 18 cycles.
          The first pass in this project on an instrument that quotes.
          Every robustness check NOT in the pre-registration lands at or
          below the bar.
```

**I am not a financial adviser. Nothing here is a recommendation to take a
position.** This is a measurement result.

---

## 1. What changed, and why it is not a re-specification

One input. v4 assumed BTC collateral was worth nothing against a short BTC
future and imposed a 73.5% USD buffer. Kraken credits BTC at **99%**:

> `Margin Equity = [Balance Value in USD × (1 − Haircut)] + Unrealised P&L`

Haircut 1%, maintenance 1% (live, from the instruments endpoint), so
`buffer = 0.735 × 0.01 + 0.01 = 1.74%`. Capital 1.02× instead of 1.73×.

The threshold was frozen at ≤ 0.30 before the figure was read. It came in at
0.01 — a 30× margin, not a marginal call. Two independent Kraken sources
agree.

## 2. The result

```
[PASS] Gate A  net excess over T-bill >= 2.0 pts      +3.51 pts
[PASS] Gate B  positive in EVERY era                  +0.7  +8.0  +2.6
[PASS] Gate C  >= 12 cycles, >= 3 per era             18 cycles, 6/6/6
```

Twenty-four investigations; this is the first to clear its own
pre-registered gates on a contract with a live book. That is worth stating
plainly before the rest of this document takes it apart.

## 3. Era 1 passes on a weighting convention

Gate B's first era returns **+0.7**. Here is what is inside it:

```
2022-03-25   210 days   +7.0
2022-06-24    90 days   +1.7
2022-09-30    97 days   +2.9
2022-12-30    90 days   -5.7
2023-03-31    90 days   -8.1
2023-06-30    90 days   -1.5
```

| weighting | era 1 | Gate B |
|---|---|---|
| day-weighted (what the script does) | **+0.68** | PASS |
| equal-weighted per cycle | **−0.73** | **FAIL** |
| day-weighted, dropping the 210-day cycle | **−2.17** | — |

**One cycle, 2.3× the length of every other and the best in its era, is
carrying five cycles that average −2.1 between them.**

Day-weighting is the correct convention — you earn the excess over the days
you are deployed, and I am not proposing to change it. But Gate B's era-1
pass is one long observation deep, and that was invisible in the summary
line.

## 4. The two ETF quarters now break Gate A

`RESULT_KRAKENBASIS_v7` ran this check at zero buffer and got +2.04 — "still
passes, barely". With the sourced 1.74% buffer:

```
all 18 cycles                       +3.51 pts    PASS
drop 2024-03 and 2024-06            +1.84 pts    FAIL
those two quarters alone             +1.67 pts of the total
```

The spot-ETF launch half-year returned +14.5 and +21.8 points. **Remove it
and the candidate fails its own Gate A.** The 1.74% buffer — tiny as it is —
was enough to tip this check from just-passing to just-failing.

Six of eighteen cycles lost to Treasury bills. Two by more than five points.

## 5. Era 1 is the contract that no longer trades

Cycles 1–6 are `FI_` (inverse). Cycles 7–18 are `FF_` (linear). The
structure switched in September 2023, and Track A confirmed twice this week
that no inverse contract is quoted today.

So the record on the instrument you could actually enter is **eras 2 and 3
only**:

```
era 2   +8.0   -- inflated by the ETF half-year
era 3   +2.6   -- the most recent 18 months
last 8 cycles  +3.25
last 6 cycles  +2.56
last 4 cycles  +2.37
```

**The current premium on the current instrument is about 2.4 to 2.6
points.** The 2.0 bar was set in v4 §2 as one point of insurance against a
1% annual chance of total loss plus one point of compensation. At +2.5 the
trade pays that insurance and roughly half a point beyond it.

## 6. The collateral costs, now measured — and a correction I owe

**An earlier draft of this section put the conversion fee at 0.80 to 1.60
points and said it alone would sink the candidate. That was wrong, and the
correction favours the trade, which is why it is recorded here rather than
quietly amended.**

The error: I assumed 0.20% was charged on the position notional. Kraken
charges it **on the amount converted** — which is the loss being covered,
not the position. On a 30% adverse quarter that is 0.20% × 30% = 6 bp of
notional, not 20 bp, and only in quarters that move against you.

What the documentation actually establishes:

```
BTC haircut                1%
BTC conversion fee         0.20%, on the amount converted
interest on uncovered loss 0.00025% per hour  ->  2.21%/yr, compounded 24/7
conversion priority        lowest-haircut collateral first
```

The interest line is a **third** cost I had not been counting at all: a
BTC-collateralised short with a USD loss carries that loss as an
interest-bearing balance until it converts.

Modelling both over a quarter (20,000 paths, loss accruing hourly on the
running mark, conversion at settlement):

| BTC vol | interest | conversion | combined |
|---|---|---|---|
| 40%/yr | 0.12 | 0.06 | **0.18 pts/yr** |
| 55%/yr | 0.16 | 0.09 | **0.25 pts/yr** |
| 80%/yr | 0.23 | 0.13 | **0.36 pts/yr** |

Era 3 restacked:

| | era 3 | Gate A |
|---|---|---|
| as measured | +2.56 | PASS |
| less collateral costs at 55% vol | **+2.24** | PASS |
| less collateral costs at 80% vol | **+2.09** | PASS |
| less the convergence tailwind (§7) as well | +1.84 | **FAIL** |
| *my earlier figure, which was wrong* | *+0.96* | *FAIL* |

**The collateral costs do not sink it. They cost about a quarter of a
point.** What still can sink it is the convergence tailwind combined with
them, and entry cost, which has no number at all — Track A's two
observations of the September book are **1.0 bp and 158 bp** six days apart.

### What remains genuinely unresolved

The uncovered-loss formula is `-(USD Balance + Unrealised PnL)`. Whether
"USD Balance" means USD **cash** or **haircut-adjusted total collateral**
decides whether a fully BTC-collateralised short accrues that 2.21%
continuously or essentially never. **The table above assumes the
conservative reading** — cash — so the real figure is at or below it.

Two Kraken pages also disagree on the auto-conversion trigger: one gives
$5,000,000 of uncovered loss, another ~120% of maintenance margin. At the
sizes involved the fee is small either way, so this no longer changes the
verdict — but it is unresolved and it is recorded as unresolved.

The rate is also quoted as "**starts at** 0.00025% per hour", implying a
tier that rises. The top of that tier is not published.

## 7. The convergence tailwind

The realised column exceeds the quoted by **+0.099% per cycle on average**,
8 of 18 positive, largest +1.41%. Annualised that is +0.40 points of the
+3.51, and its origin is unexplained — plausibly an artefact of the last
daily candle not being the settlement print. The script's own note says
convergence is not clean.

If it is an artefact, Gate A reads +3.11 and era 3 reads +2.16.

## 8. Verdict

**It passes as pre-registered. It passes narrowly on the recent, tradeable
half of the sample, and it fails several checks that were not
pre-registered.**

Both halves of that are load-bearing. The gates were fixed in v4 §8 before
any of this data was seen, and moving them now because the margin is thinner
than hoped would be the exact failure the whole apparatus exists to prevent.
The result is a PASS.

But v4 §12, written before anything was measured:

> If all four gates pass, this is **not** a green light to trade. It is a
> green light to price the things this measurement cannot see.

That list started at four items. §6 has now measured two of them and they
came in **small** — about 0.25 points combined, not the 1.6 I first
estimated. What is left is **entry cost**, which is unmeasured and whose two
observations differ by 158×, plus auto-deleveraging and counterparty risk,
which are not measurable from price data at all.

So the honest position moved in the candidate's favour today, on the back of
a mistake of mine being corrected. That is the second time this week. The
difference from the last one is that this correction is arithmetic about a
published fee schedule rather than a reading of what a venue lists.

## 9. What this does not settle, and cannot

Counterparty risk is unchanged and unpriceable. Mt Gox, QuadrigaCX and FTX
are the base rate; a venue that behaves for four quarters has told you
almost nothing about the fifth. The 1% annual loss probability behind the
2.0-point bar remains a judgement, not an estimate, and no quantity of price
data will convert it into one.

The capital efficiency and the counterparty exposure are also **the same
fact viewed twice**: what makes the trade cheap is that your BTC sits on the
exchange as margin.

## 10. Scoreboard

**Twenty-four investigations. Twenty rejections, one
measured-but-unreachable premium, one headline that dissolved on
decomposition, one real premium whose edge vanished at daily resolution,
and one — the crypto dated basis on the linear contract — that clears every
pre-registered gate with about half a point of margin over its own
counterparty-risk bar.**

## 11. The honest next step

Not a bigger backtest — v8 §1 established that a forward significance test
needs 4.3 years to add anything.

`PREREGISTRATION_v8` is now written against the wrong instrument: its frozen
rule names `FI_XBTUSD`, which does not trade. A v9 is needed for the linear
structure, and it differs in ways that matter — the collateral is posted
rather than intrinsic, the equity/notional identity no longer holds exactly,
and the recording spec must add the conversion fee and the achieved-versus-
quoted entry price.

**Item 1 is now answered** (§6): conversion is real, it is charged on the
converted amount, interest runs at 2.21%/yr on uncovered loss, and together
they cost about 0.25 points — not the 1.6 I feared.

**Item 2 is the whole remaining question that can be answered without
capital.** Entry cost is now the largest unmeasured term in the whole
candidate, and Track A run daily is what turns two contradictory snapshots
into a distribution. That is the only work left that is both free and
decisive.

Track A's frozen instrument must change with it: v8 §4 names `FI_XBTUSD`,
which does not trade, and Phase 1 has now passed on the **linear** contract.
The `--all-dated` amendment is therefore no longer a convenience — the
protocol as written records nothing about the instrument the result is
about. Logging every dated contract removes a selection rather than adding
one, so there is nothing in it to steer.
