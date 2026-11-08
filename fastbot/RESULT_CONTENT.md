# RESULT — v29 Part 2: does it matter what the release said?

```
RUN:      2026-09-25   SPEC: PREREGISTRATION_v29 section 4 (sha256 checked)
CODE:     release_content.py 1.0 (fetched on Dave's machine, FRED real-time)
          premarket_content.py 1.0 (measured)
SAMPLE:   2,634 trades, six instruments, on 457 CPI and payrolls dates
VERDICT:  G3 FAILS. MIXED - CLEAN = +0.02 bp at t +0.01. My registered
          prediction (a weak pass) was wrong. Digestion, as defined,
          joins the dead.
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.** Inputs and caveats: PROVENANCE.md.

---

## 1. The data

1,190 requests, 0 failed. 38 series-requests failed the vintage check,
which dropped **1 payrolls release (0.3%) and 18 CPI releases (5.9%)**.
The CPI drops are not random: **every one is a February release**, where
that day's vintage still ends at December. So the sample has no January
CPI prints. Declared, not repaired -- repairing it would mean choosing a
second rule after seeing the first one fail. One date carried both
releases and was dropped.

## 2. The gate

```
fade at 09:45        MIXED           CLEAN          difference      t
both releases    n 1180  +3.23   n 1454  +3.22        +0.02     +0.01  FAIL
payrolls         n  552  +3.96   n  576  +1.08        +2.88     +0.86
CPI              n  628  +2.59   n  878  +4.62        -2.02     -0.75
```

**Whether the headline and the internals agreed makes no difference to
the bounce** -- +3.23 against +3.22. The two releases split in opposite
directions and neither is significant; pooled, they cancel to nothing.

## 3. Reported, gating nothing -- and one thing that did not survive a check

v29 registered the fade against the SIZE of the naive surprise as a
reported quantity:

```
payrolls   slope t +3.67 as run.  Excluding 2020-21:  t -0.37
CPI        slope t +2.26 as run.  Excluding 2020-21:  t +2.15
           small-surprise half +0.96 bp, big-surprise half +7.08 bp
```

**The payrolls slope is entirely the pandemic.** Surprises of up to 20
million jobs in 2020 put all the leverage in a handful of prints; take
2020-21 out and the slope is gone. It should not be quoted.

**The CPI slope survives that check**, and it is the first thing in the
mechanism hunt that points somewhere: the bounce looks bigger when the
CPI print is further from its recent norm, even though (v28) it is not
bigger when the PRICE moves further. The largest surprises are real
prints -- Nov 2008 at -1.7% m/m, mid-2022 at +1.0 to +1.3% -- mostly
energy-driven. **It is ungated, on a sample that has now been looked at,
from a naive surprise proxy, with January missing.** It is a candidate
for a registration of its own, not a finding.

## 4. Predictions, scored

```
G3 passes, weakly                          +0.02 at t +0.01    WRONG
dropped by the vintage check under 5%      CPI 5.9%            WRONG
```

## 5. The mechanism hunt, closed out

```
overshoot-and-correct       dead   no scaling with the move (v22, v28)
noise-plus-selection        dead   held-out decade reproduced it (v23)
the 09:30 open corrects     dead   gold and EUR_USD show it (v24)
risk premium (accruing)     dead   gone overnight (v27)
absorption vs information   dead   v28
participation               dead   v29 Part 1
headline vs internals       dead   v29 Part 2
```

Seven explanations, seven dead. The effect -- a roughly fixed bounce of
+3 to +4 bp on release mornings, nineteen times the control -- is still
there and still unexplained. The only thread left pointing anywhere is
the size of the CPI surprise, and it has not yet been tested honestly.

---

**Investigation forty-five, Part 2.**
