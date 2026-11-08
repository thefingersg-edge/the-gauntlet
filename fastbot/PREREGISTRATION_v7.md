# PREREGISTRATION v7 — is the collateral buffer real?

```
WRITTEN:  2026-08-19, BEFORE any Kraken margin term has been read
STATUS:   FROZEN. Phase 0 carries the entire test -- see section 2.
WHY:      REGIME.md ranked capital efficiency second of what remains and
          named cross-margining. RESULT_KRAKENBASIS recorded that Gate D's
          collateral assumption was the whole rejection and that I chose it.
```

---

## 1. This is a question of fact, not of returns

`RESULT_KRAKENBASIS` measured a real premium: **+4.15 points over the
contemporaneous T-bill**, across 18 quarterly cycles, 2021-08 to 2026-06.
That measurement is not in question here and **is not being re-run.**

What is in question is one input. `PREREGISTRATION_v4` §8 specified a **USD**
collateral buffer, sized to survive the worst observed intra-cycle rally of
73.5%. That buffer multiplied committed capital by 1.73× and turned +3.75
points of excess into +0.53. It was the entire rejection.

And §5 of the result recorded the doubt at the time:

> If the short future is instead collateralised in BTC — which is what the
> inverse `FI_` contracts are for — then a BTC rally raises the
> collateral's value at the same rate as the futures loss, and the buffer
> requirement largely disappears.

**Whether Kraken accepts BTC as collateral against a short BTC future, and
at what haircut, is a contract term.** It is either true or it is not, and
it can be read from the venue. Establishing it is fact-checking a decisive
input, not re-specifying a gate.

## 2. The contamination, stated plainly

I already know the conditional answer. `RESULT_KRAKENBASIS` §2 records that
**without the buffer, both Gate A and Gate B pass.** So if Phase 0 finds
BTC collateral works, Phase 1 is arithmetic with a known outcome.

**That means Phase 0 is the whole test**, and it is being conducted by
someone who knows which answer revives the candidate. The guard is that
§4 below states, *before any Kraken document is read*, exactly what
evidence settles it each way. If the findings do not match one of those
descriptions, the answer is "undetermined" and the v4 rejection stands.

I am not entitled to a favourable reading of an ambiguous margin schedule.

## 3. The two mechanisms, and why they differ

**Inverse contracts (`FI_`).** An inverse future is denominated in USD and
settles in BTC, so a short position's P&L in BTC is
`N × (1/F_exit − 1/F_entry)`. As the price rises without limit that loss
converges to `N/F_entry` BTC — **the loss is bounded at the initial BTC
notional.** Hold that much BTC and the position cannot be liquidated by an
upward move, however violent. It is self-collateralising by construction.

**Linear contracts (`FF_`) with BTC posted as collateral.** The loss is
unbounded in USD, but the collateral's USD value rises with the price at
the same rate. The hedge is approximate rather than exact, and the gap is
the **haircut** applied to BTC collateral plus the maintenance margin.

These are not the same thing, and **the sample contains both**: of the 18
usable contracts, 6 are `FI_` (2021-08 to 2023-06) and 12 are `FF_`
(2023-09 onward). Kraken migrated. If the inverse contracts are delisted,
the bounded-loss structure is a historical fact about part of the sample
and not something available to trade today — which would be decisive on its
own.

## 4. Phase 0 — what settles it, declared before looking

Read from Kraken's public API and contract specifications. **No return
data is touched.**

**PROCEED to Phase 1 only if all of:**

| condition | threshold |
|---|---|
| BTC accepted as futures collateral | required |
| haircut on BTC collateral | **≤ 30%** |
| spot and futures in one margin pool, or BTC transferable into the futures wallet as collateral | required |
| a dated BTC contract currently listed | required |

**CONFIRM the v4 rejection if any of:**

- BTC is not accepted as collateral against a short BTC future
- the haircut exceeds 30%, so a rally still forces USD top-ups
- the two legs sit in pools that cannot offset, with no transfer route
- only inverse contracts had this property and they are delisted

**UNDETERMINED — and the v4 rejection stands — if** the published terms do
not clearly place the venue in one of those two sets. Ambiguity is not a
pass.

The 30% haircut threshold is a judgement fixed now. Its basis: above 30%,
a repeat of the observed 73.5% rally still leaves a USD shortfall large
enough that the position's capital requirement is dominated by the buffer
rather than the notional, which is the condition v4 rejected on.

## 5. Phase 1 — arithmetic only

If Phase 0 proceeds:

- the **per-cycle returns from v4 are reused unchanged.** No new
  measurement, no new sample, no new window.
- the buffer is recomputed as **haircut + maintenance margin**, from the
  figures Phase 0 read — not set to zero. A haircut is not nothing.
- **Gates A, B and C are applied exactly as frozen in v4 §8.** Not
  re-specified, not re-thresholded.

## 6. Kill conditions

- **Phase 0 confirms or is undetermined** → stop. The v4 rejection stands
  and is now confirmed rather than assumed.
- **No re-measuring returns.** If Phase 1's arithmetic is close to the bar,
  that is the answer; the sample does not get extended to break a tie.
- **No instrument shopping.** BTC only, Kraken only. If some other venue
  offers better collateral terms, that is a different pre-registration with
  its own prior and its own counterparty question.
- **A pass is not a green light.** `PREREGISTRATION_v4` §12 already fixed
  what a pass means: *"a counterparty-risk result, and that is a question
  about a venue, not about a premium."* Exchange failure remains priced
  only as the 2-point judgement in v4 §2 and remains unmeasurable from
  price data.

## 7. My prediction

**I predict Phase 0 proceeds, and that the honest verdict then becomes a
counterparty-risk result rather than a strategy.**

Reasoning: multi-collateral margining with BTC is standard at crypto
derivatives venues and haircuts are typically 10–25%, inside the threshold.
If so the buffer falls from 73.5% to roughly 20–35%, committed capital from
1.73× to about 1.25×, and the excess from +0.53 to somewhere near +2.5 to
+3.0 points — over the 2.0 bar but not by much, on a position whose
remaining risk is that the venue holds both legs.

**I have now been right on the verdict and wrong on the mechanism four
times running.** This prediction names the mechanism — the haircut, not the
acceptance — so that failure mode stays visible.

## 8. What this cannot see

- **Liquidation mechanics under stress.** A haircut in a schedule is not a
  haircut applied during a 40% hour.
- **Whether the venue raises haircuts mid-episode**, which is the crypto
  analogue of the SPAN margin problem that killed the VIX carry.
- **Counterparty risk**, unchanged and unpriced.
- **Whether the inverse structure's bounded loss survived Kraken's own
  auto-deleveraging**, which is a term that bites exactly when it matters.

## 9. Self-test requirements

1. the inverse-contract P&L must be shown **bounded** — a short's BTC loss
   must converge to the initial notional as price → ∞, and a planted linear
   contract must show unbounded loss over the same path
2. the buffer arithmetic must reproduce v4's 1.73× from a 73.5% rally and
   a 100% haircut, as a regression check on the original
3. a haircut of exactly 30% must sit on the correct side of Gate 0, and
   30.1% on the other
4. an ambiguous or missing margin term must return **undetermined**, not a
   default
5. Phase 1 must be shown to use v4's stored returns and not recompute them

## 10. Scoreboard entering this test

**Twenty-three investigations. Nineteen rejections, one
measured-but-unreachable premium, one headline that dissolved on
decomposition, one real premium whose edge vanished at daily resolution,
one real premium consumed by its own margin requirement.**

This asks whether the last of those was consumed by a real requirement or
by one I invented.
