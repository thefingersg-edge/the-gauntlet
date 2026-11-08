# MIGRATED — the premium is real, historical, and no longer reachable

```
SPEC:     none -- a declared MEASUREMENT (fastbot Rule 1), not a backtest; thresholds frozen in the script before any volume was read. Follows the PREREGISTRATION_v8 Track A basis question. Registry note added 2026-09-26
RUN:      2026-08-29
METHOD:   liquidity_shift.py v1.0, thresholds frozen before any volume read
VERDICT:  MIGRATED. The quarterly dated contract lost 93.2% of its volume
          while the perpetual on the same venue, in the same units, over
          the same window, fell 17.0% and sits squarely inside its own
          historical range.
```

**I am not a financial adviser. This is a measurement.**

---

## 1. The comparison

| series | baseline/month | last 6 months | fall |
|---|---|---|---|
| FF quarterly (BTC) | 1,303 | **89** | **93.2%** |
| PF_XBTUSD perpetual (BTC) | 179,938 | 149,285 | 17.0% |

Same venue, same quote convention, same API, same window. The perpetual's
2026 range is 97,921–196,971 BTC/month against a 2024–25 range of
78,012–407,991 — **inside it, not below it.**

The quarterly is now **5.9 basis points** of the perpetual's monthly
volume. In the baseline it was 72.

## 2. The collapse, month by month

```
2025-06   1,200.5 BTC  ########################
2025-07     803.8 BTC  ################
2025-08     657.2 BTC  #############
2025-09     369.2 BTC  #######
2025-10     706.9 BTC  ##############
2025-11     562.3 BTC  ###########
2025-12     247.1 BTC  ####
2026-01     191.8 BTC  ###
2026-02     216.0 BTC  ####
2026-03      40.7 BTC  #
2026-04       7.0 BTC  #
2026-05       4.0 BTC  #
2026-06      71.7 BTC  #
```

**April 2026: 7.02 BTC traded across the entire month — about $560,000.
May: 4.04 BTC, about $320,000.** That is not a thin market. It is one or
two trades a week.

The perpetual over those same months: 123,260 and 115,235 BTC. Untouched.

## 3. What this settles

`RESULT_EXECCOST` left one question: did liquidity leave the quarterly
contract, or leave Kraken? **It left the contract.**

That closes the chain the last three results opened:

- the premium is real — +4.15 points over the T-bill across 18 cycles
- the capital objection was mine, not Kraken's — the haircut is 1%
- every pre-registered gate passes on 2023–2025
- **and the instrument those gates describe has stopped trading**

## 4. This is the fourth death by availability

Not by the premium being absent. By there being no one on the other side.

```
VRP                  premium real, the hedge it needed did not exist
VIX term structure   premium real, the edge vanished at daily resolution
Kraken inverse       structure perfect, zero bid, zero OI, zero volume
Kraken quarterly     every gate passes, 4 BTC a month
```

Four candidates with a documented premium behind them, and each one failed
on something other than whether the premium was there. **That is now a
pattern rather than a run of bad luck**, and it is the most useful thing
twenty-six investigations have produced.

The market does not leave paid risk lying around in instruments that are
easy to reach. Where the premium survived measurement, the access did not.

## 5. What is NOT concluded

**Kraken has announced nothing.** Every 2026 delisting on their derivatives
suspensions page is a perpetual altcoin contract — `PF_LRCUSD`,
`PF_MOVEUSD`, `PF_STORJUSD`. Nothing touching `FF_XBTUSD_*`. So this is a
market that left, not a product being withdrawn, and it could in principle
come back.

I have not established *where* it went beyond "not to Kraken's perpetual,
which was already large". CME dated futures, offshore quarterlies and the
ETF complex are all candidates and none was tested. That was outside what
this probe was built to answer.

**The inverse perpetual `PI_XBTUSD` also declined heavily** — 1.12bn USD in
March 2023 to 48m in August 2025. But it is USD-quoted and the script
correctly refused to let it carry the verdict against a BTC-quoted chain.
It is consistent with the whole inverse product line dying, which matches
Track A finding the inverse dated contracts unquoted, but it is not
evidence I am entitled to use here.

## 6. The one live thread

**The perpetual is liquid and the basis persists.** Track A has the
September quarterly at +3.6% annualised and December at +3.9–4.4% right
now, on a book nobody trades.

A cash-and-carry on a perpetual is a **funding-rate trade**, not a
convergence trade. It has no fixed maturity, no settlement to converge to,
and its carry is a variable funding payment that can flip sign. **None of
the 18 cycles in `RESULT_KRAKENBASIS` measured that.** It is a different
trade with a different risk and its own pre-registration, and the honest
statement is that this project has not tested it at all.

Whether it is worth testing is a real question, not a formality. Funding
rates on major perpetuals are the most watched number in crypto, which is
a reason to expect the premium to be smaller — the opposite of the dated
basis, which was reachable precisely because it was awkward.

## 7. Scoreboard

**Twenty-six investigations. Twenty rejections, two
measured-but-unreachable premia, one headline that dissolved on
decomposition, one real premium whose edge vanished at daily resolution,
and one that cleared every pre-registered gate on a contract that now
trades four bitcoin a month.**

The only thing that has beaten equity beta here is still equity beta.

## 8. What this cost to find out

No capital. Track A ran eleven days and never committed a position; the
retrospective work was four probes and an afternoon.

**The forward protocol found the inverse contract was dead on day one, and
the retrospective one found the linear contract was dying within a week of
being asked.** Both arrived before any money moved, which is the entire
argument for building the measurement before the position.
