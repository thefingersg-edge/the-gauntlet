# PREREGISTRATION v26 — does the path tell you when to get out?

```
WRITTEN:  2026-09-21, before any path measurement of the release fade
          exists. No checkpoint split, excursion or exit rule has been
          computed on real data for this trade.
STATUS:   FROZEN
SUBJECT:  exits for rule A -- banking, locking, stops, trailing
CODE:     premarket_paths.py 1.0, written against this document
CHANGES:  nothing in PREREGISTRATION_v25. The forward test runs rule A
          as registered, whatever this finds.
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.**

---

## 1. Why

Dave's question, in his words: *"if it's a winning trade, did we make
the most of it -- could we have made more without risking anything?"*

On 2026-09-21 three exit ideas were put on SIMULATED paths: a tight
trailing stop, trailing the winners after 09:45, and banking or locking a
profit line during the hold. All three lowered the average. That is not
a finding about the market. On a random path no exit rule changes the
expected profit -- it only trades win rate against win size -- so a
simulation of a random path could only ever say that.

**An exit rule can add money only if the real path is predictable**, and
the direction of the predictability decides which kind:

```
early winners give back          -> banking or locking helps
early losers keep losing         -> a stop helps
winners keep going after 09:45   -> trailing helps
```

None of that has been measured on this trade. This registration
measures it, then answers Dave's question in money.

## 2. The trade -- rule A, exactly as v25 section 2

```
signal   the 08:30-08:45 ET bar, mid open against mid close
         FADE: close > open -> short, close < open -> long, equal -> none
entry    the open of the 08:45 bar
exit     the open of the 09:45 bar (the time exit)
events   CPI and payrolls at 08:30 ET. Claims excluded, as in v25.
```

## 3. Data, fixed now

```
instruments  SPX500_USD NAS100_USD US30_USD DE30_EUR EUR_USD XAU_USD
bars         M15 bid and ask in data/v24, verified clean by verify_pull.py
events       events_v2.csv
window       the start of each file (2005, gold 2006) to 2026-09-17
EXCLUDED     every event from 2026-09-18 on -- the forward test's sample
             stays unseen
usable       every 15-minute bar from 08:30 to 11:45 ET present on both
             sides, and a signal bar that is not a doji
floor        an instrument with fewer than 150 usable events is reported
             and not pooled
```

**Marks.** m(t) is the trade's P&L in bp at the MID OPEN of the bar
starting at t, measured from the entry mid, signed in the trade's
direction. Checkpoints are bar opens and nothing else.

**No stop or target is simulated inside a bar.** exit_shape.py wrote the
reason down after silver15's only false PASS: an OHLC bar cannot say
whether a stop or a target inside it was hit first, and assuming the
favourable order manufactures edge. Every decision here is taken at a bar
open, where the price is known, and filled at that same open's bid or
ask.

## 4. Gate 0 -- positive control. Failing it voids the run.

On v24's own inclusion rule, rule A's gross per instrument must
reproduce RESULT_INSTRUMENTS section 1 -- same n, same mean to the
rounding shown (0.005 bp), and this file's m(09:45) must equal v24's
trade() to 1e-9 bp on every trade:

```
NAS100_USD 525 +6.97   US30_USD 529 +1.17   EUR_USD 540 +1.54
XAU_USD    501 +4.29   DE30_EUR 531 +2.52
```

A new file that reads the same bars and cannot reproduce a published
number is a bug in the new file, not a finding about the market.

## 5. Stage 1 -- is the path predictable? Three gated questions

```
Q1  BANKING    trades in profit at 09:15:  mean of m(09:45) - m(09:15)
               banking can only help if this is NEGATIVE
Q2  STOPS      trades losing at 09:15:     mean of m(09:45) - m(09:15)
               a stop can only help if this is NEGATIVE
Q3  TRAILING   trades in profit at 09:45:  mean of m(10:45) - m(09:45)
               trailing can only help if this is POSITIVE and larger
               than the ~1 bp a stop costs to fill
```

A question PASSES only if both hold:

- Q1, Q2: mean < 0 at t <= -2.4.  Q3: mean >= +1.0 bp at t >= +2.4.
- The same sign in both halves of the sample, split at the median
  release date.

**t uses standard errors clustered by release date.** Six instruments
react to the same release on the same morning; RESULT_INSTRUMENTS
section 4 says they are closer to one observation per date than six.
**2.4** is Bonferroni for three two-sided looks at 5%.

A mark of exactly zero at the checkpoint is neither winner nor loser
and is left out of that question.

**Reported, not gated:** winners minus losers at each checkpoint, losers
after 09:45, and each question per instrument, per release and per half.

## 6. Stage 2 -- Dave's rule, in money

**Part A -- money left on the table. DESCRIPTIVE ONLY.** For trades that
rule A closed as winners: the best executable price reached during the
hold -- the bid high for a long, the ask low for a short, 08:45 to the
09:45 open -- against where they closed. For losers: the share that were
up at least +3 bp net at some point. For winners: the share that were
down at least 10 bp at some point.

**This always finds money left on the table, because it is computed
after the fact.** It is reported so the size is known. It cannot pass or
fail anything.

**Part B -- the question asked honestly.** Four exit rules, fixed now,
decided only at bar opens, each run on EVERY trade and compared with
rule A trade by trade, at executable bid and ask:

```
E1  BANK     at the 09:00, 09:15 or 09:30 open, the first time m >= +10 bp:
             exit there. Otherwise the 09:45 time exit.
E2  LOCK     the first time m >= +10 bp at the 09:00, 09:15 or 09:30 open,
             a floor of +3 bp is set; exit at the first LATER open before
             09:45 where m < +3 bp. Otherwise the 09:45 time exit.
E3  EXTEND   if m(09:45) > 0, hold to the 10:45 open instead.
E4  TRAIL    if m(09:45) > 0, hold; at each later open from 10:00, exit if
             m is below max(m(09:45), best mark at the previous opens
             from 09:45 - 10 bp); otherwise out at the 11:45 open.
```

The numbers come from the conversation, not from any data: +10 bp is
the round trip plus a margin worth banking, +3 bp covers the cost and
returns something, 10 bp is the trail used in the simulations. **No
other values are tried in this run.**

**"Without risking anything" is three conditions, all required:**

```
1  MORE MONEY        mean (rule - A), net bp per trade, > 0 at
                     clustered t >= 2.5
2  NO FATTER TAIL    the rule's 5th-percentile trade is no worse than A's
3  NO WORSE WORST    the rule's worst trade is no worse than A's
```

**2.5** is Bonferroni for four looks.

## 7. Predictions, registered before the run

- **Q1 positive**, around +2 to +4 bp: winners at 09:15 still collect
  the reversion. Banking cannot help.
- **Q2 positive**, near Q1: losers at 09:15 recover about as much as
  winners do. Stops cannot help.
- **Q3 within 1 bp of zero.** Trailing cannot help.
- **No Part B rule passes.** E1 and E2 lower the average; E3 and E4 land
  within 1 bp of rule A.
- **Part A shows several bp left on the table in the winners**, and a
  large share of the losers were once up more than the cost.

My registered predictions in this line have been wrong about half the
time, three of them on the sign.

## 8. Kill conditions, and what each outcome means

- **Nothing here changes the forward test.** v25 section 7 forbids
  switching rules mid-test. A pass is a candidate for its own
  registration, never an edit to v25.
- **No parameter search.** The checkpoints, +10, +3 and 10 bp are frozen
  above. A second set of values chosen after these results is the
  fishing this project exists to avoid.
- **The forward sample stays unseen.** Nothing from 2026-09-18 on.
- **If a question passes**, the intra-bar version of that exit needs
  1-minute bid and ask and its own registration. Decisions every 15
  minutes are a coarse version of a real stop; this run asks whether the
  idea has a basis at all.
- **If everything fails**, exits are settled for this trade. The time
  exit stays, and Dave's question has its answer: there was more in the
  winners only in hindsight, and no rule could have taken it without
  paying for it on other trades.

---

**Investigation forty-two.**
