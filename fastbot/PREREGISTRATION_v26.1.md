# PREREGISTRATION v26.1 — amendment: the longer holds Dave asked about

```
WRITTEN:  2026-09-21, after v26 was frozen and BEFORE it was run. No
          path of the release fade has been computed on real data --
          premarket_paths.py has run its self-test and nothing else.
AMENDS:   PREREGISTRATION_v26. Adds one gated question and one
          descriptive table. Changes nothing already registered: not the
          sample, not Q1-Q3, not E1-E4, not Gate 0, not any threshold.
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.**

---

## 1. What was asked

Dave, while v26 was being written:

> *"some of them could have been much bigger if they had held on for
> longer, so the trigger is looking reasonable but the time might be too
> short"*

> *"can we add to the test looking at longer periods to see after x
> amount of hours had the price continued in the predicted direction"*

## 2. Where the idea came from, stated because it matters

It came from looking at trades on the TradingView chart -- SPX500USD,
variant B, mostly 2025-2026. The trades that went on to be bigger are
the ones that get noticed; that is v26 Part A's problem, found by eye.
**That SPX slice has already been seen for this question.** The pooled
test below is dominated by five other instruments and twenty years, and
it is ALSO reported without SPX500_USD -- declared here, not chosen
after.

## 3. What is added

### 3a. Gated -- HX: does the fade keep going after the time exit?

On every v26 trade that also has the 12:45, 13:45, 14:45 and 15:45 ET bar
opens on both sides:

```
HX   mean of m(15:45) - m(09:45), all trades, winners and losers
     PASS: mean > 0 at clustered t >= 2.0, the same sign in both halves
```

15:45 ET is the last bar open of the US cash session, before the 17:00
ET rollover, so no horizon here pays financing -- Dave's standing
requirement is profit after costs AND financing. **One look, so 2.0.**
Standard errors clustered by release date, halves split at the median
release date, exactly as v26 section 5.

### 3b. Descriptive -- the shape of the average trade, hour by hour

At the 09:45 (rule A), 10:45, 11:45, 12:45, 13:45, 14:45 and 15:45 opens:

```
mean gross (mid)   share in profit   SD   mean net (bid/ask)   net Sharpe/yr
```

and the move after 09:45 for the trades winning and the trades losing
at 09:45. **No verdict, and no horizon is selected from this table.**

## 4. How to read it, fixed now

A longer hold earns a registration of its own **only if HX passes AND
the net Sharpe at the longer horizon is above rule A's.** A longer hold
that adds profit and risk in equal measure is variant D again -- +5.58
bp for 58.9 bp of swing, against +3.93 for 31.4, the same Sharpe -- and
is not an improvement, however big the best trades get.

## 5. Prediction

**HX lands within 2 bp of zero and fails.** The share of trades in
profit stays between 50% and 55% at every horizon. The SD grows with the
hold faster than the mean, so the net Sharpe is highest at or near
09:45.

## 6. Why this amendment is admissible

It is written before any v26 number exists. It adds and it removes or
loosens nothing. The gate it adds is the question Dave asked, at the
threshold this project uses for a single look, and a pass would earn
only a separate registration and a forward test -- never a change to
rule A or to v25.

---

**Investigation forty-two, amended before it ran.**
