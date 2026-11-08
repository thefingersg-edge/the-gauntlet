# PREREGISTRATION v51: break of structure (BOS) and change of character (CHoCH), with a swing-width robustness gate

Frozen 2026-10-01, before any return following a BOS or CHoCH has been computed. The budget (scripts/budget_v51_53.py, log data/budget_v51_53.log) used prices only to *locate* events and to compute squared 16-bar returns. The harness (scripts/structure_v51.py) must pin this file and scripts/struct15.py (sha a162ce2a0eb39525ce7e2fb96ecf8f33aa5509a218eb6d424d18b268fbc7f6ef).

I am not a financial adviser. This is a measurement, not a recommendation.

## Question
- Smart-money-concept traders read market structure: a **BOS** (price closes beyond the last swing in the direction of the trend, meaning continuation) and a **CHoCH** (the first close beyond the last swing *against* the trend, meaning a possible reversal).
- Every swing-pivot pattern tested so far (pineport ZOO, REVERSALS, ADAPTIVE B; fastbot v20) failed because it depended on the pivot window: change it by one bar and 40–49% of detections vanish.
- **So the gate is built around that failure. A signal only counts if it works at every swing width from 2 to 5.**

## Data
- 15m mid bars from bid/ask: SPX500, NAS100 and XAUUSD (data/v24), and UK100 (built from data/v38 5m on the UTC 15m grid). All loaded via struct15.load15.
- Common end date: **2026-09-25**. Starts are 2005 (2006-03 for gold).

## Definitions (all in struct15.py, frozen by the sha above)
- **Swing high at bar i (width k):** high[i] > the highs of the k bars before, and ≥ the highs of the k bars after. Swing lows mirror this. A swing is only **known at bar i+k**.
- **Structure state:**
  - The last confirmed swing high and swing low are tracked.
  - A close above the unbroken last swing high is an up-break; a close below the unbroken last swing low is a down-break. Each level breaks at most once.
  - The first break only sets the state. After that, a break in the direction of the state is a **BOS**, and a break against it is a **CHoCH**. The state then flips.
- **Trade:** enter at the open of bar j+1 in the break's direction, and exit at the close of bar j+16 (4 hours).
  - **Cost:** one full quoted spread at the entry bar's open.
  - **Gaps:** a trade is dropped if its holding window spans more than 8 calendar hours (weekend or closure).
- Overlapping trades are allowed. SEs are clustered by the UTC date of entry.
- **Eras:** 2005–12, 2013–19, 2020–26.

## Gates (two signal types, CHoCH and BOS, so t ≥ 2.24). Each type passes only if ALL four hold.
- **G1, robust across swing widths:** pooled over the four instruments, the mean **net** P&L per trade is > 0 with t ≥ 2.24, **for every k in {2, 3, 4, 5}**.
- **G2, not just drift:**
  - **Excess** = the signed 16-bar return minus direction × (the instrument's mean 16-bar return over that calendar year).
  - The mean gross excess must be > 0 for every k.
- **G3, eras:** at k = 3, the mean net is > 0 in each era.
- **G4, breadth:** at k = 3, the mean net is > 0 in at least 3 of the 4 instruments.

## Reported (not gated)
- 1h bars, built by resampling the 15m.
- Exit at the next opposite structure event instead of 4h.
- "Confirmed CHoCH": a CHoCH followed by a BOS in the same direction.
- Longs and shorts separately; by hour of day.
- A random-entry control: same count, direction and holding period, at random bars.

## Budget (from budget_v51_53.py; no outcomes)
| Instrument | 4h RMS | Median spread | CHoCH count, k=2 → k=5 |
|---|---|---|---|
| SPX500 | 48 bp | 1.05 bp | 23,590 → 12,526 |
| NAS100 | 56 bp | 1.08 bp | 24,507 → 12,975 |
| UK100 | 54 bp | 1.67 bp | 17,340 → 8,886 |
| XAUUSD | 46 bp | 2.40 bp | 23,420 → 12,074 |

BOS counts are similar.
- The naive MDE per trade is 0.9–1.8 bp per instrument. Allowing for overlap and day clustering, the pooled MDE is **about 1–2 bp**. That is the size of the spread, so the test can see an edge that would pay for itself.
- **Prediction, written now:** FAIL. G1 fails on at least one width, because swing-based signals have been width-fragile everywhere else in this programme.

## Blind spots
- Practitioners draw structure by eye, and often on a higher timeframe. One causal, mechanical definition cannot capture every discretionary reading. It does capture the part that can be automated.
- The 4h exit is fixed. Exits were shown not to rescue entries (result_v2), so exit shapes are reported, not gated.

## One run.
