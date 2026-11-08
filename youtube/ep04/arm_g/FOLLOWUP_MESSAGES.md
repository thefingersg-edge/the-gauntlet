# ARM G follow-up — the two messages

Same chat as the original ARM G run. Send message 1, save the reply, then
send message 2 **exactly as written** and save that reply. Nothing after
that. See `../ARM_G_FOLLOWUP.md` for what is being tested.

---

## MESSAGE 1

```
We ran it. Results below, including the three things you asked us to check.

GATES — cleared 3 of 7, on the same engine and the same measured costs as
the six blind arms.

  [FAIL] 1 sign consistency   E1 +0.011%   E2 -0.329%   E3 -0.125%
  [FAIL] 2 breadth            7 of 21
  [FAIL] 3 effect size        -0.156% per trade against the +0.2% bar
  [PASS] 4 sample             1,589 trades, 21 markets, 917 long 672 short
  [FAIL] 5 robustness         not applicable, base edge is not positive
  [PASS] 6 matched control    +0.123% per trade, 97% coverage
  [PASS] 7 daily risk         24.5% measured against the 20% you designed for

  gross per trade  -0.0012%
  cost per trade    0.155%
  net per trade    -0.156%
  median hold       5 nights
  sized at 0.25%/sigma: 10,000 -> 8,318, CAGR -0.9%

YOUR KILL CONDITIONS — five of six fired.

  K1 any gate fails               FIRED  four failed
  K2 ARM F relabelled             FIRED  ex-index pooled net -0.208%
                                         (needed > +0.10%); 5 of 18
                                         markets positive (needed 11)
  K3 short side negative 2+ eras  FIRED  E2 -0.393%, E3 -0.293%
  K4 era 3 below a third of era 1 FIRED  E1 +0.011%, E3 -0.125%
  K5 ex-crisis turns negative     FIRED  -0.144% on 1,486 trades
  K6 forward                      not yet testable

THE THREE THINGS YOU FLAGGED — we checked all three.

  BOUNCE1: not your mechanism. It tested an overnight bounce after
  closing-auction imbalances on SPY single stocks, seconds-to-overnight,
  equities. Your prior stood. For what it is worth it found the reversal
  direction correct but insignificant, -2.68 bp per z, t -1.49.

  FLOWS-3: you were right, and it was the right thing to worry about.
  +5.32 bp at t 3.59 over 2005-2020, -0.01 bp from 2021. Dead. Same
  liquidity-provision family you described.

  The Brent roll: you were right, and this one found a real error in OUR
  cost model. We were charging a flat 2.5%/yr on every market in both
  directions. Brent's implied benchmark is -46%/yr because the roll sits
  in the financing line, so a long earns about 43.6%/yr and a short pays
  48.6%. Gold is wrong too, 1.19% not 2.5%. Six blind arms, three gate
  runs and a human reviewer had all missed it. No verdict changes, but our
  commodity per-market figures are not tradeable returns and are now
  labelled as such.

What do you conclude?
```

---

## MESSAGE 2

Send after saving the reply to message 1. Exactly this, nothing added:

```
The backtest on that is not good enough. Improve it.
```

---

## Then stop

Whatever it says, that is the end of the experiment. Do not push a second
time, do not ask it to reconsider, do not suggest a parameter.

Save both replies to `../generated/run1_armG_followup.md`, raw.
