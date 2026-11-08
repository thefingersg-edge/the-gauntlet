# The Kraken dated basis — a real premium, rejected by the collateral it needs

```
RUN:      2026-08-19
METHOD:   kraken_basis.py v1.1, PREREGISTRATION_v4, ONE RUN
DATA:     18 quarterly BTC cycles, 2021-08-27 -> 2026-06-26, both legs
          from Kraken; DGS3MO for the contemporaneous benchmark
VERDICT:  REJECTED. Gate A +0.47 pts against a 2.0 bar; Gate B negative in
          two of three eras. The premium is real and large. The capital
          that has to sit idle beside it is what kills it.
```

---

## 1. The result

```
[FAIL] Gate A  net excess over T-bill >= 2.0 pts    +0.47 pts
[FAIL] Gate B  positive in EVERY era                -0.6  +2.5  -0.2
[PASS] Gate C  >= 12 cycles, >= 3 per era           18 cycles, 6/6/6
```

Per §9 this stops. No basis-threshold filter, no reversed trade, no ETH
rescue.

## 2. Gate D is the whole rejection, and that is worth saying precisely

```
time-weighted, annualised, over 4.8 years

  realised basis on notional        +7.98%
  contemporaneous T-bill            +3.84%
  gross spread over the bill        +4.15 pts

  excess WITHOUT the Gate D buffer  +3.75 pts   -> Gate A PASS
  excess WITH the 1.73x buffer      +0.53 pts   -> Gate A FAIL
  the buffer alone costs             3.22 pts
```

The worst observed intra-cycle rally was **73.5%**, so surviving a repeat
requires holding 73.5% of notional as collateral doing nothing. Capital
committed becomes 1.73× the traded notional and every return is divided by
1.73.

**Without that buffer both Gate A and Gate B would have passed.** Shifting
each era up by ~3.2 points turns −0.6 / +2.5 / −0.2 into +2.6 / +5.7 /
+3.0. The entire verdict rests on one pre-registered gate.

That gate was written before any data was pulled, and §8 called it *"the
crypto analogue of the VIX margin spiral, and the gate I expect to do the
real damage."* It did exactly that. This is the second consecutive
investigation — after `RESULT_VIXCARRY.md` — where a genuine premium was
defeated not by its size but by the capital required to hold it through
its own worst case.

## 3. My prediction: right answer, wrong reason

§3 recorded, before running:

> **I predict this fails Gate A.** … the dated basis and the perpetual
> funding rate are linked by arbitrage … silver15 already measured funding
> at +1.46% against T-bills at 3.66%, a *negative* excess.

Gate A did fail. **But the reasoning was wrong.** I predicted a *small*
basis. The measured basis is **+7.98% against a 3.84% bill — a +4.15 point
spread**, far larger than the funding-linked argument implied. The premium
is much healthier than I expected; it is the margin structure that fails.

On Gate B I said it would fail *"specifically in 2022"*. Half right. The
first era, which spans 2022 into mid-2023, is negative at −0.6. But the
**third era, 2025-2026, is also negative at −0.2**, which I did not
predict. Two of three, not one.

Correct verdict, wrong mechanism, and a prediction that was only half
right on the detail. Recorded here the same way the VIX direction error
was.

## 4. The shape of the failure, which is economically coherent

| period | quoted basis | T-bill | excess |
|---|---|---|---|
| 2021-08 → 2022-09 | 0.8 – 7.9% | 0.15 – 2.7% | positive |
| **2022-12 → 2023-06** | **−3.7 – +5.5%** | **4.2 – 5.3%** | **−6.7 to −3.0** |
| 2024 (ETF bull run) | 8.8 – 29.0% | 4.6 – 5.5% | +0.2 to +10.5 |
| 2025-08 → 2026-06 | 3.8 – 6.9% | 3.7 – 4.4% | −3.6 to +1.7 |

**Eight of eighteen cycles lost to Treasury bills. Six had a raw basis
below the bill**, twice going into outright backwardation.

The mechanism is legible. The dated basis is a price for leveraged long
demand, so it collapses precisely when crypto falls — and rates rose
through exactly that stretch. The premium and its benchmark moved in
opposite directions at the worst possible time. That is not bad luck; it
is a correlation the trade carries structurally.

Note also what 2024 shows: a 29% annualised basis existed and was real. A
sample stopping in mid-2024 would have produced a spectacular result. That
is the `RESULT_VRP.md` +1.34 problem in a different asset, and the reason
§4 refused to run without 2022.

## 5. What this cannot see, and one limitation that is mine

**Exchange counterparty risk is unpriced.** It was folded into the 2-point
threshold as a judgement, as §2 said. Nothing measured here bears on it.

**Convergence is not clean.** The largest index-to-future gap at expiry is
1.41% of spot, and the realised column sits **+0.37 points above the
quoted** basis on average. Small, but it flatters the strategy, and it may
be an artifact of the last daily candle not being the settlement print
rather than a real effect. It does not change the verdict — removing it
makes Gate A worse.

**The collateral assumption is the biggest lever, and I fixed it in
advance.** §8 specified a **USD** buffer. If the short future is instead
collateralised in BTC — which is what the inverse `FI_` contracts are for
— then a BTC rally raises the collateral's value at the same rate as the
futures loss, and the buffer requirement largely disappears. On that
structure this would have passed.

I am not re-running it that way. Changing the collateral assumption after
seeing that it is the binding constraint is re-specification, and §9
forbids exactly this. It would need its own pre-registration — and that
one would be **much weaker evidence**, because it would be written by
someone who already knows the answer. Any honest version of it has to
carry that caveat on its face.

## 6. Verdict

**A real, large, economically coherent premium that this account cannot
harvest as specified.**

+4.15 points over the bill is not nothing. It is a genuine payment for
providing leverage to a market that persistently wants it. What defeats it
is the same thing that defeated the VIX carry: the position must survive
its own worst case, and the capital that guarantees that survival earns
nothing while it waits.

## 7. Scoreboard

**Twenty-one investigations. Seventeen rejections, one
measured-but-unreachable premium, one headline that dissolved on
decomposition, one real premium whose edge vanished at daily resolution,
and one real premium consumed by its own margin requirement.**

Two candidates have now survived every test of whether the premium exists
and failed on the capital needed to hold it. That is a pattern rather than
a coincidence, and it is the most useful thing this project has learned:
**the search kept finding real premia and losing them at the point where
survivability is priced.**

The only thing that has beaten equity beta here is still equity beta.
