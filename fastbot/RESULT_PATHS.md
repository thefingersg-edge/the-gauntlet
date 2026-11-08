# RESULT — does the path tell you when to get out?

```
RUN:      2026-09-25
SPEC:     PREREGISTRATION_v26, amended by v26.1. Both frozen before the
          run and checked by sha256 at run time.
CODE:     premarket_paths.py 1.1
SAMPLE:   six instruments, 3,157 fade trades on 544 CPI and payrolls
          dates, 2005-01-07 .. 2026-09-11. The forward test's sample
          (2026-09-18 on) was excluded and is still unseen.
VERDICT:  Every gate fails. No exit rule tested is justified. The one
          thing that pointed Dave's way -- the drift does not stop at
          09:45 -- missed its bar at t = 1.76.
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.**

---

## 1. Gate 0 -- the pipeline reproduces v24 exactly

```
NAS100_USD  n 525 (525)  +6.9739 (+6.97)      US30_USD  n 529 (529)  +1.1670 (+1.17)
EUR_USD     n 540 (540)  +1.5441 (+1.54)      XAU_USD   n 501 (501)  +4.2936 (+4.29)
DE30_EUR    n 531 (531)  +2.5174 (+2.52)
max |this file - v24's trade()| over every trade:  0.0e+00
```

Same events, same numbers, to the last bit. Three trades were also
re-derived from the raw bid and ask files by separate code: 2005 SPX
(zero spread era, net == gross), 2026 SPX and 2026 gold, all exact.

## 2. Stage 1 -- the path IS predictable, and not in a direction that helps

```
Q1  BANKING   winners at 09:15 add another  +2.03 bp by 09:45   t +1.93  [FAIL]
Q2  STOPS     losers  at 09:15 recover      +4.00 bp by 09:45   t +3.28  [FAIL]
Q3  TRAILING  winners at 09:45 add          +2.75 bp by 10:45   t +1.32  [FAIL]
```

**Q2 is the most significant number in the run, and it points the wrong
way for stops.** A trade that is underwater at 09:15 goes on to recover
twice what a winning trade adds. A stop is a machine for closing exactly
those trades at exactly the wrong moment. The gate asked for a negative
number and got +4.00 at t = +3.28.

Banking fails for the mirror reason: winners at 09:15 keep going, so
banking hands back +2 bp.

Per instrument, Q2 is positive on all six (SPX +6.27, NAS +8.64, DE30
+4.90, XAU +1.59, US30 +1.85, EUR +0.82). Q1 is positive on five of six.

> **CAVEAT added 2026-09-25, from a review of this document.** Q1 and Q2
> condition on the mark at 09:15 and then measure from that same quote.
> A 09:15 mid that is noisily low makes a trade look like a loser AND
> inflates its apparent recovery. Re-measured with a fifteen-minute gap
> -- condition at 09:15, measure 09:30 to 09:45 -- **Q2 is +2.95 bp at
> t +2.74 rather than +4.02**, and Q1 is +1.88 at t +1.97 rather than
> +2.03. Both verdicts stand, because both had to be NEGATIVE to pass
> and both are positive either way. But "recover twice what the winners
> add" above should be read as about half again, not twice.

## 3. Part A -- the hindsight money, and the price of it

```
rule A winners  n 1,642  closed +25.97 bp net, best during the hold +39.24
                         LEFT ON THE TABLE  +13.27 bp  (median +9.02)
rule A losers   n 1,515  73% were up at least +3 bp net at some point
rule A winners           51% were down at least 10 bp at some point
```

There is money left on the table -- 13 bp per winner. The same table
says why you cannot have it. **73% of the losers were up +3 bp at some
point**, so a +3 lock-in is not free money lying about; it is a rule
that also caps every winner. **Half the winners were 10 bp underwater on
the way**, so a 10 bp stop kills half of them.

## 4. Part B -- the four rules, run on every trade

```
rule                    net bp    vs A      t   5th pct    worst  changed
rule A (time exit)       +2.07                    -52.9   -160.8
E1 bank +10              +0.86   -1.21  -2.20     -49.3   -160.8     40%  FAIL
E2 lock +3 after +10     +1.77   -0.30  -1.28     -51.3   -160.8      5%  FAIL
E3 extend winners        +3.56   +1.50  +1.32     -61.4   -337.4     54%  FAIL
E4 trail winners         +2.70   +0.63  +0.88     -54.9   -160.8     54%  FAIL
```

**E1 is the only rule whose effect on the average is significant, and it
is negative**: banking a +10 bp line costs 1.21 bp a trade, on 40% of
trades, and it is negative on five of the six instruments.

**E3 and E4 make more money and fail anyway.** They fail the other two
conditions -- E3's worst trade is -337 bp against rule A's -161, and its
5th percentile is worse too. That is what "without risking anything"
was three conditions for: a rule that makes more by holding longer is
not free, it is leveraged in time.

## 5. The amendment -- Dave's longer holds

```
HX   m(15:45) - m(09:45), all trades     +4.32 bp   t +1.76   [FAIL]
     halves  +2.05 / +6.48
     without SPX500_USD (declared)       +4.12 bp   t +1.81

at the open of   gross   in profit    SD     net   net Sharpe/yr
09:45            +3.60      54%     35.6   +2.19      0.30   <- rule A
10:45            +5.05      53%     59.3   +3.65      0.30
11:45            +4.88      52%     66.3   +3.46      0.26
12:45            +5.15      52%     70.7   +3.73      0.26
13:45            +6.91      52%     75.3   +5.46      0.35
14:45            +9.10      52%     81.2   +7.64      0.46
15:45            +7.92      52%     87.6   +6.21      0.35

after 09:45        10:45   11:45   12:45   13:45   14:45   15:45
winning at 09:45   +2.66   +1.61   +2.46   +4.66   +7.81   +7.44
losing  at 09:45   -0.00   +0.89   +0.52   +1.70   +2.62   +0.48
```

Ungated arithmetic on the registered split: winners at 09:45 go on to
make **+7.43 bp more by 15:45, t +2.29** (n 1,696); losers make +0.48 at
t +0.14. The share of trades in profit barely moves -- 54% at 09:45,
52% at 15:45 -- so the afternoon is not turning losers into winners. It
is making the winners bigger.

**This failed, and it is the first thing in this line that has pointed
Dave's way.** Positive in both halves, slightly stronger without the
instrument he looked at, and the drift is still there hours after the
release. It is also exactly the shape that has fooled this project
before: the 30-minute signal bar was +2.69 bp at t +1.63 on the sample
that chose it, and -0.09 bp on 2,626 fresh events. t = 1.76 against a
bar of 2.0 set beforehand is a fail, and **this sample is now used up
for this question.**

One more reason not to act on it: by 15:45 the trade has been open the
whole session. That is no longer a one-hour event trade; it overlaps
whatever the market does on the day, and nothing here separates the two.

## 6. Predictions, scored

```
Q1 positive, +2 to +4 bp                   +2.03           RIGHT
Q2 positive, near Q1                       +4.00, twice Q1  right on sign
Q3 within 1 bp of zero                     +2.75           WRONG
no Part B rule passes                      none did        RIGHT
Part A: bp left on the table, many losers  +13.27 and 73%  RIGHT
HX within 2 bp of zero, and fails          failed at +4.32 HALF WRONG
```

The half I got wrong is the half Dave asked about.

## 7. What this settles, and what it does not

**Settled: exits.** Banking, locking, stops and trailing have now been
measured on 3,157 trades and 23 years, against gates set in advance.
None of them earns its keep, and the two that made more money did it by
taking more risk. **The time exit stays**, and "could we have made more
without risking anything" has its answer: in hindsight yes, 13 bp a
winner; by rule, no.

**Not settled: whether the drift continues into the afternoon.** That
needs a sample this one has not seen. Three exist, in the order they
should be used:

1. **A control on quiet days.** The same rule on the 08:30 bar of
   non-release mornings. If the afternoon drift is there too, this is an
   intraday pattern wearing the release's name, and the release has
   nothing to do with it. That test comes first because it can only
   subtract.
2. **Weekly claims.** 903 events at the same 08:30 slot, dropped from
   the strategy in v22 (+0.59 bp gross, eaten by the spread) and never
   used for a horizon question. An independent sample, available today.
3. **The forward test.** v25 section 4 records the entry and the exit.
   Recording the later marks as well costs nothing, changes no rule and
   decides no gate -- apparatus, not measurement -- and it would answer
   this out of sample as the events arrive.

---

**Investigation forty-two.** The first run in this line where the thing
that failed its gate was the thing Dave predicted.

---

**Inputs as run, and the standing caveats: PROVENANCE.md**
