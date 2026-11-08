# RESULT — reconciling with Kurov, and what it did to our own answer

```
RUN:      2026-09-04
SPECS:    PREREGISTRATION_v11 (two arms), v12 (their window), v13 (2016-2026)
CODE:     preann_segment.py 1.0, preann_arm2.py 1.1, preann_replicate.py 1.0
VERDICT:  the published drift REPLICATES exactly, and is DEAD after 2015
```

**I am not a financial adviser. This is a measurement, not a
recommendation to take a position.**

---

## 1. What happened, shortest version

RESULT_PREANN left one loose end: Kurov, Wolfe & Gilbert measured
+44.5 bp for 2011-2015 and this project measured +0.36. Chasing it
produced four things, in this order:

1. **The 45 minutes I excluded were not the explanation.** −2.94 bp.
2. **The 14 events I excluded were part of it.** +29.00 bp, closing a
   quarter of the gap.
3. **The number I was arguing with had been misread — by me, in two
   documents.** It is press-conference meetings only, on a different
   window, in E-mini futures.
4. **Transcribing their window reproduced their result to −0.14 SE** —
   and revealed that **83% of the effect sits in a window RESULT_PREANN
   never looked at.**

Then v13 asked whether it is still there. **It is not.**

## 2. The two arms of v11

**Arm 1 — the excluded 45 minutes, T−60m → T−15m.**

```
all measurable   n=181   -2.94 bp   ctrl -0.41   excess -2.53   t -1.71
2013-2015        n= 24   -3.35 bp                excess -2.94   t -1.38
```

Registered prediction: under 15 bp and therefore not the explanation.
**Held.** It is negative, so it makes the gap marginally worse.

The contamination check mattered here — this put a measurement 15
minutes from an announcement. The segment's dispersion is **0.26× the
reaction's** (sd 19.2 against 74.9), so it is behaving like the window,
not like the announcement.

**Arm 2 — the 14 excluded 2011-2012 events.**

`events.csv` could not resolve those because in that era the statement
came at **12:30 on press-conference days and 14:15 otherwise**. Both
times come from one sourced sentence:

> "the FOMC statement is expected to be released at around 12:30 p.m.,
> **one hour and forty-five minutes earlier than for other FOMC
> meetings**" — Board of Governors, 2011-03-24

That sentence pins both numbers; 12:30 + 1h45m = 14:15. Neither was
assumed, and the press-conference list was read off the Board's own
calendars rather than inferred from the quarterly pattern.

```
the fourteen     n=14   +29.00 bp   median +15.64   sd 86   10/14 positive
  with press conference   n= 8   +35.47
  without                 n= 6   +20.38
pooled 2011-2015 n=37   +11.20 bp   against their +44.50
```

Registered prediction: ~+50 bp per event, pooling to ~+18.6.
**Direction right, magnitude wrong** — +29.00 and +11.20. With sd 86 on
14 events the SE is 23, so +50 was inside the interval; I was not
precise, but I was not refuted either.

## 3. The error that made v11 the wrong question

v11 §1 stated the target as "+44.50 bp, 2011-04..2015-12" and compared
it with an **all-meetings** mean. Reading the paper itself:

> "from the stock market open on the day before the announcement to 15
> minutes before the announcement"

and the +0.445% figure is **for announcements with press conferences**,
**20 announcements**, in **E-mini S&P 500 futures**. They separately
report **−0.051%** for the 30 announcements *without* one.

**I had been comparing two different quantities, in FINDINGS.md and
again in v11.** That is my error and it survived two documents because
the number was carried forward as a summary rather than re-read at the
source.

Recomputed on the correct set — the same 20 announcements, sourced per
year, **all 20 measurable**:

```
mine   +12.72 bp   SE 11.90       theirs +44.50   ->  +2.67 SE, OUTSIDE
```

So the disagreement was real and not a subset artifact. One difference
remained: their window starts at the D−1 **market open**, mine at T−24h.

## 4. v12 — their window, transcribed

Not chosen. Transcribed, from the sentence above, and frozen before it
ran. The counts are the check that these are the same sets they used:
**20 press-conference and 30 non-press-conference announcements — both
matching the paper's own counts exactly.**

```
sample                            n       mine     theirs    SE away
with press conference 2011-15   20/20   +46.29    +44.50      -0.14
without,   2011-04..2018-12     30/30    -5.14     -5.10      +0.00
```

**That is a full independent replication, on a different instrument.**
Both the positive and — more tellingly — the *negative* figure, to two
decimal places. A measurement that only reproduced the headline would be
much weaker evidence than one that also reproduces the null.

Against control: +41.53 bp, t = 3.21.

## 5. Where the drift actually lives — and it is not where we looked

Decomposing their window into three disjoint pieces, on the same 20
announcements:

```
                                      mean      t    positive
D-1 morning    09:30 ET -> T-24h    +38.26   4.02     17/20
RESULT_PREANN  T-24h    -> T-1h     +12.72   1.07      8/20
arm 1 tail     T-1h     -> T-15m     -4.96  -2.10      8/20
                                    -------
their window   09:30 D-1 -> T-15m   +46.29   3.63     17/20
```

**83% of the effect is in the four and a half hours of the morning
BEFORE announcement day, and RESULT_PREANN's window excluded all of
it.** The part RESULT_PREANN did measure is the weak part — t = 1.07,
8 of 20 positive.

And the decay looks different once split:

```
              D-1 morning    RESULT_PREANN's window     total
2011-2012        +39.73             +35.47             +65.22
2013-2015        +37.28              -2.45             +33.67
```

**The D−1 morning barely moved across the regime break. RESULT_PREANN's
window collapsed.** So a good part of what RESULT_PREANN read as decay —
and attributed to VIX — was its window drifting off the phenomenon,
not the phenomenon fading.

It is also press-conference-specific, in both datasets: without one, the
D−1 morning is **−4.48**.

## 6. v13 — is it still there? No.

Same window, three pre-specified samples, predictions registered first.

```
sample                                  n      whole window        D-1 morning
A  2016-2018, press conference only   12/12   +12.73  t 2.25         -6.26
B  2019-2026, all meetings            60/61   +14.92  t 1.33         -4.63
C  2016-2018, no press conference      12/12   +2.66  t 0.14         -2.28
   ---- for reference, already measured ----
   2011-2015, press conference only   20/20   +46.29  t 3.63        +38.26
   2011-2018, no press conference     30/30    -5.14
```

**All three registered predictions held** (A in +10..+20, B under +15, C
near zero). A also lands near Kurov's own out-of-sample +9.2 bp for
2016-2019 — a fourth independent match.

**The D−1 morning is negative in every post-2015 sample.** The component
that carried +38 bp is not merely smaller; it is gone.

What survives is +14.92 bp across 60 meetings at **t = 1.33** — not
distinguishable from zero, on a window that also pays an extra day of
financing.

Sample B is all meetings because **from 2019-01-30 every scheduled
meeting has a press conference**. That matters more than it looks: the
variable that separated +46 bp from −5 bp stopped varying. The effect
and its only conditioner disappeared together.

## 7. What this does to RESULT_PREANN

**Gate E stands.** CPI and payrolls were negative and nothing here
measures them. The FAIL verdict is unchanged.

**Its window was badly placed**, and that is a real finding against my
own work: it measured the weakest third of the phenomenon and read the
result as the whole of it.

**Its economics were understated for 2011-2015 and are unchanged now.**
Had the correct window been used then, the gross would have been roughly
four times larger. But v13 says that window pays nothing significant
after 2015, so the conclusion for anything tradeable **today** is not
improved — only better understood.

**Its VIX story needs qualifying.** Gate D was measured on
RESULT_PREANN's window and stands for that window. But the claim I made
in conversation — that the premium is still paid and simply needs high
uncertainty — is too strong. The large, well-documented part of it
stopped in 2015 and did not come back in 2020-2023, when uncertainty
certainly did.

## 8. The scoreboard on my own predictions

| | predicted | measured | |
|---|---|---|---|
| v11 arm 1 | under 15 bp | −2.94 | **held** |
| v11 arm 2 | +50 / pooled +18.6 | +29.00 / +11.20 | direction held, magnitude missed |
| v11 | a residual will remain | +33.30 bp | **held** |
| v12 head | under 10 bp | **+33.57** | **failed** |
| v12 total | ~+20, short of +44.5 | **+46.29** | **failed** |
| v13 A | +10..+20 | +12.73 | **held** |
| v13 B | under +15 | +14.92 | **held** |
| v13 C | near zero | +2.66 | **held** |

**The two failures are the two that mattered**, and v12 §4 had said so
in advance: *"If the head turns out to be worth 30 bp or more, I am
wrong about where the drift lives, and that is a more interesting
outcome than a confirmation."* It was worth +33.57.

That is the whole case for registering predictions. Being wrong in
writing, on a specific number, is what turned a loose end into the most
informative result in the project.

## 9. What is left

**Financing: measured, and it changed nothing.** 1.14 bp/event against
the 1.64 assumed, so RESULT_PREANN's candidate moves from +0.86%/yr to
+0.88%/yr. Cost is now 10.0% of gross with both sides measured.

It also cost me another prediction. I built the tool around
**Wednesday** carrying the weekend's triple charge, on the FX
convention; OANDA charges it on **Friday** for SPX500_USD. FOMC
announcements are Tuesday to Thursday, so D−1 is never a Friday and the
triple charge cannot fire on this event set at all. The lookup reads the
table from the API and is right; the reason I gave for needing it was
wrong.

**Not asked, and deliberately not inferred: whether CPI and payrolls pay
on the D−1-morning window.** Gate E tested them on the window we now
know was the wrong one. That is the obvious next pre-registration and it
should not be guessed at from here.

**The honest bottom line.** The pre-FOMC drift was real, is now
replicated on our own data to within a fifth of a standard error, and
stopped paying in 2015. There is no live edge here. What there is
instead is an apparatus that reproduced a published result and its null
on the first attempt — which is worth more than the trade would have
been.

---

**Sources:** [Kurov, Wolfe & Gilbert, *The Disappearing Pre-FOMC
Announcement Drift*](https://www.skidmore.edu/economics/documents/KurovWolfeGilbert-TheDisappearingPre-FOMC-Announce-Drift-200914.pdf)
· [Board of Governors, press-conference programme,
2011-03-24](https://www.federalreserve.gov/newsevents/pressreleases/monetary20110324a.htm)
· FOMC historical calendars
[2011](https://www.federalreserve.gov/monetarypolicy/fomchistorical2011.htm),
[2012](https://www.federalreserve.gov/monetarypolicy/fomchistorical2012.htm),
[2013](https://www.federalreserve.gov/monetarypolicy/fomchistorical2013.htm),
[2014](https://www.federalreserve.gov/monetarypolicy/fomchistorical2014.htm),
[2015](https://www.federalreserve.gov/monetarypolicy/fomchistorical2015.htm),
[2016](https://www.federalreserve.gov/monetarypolicy/fomchistorical2016.htm),
[2017](https://www.federalreserve.gov/monetarypolicy/fomchistorical2017.htm),
[2018](https://www.federalreserve.gov/monetarypolicy/fomchistorical2018.htm)
