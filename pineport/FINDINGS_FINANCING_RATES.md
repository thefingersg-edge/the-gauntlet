VERDICT: OANDA's markup is a constant 2.50% on indices AND Brent; gold is the outlier at 1.19% (metals are priced off the pair's rate differential). The SPX500 carry verdict used exactly the right rate — validated. But Brent's implied "benchmark" is −46.10%/yr, which is the futures curve, not interest: a long EARNS 43.6%/yr and a short PAYS 48.6%/yr. Every commodity in the 21-CFD panel needs its price-series construction checked before any result on it is trusted.

# Findings — OANDA financing rate cards, measured

**Measured:** 2026-10-11, from the live rate cards on Dave's account (all costs
applied 22:00 GMT+1, account GBP).
**Status: a cost measurement.** No pre-registration of its own, for the reason
given in `journal/FINDINGS_GOLD_4H_CARRY.md` — this records a charge, not a
hypothesis. The method was registered in `PREREGISTRATION_SPX500_H4_CARRY.md`.

---

## 1. The cards, decomposed

Using OANDA's sign convention — long rate = −(B + M), short rate = +(B − M),
so B is the reference rate and M the admin markup:

| instrument | long | short | implied B | markup |
|---|---|---|---|---|
| XAU_USD | −5.45% | +3.07% | 4.26% | **1.19%** |
| SPX500 | −6.38% | +1.38% | 3.88% | **2.50%** |
| NAS100 | −6.38% | +1.38% | 3.88% | **2.50%** |
| UK100 | −6.23% | +1.23% | 3.73% | **2.50%** |
| Brent | **+43.60%** | **−48.60%** | **−46.10%** | **2.50%** |

Four things fall out, in increasing order of consequence.

---

## 2. The markup is a constant 2.50% — except on metals

SPX500, NAS100, UK100 and Brent all carry exactly 2.50%. Gold carries 1.19%.

OANDA prices metals off the **interest-rate differential of the pair**
(XAU against USD) rather than index CFD terms, which is why the markup differs.
The error recorded in `journal/FINDINGS_GOLD_4H_CARRY.md` §9 was assuming the
index markup transferred *to* gold. It does not — but it transfers to
everything else measured here, including a commodity.

**Practical rule for this tree: 2.50% is the right default for index and
commodity CFDs; metals must be looked up.**

---

## 3. The SPX500 carry verdict used exactly the right rate

`PREREGISTRATION_SPX500_H4_CARRY.md` assumed DFF 3.88% + a 2.50% markup =
**6.38%** for longs. The card says **−6.38%**. Exact.

So `FINDINGS_SPX500_H4_CARRY.md` is a measurement at the true rate, not an
estimate. Its verdict — condition 3 fired, 2005-2008 earns +0.39%/yr against a
risk-free 3.78%, below cash — stands on measured inputs. The robustness check
added there (condition 3 fires at every markup including zero) was belt and
braces; it turns out not to have been needed.

The short credit is also confirmed at **1.38%**, exactly as modelled. That
matters less for SPX500 H4, where shorts were only 1.7-2.0% of exposure.

---

## 4. The benchmark follows the instrument's currency

UK100's implied benchmark is **3.73%**, not 3.88%. That is a GBP reference
(SONIA) against USD (SOFR/fed funds) for the US indices.

Any future carry work must take the benchmark from the **instrument's own
currency**, not a single USD series. `carry_cost.py` currently accepts one
`--benchmark` file, which is correct for one instrument at a time and wrong if
it is ever pointed at a mixed panel. Noted as a limitation rather than fixed,
because nothing has yet needed the panel case.

---

## 5. Brent is not an interest-rate product, and this is the finding that matters

Brent's implied "benchmark" of **−46.10%/yr** is not a rate. It is the
**futures curve**. Brent is in steep backwardation — spot above the forward —
so the financing line carries the roll: a **long earns +43.6%/yr** and a
**short pays 48.6%/yr**.

For scale: every measured effect in this programme is in basis points per trade
or fractions of an R. A ±45%/yr carry is two orders of magnitude larger than
anything in `PROGRAMME.md`.

### This is not free money, and the reason matters

Backwardation means the market expects spot to fall. A long earning +43.6%/yr
in carry is being compensated for an expected spot decline of about the same
size. Whether the two cancel depends on **how OANDA constructs the Brent price
series** — if the CFD tracks the front futures contract and the financing line
*is* the roll adjustment, it is approximately a wash by construction, and the
carry is the mechanism that keeps a rolling series continuous rather than an
edge.

> **Update 2026-10-11:** construction measured in `FINDINGS_BRENT_SERIES.md`.
> `BCO_USD` is a continuous, spot-like series and does not roll in price; the
> roll is carried in financing. It is **not** "a wash by construction" for a
> price-only backtest: the financing term is simply missing from one.

### What it means for this tree

**`BCO_USD` is in the 21-CFD panel** (`fetch_oanda.py` line 83), with h1, h4 and
m15 files on disk, alongside copper (`XCU_USD`), natural gas, wheat, corn and
sugar — all futures-curve products with the same structure.

**No conclusion in the programme is overturned**, because all twelve
directional families failed and an unpriced carry only makes a failing strategy
fail harder. The exposure is to the **data**, not the verdicts:

- A backtest on OANDA commodity *price* data that ignores financing is not
  measuring a tradeable return. At ±45%/yr the omission is larger than any
  signal tested.
- The direction of the error is opposite for longs and shorts, so a
  long/short strategy on Brent would be mis-stated in both legs at once —
  and nothing in the panel work distinguished them.
- This is standing rule 5's territory one level out: not "check the data
  vintage" but **check what the broker's price series actually represents**.
  The two bugs that rule exists for (21:00 UTC daily rolls, the resampled_h4
  grid) were both found by asking what the broker's clock does. This asks what
  the broker's *contract* does.

### What should happen before any commodity result is quoted

1. Establish whether OANDA's commodity CFD price series is front-futures
   (rolled) or synthetic spot, and whether the roll appears as a price
   discontinuity, as a financing adjustment, or both.
2. If the roll is in the financing line and not the price, then **every
   commodity backtest in the panel is missing a term larger than its signal**,
   and any that produced a near-miss should be re-read as uninformative rather
   than negative.
3. Separately: a carry of this size is worth understanding on its own terms.
   `PROGRAMME.md` §3 concluded that every measured premium "died on access —
   the hedge, the venue or the liquidity was not there". Backwardation carry is
   a textbook premium and it is quoted, accessible, on the account. Whether it
   is *net* of the expected spot path is exactly the question §3 asks of every
   premium, and it has not been asked here. **That would need its own
   pre-registration, written before anything is run**, and the prior should be
   that it is a wash by construction.

---

## 6. Summary of what changed

| claim | status |
|---|---|
| SPX500 carry verdict (below cash, condition 3) | **validated on measured rates** |
| gold carry +0.0172R/trade | measured; see `journal/FINDINGS_GOLD_4H_CARRY.md` §0 |
| 2.50% markup as a default | **confirmed** for indices and commodities; wrong for metals |
| USD benchmark for all instruments | **wrong** — follows instrument currency |
| commodity backtests in the 21-CFD panel | **unverified**, pending §5 |

*Not financial advice. Measurement, not recommendation.*
