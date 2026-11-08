# Track A, day one — the PROCEED is withdrawn

```
RUN:      2026-08-19, first observation
METHOD:   basis_monitor.py v1.2 --survey, PREREGISTRATION_v8 Track A.
          No capital. One API call.
VERDICT:  PREREGISTRATION_v7's PROCEED is WITHDRAWN. All three inverse
          contracts are listed and none is traded. The instrument the
          capital argument depends on has no market.
```

---

## 1. What the survey found

```
symbol              type        bid      ask       OI   vol24h   state
FI_XBTUSD_260828    inverse       -        -        0        0   DEAD
FI_XBTUSD_260925    inverse       -        -        0        0   DEAD
FI_XBTUSD_261225    inverse       -        -        0        0   DEAD
FF_XBTUSD_260828    linear    79,842   79,849   0.3145   5.8962   quoted
FF_XBTUSD_260925    linear    80,122   80,130  17.7596  17.5807   quoted
FF_XBTUSD_261225    linear    80,845   81,209  11.5704  10.0841   quoted
```

Every inverse contract: no bid, no ask, zero open interest, zero volume,
and `markPrice` exactly equal to `indexPrice` — which is what a venue
publishes when nothing is pricing an instrument. Every linear contract:
quoted, with real interest and real turnover.

## 2. The error, named precisely

`PREREGISTRATION_v7` read `tradeable: true` from the instruments endpoint
and treated it as availability.

**`tradeable` means the venue permits orders. It does not mean anyone is
sending them.** That distinction is the entire distance between a contract
existing and a contract you can get into, and I did not check it. The
inverse contracts are a paper listing — a legacy product Kraken has not
delisted but which the market left when it migrated to linear, somewhere
around the middle of v4's own sample.

So v7's chain was: inverse contracts are listed → margined in BTC → no
haircut → buffer zero → both gates pass. **The first link is false in the
sense that matters.** The arithmetic in v7 §2 is still correct; it
describes an instrument with no counterparty.

## 3. What this does and does not overturn

**Withdrawn:** v7's PROCEED, and the +3.64-point Gate A result that
depended on a zero buffer.

**Not overturned:** the premium itself. `RESULT_KRAKENBASIS` measured
+4.15 points of excess over the T-bill across 18 cycles, and nothing here
touches that. The basis is visibly present right now — the front linear
contract sits **2.75% above the index**, 3.11% on the September.

**Reverted to:** the linear contract, for which v7's own Gate 0 returned
**UNDETERMINED** because Kraken publishes BTC collateral haircuts in
support documentation rather than the API. Per v7 §4, *ambiguity is not a
pass*, and v4's rejection stands until that figure is supplied with a
source.

This is not a dead end. It is a redirect to the question that was always
the real one, and the threshold for it was fixed in advance: **a haircut
of 30% or less proceeds.** One sourced number decides it.

## 4. The other day-one finding, which runs the other way

Track A also measured what v4 §7 could only assume:

| contract | spread | half-spread crossed |
|---|---|---|
| front (Aug) | **0.9 bp** | 0.4 bp |
| second (Sep) | **1.0 bp** | 0.5 bp |
| far (Dec) | 44.9 bp | 22.5 bp |

v4 assumed 0.05% taker plus one tick per leg. **On the two contracts the
frozen rule actually trades, the spread is about one basis point** — the
cost model was conservative, not optimistic. The taker fee is separate and
unchanged.

The December contract at 45bp shows how fast depth thins past the front
two. The rule never holds it, but it is worth knowing that the liquidity
is concentrated in exactly two contracts.

## 5. What Track A was for, and what it cost

`PREREGISTRATION_v8` §2 listed five things no quantity of history can
settle and said one cycle answers them. **The first one — whether the
printed price is obtainable — was answered in a single API call, before
any capital was committed, and it withdrew a pass.**

That is the entire argument for forward evidence, demonstrated at zero
cost on day one. A backtest cannot tell you an instrument has no
counterparty, because a backtest only sees the prices of trades that
happened, in years when they did.

## 6. Verdict

**The premium is real, the capital argument that revived it describes an
instrument with no market, and the tradeable version returns to an open
question with a fixed threshold and a known answer format.**

`RESULT_KRAKENBASIS_v7` closed by saying the rejection it overturned was
mine rather than the market's. The correction to that is smaller and
sharper: **the rejection was right, my reason for it was wrong, and my
reason for overturning it was wrong too.** The buffer I imposed does not
apply to the inverse contract; the inverse contract does not trade; the
linear contract's buffer is unmeasured.

## 7. Scoreboard

**Twenty-four investigations. Twenty rejections, one
measured-but-unreachable premium, one headline that dissolved on
decomposition, one real premium whose edge vanished at daily resolution,
and one real premium whose capital requirement remains genuinely
undetermined.**

The only thing that has beaten equity beta here is still equity beta.

## 8. The one thing that would settle it

Kraken Futures publishes collateral haircuts for multi-collateral wallets.
With that figure and its source:

```
python kraken_collateral.py --btc-haircut <h> --source "<where>"
```

- **h ≤ 0.30** → PROCEED, and Phase 1 re-runs on the same returns
- **h > 0.30** → v4's rejection is CONFIRMED rather than assumed
- **no sourced figure** → UNDETERMINED, and it stays rejected

The threshold was frozen before any of this was read, and it does not move
now.
