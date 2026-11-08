# Track A, day two — a false PROCEED, and a spread that moved 158×

```
SPEC:     PREREGISTRATION_v8, Track A (observation only) -- registry link added 2026-09-26
RUN:      2026-08-25, second observation (first was 2026-08-19)
METHOD:   kraken_collateral.py v1.2 + basis_monitor.py v1.2 --survey/--out
VERDICT:  the PROCEED printed today is VOID for two independent reasons,
          one of which is my fault. Gate 0 returns to UNDETERMINED, and
          v4's rejection stands. Fixes shipped as v1.3 of both files.
```

---

## 1. The haircut was mine, not Kraken's

The run that printed PROCEED was this:

```
BTC COLLATERAL HAIRCUT
    20.0%   source: Kraken Futures collateral schedule, <url>
```

**`0.20` was a number I invented, in an example command, to show the
argument syntax.** The source field is the literal placeholder `<url>`
from that same example. No figure was looked up. Nothing was sourced.

That is my error and it is a bad one. This project's entire discipline is
about not letting invented numbers into gates, and I handed over a
runnable command with an invented number already in it. The correct
example was `--btc-haircut <the figure you found>`, which fails loudly,
rather than `--btc-haircut 0.20`, which runs and returns a pass.

## 2. The gate should have caught it anyway, and did not

`gate_0()` took `known=bool(source)`. Any non-empty string satisfied
that — including the string `"...schedule, <url>"`.

**A gate that can be passed by pasting the example is not a gate.** It is
the same failure class as the hold limit read off the display grid in
`vix_carry_budget.py`: passing for a reason unrelated to the thing being
tested.

v1.3 adds `source_is_real()` — rejects placeholder markers, requires ≥15
characters and a checkable locator (a URL, or a date the document pins
to). The self-test plants **the exact string that passed today** and
asserts it fails:

```
[PASS] the placeholder that actually passed v1.2 is REJECTED
       'Kraken Futures collateral schedule, <url>' -> contains the placeholder '<'
[PASS] and gate_0 returns UNDETERMINED when handed it
```

## 3. The second defect: this file still read `tradeable` as availability

`RESULT_TRACKA` named this error six days ago. The file kept making it.

Today `kraken_collateral.py` printed *"3 inverse dated contract(s) are
listed and tradeable"* — and minutes later, from the same venue, in the
same directory, `basis_monitor.py` printed *"inverse: 0 of 3 quoted"*.

**Two scripts disagreeing about the same three contracts.** The cause was
two separate definitions of liveness: `basis_monitor` had a real one,
`kraken_collateral` had none and inferred it from a flag that does not
mean it.

v1.3 fixes the structure, not just the symptom:

- `is_dead()` now lives in `kraken_collateral.py` as the single canonical
  definition; `basis_monitor` imports it rather than keeping a copy
- `kraken_collateral` fetches the tickers endpoint and reads liveness
  from it
- `gate_0_inverse()`'s first argument is renamed `dated_inverse_quoted`
  and means it
- the self-test asserts the two files agree on a battery of tickers —
  and plants a divergent predicate to prove the agreement check fires

## 4. What the corrected run says

Re-running the identical command through v1.3:

```
6 visible, 6 flagged tradeable, 3 actually quoted, 0 of those inverse
  FI_XBTUSD_260828  inverse  DEAD    FF_XBTUSD_260828  linear  quoted
  FI_XBTUSD_260925  inverse  DEAD    FF_XBTUSD_260925  linear  quoted
  FI_XBTUSD_261225  inverse  DEAD    FF_XBTUSD_261225  linear  quoted

SOURCE REJECTED -- contains the placeholder '<'.

GATE 0
  inverse branch: UNDETERMINED  -- no inverse contract is quoted
  linear branch:  UNDETERMINED  -- needs a SOURCED haircut
  UNDETERMINED
```

Both branches fail, for different reasons, and neither failure is new
information — v7 said the linear branch was UNDETERMINED and Track A day
one said the inverse branch was dead. **What is new is that the tooling
now says so instead of printing a pass.**

## 5. The day-two market observation, which is the substantive finding

This is where I over-read a single data point last time.

`RESULT_TRACKA` §4 concluded: *"on the two contracts the frozen rule
actually trades, the spread is about one basis point"* and that v4's cost
model was **conservative**. That was one observation. Here is the second:

| contract | spread 19 Aug | spread 25 Aug | change |
|---|---|---|---|
| Aug (front) | 0.88 bp | 0.75 bp | flat |
| **Sep (second)** | **1.00 bp** | **158.38 bp** | **158×** |
| Dec (far) | 44.92 bp | 38.26 bp | flat |

The September book widened by a factor of 158 in six days. Decomposing
today's quotes against an index of 79,889:

```
              price      vs index    annualised
bid          78,923       -1.210%      -13.4%
mid          79,553       -0.421%       -4.9%
ask          80,183       +0.368%       +4.4%
```

**The spread straddles the sign of the basis.** The ask side is priced
sanely — +4.4% annualised, in line with December's +4.3%. The bid sits
1.21% *below* spot.

And the frozen rule is a **seller**. A seller takes the bid. Entered at
today's quote by crossing, the trade designed to harvest a positive basis
would instead lock in **−13.4% annualised** — the premium's own sign,
reversed, purely by spread.

I do not know whether that bid is a real resting book or a momentarily
one-sided snapshot; one observation cannot tell you. **That is the point,
and it is precisely the caution I failed to attach to the 1bp figure six
days ago.** Two observations of the same contract differ by 158×, so
neither is "the" spread, and v4's cost assumption is not established as
conservative. It is unmeasured: the half-spread a seller crosses on the
September contract was **0.5 bp on 19 August and 79 bp on 25 August**, and
the bid itself sat 121 bp below the index.

## 6. The finding that runs the other way

The front contract, 3 days from expiry:

```
index 79,889.33    mid 79,909    basis +0.025%    annualised +3.0%
```

Six days ago that same contract sat **2.75% above the index** with 9 days
to run. It has converged to within 2.5 basis points of spot, and its open
interest has drained from 0.31 to 0.18 as it runs off.

**Convergence is the one assumption underpinning every cash-and-carry
figure in v4, and it is now observed live rather than assumed.** That is
a genuine tick in the candidate's favour, and it cost nothing.

## 7. Where this leaves it

Nothing in today's run changes the premium. `RESULT_KRAKENBASIS` measured
+4.15 points over the T-bill across 18 cycles and that stands untouched;
December is quoted at +4.3% annualised right now.

What has changed is that the candidate now has **three** open questions
rather than one:

1. the BTC collateral haircut on the linear contract — still unsourced,
   threshold still frozen at ≤ 0.30
2. the inverse structure that removed the buffer — confirmed dead twice
3. **new:** entry cost on the contract the rule would trade, which two
   observations put anywhere between 0.5 and 121 bp

Item 3 is the one Track A was built to find, arriving on day six of a
protocol that has still committed no capital.

## 8. A proposed amendment, not taken unilaterally

`basis_monitor.py --out` follows the front **inverse** contract, per v8
§4. That contract does not trade, so the log records an empty row every
day forever.

v1.3 adds `--all-dated`, which logs every dated contract instead. It is
**off by default**, because v8 §6 says the protocol is not modified
mid-cycle and a frozen rule that quietly changes is worth nothing. What
would make it defensible: logging *everything* removes a selection rather
than adding one — there is no choice left to steer.

Your call. Left alone, Track A keeps recording nothing.

## 9. Scoreboard

**Twenty-four investigations. Twenty rejections, one
measured-but-unreachable premium, one headline that dissolved on
decomposition, one real premium whose edge vanished at daily resolution,
and one real premium that is undetermined on capital, unavailable in the
structure that fixed it, and now unmeasured on entry cost.**

Unchanged: the only thing that has beaten equity beta here is equity beta.

## 10. What to run

```bash
python3 kraken_collateral.py --self-test      # 56 checks, all pass
python3 basis_monitor.py --self-test
python3 kraken_collateral.py                  # no haircut: UNDETERMINED, honestly
```

And when a **real** figure with a **real** source exists:

```bash
python3 kraken_collateral.py \
  --btc-haircut 0.XX \
  --source "https://support.kraken.com/... retrieved 2026-08-25"
```

≤ 0.30 proceeds, > 0.30 confirms the rejection, no sourced figure stays
undetermined. The threshold has not moved and does not move now.
